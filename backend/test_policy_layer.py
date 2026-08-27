"""
Comprehensive Test Suite for 3-Tier Governance & Compliance Architecture:
Universal Framework (ISO 27001) -> Internal Policy (Multi-Chunk & Human-Confirmed) -> Evidence
"""
import unittest
import asyncio
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.config import settings
from app.ingestion.chunker import chunk_document, Chunk
from app.ingestion.extractor import PageContent
from app.services.ai_service import ai_service
from app.services.gap_analysis_service import GapItem, GapReport, _classify_severity


class TestPolicyLayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ai_service.is_ready:
            ai_service.initialize()

    def test_chunker_source_type_tagging(self):
        """Verify chunker attaches explicit source_type to each chunk."""
        pages = [PageContent(page_number=1, raw_text="# Access Control Policy\nAll users must use MFA and 14-char passwords.")]
        
        # 1. Policy chunking
        policy_chunks = chunk_document(
            pages=pages,
            document_id="doc-123",
            org_id="org-123",
            source_type="internal_policy",
        )
        self.assertGreater(len(policy_chunks), 0)
        self.assertEqual(policy_chunks[0].source_type, "internal_policy")
        
        # 2. Evidence chunking
        evidence_chunks = chunk_document(
            pages=pages,
            document_id="doc-456",
            org_id="org-123",
            source_type="evidence",
        )
        self.assertGreater(len(evidence_chunks), 0)
        self.assertEqual(evidence_chunks[0].source_type, "evidence")

    def test_multi_chunk_policy_mapping(self):
        """Verify mapping multiple policy chunks into aggregated control mappings."""
        chunks = [
            Chunk(
                chunk_id="c-001",
                document_id="doc-p1",
                org_id="org-test",
                page_number=1,
                section_heading="Section 4.1 Password Rules",
                chunk_index=0,
                text="Access control policy mandates 14 character passwords with special characters and uppercase letters.",
                token_count=20,
                source_type="internal_policy",
            ),
            Chunk(
                chunk_id="c-002",
                document_id="doc-p1",
                org_id="org-test",
                page_number=2,
                section_heading="Section 4.2 Multi-Factor Authentication",
                chunk_index=1,
                text="Multi-factor authentication (MFA) is required for all administrative access and remote SSH sessions.",
                token_count=20,
                source_type="internal_policy",
            ),
        ]
        
        mappings = ai_service.map_policy_chunks_to_controls(
            chunks=chunks,
            threshold=settings.POLICY_MATCH_THRESHOLD,
        )
        
        self.assertGreater(len(mappings), 0)
        first_map = mappings[0]
        self.assertIn("control_annex", first_map)
        self.assertIn("policy_chunks", first_map)
        self.assertEqual(first_map["mapping_status"], "suggested")
        self.assertIsNone(first_map["confirmed_by"])
        self.assertGreater(len(first_map["policy_chunks"]), 0)

    def test_policy_evidence_alignment_satisfied(self):
        """Test Case: Evidence strictly complies with the internal company policy."""
        policy_texts = [
            "Access Control Policy: Multi-factor authentication (MFA) is mandatory for all administrative access.",
            "Password Standards: Minimum password length is 14 characters with 90-day rotation.",
        ]
        evidence_text = "Okta IAM Configuration: MFA required for all admins. Minimum password length = 16 characters. Password rotation = 90 days."
        
        result = ai_service.evaluate_policy_evidence_alignment(
            policy_text=policy_texts,
            evidence_text=evidence_text,
            control_title="Access Control & Authentication",
            control_annex="5.17",
        )
        
        self.assertTrue(result["is_aligned"], f"Expected aligned but got: {result}")
        self.assertEqual(result["compliance_state"], "satisfied")
        self.assertIsNone(result["mismatch_reason"])
        self.assertGreaterEqual(result["confidence"], 35.0)

    def test_policy_evidence_alignment_mismatch_password_length(self):
        """Test Case: Policy-Evidence Mismatch (Policy requires 14 chars, evidence config shows 8 chars)."""
        policy_text = "Corporate Password Policy: All employee passwords must have a minimum password length of 14 characters."
        evidence_text = "Active Directory Default Domain Policy: Minimum password length: 8 characters. Complexity enabled."
        
        result = ai_service.evaluate_policy_evidence_alignment(
            policy_text=policy_text,
            evidence_text=evidence_text,
            control_title="Authentication Information",
            control_annex="5.17",
        )
        
        self.assertFalse(result["is_aligned"])
        self.assertEqual(result["compliance_state"], "policy_evidence_mismatch")
        self.assertIsNotNone(result["mismatch_reason"])
        self.assertIn("14", result["mismatch_reason"])
        self.assertIn("8", result["mismatch_reason"])

    def test_policy_evidence_alignment_mismatch_mfa_disabled(self):
        """Test Case: Policy-Evidence Mismatch (Policy mandates MFA, evidence config shows MFA disabled)."""
        policy_text = "Information Security Policy: MFA required for all remote access and cloud consoles."
        evidence_text = "VPN Configuration Report: remote_access_gateway, mfa: disabled, auth_type: pap."
        
        result = ai_service.evaluate_policy_evidence_alignment(
            policy_text=policy_text,
            evidence_text=evidence_text,
            control_title="Access Control",
            control_annex="5.15",
        )
        
        self.assertFalse(result["is_aligned"])
        self.assertEqual(result["compliance_state"], "policy_evidence_mismatch")
        self.assertIsNotNone(result["mismatch_reason"])
        self.assertIn("MFA", result["mismatch_reason"])

    def test_gated_vagueness_detection(self):
        """Test Case: Policy Too Vague (Subjective boilerplate with zero auditable metrics)."""
        vague_policy = "Security Policy: We take appropriate measures and reasonable steps to ensure good security for company systems as deemed necessary."
        evidence_text = "Firewall ruleset version 12.4 active with default deny."
        
        result = ai_service.evaluate_policy_evidence_alignment(
            policy_text=vague_policy,
            evidence_text=evidence_text,
            control_title="Information Security Management",
            control_annex="5.1",
        )
        
        self.assertFalse(result["is_aligned"])
        self.assertEqual(result["compliance_state"], "policy_too_vague")
        self.assertIsNotNone(result["mismatch_reason"])
        self.assertIn("appropriate measures", result["mismatch_reason"].lower())
        self.assertIsNotNone(result["cited_excerpt"])

    def test_gap_item_four_states_serialization(self):
        """Test GapItem properly serializes 4 states, policy confirmation flags, and summary counts."""
        # 1. State: no_policy
        g1 = GapItem(
            control_annex="5.1",
            control_title="Policies for information security",
            clause_id="5.1",
            severity="high",
            reason="No internal company policy document covers this control requirement.",
            compliance_state="no_policy",
        )
        d1 = g1.to_dict()
        self.assertEqual(d1["compliance_state"], "no_policy")
        self.assertIsNone(d1["policy_title"])

        # 2. State: policy_evidence_mismatch
        g2 = GapItem(
            control_annex="5.17",
            control_title="Authentication information",
            clause_id="5.17",
            severity="high",
            reason="Policy-Evidence Mismatch: Policy requires 14 chars, evidence config shows 8 chars.",
            compliance_state="policy_evidence_mismatch",
            policy_title="Access_Policy_2026.pdf",
            policy_confidence=88.5,
            mapping_status="confirmed",
            is_policy_confirmed=True,
            mismatch_details={"is_aligned": False, "mismatch_reason": "Policy requires 14 chars, evidence config shows 8 chars."},
        )
        d2 = g2.to_dict()
        self.assertEqual(d2["compliance_state"], "policy_evidence_mismatch")
        self.assertEqual(d2["mapping_status"], "confirmed")
        self.assertTrue(d2["is_policy_confirmed"])

        # 3. State: policy_too_vague
        g3 = GapItem(
            control_annex="8.1",
            control_title="User endpoint devices",
            clause_id="8.1",
            severity="high",
            reason="Policy Too Vague: Policy uses subjective boilerplate without actionable criteria.",
            compliance_state="policy_too_vague",
            policy_title="Endpoint_Guidelines.pdf",
            policy_confidence=75.0,
            mapping_status="suggested",
            is_policy_confirmed=False,
        )
        d3 = g3.to_dict()
        self.assertEqual(d3["compliance_state"], "policy_too_vague")
        self.assertFalse(d3["is_policy_confirmed"])

        # 4. State: satisfied
        g4 = GapItem(
            control_annex="8.24",
            control_title="Use of cryptography",
            clause_id="8.24",
            severity="low",
            reason="Evidence satisfies internal policy requirements.",
            compliance_state="satisfied",
            policy_title="Cryptography_Policy.pdf",
            policy_confidence=92.0,
            mapping_status="confirmed",
            is_policy_confirmed=True,
        )
        d4 = g4.to_dict()
        self.assertEqual(d4["compliance_state"], "satisfied")

        # Test GapReport summary counts
        report = GapReport(
            total_controls=93,
            applicable_controls=93,
            implemented=1,
            partially_implemented=1,
            missing=2,
            gaps=[g1, g2, g3, g4],
            compliance_percentage=25.0,
        )
        rep_dict = report.to_dict()
        self.assertEqual(rep_dict["summary"]["no_policy"], 1)
        self.assertEqual(rep_dict["summary"]["policy_evidence_mismatch"], 1)
        self.assertEqual(rep_dict["summary"]["policy_too_vague"], 1)
        self.assertEqual(rep_dict["summary"]["satisfied"], 1)
        self.assertEqual(rep_dict["summary"]["unconfirmed_policy_mappings"], 1)


if __name__ == "__main__":
    unittest.main()
