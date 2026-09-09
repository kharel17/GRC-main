"""
Pytest suite for Gemini Skills Adapter and AIService Integration.
"""

import pytest
from app.services.gemini_skills_adapter import GeminiSkillsAdapter
from app.services.ai_service import AIService


def test_gemini_skills_tool_declarations():
    adapter = GeminiSkillsAdapter()
    declarations = adapter.get_tool_declarations()
    assert len(declarations) == 4
    names = [d["name"] for d in declarations]
    assert "process_compliance_document" in names
    assert "map_controls" in names
    assert "analyze_risk" in names
    assert "audit_codebase" in names


def test_gemini_skills_mcp_formatting():
    adapter = GeminiSkillsAdapter()
    mcp_tools = adapter.get_mcp_tools()
    assert len(mcp_tools) == 4
    for tool in mcp_tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"


def test_process_compliance_document_fallback():
    adapter = GeminiSkillsAdapter()
    sample = "This is our Information Security Policy. Access requires MFA. All databases are encrypted with AES-256."
    res = adapter.process_compliance_document(sample)
    assert res["category"] == "policy"
    assert len(res["security_practices"]) >= 1


def test_map_controls_heuristic():
    adapter = GeminiSkillsAdapter()
    controls = [
        {"id": "5.15", "annex": "5.15", "title": "Access control", "description": "Access control policy"},
        {"id": "8.24", "annex": "8.24", "title": "Use of cryptography", "description": "Encryption standards"},
    ]
    matches = adapter.map_controls("Data encryption at rest using AES-256 keys", candidate_controls=controls)
    assert len(matches) > 0
    assert matches[0]["annex"] in ["8.24", "5.15"]


def test_analyze_risk_heuristic():
    adapter = GeminiSkillsAdapter()
    res = adapter.analyze_risk("Severe data leak vulnerability in public endpoint")
    assert res["likelihood"] >= 1
    assert res["impact"] >= 4
    assert res["risk_score"] == res["likelihood"] * res["impact"]


def test_ai_service_adapter_integration():
    service = AIService()
    assert service.skills_adapter is not None
    assert service.GEMINI_GENERATE_MODEL == "gemini-3.8-flash"
