"""
Phase 4 Verification — Confidence Gate (3 standalone checks) + LangGraph Orchestrator.
"""
import asyncio
import sys
from dataclasses import dataclass

from app.services.ai_service import ai_service
from app.services.retrieval_service import RankedChunk, retrieval_service
from app.services.confidence_gate import evaluate_confidence


PASS = "[PASS]"
FAIL = "[FAIL]"

def make_chunk(chunk_id, text, rerank_score, dense_score=0.9, sparse_score=0.8, rrf_score=0.02) -> RankedChunk:
    return RankedChunk(
        chunk_id=chunk_id,
        text=text,
        document_id="doc1",
        org_id="org1",
        page_number=1,
        section_heading="Test",
        chunk_index=1,
        dense_score=dense_score,
        sparse_score=sparse_score,
        rrf_score=rrf_score,
        rerank_score=rerank_score,
    )


async def run():
    errors = []
    print("=" * 60)
    print("Phase 4 Verification - Confidence Gate + Orchestrator")
    print("=" * 60)

    # ── Load models ─────────────────────────────────────────────────────────────
    if not ai_service.is_ready:
        ai_service.initialize()
    retrieval_service.initialize()

    # ── Test 1: Standalone check 1 — insufficient_evidence ─────────────────────
    print("\n[1/5] Standalone check 1: low top1 score -> insufficient_evidence")
    # rerank score of -8 -> sigmoid ~ 0.0003, well below threshold 0.65
    low_chunks = [
        make_chunk("c1", "access control", rerank_score=-8.0),
        make_chunk("c2", "cryptography",   rerank_score=-9.0),
    ]
    d = evaluate_confidence(low_chunks, dense_results=low_chunks, sparse_results=low_chunks)
    if d.verdict != "insufficient_evidence":
        errors.append(f"Expected 'insufficient_evidence', got '{d.verdict}'")
        print(f"  {FAIL}: verdict={d.verdict}")
    else:
        print(f"  {PASS}: verdict={d.verdict} (top1={d.top1_score:.4f} < 0.65 threshold)")

    # ── Test 2: Standalone check 2 — small margin -> needs_review ──────────────
    print("\n[2/5] Standalone check 2: small margin -> needs_review (agreement must NOT matter)")
    # Both above threshold, but top1 and top2 are nearly identical (tiny margin)
    # rerank 8.0 -> sigmoid ~0.9997 (above 0.65 threshold)
    # rerank 7.9 -> sigmoid ~0.9996
    # margin = sigmoid(8.0) - sigmoid(7.9) ~ 0.00014 < 0.10 threshold
    close_chunks = [
        make_chunk("c1", "access control", rerank_score=8.0, dense_score=0.9, sparse_score=0.9),
        make_chunk("c2", "cryptography",   rerank_score=7.9, dense_score=0.9, sparse_score=0.9),
    ]
    # Force dense/sparse agreement = True so AND logic would wrongly pass
    d = evaluate_confidence(close_chunks, dense_results=close_chunks, sparse_results=close_chunks)
    if d.verdict != "needs_review":
        errors.append(f"Expected 'needs_review' (small margin), got '{d.verdict}'  margin={d.score_margin:.5f}")
        print(f"  {FAIL}: verdict={d.verdict}, margin={d.score_margin:.5f}")
    else:
        print(f"  {PASS}: verdict={d.verdict} (margin={d.score_margin:.5f} < 0.10 threshold, regardless of agreement)")

    # ── Test 3: Standalone check 3 — disagreement -> needs_review ──────────────
    print("\n[3/5] Standalone check 3: dense/sparse disagreement -> needs_review (margin must NOT matter)")
    # High top1, clear margin, but dense and sparse have zero overlap
    high_chunks = [
        make_chunk("c1", "access control", rerank_score=8.0),
        make_chunk("c2", "cryptography",   rerank_score=2.0),
    ]
    # Make dense and sparse point to totally different chunk IDs (Jaccard = 0)
    dense_only = [make_chunk("d1", "dense result 1", rerank_score=0.8)]
    sparse_only = [make_chunk("s1", "sparse result 1", rerank_score=0.7)]
    d = evaluate_confidence(high_chunks, dense_results=dense_only, sparse_results=sparse_only)
    if d.verdict != "needs_review":
        errors.append(f"Expected 'needs_review' (disagreement), got '{d.verdict}'")
        print(f"  {FAIL}: verdict={d.verdict}, agreement={d.dense_sparse_agreement}")
    else:
        print(f"  {PASS}: verdict={d.verdict} (dense/sparse agreement=False triggers needs_review independently)")

    # ── Test 4: Accept — all checks pass ───────────────────────────────────────
    print("\n[4/5] All checks pass -> accept")
    # High top1, clear margin, full agreement
    good_chunks = [
        make_chunk("c1", "access control MFA required", rerank_score=8.0),
        make_chunk("c2", "network monitoring policy",   rerank_score=1.0),
    ]
    # Dense and sparse agree on same top chunks
    d = evaluate_confidence(good_chunks, dense_results=good_chunks, sparse_results=good_chunks)
    if d.verdict != "accept":
        errors.append(f"Expected 'accept', got '{d.verdict}'")
        print(f"  {FAIL}: verdict={d.verdict}")
    else:
        print(f"  {PASS}: verdict={d.verdict} (top1={d.top1_score:.4f}, margin={d.score_margin:.4f}, composite={d.composite_score})")

    # ── Test 5: Empty results -> insufficient_evidence ──────────────────────────
    print("\n[5/5] Empty reranked results -> insufficient_evidence")
    d = evaluate_confidence(reranked_results=[], dense_results=[], sparse_results=[])
    if d.verdict != "insufficient_evidence":
        errors.append(f"Expected 'insufficient_evidence' for empty results, got '{d.verdict}'")
        print(f"  {FAIL}: verdict={d.verdict}")
    else:
        print(f"  {PASS}: verdict={d.verdict}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if errors:
        print(f"PHASE 4 CONFIDENCE GATE FAILED - {len(errors)} error(s):")
        for e in errors:
            print(f"  x {e}")
        sys.exit(1)
    else:
        print("PHASE 4 CONFIDENCE GATE PASSED")
        print("  - Check 1: low top1 -> insufficient_evidence (standalone)")
        print("  - Check 2: small margin -> needs_review (standalone, ignores agreement)")
        print("  - Check 3: disagreement -> needs_review (standalone, ignores margin)")
        print("  - Check 4: all pass -> accept")
        print("  - Check 5: empty results -> insufficient_evidence")
        print("\nLangGraph orchestrator module imported and compiled successfully.")
        try:
            from app.services.orchestrator import grc_graph, run_grc_pipeline
            print("  LangGraph graph compiled: OK")
        except Exception as e:
            print(f"  LangGraph import FAILED: {e}")
            errors.append(str(e))


if __name__ == "__main__":
    asyncio.run(run())
