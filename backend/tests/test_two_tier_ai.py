"""
Test suite for Two-Tier AI Evidence Verification and Starter Policy Generation.
Validates:
1. EvidenceAnalysisResult two-tier data model fields and serialization.
2. Two-tier retrieval logic in analyze_evidence_qdrant:
   - Tier 1: vector_store.dense_search in grc_doc_chunks scoped to org_id
   - Tier 2: vector_store.dense_search in grc_iso_controls
3. Baseline policy generator synthesizing Access Control, Incident Response, and Data Protection policies.
"""
from typing import Any, List, Optional
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.ai_models import EvidenceAnalysisResult, ControlMatch
from app.services.ai_service import AIService
from app.services.policy_generator import (
    generate_starter_policies,
    BASELINE_POLICY_TEMPLATES,
)


def test_evidence_analysis_result_two_tier_fields():
    """Verify EvidenceAnalysisResult schema supports policy-first fields."""
    ctrl_match = ControlMatch(
        control_id="ISO-A.9.4.2",
        annex="A.9.4.2",
        title="User Authentication",
        description="Appropriate authentication methods shall be used.",
        clause_id="9.4.2",
        confidence=0.92,
    )

    result = EvidenceAnalysisResult(
        category="policy",
        matched_controls=[ctrl_match],
        summary="Compliant with both internal policy and ISO standard.",
        internal_policy_match={
            "found": True,
            "policy_title": "Access Control Policy",
            "clause_summary": "All corporate accounts must enforce hardware or TOTP MFA.",
            "is_compliant_with_policy": True,
            "confidence_score": 0.95,
        },
        framework_control_match={
            "control_id": "A.9.4.2",
            "title": "User authentication",
            "is_compliant_with_framework": True,
            "confidence_score": 0.90,
        },
        two_tier_evaluation={
            "internal_policy_match": {"found": True, "policy_title": "Access Control Policy"},
            "framework_control_match": {"control_id": "A.9.4.2"},
            "gap_analysis": "Evidence strictly meets internal policy and satisfies ISO 27001 A.9.4.2.",
        },
    )

    d = result.to_dict()
    assert d["category"] == "policy"
    assert len(d["matched_controls"]) == 1
    assert d["internal_policy_match"]["policy_title"] == "Access Control Policy"
    assert d["framework_control_match"]["control_id"] == "A.9.4.2"
    assert d["two_tier_evaluation"]["gap_analysis"] is not None


@pytest.mark.anyio
async def test_analyze_evidence_qdrant_two_tier_lookup():
    """Verify analyze_evidence_qdrant performs Tier 1 and Tier 2 searches when org_id is provided."""
    service = AIService()
    service._is_ready = True
    test_org_id = str(uuid4())

    fake_iso_hit = {
        "score": 0.85,
        "payload": {
            "control_id": "A.9.4.2",
            "annex": "A.9.4.2",
            "title": "User authentication for external connections",
            "description": "Appropriate authentication methods shall be used to control access.",
            "clause_id": "9.4.2",
        }
    }

    fake_policy_hit = {
        "score": 0.88,
        "payload": {
            "section_heading": "Access Control Policy v2",
            "text": "All employees must authenticate with multi-factor authentication (MFA).",
            "org_id": test_org_id,
        }
    }

    async def fake_dense_search(query_vector: list, collection_name: str, top_k: int = 10, org_id: Optional[str] = None):
        if collection_name == "grc_doc_chunks":
            return [fake_policy_hit]
        elif collection_name == "grc_iso_controls":
            return [fake_iso_hit]
        return []

    mock_vector_store = MagicMock()
    mock_vector_store.is_ready = True
    mock_vector_store.dense_search = AsyncMock(side_effect=fake_dense_search)

    with patch("app.services.vector_store.vector_store", mock_vector_store), \
         patch.object(service, "_embed_text", return_value=[0.1] * 768), \
         patch.object(service, "_categorize", return_value="technical"):

        result = await service.analyze_evidence_qdrant(
            text="Active Directory export showing Duo MFA enforcement for all 150 employees.",
            org_id=test_org_id,
        )

        assert result.category == "technical"
        assert result.internal_policy_match is not None
        assert result.internal_policy_match["found"] is True
        assert "Access Control Policy" in result.internal_policy_match["policy_title"]

        assert result.framework_control_match is not None
        assert result.framework_control_match["control_id"] == "A.9.4.2"

        assert result.two_tier_evaluation is not None
        assert "Evidence satisfies both internal policy" in result.two_tier_evaluation["gap_analysis"]

        # Ensure vector_store.dense_search was called for both collections
        calls = mock_vector_store.dense_search.call_args_list
        called_collections = [c.kwargs.get("collection_name") for c in calls]
        assert "grc_iso_controls" in called_collections
        assert "grc_doc_chunks" in called_collections


def test_baseline_policy_templates():
    """Ensure baseline policy templates exist with proper metadata and ISO mappings."""
    assert len(BASELINE_POLICY_TEMPLATES) == 3
    template_keys = [t["template_key"] for t in BASELINE_POLICY_TEMPLATES]
    assert "access_control" in template_keys
    assert "incident_response" in template_keys
    assert "data_protection" in template_keys

    for t in BASELINE_POLICY_TEMPLATES:
        assert len(t["mapped_controls"]) > 0
        content_func = t["generate_content"]
        rendered = content_func(
            org_name="Globex Corp",
            industry="Healthcare",
            infrastructure="AWS HIPAA Cloud",
            data_types="ePHI & PII",
        )
        assert "Globex Corp" in rendered
        assert "Healthcare" in rendered or "AWS HIPAA Cloud" in rendered or "ePHI & PII" in rendered


@pytest.mark.anyio
async def test_generate_starter_policies_service():
    """Verify generate_starter_policies orchestrates creation, persistence, and vector indexing."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    org_id = uuid4()
    user_id = uuid4()

    mock_vector_store = MagicMock()
    mock_vector_store.is_ready = True
    mock_vector_store.upsert_chunks = AsyncMock()

    fake_analysis = {
        "document_category": "policy",
        "implemented_controls": ["A.5.15"],
        "missing_controls": [],
        "security_practices": ["MFA enforcement"],
        "summary": "Sample summary",
    }

    with patch("app.services.policy_generator.vector_store", mock_vector_store), \
         patch("app.services.policy_generator.ai_service._embed_texts", side_effect=lambda texts: [[0.05] * 768] * len(texts)), \
         patch("app.services.policy_generator.ai_service._is_ready", True), \
         patch("app.services.policy_generator._run_document_analysis_async", new_callable=AsyncMock, return_value=fake_analysis):

        policies = await generate_starter_policies(
            db=mock_db,
            organization_id=org_id,
            user_id=user_id,
            org_name="Initech Technologies",
            industry="Fintech",
            infrastructure="Google Cloud Platform & Kubernetes",
            data_types="Customer Financial Records and PCI DSS Cardholder Data",
        )

        assert len(policies) == 3
        # Ensure db added records
        assert mock_db.add.call_count == 3
        assert mock_db.commit.called

        # Ensure vector store upsert was invoked with chunks stamped with org_id
        assert mock_vector_store.upsert_chunks.called
        upsert_calls = mock_vector_store.upsert_chunks.call_args_list
        assert len(upsert_calls) == 3
        for call in upsert_calls:
            chunks, embeddings = call.args
            assert len(chunks) > 0
            assert chunks[0].org_id == str(org_id)
            assert len(embeddings) == len(chunks)
