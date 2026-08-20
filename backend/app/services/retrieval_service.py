"""
Hybrid Retrieval Service — Dense + BM25 Sparse + RRF Fusion + CrossEncoder Reranking.

All methods are stateless; they accept org_id and query_text and return RankedChunk lists.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import numpy as np

from app.config import settings
from app.services.vector_store import vector_store

logger = logging.getLogger("grc.retrieval")


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class RankedChunk:
    chunk_id: str
    text: str
    document_id: str
    org_id: str
    page_number: int
    section_heading: str
    chunk_index: int
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: float = 0.0


# ── Retrieval Service ──────────────────────────────────────────────────────────

class RetrievalService:
    """
    Orchestrates hybrid retrieval (dense + sparse) with RRF fusion and CrossEncoder reranking.
    Dense retrieval uses Qdrant. Sparse retrieval uses BM25 (rank_bm25).
    Reranking uses cross-encoder/ms-marco-MiniLM-L6-v2.
    """

    def __init__(self):
        self._cross_encoder = None
        self._bm25_corpus: Dict[str, Any] = {}  # keyed by collection / org
        self._is_ready = False

    def initialize(self) -> None:
        """Load the CrossEncoder model. Called once at startup after AI service init."""
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Retrieval: Loading CrossEncoder '{settings.RERANK_MODEL}'...")
            self._cross_encoder = CrossEncoder(
                settings.RERANK_MODEL,
                max_length=512,
            )
            self._is_ready = True
            logger.info("Retrieval: CrossEncoder loaded ✓")
        except Exception as e:
            logger.warning(f"Retrieval: CrossEncoder failed to load ({e}). Reranking disabled.")
            self._cross_encoder = None
            self._is_ready = False

    # ── Dense retrieval ──────────────────────────────────────────────────────────

    async def dense_retrieve(
        self,
        query_embedding: np.ndarray,
        collection: str,
        top_k: int,
        org_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> List[RankedChunk]:
        """Retrieve top-k chunks by dense cosine similarity via Qdrant."""
        hits = await vector_store.dense_search(
            query_vector=query_embedding,
            collection_name=collection,
            top_k=top_k,
            org_id=org_id,
            document_id=document_id,
        )

        results: List[RankedChunk] = []
        for h in hits:
            p = h.get("payload", {})
            results.append(RankedChunk(
                chunk_id=h["id"],
                text=p.get("text", ""),
                document_id=str(p.get("document_id", "")),
                org_id=str(p.get("org_id", "")),
                page_number=int(p.get("page_number", 0)),
                section_heading=p.get("section_heading", ""),
                chunk_index=int(p.get("chunk_index", 0)),
                dense_score=float(h.get("score", 0.0)),
            ))
        return results

    # ── Sparse / BM25 retrieval ───────────────────────────────────────────────

    async def sparse_retrieve(
        self,
        query: str,
        candidate_chunks: List[RankedChunk],
        top_k: int,
    ) -> List[RankedChunk]:
        """
        BM25 sparse retrieval over a candidate corpus.
        Falls back gracefully if rank_bm25 is unavailable.
        """
        if not candidate_chunks:
            return []

        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.debug("rank_bm25 not installed; sparse retrieval skipped")
            return []

        # Tokenise corpus
        tokenised_corpus = [chunk.text.lower().split() for chunk in candidate_chunks]
        bm25 = BM25Okapi(tokenised_corpus)
        query_tokens = query.lower().split()
        scores = bm25.get_scores(query_tokens)

        # Annotate candidates with sparse scores, sort, return top-k
        scored = []
        for chunk, score in zip(candidate_chunks, scores):
            chunk.sparse_score = float(score)
            scored.append(chunk)

        scored.sort(key=lambda c: c.sparse_score, reverse=True)
        return scored[:top_k]

    # ── RRF Fusion ────────────────────────────────────────────────────────────

    def rrf_fuse(
        self,
        dense_results: List[RankedChunk],
        sparse_results: List[RankedChunk],
        k: int = 60,
    ) -> List[RankedChunk]:
        """
        Reciprocal Rank Fusion.
        score(d) = Σ 1 / (k + rank_i(d))   where k=60 (standard constant, no hand-tuning needed)
        """
        rrf_scores: Dict[str, float] = {}
        chunk_index: Dict[str, RankedChunk] = {}

        for rank_list in (dense_results, sparse_results):
            for rank, chunk in enumerate(rank_list, start=1):
                cid = chunk.chunk_id
                rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank)
                # Keep whichever entry we've seen; dense_score and sparse_score
                # are set separately before fusion is called
                if cid not in chunk_index:
                    chunk_index[cid] = chunk
                else:
                    # Merge scores from both sides
                    existing = chunk_index[cid]
                    if chunk.dense_score > existing.dense_score:
                        existing.dense_score = chunk.dense_score
                    if chunk.sparse_score > existing.sparse_score:
                        existing.sparse_score = chunk.sparse_score

        # Assign fused score and sort
        for cid, rrf_score in rrf_scores.items():
            chunk_index[cid].rrf_score = rrf_score

        fused = sorted(chunk_index.values(), key=lambda c: c.rrf_score, reverse=True)
        return fused

    # ── CrossEncoder Reranking ────────────────────────────────────────────────

    def rerank(
        self,
        query: str,
        candidates: List[RankedChunk],
        top_n: int,
    ) -> List[RankedChunk]:
        """
        Rerank candidates using CrossEncoder.
        Falls back to RRF ordering if CrossEncoder not available.
        """
        if not candidates:
            return []

        if self._cross_encoder is None or not self._is_ready:
            logger.debug("Retrieval: CrossEncoder not ready; returning RRF-ranked results")
            return candidates[:top_n]

        pairs = [(query, chunk.text) for chunk in candidates]
        try:
            scores = self._cross_encoder.predict(pairs)
        except Exception as e:
            logger.warning(f"Retrieval: CrossEncoder predict failed ({e}); falling back to RRF order")
            return candidates[:top_n]

        for chunk, score in zip(candidates, scores):
            chunk.rerank_score = float(score)

        candidates.sort(key=lambda c: c.rerank_score, reverse=True)
        return candidates[:top_n]

    # ── Full Pipeline ─────────────────────────────────────────────────────────

    async def hybrid_retrieve(
        self,
        query: str,
        collection: str,
        org_id: Optional[str] = None,
        document_id: Optional[str] = None,
        top_k_dense: Optional[int] = None,
        top_k_sparse: Optional[int] = None,
        rerank_top_n: Optional[int] = None,
    ) -> List[RankedChunk]:
        """
        Full pipeline: embed query → dense retrieve → BM25 sparse on dense results
        → RRF fuse → CrossEncoder rerank → return top-N.
        """
        top_k_dense = top_k_dense or settings.RETRIEVAL_TOP_K_DENSE
        top_k_sparse = top_k_sparse or settings.RETRIEVAL_TOP_K_SPARSE
        rerank_top_n = rerank_top_n or settings.RERANK_TOP_N

        # 1. Embed query
        from app.services.ai_service import ai_service
        if not ai_service.is_ready:
            logger.warning("Retrieval: ai_service not ready; cannot embed query")
            return []

        query_embedding = ai_service._embed_text(query)

        # 2. Dense retrieval via Qdrant
        dense_results = await self.dense_retrieve(
            query_embedding=query_embedding,
            collection=collection,
            top_k=top_k_dense,
            org_id=org_id,
            document_id=document_id,
        )
        logger.debug(f"Retrieval: dense={len(dense_results)} hits")

        if not dense_results:
            return []

        # ── Reranker Bypass for ISO 27001 Controls ──
        # Skip BM25, RRF, and CrossEncoder because the MS-MARCO reranker suffers
        # from severe domain/vocabulary mismatch on short ISO control descriptions.
        # Set rerank_score to the raw dense cosine similarity score directly.
        if collection == settings.QDRANT_COLLECTION_ISO_CONTROLS:
            for chunk in dense_results:
                chunk.rerank_score = chunk.dense_score
            logger.info(
                f"Retrieval: bypassed reranker for {collection} query='{query[:60]}...' "
                f"returning {len(dense_results[:rerank_top_n])} dense hits"
            )
            return dense_results[:rerank_top_n]

        # 3. Sparse BM25 over the dense candidate set
        sparse_results = await self.sparse_retrieve(
            query=query,
            candidate_chunks=list(dense_results),  # new list so scores are set independently
            top_k=top_k_sparse,
        )
        logger.debug(f"Retrieval: sparse={len(sparse_results)} hits")

        # 4. RRF fusion
        fused = self.rrf_fuse(dense_results, sparse_results)
        logger.debug(f"Retrieval: fused={len(fused)} unique chunks after RRF")

        # 5. CrossEncoder reranking
        reranked = self.rerank(query=query, candidates=fused, top_n=rerank_top_n)
        logger.info(
            f"Retrieval: query='{query[:60]}...' "
            f"dense={len(dense_results)} sparse={len(sparse_results)} "
            f"fused={len(fused)} reranked_to={len(reranked)}"
        )

        return reranked


# Global singleton
retrieval_service = RetrievalService()
