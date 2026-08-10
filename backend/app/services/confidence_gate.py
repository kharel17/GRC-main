"""
Retrieval Confidence Gate — Three standalone checks (plan-approved logic).

Checks fire independently, not ANDed together:
  1. top1_score < CONFIDENCE_GATE_TOP1_THRESHOLD  → insufficient_evidence
  2. score_margin < CONFIDENCE_GATE_MARGIN_THRESHOLD → needs_review  (standalone)
  3. dense_sparse_agreement == False               → needs_review  (standalone)
  4. otherwise                                     → accept
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, List, Optional

import numpy as np

from app.config import settings
from app.services.retrieval_service import RankedChunk

logger = logging.getLogger("grc.confidence_gate")

Verdict = Literal["accept", "needs_review", "insufficient_evidence"]


@dataclass
class ConfidenceDecision:
    verdict: Verdict
    top1_score: float
    top2_score: float
    score_margin: float
    dense_sparse_agreement: bool
    composite_score: float
    reason: str
    # Individual check flags for traceability
    failed_min_threshold: bool = False
    failed_margin: bool = False
    failed_agreement: bool = False


def _compute_dense_sparse_agreement(
    dense_results: List[RankedChunk],
    sparse_results: List[RankedChunk],
    top_k: int = 5,
) -> bool:
    """
    Check whether the top-k results from dense and sparse lists substantially agree.
    Agreement = Jaccard similarity of their top-k chunk_id sets >= 0.4.
    """
    if not dense_results or not sparse_results:
        return False

    dense_ids = {r.chunk_id for r in dense_results[:top_k]}
    sparse_ids = {r.chunk_id for r in sparse_results[:top_k]}
    if not dense_ids and not sparse_ids:
        return True
    union = dense_ids | sparse_ids
    if not union:
        return False
    jaccard = len(dense_ids & sparse_ids) / len(union)
    agreed = jaccard >= 0.4
    logger.debug(f"Confidence gate: dense/sparse Jaccard={jaccard:.3f} → agreement={agreed}")
    return agreed


def _composite_score(
    top1_rerank: float,
    rrf_score: float,
    citation_score: float = 1.0,
) -> float:
    """
    Composite confidence score:
      0.4 * rerank_top1  +  0.3 * rrf_normalized  +  0.3 * citation_score
    rrf_score is normalized to [0,1] by assuming max RRF score ~ 1/(60+1).
    """
    MAX_RRF = 1.0 / 61.0  # maximum possible RRF score for rank-1 in one list
    rrf_norm = min(rrf_score / MAX_RRF, 1.0) if MAX_RRF > 0 else 0.0
    return round(0.4 * top1_rerank + 0.3 * rrf_norm + 0.3 * citation_score, 4)


def evaluate_confidence(
    reranked_results: List[RankedChunk],
    dense_results: Optional[List[RankedChunk]] = None,
    sparse_results: Optional[List[RankedChunk]] = None,
    citation_score: float = 1.0,
) -> ConfidenceDecision:
    """
    Evaluate retrieval confidence from the reranked result list.

    The CrossEncoder score is a raw logit (unbounded). We normalise it to [0,1]
    using a sigmoid for threshold comparison.
    """
    if not reranked_results:
        return ConfidenceDecision(
            verdict="insufficient_evidence",
            top1_score=0.0,
            top2_score=0.0,
            score_margin=0.0,
            dense_sparse_agreement=False,
            composite_score=0.0,
            reason="No retrieval results available",
            failed_min_threshold=True,
        )

    def sigmoid(x: float) -> float:
        import math
        return 1.0 / (1.0 + math.exp(-x))

    top1_raw = reranked_results[0].rerank_score
    top2_raw = reranked_results[1].rerank_score if len(reranked_results) > 1 else top1_raw

    # Normalise CrossEncoder top-1 logit via sigmoid for min-threshold check [0,1]
    top1_norm = sigmoid(top1_raw)
    top2_norm = sigmoid(top2_raw)

    # Compute margin directly from raw CrossEncoder logit difference to avoid sigmoid saturation
    # Raw logit margin: separation >= 1.0 logit indicates a clear, non-ambiguous top match
    raw_margin = top1_raw - top2_raw if len(reranked_results) > 1 else 10.0
    margin = raw_margin  # Export raw logit margin

    top1_rrf = reranked_results[0].rrf_score

    agreed = _compute_dense_sparse_agreement(
        dense_results or [],
        sparse_results or [],
    )

    composite = _composite_score(top1_norm, top1_rrf, citation_score)

    failed_threshold = top1_norm < settings.CONFIDENCE_GATE_TOP1_THRESHOLD
    # Margin threshold reads directly from config — no code-level override.
    # Config default is 1.0 logit (raw CrossEncoder separation for clear match).
    failed_margin = raw_margin < settings.CONFIDENCE_GATE_MARGIN_THRESHOLD
    failed_agreement = not agreed

    # ── Three independent standalone checks (plan-mandated order) ─────────────

    # 1. Low top-1 score
    if failed_threshold:
        return ConfidenceDecision(
            verdict="insufficient_evidence",
            top1_score=top1_norm,
            top2_score=top2_norm,
            score_margin=margin,
            dense_sparse_agreement=agreed,
            composite_score=composite,
            reason=(
                f"Top match below minimum similarity threshold "
                f"({top1_norm:.3f} < {settings.CONFIDENCE_GATE_TOP1_THRESHOLD})"
            ),
            failed_min_threshold=True,
        )

    # 2. Small score margin (ambiguous — multiple controls plausibly apply)
    if failed_margin:
        return ConfidenceDecision(
            verdict="needs_review",
            top1_score=top1_norm,
            top2_score=top2_norm,
            score_margin=margin,
            dense_sparse_agreement=agreed,
            composite_score=composite,
            reason=(
                f"Small score margin between top candidates — ambiguous match "
                f"(margin={margin:.3f} < {settings.CONFIDENCE_GATE_MARGIN_THRESHOLD})"
            ),
            failed_margin=True,
        )

    # 3. Dense and sparse algorithms disagreed on top result
    if failed_agreement:
        return ConfidenceDecision(
            verdict="needs_review",
            top1_score=top1_norm,
            top2_score=top2_norm,
            score_margin=margin,
            dense_sparse_agreement=agreed,
            composite_score=composite,
            reason="Dense and sparse retrieval algorithms disagreed on top result",
            failed_agreement=True,
        )

    # 4. Clear winner
    return ConfidenceDecision(
        verdict="accept",
        top1_score=top1_norm,
        top2_score=top2_norm,
        score_margin=margin,
        dense_sparse_agreement=agreed,
        composite_score=composite,
        reason="High retrieval confidence with clear top match",
    )
