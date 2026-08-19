"""
CLI Runner for GRC Retrieval Golden Set Benchmark & Gate Threshold Calibration.
"""
import asyncio
import logging
import sys

from app.config import settings
from app.services.ai_service import ai_service
from app.services.retrieval_service import RankedChunk, retrieval_service
from app.services.vector_store import vector_store
from eval.evaluator import Evaluator, QueryEvalMetrics

logger = logging.getLogger("grc.eval.runner")

# Expanded realistic corpus including positive policy text, ambiguous overlapping text, and distractor noise
BENCHMARK_CORPUS = [
    RankedChunk("c101", "5.15 Access control policy. Role-based access control (RBAC) restricts access to systems. Multi-factor authentication (MFA) is required for all administrative accounts.", "doc1", "org1", 1, "5.15 Access Control", 1),
    RankedChunk("c102", "8.24 Cryptography policy. AES-256 encryption required for data at rest. TLS 1.3 enforced for data in transit.", "doc1", "org1", 2, "8.24 Cryptography", 2),
    RankedChunk("c103", "5.24 Incident management. Security incident response procedure. Incident reporting required within 4 hours.", "doc1", "org1", 3, "5.24 Incident Management", 3),
    RankedChunk("c104", "6.1 Human resource security. Pre-employment background screening required. Non-disclosure agreements (NDA) signed before access.", "doc1", "org1", 4, "6.1 HR Security", 4),
    RankedChunk("c105", "8.15 Logging and monitoring. Audit log collection via SIEM. Privileged access events logged with tamper-evident integrity.", "doc1", "org1", 5, "8.15 Logging", 5),
    RankedChunk("c106", "7.1 Physical security perimeter. Biometric access control, CCTV monitoring of server room.", "doc1", "org1", 6, "7.1 Physical Security", 6),
    RankedChunk("c107", "5.29 Business continuity. Disaster recovery quarterly drills. Recovery time objective (RTO) maximum 4 hours.", "doc1", "org1", 7, "5.29 Business Continuity", 7),
    RankedChunk("c108", "8.8 Vulnerability management. Weekly automated vulnerability scans. Critical patch management window is 72 hours.", "doc1", "org1", 8, "8.8 Vulnerability Management", 8),
    RankedChunk("c109", "5.17 Authentication information. Passwords and secret authentication credentials rules and complexity requirements.", "doc1", "org1", 9, "5.17 Authentication Credentials", 9),
    RankedChunk("c110", "5.12 Classification of information. Information labeling, classification schema, and storage media handling.", "doc1", "org1", 10, "5.12 Information Classification", 10),
]


async def run_evaluation():
    print("=" * 75)
    print(" GRC Retrieval Pipeline & Confidence Gate Calibration Benchmark")
    print("=" * 75)

    # 1. Initialize services
    if not ai_service.is_ready:
        ai_service.initialize()
    retrieval_service.initialize()
    await vector_store.initialize_collections()

    evaluator = Evaluator()
    results: list[QueryEvalMetrics] = []

    use_qdrant = vector_store.is_ready
    if use_qdrant:
        print(" Evaluation Mode : QDRANT LIVE STORE")
        from app.ingestion.chunker import Chunk
        benchmark_chunks = [
            Chunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                org_id=c.org_id,
                page_number=c.page_number,
                section_heading=c.section_heading,
                chunk_index=c.chunk_index,
                text=c.text,
                token_count=len(c.text.split()),
            )
            for c in BENCHMARK_CORPUS
        ]
        embeddings = ai_service._embed_texts([c.text for c in benchmark_chunks])
        await vector_store.upsert_chunks(benchmark_chunks, embeddings)
    else:
        print(" Evaluation Mode : BENCHMARK CORPUS (BM25 + CrossEncoder, Qdrant offline)")

    print(f" Loaded {len(evaluator.test_cases)} test queries (Positive, Ambiguous, Hard-Negative).\n")
    print(f" Current Config Thresholds: TOP1 = {settings.CONFIDENCE_GATE_TOP1_THRESHOLD}, MARGIN = {settings.CONFIDENCE_GATE_MARGIN_THRESHOLD}\n")

    # 2. Iterate through test cases
    for tc in evaluator.test_cases:
        qid = tc["id"]
        query = tc["query"]
        domain = tc["domain"]
        expected_annexes = tc.get("expected_annexes", [])
        expected_keywords = tc.get("expected_keywords", [])
        expected_verdict = tc.get("expected_verdict", "accept")

        if use_qdrant:
            retrieved = await retrieval_service.hybrid_retrieve(
                query=query,
                collection="grc_doc_chunks",
                top_k_dense=20,
                top_k_sparse=20,
                rerank_top_n=10,
            )
        else:
            sparse = await retrieval_service.sparse_retrieve(query, list(BENCHMARK_CORPUS), top_k=8)
            fused = retrieval_service.rrf_fuse(list(BENCHMARK_CORPUS), sparse)
            retrieved = retrieval_service.rerank(query, fused, top_n=8)

        metrics = evaluator.evaluate_query(
            query_id=qid,
            query_text=query,
            domain=domain,
            expected_annexes=expected_annexes,
            expected_keywords=expected_keywords,
            expected_verdict=expected_verdict,
            retrieved_chunks=retrieved,
        )
        results.append(metrics)

        correct_flag = "OK" if metrics.verdict_correct else "MISMATCH"
        print(
            f"[{qid:<10}] {domain:<26} | Exp: {expected_verdict:<22} | Act: {metrics.actual_verdict:<22} "
            f"| Top1: {metrics.top1_score:.4f} | Margin: {metrics.score_margin:.4f} | [{correct_flag}]"
        )

    # 3. Aggregate results
    summary = evaluator.summarize(results)

    print("\n" + "=" * 75)
    print(" BENCHMARK SUMMARY & GATE CALIBRATION RESULTS")
    print("=" * 75)
    print(f" Total Queries Evaluated   : {summary.total_queries}")
    print(f" Mean Reciprocal Rank (MRR): {summary.mrr:.4f}")
    print(f" Gate Verdict Accuracy     : {summary.gate_accuracy * 100:.1f}% ({sum(1 for m in results if m.verdict_correct)}/{summary.total_queries})")
    print("-" * 75)

    pos_scores = [m.top1_score for m in results if m.expected_verdict == "accept"]
    neg_scores = [m.top1_score for m in results if m.expected_verdict == "insufficient_evidence"]
    amb_margins = [m.score_margin for m in results if m.expected_verdict == "needs_review"]

    print(" Score Distributions:")
    if pos_scores:
        print(f"   Positive Matches Top1 Score Range  : min={min(pos_scores):.4f}, max={max(pos_scores):.4f}, mean={sum(pos_scores)/len(pos_scores):.4f}")
    if neg_scores:
        print(f"   Hard-Negative Top1 Score Range     : min={min(neg_scores):.4f}, max={max(neg_scores):.4f}, mean={sum(neg_scores)/len(neg_scores):.4f}")
    if amb_margins:
        print(f"   Ambiguous Match Margin Range       : min={min(amb_margins):.4f}, max={max(amb_margins):.4f}, mean={sum(amb_margins)/len(amb_margins):.4f}")

    print("-" * 75)
    print(" Recall @ K (Positive Queries):")
    for k, r in summary.avg_recall_at_k.items():
        print(f"   Recall@{k:<2}  : {r:.4f} ({r*100:.1f}%)")
    print("=" * 75)

    return summary


if __name__ == "__main__":
    asyncio.run(run_evaluation())
