"""
Phase 5 Verification:
  1. DataResidency validator — all 6 cases (LLM_MODE=cloud block, QDRANT_URL resolution,
     fail-closed on unresolvable, threshold default warning, strict-pass, off-mode skip)
  2. LLMBackend — local-only path exercises _run_document_analysis
  3. CitationVerifier — existence + semantic similarity checks
"""
import asyncio
import sys
import types
from unittest.mock import MagicMock, patch

PASS = "[PASS]"
FAIL = "[FAIL]"

errors = []

def check(label: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  {PASS}: {label}")
    else:
        errors.append(f"{label}: {detail}")
        print(f"  {FAIL}: {label}" + (f" — {detail}" if detail else ""))


# ─────────────────────────────────────────────────────────────────────────────
# 1. DATA RESIDENCY VALIDATOR
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("Phase 5 Verification - Data Residency + LLM Backend + Citations")
print("=" * 60)
print("\n[1/3] Data Residency Validator")

from app.services.data_residency import (
    DataResidencyError,
    validate_data_residency,
    _validate_qdrant_url,
)

# Build a minimal settings mock
def make_settings(**kwargs):
    s = MagicMock()
    s.DATA_RESIDENCY_MODE = kwargs.get("DATA_RESIDENCY_MODE", "strict")
    s.LLM_MODE = kwargs.get("LLM_MODE", "local-only")
    s.QDRANT_URL = kwargs.get("QDRANT_URL", "http://localhost:6333")
    s.CONFIDENCE_GATE_TOP1_THRESHOLD = kwargs.get("top1", 0.65)
    s.CONFIDENCE_GATE_MARGIN_THRESHOLD = kwargs.get("margin", 0.10)
    return s

# Case 1a: cloud LLM_MODE hard-blocked in strict mode
try:
    validate_data_residency(make_settings(LLM_MODE="cloud"))
    check("Case 1a: cloud LLM_MODE blocked", False, "Expected DataResidencyError, got none")
except DataResidencyError as e:
    check("Case 1a: cloud LLM_MODE blocked", True)

# Case 1b: off-mode skips all checks (no error even with cloud LLM_MODE)
try:
    validate_data_residency(make_settings(DATA_RESIDENCY_MODE="off", LLM_MODE="cloud"))
    check("Case 1b: off-mode skips all checks", True)
except DataResidencyError:
    check("Case 1b: off-mode skips all checks", False, "Should not raise in 'off' mode")

# Case 1c: localhost passes (loopback)
try:
    _validate_qdrant_url("http://localhost:6333")
    check("Case 1c: localhost resolves to loopback -> pass", True)
except DataResidencyError as e:
    check("Case 1c: localhost resolves to loopback -> pass", False, str(e))

# Case 1d: unresolvable hostname fails closed
try:
    _validate_qdrant_url("http://this-hostname-definitely-does-not-exist-xyzzy.internal:6333")
    check("Case 1d: unresolvable hostname fails closed", False, "Expected DataResidencyError, got none")
except DataResidencyError as e:
    check("Case 1d: unresolvable hostname fails closed", "could not be resolved" in str(e).lower())

# Case 1e: simulate a public-IP-resolving hostname (patch getaddrinfo)
import socket as _socket
import ipaddress

def fake_getaddrinfo_public(host, port, *args, **kwargs):
    # Simulate resolving to 8.8.8.8 (public Google DNS)
    return [(_socket.AF_INET, _socket.SOCK_STREAM, 0, '', ('8.8.8.8', 0))]

with patch("app.services.data_residency.socket.getaddrinfo", side_effect=fake_getaddrinfo_public):
    try:
        _validate_qdrant_url("http://cloud.qdrant.io:6333")
        check("Case 1e: public IP resolution hard-fails", False, "Expected DataResidencyError")
    except DataResidencyError as e:
        check("Case 1e: public IP resolution hard-fails", "public" in str(e).lower())

# Case 1f: simulate a no-dot Docker Compose hostname resolving to private bridge IP
def fake_getaddrinfo_private(host, port, *args, **kwargs):
    return [(_socket.AF_INET, _socket.SOCK_STREAM, 0, '', ('172.18.0.5', 0))]

with patch("app.services.data_residency.socket.getaddrinfo", side_effect=fake_getaddrinfo_private):
    try:
        _validate_qdrant_url("http://qdrant:6333")
        check("Case 1f: Docker service hostname resolves to private bridge IP -> pass", True)
    except DataResidencyError as e:
        check("Case 1f: Docker service hostname resolves to private bridge IP -> pass", False, str(e))

# Case 1g: threshold default warning (no error raised, just a warning)
import logging
import io
log_stream = io.StringIO()
handler = logging.StreamHandler(log_stream)
logging.getLogger("grc.data_residency").addHandler(handler)
logging.getLogger("grc.data_residency").setLevel(logging.WARNING)

with patch("app.services.data_residency.socket.getaddrinfo", side_effect=fake_getaddrinfo_private):
    try:
        validate_data_residency(make_settings(top1=0.65, margin=0.10))
    except DataResidencyError:
        pass

log_output = log_stream.getvalue()
check(
    "Case 1g: default thresholds emit WARNING in strict mode",
    "untuned" in log_output.lower() or "defaults" in log_output.lower(),
    f"Log: '{log_output[:120]}'"
)


# ─────────────────────────────────────────────────────────────────────────────
# 2. LLM BACKEND — LOCAL-ONLY PATH
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/3] LLM Backend (local-only)")

from app.services.ai_service import ai_service
if not ai_service.is_ready:
    ai_service.initialize()

from app.services.llm_backend import LocalOnlyBackend

backend = LocalOnlyBackend()
context_chunks = [
    {"chunk_id": "c1", "text": "5.15 Access control. Role-based access and MFA required for admins."},
    {"chunk_id": "c2", "text": "8.24 Cryptography. AES-256 encryption at rest, TLS 1.3 in transit."},
]
result = backend.generate_structured(
    prompt="Analyse these ISO 27001 controls.",
    context_chunks=context_chunks,
)
check("Local-only backend returns LLMResult", result is not None)
check("backend_used is 'local-only'", result.backend_used == "local-only", result.backend_used)
check("Summary is non-empty", bool(result.summary), repr(result.summary))
check("document_category is set", bool(result.document_category), result.document_category)
print(f"    summary='{result.summary[:80]}...'")
print(f"    category='{result.document_category}', controls={result.implemented_controls[:3]}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. CITATION VERIFIER
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/3] Citation Verifier")

from app.services.citation_verifier import verify_citations

answer = "The system implements role-based access control and multi-factor authentication."
context = [
    {"chunk_id": "c1", "text": "5.15 Access control: RBAC and MFA are required."},
    {"chunk_id": "c2", "text": "8.24 Cryptography: AES-256 encryption at rest."},
    {"chunk_id": "c3", "text": "5.24 Incident response: Incidents must be reported within 4 hours."},
]

# Case 3a: cited chunks that exist and are semantically relevant
vr = verify_citations(answer, cited_chunk_ids=["c1"], context_chunks=context)
check("3a: relevant citation verified", vr.passed, f"score={vr.citation_score}, reason={vr.reason}")
check("3a: c1 in verified list", any(v.chunk_id == "c1" for v in vr.verified),
      f"verified={[v.chunk_id for v in vr.verified]}")

# Case 3b: hallucinated chunk_id (not in context)
vr2 = verify_citations(answer, cited_chunk_ids=["nonexistent-id"], context_chunks=context)
check("3b: hallucinated chunk_id fails", not vr2.passed,
      f"score={vr2.citation_score}, failed={[v.chunk_id for v in vr2.failed]}")

# Case 3c: no citations — should pass (nothing to verify)
vr3 = verify_citations(answer, cited_chunk_ids=[], context_chunks=context)
check("3c: empty citations -> pass (nothing to verify)", vr3.passed)

# Case 3d: mixed — one good, one hallucinated
vr4 = verify_citations(answer, cited_chunk_ids=["c1", "ghost-id"], context_chunks=context)
print(f"    3d: mixed citations score={vr4.citation_score:.2f}, passed={vr4.passed}")
check("3d: mixed citations score = 0.5 (1 of 2 verified)", abs(vr4.citation_score - 0.5) < 0.01,
      f"score={vr4.citation_score}")


# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if errors:
    print(f"PHASE 5 VERIFICATION FAILED - {len(errors)} error(s):")
    for e in errors:
        print(f"  x {e}")
    sys.exit(1)
else:
    print("PHASE 5 VERIFICATION PASSED")
    print("  - Data residency: cloud block, off-mode, loopback, fail-closed, public-IP fail,")
    print("    Docker service name + private bridge IP pass, threshold default warning")
    print("  - LLM backend: local-only returns valid LLMResult")
    print("  - Citation verifier: existence + semantic similarity, hallucination detection")
