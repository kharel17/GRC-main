"""
Test & Verification Suite for Gemini Skills Integration.

Validates:
1. Tool declaration schemas and MCP tool formatting.
2. Skill execution (Document Processing, Control Mapping, Risk Analysis).
3. AIService integration with GeminiSkillsAdapter.
4. Static AppSec Code Auditor execution.
"""

import sys
import os
from pathlib import Path

# Configure utf-8 encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure paths are configured
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

def test_tool_declarations(adapter):
    print("[1/5] Testing Tool Declarations & MCP Schemas...")
    gemini_tools = adapter.get_tool_declarations()
    assert len(gemini_tools) == 4, f"Expected 4 tool declarations, got {len(gemini_tools)}"
    tool_names = {t["name"] for t in gemini_tools}
    expected_names = {"process_compliance_document", "map_controls", "analyze_risk", "audit_codebase"}
    assert tool_names == expected_names, f"Tool names mismatch: {tool_names}"

    mcp_tools = adapter.get_mcp_tools()
    assert len(mcp_tools) == 4, f"Expected 4 MCP tools, got {len(mcp_tools)}"
    print("  ✓ Gemini & MCP tool schemas validated successfully.")

def test_document_processing(adapter):
    print("[2/5] Testing process_compliance_document skill...")
    sample_text = """
    Information Security Policy - Section 4: Access Control
    All corporate users must authenticate using Multi-Factor Authentication (MFA).
    Password complexity rules require at least 14 characters with periodic reviews.
    All system activity logs are collected into the central SIEM.
    """
    res = adapter.process_compliance_document(sample_text, filename="access_policy.txt")
    assert "summary" in res, "Missing 'summary' in document processing result"
    assert "security_practices" in res, "Missing 'security_practices'"
    assert "category" in res, "Missing 'category'"
    print(f"  ✓ Category: {res.get('category')}")
    print(f"  ✓ Security Practices found: {len(res.get('security_practices', []))}")

def test_control_mapping(adapter):
    print("[3/5] Testing map_controls skill...")
    sample_evidence = "Multi-factor authentication (MFA) is enforced for all cloud portal logins."
    dummy_controls = [
        {"id": "A.5.15", "annex": "5.15", "title": "Access control", "description": "Rules to control physical and logical access."},
        {"id": "A.5.17", "annex": "5.17", "title": "Authentication information", "description": "Allocation and management of authentication info."},
        {"id": "A.8.5", "annex": "8.5", "title": "Secure authentication", "description": "Secure authentication technologies like MFA."},
    ]
    matches = adapter.map_controls(sample_evidence, candidate_controls=dummy_controls, top_n=2)
    assert isinstance(matches, list), "map_controls must return a list"
    assert len(matches) > 0, "Expected at least one control match"
    print(f"  ✓ Matched top control: {matches[0].get('annex')} - {matches[0].get('title')} (Confidence: {matches[0].get('confidence')})")

def test_risk_analysis(adapter):
    print("[4/5] Testing analyze_risk skill...")
    risk_desc = "Critical production database backups are stored in unencrypted S3 bucket accessible to all employees."
    risk_res = adapter.analyze_risk(risk_desc)
    assert "likelihood" in risk_res, "Missing 'likelihood'"
    assert "impact" in risk_res, "Missing 'impact'"
    assert "risk_score" in risk_res, "Missing 'risk_score'"
    assert risk_res["risk_score"] == risk_res["likelihood"] * risk_res["impact"], "Risk score math error"
    print(f"  ✓ Risk Score: {risk_res['risk_score']} (L={risk_res['likelihood']}, I={risk_res['impact']})")
    print(f"  ✓ Reasoning: {risk_res.get('reasoning')[:80]}...")

def test_code_auditor(adapter):
    print("[5/5] Testing audit_codebase skill...")
    audit_res = adapter.audit_codebase(target_dirs=["backend"])
    assert "summary" in audit_res, "Missing summary in audit_codebase"
    assert "persona" in audit_res, "Missing persona in audit_codebase"
    print(f"  ✓ Persona: {audit_res['persona']}")
    print(f"  ✓ Audit Summary: {audit_res['summary']}")

def main():
    print("=" * 65)
    print(" GRC GEMINI SKILLS INTEGRATION TEST SUITE")
    print("=" * 65)

    from backend.app.services.gemini_skills_adapter import GeminiSkillsAdapter
    adapter = GeminiSkillsAdapter()

    test_tool_declarations(adapter)
    test_document_processing(adapter)
    test_control_mapping(adapter)
    test_risk_analysis(adapter)
    test_code_auditor(adapter)

    print("-" * 65)
    print("✓ All Gemini Skills tests passed successfully!")
    print("=" * 65)

if __name__ == "__main__":
    main()
