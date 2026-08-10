"""
Phase 7 Verification Script — Known Bug Fixes & Cache Migration.
"""
import inspect
import sys

from app.api import ai as ai_api
from app.api import tickets as tickets_api
from app.services.ai_service import ai_service, _run_document_analysis
from app.services.ticket_service import TicketService

PASS = "[PASS]"
FAIL = "[FAIL]"
errors = []

def check(label: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  {PASS}: {label}")
    else:
        errors.append(f"{label}: {detail}")
        print(f"  {FAIL}: {label}" + (f" — {detail}" if detail else ""))


def run():
    print("=" * 60)
    print("Phase 7 Verification — Known Bug Fixes & Cache Migration")
    print("=" * 60)

    # 1. Bug 1: Org-scoping in compliance_gaps
    print("\n[1/4] Bug 1: Org-scoping in compliance_gaps endpoint...")
    src_ai_api = inspect.getsource(ai_api.compliance_gaps)
    has_org_filter = "models.Evidence.organization_id == current_user.organization_id" in src_ai_api
    check("compliance_gaps filters Evidence query by current_user.organization_id", has_org_filter,
          f"Source check: {has_org_filter}")

    # 2. Bug 2: Gemini JSON structured output response_mime_type
    print("\n[2/4] Bug 2: Gemini structured output configuration...")
    src_ai_service = inspect.getsource(ai_service._analyze_document_gemini)
    has_json_config = "response_mime_type=\"application/json\"" in src_ai_service
    check("_analyze_document_gemini sets response_mime_type='application/json'", has_json_config,
          f"Config check: {has_json_config}")

    # 3. Bug 3: Honest docstrings & labeling for finding ingestion
    print("\n[3/4] Bug 3: Honest docstring & labeling for rule-based finding ingestion...")
    src_tickets_api = inspect.getsource(tickets_api.create_ticket_from_ai)
    src_ticket_svc = inspect.getsource(TicketService.process_ai_finding)

    has_rule_label = "Module A: Rule-Based Finding Ingestion" in src_tickets_api
    has_rule_comment = "deterministic rule-based heuristics" in src_ticket_svc

    check("tickets API labels endpoint as Rule-Based Finding Ingestion", has_rule_label, src_tickets_api[:100])
    check("ticket_service documents process_ai_finding as rule-based keyword mapping", has_rule_comment, src_ticket_svc[:100])

    # 4. Cache Migration TODO
    print("\n[4/4] Cache Migration TODO comment...")
    src_gaps = inspect.getsource(ai_service.get_compliance_gaps)
    full_ai_src = inspect.getsource(ai_service.__class__)
    has_cache_todo = "CACHE MIGRATION" in full_ai_src or "CACHE MIGRATION" in src_gaps
    check("ai_service.py contains explicit TODO for Qdrant cache migration", has_cache_todo)

    print("\n" + "=" * 60)
    if errors:
        print(f"PHASE 7 VERIFICATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("PHASE 7 VERIFICATION PASSED [OK]")
        print("  - Bug 1: Org-scoping added to compliance_gaps")
        print("  - Bug 2: Gemini response_mime_type config set")
        print("  - Bug 3: Ticket ingestion accurately labeled as rule-based")
        print("  - Cache Migration: TODO explicitly documented in ai_service.py")


if __name__ == "__main__":
    run()
