"""
Phase 5 Re-Verification (post-fix):
  1. DataResidency validator — unchanged, re-confirmed
  2. LLM backend — determinism check: same 2-chunk input produces same output across 3 runs
  3. CitationVerifier — three-tier checks including:
       - empty citations with context -> NEEDS_REVIEW (not ACCEPT)
       - empty citations without context -> FAIL
       - score == 1.0 -> ACCEPT
       - 0.5 <= score < 1.0 -> NEEDS_REVIEW
       - score < 0.5 -> FAIL
       - Orchestrator routes on tier string, not .passed bool
"""
import asyncio
import sys
from unittest.mock import MagicMock, patch
import socket as _socket

PASS = "[PASS]"
FAIL = "[FAIL]"
errors = []

def check(label, condition, detail=""):
    if condition:
        print(f"  {PASS}: {label}")
    else:
        errors.append(f"{label}: {detail}")
        print(f"  {FAIL}: {label}" + (f" -- {detail}" if detail else ""))


# ============================================================
print("=" * 60)
print("Phase 5 Re-Verification (post-fix)")
print("=" * 60)


# ────────────────────────────────────────────────────────────
# 1. DATA RESIDENCY — abbreviated re-check (full suite run separately)
# ────────────────────────────────────────────────────────────
print("\n[1/3] Data Residency (spot-check)")
from app.services.data_residency import DataResidencyError, validate_data_residency, _validate_qdrant_url

def make_settings(**kw):
    s = MagicMock()
    s.DATA_RESIDENCY_MODE = kw.get("DATA_RESIDENCY_MODE", "strict")
    s.LLM_MODE = kw.get("LLM_MODE", "local-only")
    s.QDRANT_URL = kw.get("QDRANT_URL", "http://localhost:6333")
    s.CONFIDENCE_GATE_TOP1_THRESHOLD = kw.get("top1", 0.65)
    s.CONFIDENCE_GATE_MARGIN_THRESHOLD = kw.get("margin", 0.10)
    return s

try:
    validate_data_residency(make_settings(LLM_MODE="cloud"))
    check("cloud LLM_MODE blocked in strict mode", False, "Expected DataResidencyError")
except DataResidencyError:
    check("cloud LLM_MODE blocked in strict mode", True)

def _fake_private(h, p, *a, **k):
    return [(_socket.AF_INET, _socket.SOCK_STREAM, 0, '', ('172.18.0.5', 0))]

with patch("app.services.data_residency.socket.getaddrinfo", side_effect=_fake_private):
    try:
        _validate_qdrant_url("http://qdrant:6333")
        check("Docker service hostname -> private bridge IP -> pass", True)
    except DataResidencyError as e:
        check("Docker service hostname -> private bridge IP -> pass", False, str(e))

try:
    _validate_qdrant_url("http://this-definitely-does-not-resolve-xyzzy.internal:9999")
    check("Unresolvable hostname fails closed", False, "Expected DataResidencyError")
except DataResidencyError:
    check("Unresolvable hostname fails closed", True)


# ────────────────────────────────────────────────────────────
# 2. LLM BACKEND DETERMINISM
# ────────────────────────────────────────────────────────────
print("\n[2/3] LLM Backend Determinism (3 independent runs, same input)")
from app.services.ai_service import ai_service
if not ai_service.is_ready:
    ai_service.initialize()

from app.services.llm_backend import LocalOnlyBackend

CONTEXT = [
    {"chunk_id": "c1", "text": "5.15 Access control. Role-based access and MFA required for admins."},
    {"chunk_id": "c2", "text": "8.24 Cryptography. AES-256 encryption at rest, TLS 1.3 in transit."},
]
PROMPT = "Analyse these ISO 27001 controls."

backend = LocalOnlyBackend()
results = [backend.generate_structured(PROMPT, CONTEXT) for _ in range(3)]

categories = [r.document_category for r in results]
controls   = [tuple(c.get("control_annex", c) if isinstance(c, dict) else c for c in r.implemented_controls) for r in results]

print(f"  Run 1: category={results[0].document_category}, controls={[c.get('control_annex', c) if isinstance(c, dict) else c for c in results[0].implemented_controls]}")
print(f"  Run 2: category={results[1].document_category}, controls={[c.get('control_annex', c) if isinstance(c, dict) else c for c in results[1].implemented_controls]}")
print(f"  Run 3: category={results[2].document_category}, controls={[c.get('control_annex', c) if isinstance(c, dict) else c for c in results[2].implemented_controls]}")

check("category identical across 3 runs", len(set(categories)) == 1, f"got {set(categories)}")
check("controls identical across 3 runs", len(set(controls)) == 1, f"got {set(controls)}")
check("summary non-empty", all(bool(r.summary) for r in results))


# ────────────────────────────────────────────────────────────
# 3. CITATION VERIFIER — three-tier
# ────────────────────────────────────────────────────────────
print("\n[3/3] CitationVerifier — three-tier routing")
from app.services.citation_verifier import verify_citations, CitationTier, score_to_tier

CONTEXT_CHUNKS = [
    {"chunk_id": "c1", "text": "5.15 Access control: RBAC and MFA are required for all admins."},
    {"chunk_id": "c2", "text": "8.24 Cryptography: AES-256 encryption at rest."},
    {"chunk_id": "c3", "text": "5.24 Incident response: Report incidents within 4 hours."},
]
ANSWER = "The system implements role-based access control and multi-factor authentication."

# 3a: Empty citations + context -> NEEDS_REVIEW (not ACCEPT)
vr = verify_citations(ANSWER, cited_chunk_ids=[], context_chunks=CONTEXT_CHUNKS)
check("3a: empty citations + context -> NEEDS_REVIEW (not ACCEPT)", vr.tier == CitationTier.NEEDS_REVIEW,
      f"tier={vr.tier}, reason={vr.reason}")

# 3b: Empty citations + no context -> FAIL
vr = verify_citations(ANSWER, cited_chunk_ids=[], context_chunks=[])
check("3b: empty citations + no context -> FAIL", vr.tier == CitationTier.FAIL,
      f"tier={vr.tier}")

# 3c: All citations verified -> score 1.0 -> ACCEPT
vr = verify_citations(ANSWER, cited_chunk_ids=["c1"], context_chunks=CONTEXT_CHUNKS)
check("3c: all verified -> tier ACCEPT", vr.tier == CitationTier.ACCEPT,
      f"tier={vr.tier}, score={vr.citation_score}")
check("3c: citation_score == 1.0", vr.citation_score == 1.0, f"score={vr.citation_score}")

# 3d: Mixed (1 good, 1 hallucinated) -> score 0.5 -> NEEDS_REVIEW (not ACCEPT)
vr = verify_citations(ANSWER, cited_chunk_ids=["c1", "ghost-id"], context_chunks=CONTEXT_CHUNKS)
check("3d: 0.5 score -> NEEDS_REVIEW (not ACCEPT)", vr.tier == CitationTier.NEEDS_REVIEW,
      f"tier={vr.tier}, score={vr.citation_score}")
print(f"    score={vr.citation_score}, tier={vr.tier.value}")

# 3e: All hallucinated (score 0.0) -> FAIL
vr = verify_citations(ANSWER, cited_chunk_ids=["ghost1", "ghost2"], context_chunks=CONTEXT_CHUNKS)
check("3e: all hallucinated -> FAIL", vr.tier == CitationTier.FAIL,
      f"tier={vr.tier}, score={vr.citation_score}")

# 3f: score_to_tier boundary checks
check("3f: score_to_tier(1.0) == ACCEPT",     score_to_tier(1.0)  == CitationTier.ACCEPT)
check("3f: score_to_tier(0.5) == NEEDS_REVIEW", score_to_tier(0.5) == CitationTier.NEEDS_REVIEW)
check("3f: score_to_tier(0.49) == FAIL",        score_to_tier(0.49) == CitationTier.FAIL)
check("3f: score_to_tier(0.0) == FAIL",          score_to_tier(0.0)  == CitationTier.FAIL)

# 3g: Confirm orchestrator _verify_router reads tier string, not .passed
from app.services.orchestrator import _verify_router
accept_state  = {"verification_result": {"tier": "accept"}}
review_state  = {"verification_result": {"tier": "needs_review"}}
fail_state    = {"verification_result": {"tier": "fail"}}
check("3g: router: tier=accept -> 'accept'",      _verify_router(accept_state) == "accept")
check("3g: router: tier=needs_review -> 'needs_review'", _verify_router(review_state) == "needs_review")
check("3g: router: tier=fail -> 'needs_review'",  _verify_router(fail_state) == "needs_review",
      "FAIL should route to needs_review for human decision, not accept")


# ────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if errors:
    print(f"PHASE 5 RE-VERIFICATION FAILED - {len(errors)} error(s):")
    for e in errors:
        print(f"  x {e}")
    sys.exit(1)
else:
    print("PHASE 5 RE-VERIFICATION PASSED")
    print("  - Data residency: spot-checks pass")
    print("  - LLM backend: deterministic across 3 runs (same category, same controls)")
    print("  - CitationVerifier: three-tier routing correct")
    print("    - empty+context -> NEEDS_REVIEW, empty+no-context -> FAIL")
    print("    - score=1.0 -> ACCEPT, score=0.5 -> NEEDS_REVIEW, score=0.0 -> FAIL")
    print("    - Orchestrator _verify_router branches on tier string, not .passed bool")
