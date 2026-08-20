"""
Citation Verifier — Ground-truth chunk citation verification.

Checks that a generated answer's citations (chunk_ids) are:
  1. Present in the retrieved context pool (existence check).
  2. Semantically relevant to the answer text (cosine similarity >= threshold).

Three-tier scoring (per spec):
  citation_score == 1.0  → ACCEPT       (all citations verified)
  citation_score >= 0.5  → NEEDS_REVIEW (partial verification)
  citation_score <  0.5  → FAIL         (majority unverified)

Empty-citation handling:
  - cited_chunk_ids == [] AND context_chunks non-empty  → NEEDS_REVIEW
    (LLM produced a claim with zero citations — suspicious, not a free pass)
  - cited_chunk_ids == [] AND context_chunks empty       → FAIL
    (no evidence available at all)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger("grc.citation_verifier")


# ── Tier enum ─────────────────────────────────────────────────────────────────

class CitationTier(str, Enum):
    """
    Routing tier derived from citation_score.
    The orchestrator's verify node branches on this tier directly —
    NOT on a flattened passed/failed boolean.
    """
    ACCEPT       = "accept"        # score == 1.0 — all citations verified
    NEEDS_REVIEW = "needs_review"  # 0.5 <= score < 1.0 — partial verification
    FAIL         = "fail"          # score < 0.5 — majority unverified


def score_to_tier(score: float) -> CitationTier:
    """Map a citation_score float to a CitationTier."""
    if score >= 1.0:
        return CitationTier.ACCEPT
    elif score >= 0.5:
        return CitationTier.NEEDS_REVIEW
    else:
        return CitationTier.FAIL


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class CitationVerdict:
    chunk_id: str
    exists_in_context: bool
    semantic_similarity: float    # cosine similarity of answer text vs chunk text
    passes_threshold: bool
    excerpt: str                  # first 120 chars of the chunk text


@dataclass
class CitationVerificationResult:
    tier: CitationTier
    citation_score: float         # fraction of cited chunks that passed all checks
    verified: List[CitationVerdict] = field(default_factory=list)
    failed: List[CitationVerdict] = field(default_factory=list)
    reason: str = ""

    @property
    def passed(self) -> bool:
        """Shim for orchestrator code that reads .passed — True for ACCEPT or NEEDS_REVIEW."""
        return self.tier in (CitationTier.ACCEPT, CitationTier.NEEDS_REVIEW)


_SIMILARITY_THRESHOLD = 0.25     # minimum cosine similarity between answer and cited chunk


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Safe cosine similarity between two 1-D vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _existence_only(
    unique_ids: List[str],
    chunk_map: Dict[str, str],
) -> List[CitationVerdict]:
    return [
        CitationVerdict(
            chunk_id=cid,
            exists_in_context=cid in chunk_map,
            semantic_similarity=1.0 if cid in chunk_map else 0.0,
            passes_threshold=cid in chunk_map,
            excerpt=chunk_map.get(cid, "")[:120],
        )
        for cid in unique_ids
    ]


def _semantic_check(
    unique_ids: List[str],
    chunk_map: Dict[str, str],
    embeddings: np.ndarray,   # shape (1 + len(unique_ids), dim)
    threshold: float,
) -> List[CitationVerdict]:
    answer_emb = embeddings[0]
    verdicts = []
    for i, cid in enumerate(unique_ids):
        exists = cid in chunk_map
        chunk_text = chunk_map.get(cid, "")
        if not exists:
            verdicts.append(CitationVerdict(
                chunk_id=cid,
                exists_in_context=False,
                semantic_similarity=0.0,
                passes_threshold=False,
                excerpt="",
            ))
            continue
        chunk_emb = embeddings[i + 1]
        sim = _cosine_similarity(answer_emb, chunk_emb)
        verdicts.append(CitationVerdict(
            chunk_id=cid,
            exists_in_context=True,
            semantic_similarity=round(sim, 4),
            passes_threshold=sim >= threshold,
            excerpt=chunk_text[:120],
        ))
    return verdicts


def verify_citations(
    answer_text: str,
    cited_chunk_ids: List[str],
    context_chunks: List[Dict[str, Any]],
    similarity_threshold: float = _SIMILARITY_THRESHOLD,
) -> CitationVerificationResult:
    """
    Verify each cited chunk_id exists in context and is semantically similar
    to the answer text. Routes empty citations to NEEDS_REVIEW or FAIL.

    Args:
        answer_text:          The generated answer/summary text.
        cited_chunk_ids:      List of chunk IDs the LLM claims to have cited.
        context_chunks:       List of dicts with keys 'chunk_id' and 'text'.
        similarity_threshold: Minimum cosine similarity to count as verified.

    Returns:
        CitationVerificationResult with tier, score, and per-citation breakdown.
    """
    # ── Empty-citation routing ─────────────────────────────────────────────────
    if not cited_chunk_ids:
        if context_chunks:
            return CitationVerificationResult(
                tier=CitationTier.NEEDS_REVIEW,
                citation_score=0.0,
                reason=(
                    "Answer contains no citations despite having retrieved context. "
                    "Evidence-grounded claims must cite supporting chunks."
                ),
            )
        else:
            return CitationVerificationResult(
                tier=CitationTier.FAIL,
                citation_score=0.0,
                reason="No citations and no retrieved context — answer is unsupported.",
            )

    # Build lookup map from context pool
    chunk_map: Dict[str, str] = {
        c.get("chunk_id", ""): c.get("text", "")
        for c in context_chunks
        if c.get("chunk_id")
    }

    from app.services.ai_service import ai_service
    unique_ids = list(dict.fromkeys(cited_chunk_ids))  # deduplicate, preserve order

    if not ai_service.is_ready:
        logger.warning("CitationVerifier: ai_service not ready; falling back to existence-only check")
        verdicts = _existence_only(unique_ids, chunk_map)
    else:
        texts_to_embed = [answer_text] + [chunk_map.get(cid, "") for cid in unique_ids]
        try:
            embeddings = ai_service._embed_texts(texts_to_embed)
            verdicts = _semantic_check(unique_ids, chunk_map, embeddings, similarity_threshold)
        except Exception as e:
            logger.warning(f"CitationVerifier: embedding failed ({e}); falling back to existence check")
            verdicts = _existence_only(unique_ids, chunk_map)

    verified = [v for v in verdicts if v.passes_threshold]
    failed_verdicts = [v for v in verdicts if not v.passes_threshold]
    score = round(len(verified) / max(len(verdicts), 1), 4)
    tier = score_to_tier(score)

    logger.info(
        f"CitationVerifier: {len(verified)}/{len(verdicts)} verified "
        f"(score={score:.2f}, tier={tier.value})"
    )

    return CitationVerificationResult(
        tier=tier,
        citation_score=score,
        verified=verified,
        failed=failed_verdicts,
        reason=(
            "All citations verified" if not failed_verdicts else
            f"{len(failed_verdicts)} citation(s) failed: "
            + ", ".join(v.chunk_id for v in failed_verdicts[:5])
        ),
    )
