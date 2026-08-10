"""
Evaluation Harness for GRC Retrieval & Confidence Gate System.
Computes Recall@K, Precision@K, Mean Reciprocal Rank (MRR), and Confidence Gate Calibration Metrics.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.confidence_gate import evaluate_confidence, ConfidenceDecision
from app.services.retrieval_service import RankedChunk

logger = logging.getLogger("grc.eval")


@dataclass
class QueryEvalMetrics:
    query_id: str
    query_text: str
    domain: str
    expected_verdict: str
    actual_verdict: str
    verdict_correct: bool
    top1_score: float
    top2_score: float
    score_margin: float
    total_retrieved: int
    reciprocal_rank: float
    recall_at_k: Dict[int, float]
    precision_at_k: Dict[int, float]
    first_relevant_rank: Optional[int]
    top_matches: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EvalSummary:
    total_queries: int
    mrr: float
    gate_accuracy: float
    avg_recall_at_k: Dict[int, float]
    avg_precision_at_k: Dict[int, float]
    query_metrics: List[QueryEvalMetrics]


def is_chunk_relevant(
    chunk_text: str,
    section_heading: str,
    expected_annexes: List[str],
    expected_keywords: List[str],
) -> bool:
    """Check if a retrieved chunk matches expected target annexes or keywords."""
    if not expected_annexes and not expected_keywords:
        return False

    text_lower = (chunk_text + " " + section_heading).lower()

    for annex in expected_annexes:
        clean_annex = annex.replace("A.", "").strip()
        if clean_annex.lower() in text_lower:
            return True

    for kw in expected_keywords:
        if kw.lower() in text_lower:
            return True

    return False


class Evaluator:
    """Evaluates retrieval quality and confidence gate calibration against golden set benchmarks."""

    def __init__(self, golden_set_path: Optional[str] = None, k_values: List[int] = None):
        self.k_values = k_values or [1, 3, 5, 10]
        if golden_set_path:
            self.golden_set_path = Path(golden_set_path)
        else:
            self.golden_set_path = Path(__file__).parent / "golden_set.json"

        self.test_cases = self._load_golden_set()

    def _load_golden_set(self) -> List[Dict[str, Any]]:
        if not self.golden_set_path.exists():
            raise FileNotFoundError(f"Golden set file not found: {self.golden_set_path}")

        with open(self.golden_set_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("test_cases", [])

    def evaluate_query(
        self,
        query_id: str,
        query_text: str,
        domain: str,
        expected_annexes: List[str],
        expected_keywords: List[str],
        expected_verdict: str,
        retrieved_chunks: List[RankedChunk],
    ) -> QueryEvalMetrics:
        """Evaluate retrieval performance and confidence gate decision for a query."""
        total_retrieved = len(retrieved_chunks)

        # Convert RankedChunk objects to dicts for metric calculations
        chunk_dicts = []
        for c in retrieved_chunks:
            chunk_dicts.append({
                "chunk_id": c.chunk_id,
                "text": c.text,
                "section_heading": c.section_heading,
                "rerank_score": c.rerank_score,
                "dense_score": c.dense_score,
                "sparse_score": c.sparse_score,
            })

        # Evaluate confidence gate decision
        gate_decision = evaluate_confidence(
            reranked_results=retrieved_chunks,
            dense_results=retrieved_chunks,
            sparse_results=retrieved_chunks,
        )

        actual_verdict = gate_decision.verdict
        verdict_correct = (actual_verdict == expected_verdict)

        # Identify relevant ranks (1-indexed)
        relevant_ranks = []
        for i, chunk in enumerate(chunk_dicts, start=1):
            text = chunk.get("text", "")
            heading = chunk.get("section_heading", "")
            if is_chunk_relevant(text, heading, expected_annexes, expected_keywords):
                relevant_ranks.append(i)

        first_rank = relevant_ranks[0] if relevant_ranks else None
        reciprocal_rank = 1.0 / first_rank if first_rank is not None else 0.0

        # Calculate Recall@K and Precision@K
        recall_at_k = {}
        precision_at_k = {}

        for k in self.k_values:
            rel_in_k = sum(1 for r in relevant_ranks if r <= k)
            annexes_covered = set()
            for chunk in chunk_dicts[:k]:
                text_lower = (chunk.get("text", "") + " " + chunk.get("section_heading", "")).lower()
                for annex in expected_annexes:
                    if annex.replace("A.", "").strip().lower() in text_lower:
                        annexes_covered.add(annex)

            if expected_annexes:
                recall = len(annexes_covered) / len(expected_annexes)
            else:
                recall = 1.0 if not expected_annexes and actual_verdict == "insufficient_evidence" else 0.0

            precision = rel_in_k / min(k, max(total_retrieved, 1))

            recall_at_k[k] = round(recall, 4)
            precision_at_k[k] = round(precision, 4)

        return QueryEvalMetrics(
            query_id=query_id,
            query_text=query_text,
            domain=domain,
            expected_verdict=expected_verdict,
            actual_verdict=actual_verdict,
            verdict_correct=verdict_correct,
            top1_score=round(gate_decision.top1_score, 4),
            top2_score=round(gate_decision.top2_score, 4),
            score_margin=round(gate_decision.score_margin, 4),
            total_retrieved=total_retrieved,
            reciprocal_rank=round(reciprocal_rank, 4),
            recall_at_k=recall_at_k,
            precision_at_k=precision_at_k,
            first_relevant_rank=first_rank,
            top_matches=chunk_dicts[:3],
        )

    def summarize(self, metrics_list: List[QueryEvalMetrics]) -> EvalSummary:
        """Aggregate query metrics into dataset-level MRR, Gate Accuracy, and Recall/Precision."""
        if not metrics_list:
            return EvalSummary(
                total_queries=0,
                mrr=0.0,
                gate_accuracy=0.0,
                avg_recall_at_k={k: 0.0 for k in self.k_values},
                avg_precision_at_k={k: 0.0 for k in self.k_values},
                query_metrics=[],
            )

        n = len(metrics_list)
        mrr = round(sum(m.reciprocal_rank for m in metrics_list) / n, 4)
        gate_acc = round(sum(1 for m in metrics_list if m.verdict_correct) / n, 4)

        avg_recall = {}
        avg_precision = {}
        for k in self.k_values:
            avg_recall[k] = round(sum(m.recall_at_k.get(k, 0.0) for m in metrics_list) / n, 4)
            avg_precision[k] = round(sum(m.precision_at_k.get(k, 0.0) for m in metrics_list) / n, 4)

        return EvalSummary(
            total_queries=n,
            mrr=mrr,
            gate_accuracy=gate_acc,
            avg_recall_at_k=avg_recall,
            avg_precision_at_k=avg_precision,
            query_metrics=metrics_list,
        )
