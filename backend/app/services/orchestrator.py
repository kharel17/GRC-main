"""
LangGraph Orchestrator — GRC Retrieval & Generation State Graph.

Nodes:
  normalize_query → dense_retrieve + sparse_retrieve → fuse → rerank
  → retrieval_gate (conditional) → generate → verify (conditional)
  → accept | needs_review (interrupt) | insufficient_evidence

Human-in-the-loop: langgraph.interrupt() fires at needs_review.
On resume, human_review_decision is stored and the result is accepted/rejected.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.config import settings
from app.services.retrieval_service import RankedChunk
from app.services.confidence_gate import ConfidenceDecision, evaluate_confidence

logger = logging.getLogger("grc.orchestrator")


# ── State Schema ──────────────────────────────────────────────────────────────

class GRCState(TypedDict):
    # Input
    query: str
    org_id: str
    document_ids: List[str]          # optional scope; empty = all docs for org
    collection: str

    # Retrieval
    dense_results: List[Dict[str, Any]]
    sparse_results: List[Dict[str, Any]]
    fused_results: List[Dict[str, Any]]
    reranked_results: List[Dict[str, Any]]

    # Gate decision
    confidence_decision: Optional[Dict[str, Any]]

    # Generation
    generation_result: Optional[Dict[str, Any]]
    verification_result: Optional[Dict[str, Any]]
    citation_score: float
    composite_score: float

    # Human-in-the-loop
    human_review_decision: Optional[str]   # "accept" | "reject"

    # Audit trace
    trace: List[Dict[str, Any]]

    # Final verdict
    verdict: Optional[Literal["accept", "needs_review", "insufficient_evidence"]]
    final_output: Optional[Dict[str, Any]]


def _trace(state: GRCState, node: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Append a trace entry and return a state patch."""
    entry = {
        "node": node,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
    }
    return {"trace": state.get("trace", []) + [entry]}


def _chunks_to_dicts(chunks: List[RankedChunk]) -> List[Dict[str, Any]]:
    from dataclasses import asdict
    return [asdict(c) for c in chunks]


# ── Node Implementations ──────────────────────────────────────────────────────

async def node_normalize_query(state: GRCState) -> Dict[str, Any]:
    """Cleans and trims the query text."""
    raw = (state.get("query") or "").strip()
    normalized = " ".join(raw.split())
    patch = _trace(state, "normalize_query", {"original": raw, "normalized": normalized})
    patch["query"] = normalized
    return patch


async def node_dense_retrieve(state: GRCState) -> Dict[str, Any]:
    """Retrieve top-K chunks by dense cosine similarity via Qdrant."""
    from app.services.ai_service import ai_service
    from app.services.vector_store import vector_store

    results: List[Dict] = []
    try:
        if ai_service.is_ready and vector_store.is_ready:
            query_emb = ai_service._embed_text(state["query"])
            hits = await vector_store.dense_search(
                query_vector=query_emb,
                collection_name=state.get("collection", settings.QDRANT_COLLECTION_DOC_CHUNKS),
                top_k=settings.RETRIEVAL_TOP_K_DENSE,
                org_id=state.get("org_id"),
            )
            results = hits
    except Exception as e:
        logger.warning(f"Orchestrator dense_retrieve failed: {e}")

    patch = _trace(state, "dense_retrieve", {"hits": len(results)})
    patch["dense_results"] = results
    return patch


async def node_sparse_retrieve(state: GRCState) -> Dict[str, Any]:
    """BM25 sparse retrieval over the dense candidate set."""
    from app.services.retrieval_service import retrieval_service, RankedChunk

    dense_dicts = state.get("dense_results", [])
    # Rebuild RankedChunk objects from dense dicts for BM25 scoring
    dense_chunks = []
    for d in dense_dicts:
        p = d.get("payload", d)  # handle both raw Qdrant hits and serialised chunks
        dense_chunks.append(RankedChunk(
            chunk_id=str(d.get("id", p.get("chunk_id", ""))),
            text=p.get("text", ""),
            document_id=str(p.get("document_id", "")),
            org_id=str(p.get("org_id", "")),
            page_number=int(p.get("page_number", 0)),
            section_heading=p.get("section_heading", ""),
            chunk_index=int(p.get("chunk_index", 0)),
            dense_score=float(d.get("score", p.get("dense_score", 0.0))),
        ))

    sparse_chunks = await retrieval_service.sparse_retrieve(
        query=state["query"],
        candidate_chunks=dense_chunks,
        top_k=settings.RETRIEVAL_TOP_K_SPARSE,
    )
    patch = _trace(state, "sparse_retrieve", {"hits": len(sparse_chunks)})
    patch["sparse_results"] = _chunks_to_dicts(sparse_chunks)
    return patch


def node_fuse(state: GRCState) -> Dict[str, Any]:
    """RRF fusion of dense and sparse result lists."""
    from app.services.retrieval_service import retrieval_service, RankedChunk

    def dicts_to_chunks(dicts: List[Dict]) -> List[RankedChunk]:
        chunks = []
        for d in dicts:
            p = d if "chunk_id" in d else d.get("payload", d)
            chunks.append(RankedChunk(
                chunk_id=str(d.get("chunk_id") or d.get("id", "")),
                text=p.get("text", ""),
                document_id=str(p.get("document_id", "")),
                org_id=str(p.get("org_id", "")),
                page_number=int(p.get("page_number", 0)),
                section_heading=p.get("section_heading", ""),
                chunk_index=int(p.get("chunk_index", 0)),
                dense_score=float(d.get("dense_score", d.get("score", 0.0))),
                sparse_score=float(d.get("sparse_score", 0.0)),
            ))
        return chunks

    dense_chunks = dicts_to_chunks(state.get("dense_results", []))
    sparse_chunks = dicts_to_chunks(state.get("sparse_results", []))
    fused = retrieval_service.rrf_fuse(dense_chunks, sparse_chunks)

    patch = _trace(state, "fuse", {"fused": len(fused)})
    patch["fused_results"] = _chunks_to_dicts(fused)
    return patch


def node_rerank(state: GRCState) -> Dict[str, Any]:
    """CrossEncoder reranking of fused candidate list."""
    from app.services.retrieval_service import retrieval_service, RankedChunk

    def from_dict(d: Dict) -> RankedChunk:
        return RankedChunk(
            chunk_id=str(d.get("chunk_id", "")),
            text=d.get("text", ""),
            document_id=str(d.get("document_id", "")),
            org_id=str(d.get("org_id", "")),
            page_number=int(d.get("page_number", 0)),
            section_heading=d.get("section_heading", ""),
            chunk_index=int(d.get("chunk_index", 0)),
            dense_score=float(d.get("dense_score", 0.0)),
            sparse_score=float(d.get("sparse_score", 0.0)),
            rrf_score=float(d.get("rrf_score", 0.0)),
        )

    fused_chunks = [from_dict(d) for d in state.get("fused_results", [])]
    reranked = retrieval_service.rerank(
        query=state["query"],
        candidates=fused_chunks,
        top_n=settings.RERANK_TOP_N,
    )
    patch = _trace(state, "rerank", {"reranked": len(reranked)})
    patch["reranked_results"] = _chunks_to_dicts(reranked)
    return patch


def node_retrieval_gate(state: GRCState) -> Dict[str, Any]:
    """Evaluate confidence and attach ConfidenceDecision to state."""
    from app.services.retrieval_service import RankedChunk

    def from_dict(d: Dict) -> RankedChunk:
        return RankedChunk(
            chunk_id=str(d.get("chunk_id", "")),
            text=d.get("text", ""),
            document_id=str(d.get("document_id", "")),
            org_id=str(d.get("org_id", "")),
            page_number=int(d.get("page_number", 0)),
            section_heading=d.get("section_heading", ""),
            chunk_index=int(d.get("chunk_index", 0)),
            dense_score=float(d.get("dense_score", 0.0)),
            sparse_score=float(d.get("sparse_score", 0.0)),
            rrf_score=float(d.get("rrf_score", 0.0)),
            rerank_score=float(d.get("rerank_score", 0.0)),
        )

    reranked = [from_dict(d) for d in state.get("reranked_results", [])]
    dense_chunks = [from_dict(d) for d in state.get("dense_results", [])]
    sparse_chunks = [from_dict(d) for d in state.get("sparse_results", [])]

    decision = evaluate_confidence(
        reranked_results=reranked,
        dense_results=dense_chunks,
        sparse_results=sparse_chunks,
    )

    from dataclasses import asdict
    patch = _trace(state, "retrieval_gate", {
        "verdict": decision.verdict,
        "top1": decision.top1_score,
        "margin": decision.score_margin,
        "agreement": decision.dense_sparse_agreement,
    })
    patch["confidence_decision"] = asdict(decision)
    patch["composite_score"] = decision.composite_score
    patch["verdict"] = decision.verdict
    return patch


def _gate_router(state: GRCState) -> str:
    """Conditional edge: route based on retrieval_gate verdict."""
    verdict = state.get("verdict", "insufficient_evidence")
    return verdict  # one of "accept", "needs_review", "insufficient_evidence"


def node_generate(state: GRCState) -> Dict[str, Any]:
    """
    Call the active LLM backend with the reranked context chunks.
    LLM_MODE controls which backend is used (local-only / self-hosted / cloud).
    """
    from app.services.llm_backend import get_llm_backend

    context_chunks = state.get("reranked_results", [])
    query = state.get("query", "")

    prompt = (
        f"Analyse the following security policy document context and answer the query: '{query}'. "
        f"Identify implemented ISO 27001 controls, missing controls, and security practices."
    )

    try:
        backend = get_llm_backend()
        result = backend.generate_structured(prompt=prompt, context_chunks=context_chunks)
        generation = {
            "summary": result.summary,
            "document_category": result.document_category,
            "implemented_controls": result.implemented_controls,
            "missing_controls": result.missing_controls,
            "security_practices": result.security_practices,
            "cited_chunks": result.cited_chunk_ids,
            "backend_used": result.backend_used,
        }
    except Exception as e:
        logger.warning(f"Orchestrator node_generate: LLM backend failed ({e}); returning empty generation")
        generation = {
            "summary": "",
            "document_category": "general",
            "implemented_controls": [],
            "missing_controls": [],
            "security_practices": [],
            "cited_chunks": [c.get("chunk_id") for c in context_chunks[:3]],
            "backend_used": "error",
        }

    patch = _trace(state, "generate", {
        "cited_chunks": len(generation["cited_chunks"]),
        "backend_used": generation["backend_used"],
    })
    patch["generation_result"] = generation
    return patch


def node_verify(state: GRCState) -> Dict[str, Any]:
    """
    Ground-truth citation verification via CitationVerifier.
    Branches on CitationTier (ACCEPT / NEEDS_REVIEW / FAIL) — not a flattened bool.

    Tier mapping:
      ACCEPT       (score == 1.0) → route to 'accept'
      NEEDS_REVIEW (score >= 0.5) → route to 'needs_review'
      FAIL         (score <  0.5) → route to 'needs_review' (human must decide)
    """
    from app.services.citation_verifier import verify_citations, CitationTier

    gen = state.get("generation_result") or {}
    cited_chunk_ids = gen.get("cited_chunks") or []
    context_chunks = state.get("reranked_results", [])
    answer_text = gen.get("summary", "")

    try:
        vr = verify_citations(
            answer_text=answer_text,
            cited_chunk_ids=cited_chunk_ids,
            context_chunks=context_chunks,
        )
        verification = {
            "tier": vr.tier.value,
            "citation_score": vr.citation_score,
            "verified_citations": [v.chunk_id for v in vr.verified],
            "failed_citations": [v.chunk_id for v in vr.failed],
            "per_citation": [
                {
                    "chunk_id": v.chunk_id,
                    "exists": v.exists_in_context,
                    "similarity": v.semantic_similarity,
                    "excerpt": v.excerpt,
                }
                for v in (vr.verified + vr.failed)
            ],
            "reason": vr.reason,
        }
        citation_score = vr.citation_score
        tier = vr.tier
    except Exception as e:
        logger.warning(f"Orchestrator node_verify: citation verification failed ({e}); defaulting to needs_review")
        verification = {
            "tier": CitationTier.NEEDS_REVIEW.value,
            "citation_score": 0.5,
            "reason": f"Verification error: {e}",
        }
        citation_score = 0.5
        tier = CitationTier.NEEDS_REVIEW

    # Verdict uses the tier directly
    verdict = "accept" if tier == CitationTier.ACCEPT else "needs_review"

    patch = _trace(state, "verify", {
        "cited": len(cited_chunk_ids),
        "citation_score": citation_score,
        "tier": tier.value if hasattr(tier, 'value') else str(tier),
    })
    patch["verification_result"] = verification
    patch["citation_score"] = citation_score
    patch["verdict"] = verdict
    return patch


def _verify_router(state: GRCState) -> str:
    """Route based on CitationTier stored in verification_result."""
    vr = state.get("verification_result") or {}
    tier = vr.get("tier", "fail")
    # Only CitationTier.ACCEPT routes to accept; NEEDS_REVIEW and FAIL both go to needs_review
    return "accept" if tier == "accept" else "needs_review"


def node_accept(state: GRCState) -> Dict[str, Any]:
    """Terminal: high-confidence result accepted."""
    patch = _trace(state, "accept", {"composite_score": state.get("composite_score")})
    patch["final_output"] = {
        "verdict": "accept",
        "composite_score": state.get("composite_score"),
        "result": state.get("generation_result"),
        "top_chunks": state.get("reranked_results", [])[:3],
        "trace": state.get("trace", []),
    }
    return patch


def node_needs_review(state: GRCState) -> Dict[str, Any]:
    """
    Human-in-the-loop interrupt.
    Execution pauses here. On resume, human_review_decision is populated.
    """
    decision = interrupt({
        "message": "Retrieval confidence insufficient for auto-acceptance. Human review required.",
        "query": state.get("query"),
        "composite_score": state.get("composite_score"),
        "confidence_reason": (state.get("confidence_decision") or {}).get("reason"),
        "top_chunks": state.get("reranked_results", [])[:3],
    })
    patch = _trace(state, "needs_review", {"human_decision": decision})
    patch["human_review_decision"] = str(decision)
    patch["verdict"] = "needs_review"
    patch["final_output"] = {
        "verdict": "needs_review",
        "composite_score": state.get("composite_score"),
        "human_review_decision": str(decision),
        "result": state.get("generation_result"),
        "trace": state.get("trace", []),
    }
    return patch


def node_insufficient_evidence(state: GRCState) -> Dict[str, Any]:
    """Terminal: retrieval score too low to proceed."""
    patch = _trace(state, "insufficient_evidence", {
        "top1": (state.get("confidence_decision") or {}).get("top1_score"),
    })
    patch["verdict"] = "insufficient_evidence"
    patch["final_output"] = {
        "verdict": "insufficient_evidence",
        "composite_score": state.get("composite_score", 0.0),
        "reason": (state.get("confidence_decision") or {}).get("reason", "Insufficient evidence"),
        "trace": state.get("trace", []),
    }
    return patch


# ── Graph Construction ────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Assemble the full LangGraph state machine."""
    g = StateGraph(GRCState)

    # Nodes
    g.add_node("normalize_query",        node_normalize_query)
    g.add_node("dense_retrieve",         node_dense_retrieve)
    g.add_node("sparse_retrieve",        node_sparse_retrieve)
    g.add_node("fuse",                   node_fuse)
    g.add_node("rerank",                 node_rerank)
    g.add_node("retrieval_gate",         node_retrieval_gate)
    g.add_node("generate",               node_generate)
    g.add_node("verify",                 node_verify)
    g.add_node("accept",                 node_accept)
    g.add_node("needs_review",           node_needs_review)
    g.add_node("insufficient_evidence",  node_insufficient_evidence)

    # Edges — linear up to retrieval_gate
    g.set_entry_point("normalize_query")
    g.add_edge("normalize_query",   "dense_retrieve")
    g.add_edge("dense_retrieve",    "sparse_retrieve")
    g.add_edge("sparse_retrieve",   "fuse")
    g.add_edge("fuse",              "rerank")
    g.add_edge("rerank",            "retrieval_gate")

    # Conditional branch at retrieval_gate
    g.add_conditional_edges("retrieval_gate", _gate_router, {
        "accept":                 "generate",
        "needs_review":           "needs_review",
        "insufficient_evidence":  "insufficient_evidence",
    })

    # Post-generation verification
    g.add_edge("generate", "verify")
    g.add_conditional_edges("verify", _verify_router, {
        "accept":       "accept",
        "needs_review": "needs_review",
    })

    # Terminals
    g.add_edge("accept",               END)
    g.add_edge("needs_review",         END)
    g.add_edge("insufficient_evidence", END)

    return g


# ── Compiled Graph Singleton ──────────────────────────────────────────────────

_checkpointer = MemorySaver()
grc_graph = build_graph().compile(checkpointer=_checkpointer, interrupt_before=["needs_review"])


async def run_grc_pipeline(
    query: str,
    org_id: str,
    collection: Optional[str] = None,
    document_ids: Optional[List[str]] = None,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the full GRC retrieval pipeline for a query.
    Returns final_output dict containing verdict, composite_score, top chunks, and trace.
    """
    import uuid as _uuid
    tid = thread_id or str(_uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}

    initial_state: GRCState = {
        "query": query,
        "org_id": org_id,
        "document_ids": document_ids or [],
        "collection": collection or settings.QDRANT_COLLECTION_DOC_CHUNKS,
        "dense_results": [],
        "sparse_results": [],
        "fused_results": [],
        "reranked_results": [],
        "confidence_decision": None,
        "generation_result": None,
        "verification_result": None,
        "citation_score": 1.0,
        "composite_score": 0.0,
        "human_review_decision": None,
        "trace": [],
        "verdict": None,
        "final_output": None,
    }

    final = await grc_graph.ainvoke(initial_state, config=config)
    return final.get("final_output") or final
