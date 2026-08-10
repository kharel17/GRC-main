"""
Phase 3 Verification — Hybrid Retrieval Service (BM25 + RRF + CrossEncoder).
Runs without a live Qdrant instance by exercising sparse retrieval, RRF, and reranking
against an in-memory synthetic corpus.
"""
import asyncio
import sys
from dataclasses import dataclass

from app.services.ai_service import ai_service
from app.services.retrieval_service import RankedChunk, retrieval_service


# ── Synthetic corpus ───────────────────────────────────────────────────────────

CORPUS = [
    ("c01", "5.15 Access control. Role-based access control restricts system access to authorised users only. Multi-factor authentication is required for all administrative accounts."),
    ("c02", "8.24 Cryptography policy. AES-256 encryption is required for data at rest. TLS 1.3 must be enforced for all data in transit between internal services."),
    ("c03", "5.24 Incident response. Security incidents must be reported within 4 hours. An incident response team is automatically notified via the SIEM alerting system."),
    ("c04", "6.1 Human resource security. Background screening is required prior to employment. Non-disclosure agreements must be signed before system access is granted."),
    ("c05", "8.15 Logging and monitoring. All privileged access events must be logged. Log integrity is protected via cryptographic hashing and stored in a tamper-evident audit trail."),
    ("c06", "7.1 Physical security perimeter. Server rooms are protected by biometric access controls and monitored 24/7 by CCTV. Visitor logs are maintained electronically."),
    ("c07", "5.29 Business continuity. Disaster recovery drills are conducted quarterly. Recovery time objectives must not exceed 4 hours for critical systems."),
    ("c08", "8.8 Vulnerability management. Automated vulnerability scans are performed weekly. Critical vulnerabilities must be patched within 72 hours of disclosure."),
]

def make_corpus() -> list[RankedChunk]:
    chunks = []
    for i, (cid, text) in enumerate(CORPUS):
        chunks.append(RankedChunk(
            chunk_id=cid,
            text=text,
            document_id="test-doc",
            org_id="test-org",
            page_number=i + 1,
            section_heading=text.split(".")[0],
            chunk_index=i + 1,
            dense_score=0.0,
            sparse_score=0.0,
        ))
    return chunks


async def run():
    errors = []
    print("=" * 60)
    print("Phase 3 Verification — Hybrid Retrieval Service")
    print("=" * 60)

    # ── Step 1: Load AI service ─────────────────────────────────────────────────
    print("\n[1/5] Loading AI embedding model...")
    if not ai_service.is_ready:
        ai_service.initialize()
    print(f"  OK: ai_service.is_ready={ai_service.is_ready}")

    # ── Step 2: Load CrossEncoder ───────────────────────────────────────────────
    print("\n[2/5] Initializing CrossEncoder reranker...")
    retrieval_service.initialize()
    print(f"  OK: retrieval_service._is_ready={retrieval_service._is_ready}")

    # ── Step 3: BM25 sparse retrieval ──────────────────────────────────────────
    print("\n[3/5] BM25 sparse retrieval...")
    query = "multi-factor authentication access control"
    corpus = make_corpus()
    sparse_results = await retrieval_service.sparse_retrieve(query, corpus, top_k=5)
    if not sparse_results:
        errors.append("BM25 returned 0 results")
    else:
        print(f"  OK: {len(sparse_results)} sparse results")
        for r in sparse_results[:3]:
            print(f"    bm25={r.sparse_score:.4f}  chunk='{r.section_heading}' | '{r.text[:60]}...'")
        top_bm25 = sparse_results[0]
        if "access" not in top_bm25.text.lower() and "authentication" not in top_bm25.text.lower():
            errors.append(f"BM25 top result did not match expected document: '{top_bm25.chunk_id}'")
        else:
            print(f"  OK: Top BM25 result is '{top_bm25.chunk_id}' (correct)")

    # ── Step 4: RRF Fusion ──────────────────────────────────────────────────────
    print("\n[4/5] RRF Fusion of dense + sparse lists...")
    # Simulate a dense list with different ordering (reverse of BM25)
    dense_simulated = list(reversed(make_corpus()))
    for i, c in enumerate(dense_simulated):
        c.dense_score = 1.0 / (i + 1)
    sparse_for_rrf = await retrieval_service.sparse_retrieve(query, make_corpus(), top_k=8)

    fused = retrieval_service.rrf_fuse(dense_simulated, sparse_for_rrf)
    if not fused:
        errors.append("RRF fusion returned 0 results")
    else:
        print(f"  OK: {len(fused)} unique chunks after RRF fusion")
        for r in fused[:3]:
            print(f"    rrf={r.rrf_score:.6f}  dense={r.dense_score:.4f}  bm25={r.sparse_score:.4f}  chunk='{r.chunk_id}'")
        # All chunks should appear (union of both lists)
        if len(fused) != len(CORPUS):
            errors.append(f"RRF did not return all {len(CORPUS)} unique chunks; got {len(fused)}")

    # ── Step 5: CrossEncoder Reranking ─────────────────────────────────────────
    print("\n[5/5] CrossEncoder reranking...")
    candidates = make_corpus()
    reranked = retrieval_service.rerank(query=query, candidates=candidates, top_n=3)
    if not reranked:
        errors.append("Reranker returned 0 results")
    else:
        print(f"  OK: {len(reranked)} results after reranking (top_n=3)")
        for r in reranked:
            print(f"    rerank={r.rerank_score:.4f}  chunk='{r.chunk_id}'  | '{r.text[:60]}...'")
        # Access control chunk should rank in top-2 for an auth query
        top_2_ids = {r.chunk_id for r in reranked[:2]}
        if "c01" not in top_2_ids:
            errors.append(f"Expected 'c01' (Access Control) in top-2 after reranking; got {top_2_ids}")
        else:
            print(f"  OK: Access Control chunk 'c01' correctly in top-2 reranked results")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if errors:
        print(f"PHASE 3 VERIFICATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("PHASE 3 VERIFICATION PASSED ✓")
        print("  - BM25 sparse retrieval working")
        print("  - RRF fusion correctly merges dense + sparse rankings")
        print("  - CrossEncoder reranking returns expected top result")


if __name__ == "__main__":
    asyncio.run(run())
