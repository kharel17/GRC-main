"""
AI Service - Data Models & Constants.

Shared data classes and keyword dictionaries used across the AI subsystem.
Extracted from ai_service.py for Single Responsibility.
"""

from typing import Optional
import numpy as np


# ---------------------------------------------------------------------------
# Data classes for AI results
# ---------------------------------------------------------------------------

class ControlMatch:
    """Represents a single AI-matched ISO 27001 control."""
    def __init__(self, control_id: str, annex: str, title: str, description: str,
                 clause_id: str, confidence: float):
        self.control_id = control_id
        self.annex = annex
        self.title = title
        self.description = description
        self.clause_id = clause_id
        self.confidence = round(confidence * 100, 1)  # 0-100 percentage

    def to_dict(self) -> dict:
        return {
            "control_id": self.control_id,
            "annex": self.annex,
            "title": self.title,
            "description": self.description,
            "clause_id": self.clause_id,
            "confidence": self.confidence,
        }


class EvidenceAnalysisResult:
    """Full result of analyzing an evidence document with optional two-tier policy evaluation."""
    def __init__(
        self,
        category: str,
        matched_controls: list[ControlMatch],
        summary: str,
        internal_policy_match: Optional[dict] = None,
        framework_control_match: Optional[dict] = None,
        two_tier_evaluation: Optional[dict] = None,
    ):
        self.category = category
        self.matched_controls = matched_controls
        self.summary = summary
        self.internal_policy_match = internal_policy_match
        self.framework_control_match = framework_control_match
        self.two_tier_evaluation = two_tier_evaluation

    def to_dict(self) -> dict:
        data = {
            "category": self.category,
            "matched_controls": [m.to_dict() for m in self.matched_controls],
            "summary": self.summary,
        }
        if self.internal_policy_match is not None:
            data["internal_policy_match"] = self.internal_policy_match
        if self.framework_control_match is not None:
            data["framework_control_match"] = self.framework_control_match
        if self.two_tier_evaluation is not None:
            data["two_tier_evaluation"] = self.two_tier_evaluation
        return data


class DocumentAnalysisAIResult:
    """Full AI analysis of a security document for Step 3."""
    def __init__(self, summary: str, category: str, 
                 implemented_controls: list[dict], 
                 missing_controls: list[dict], 
                 security_practices: list[dict]):
        self.summary = summary
        self.category = category
        self.implemented_controls = implemented_controls
        self.missing_controls = missing_controls
        self.security_practices = security_practices

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "category": self.category,
            "implemented_controls": self.implemented_controls,
            "missing_controls": self.missing_controls,
            "security_practices": self.security_practices
        }


class RiskSuggestion:
    """AI-suggested risk scoring."""
    def __init__(self, likelihood: int, impact: int, risk_score: int,
                 reasoning: str, related_controls: list[str]):
        self.likelihood = likelihood
        self.impact = impact
        self.risk_score = risk_score
        self.reasoning = reasoning
        self.related_controls = related_controls

    def to_dict(self) -> dict:
        return {
            "likelihood": self.likelihood,
            "impact": self.impact,
            "risk_score": self.risk_score,
            "reasoning": self.reasoning,
            "related_controls": self.related_controls,
        }


# ---------------------------------------------------------------------------
# Evidence category keywords (used by both engines)
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "policy": ["policy", "policies", "guideline", "framework", "standard", "directive"],
    "procedure": ["procedure", "process", "workflow", "step-by-step", "instruction", "sop"],
    "log": ["log", "audit trail", "event", "syslog", "access log", "monitoring"],
    "certificate": ["certificate", "certification", "accreditation", "iso", "soc", "attestation"],
    "report": ["report", "assessment", "review", "analysis", "finding", "summary"],
    "training": ["training", "awareness", "education", "course", "workshop", "session"],
    "contract": ["contract", "agreement", "nda", "sla", "terms", "vendor", "supplier"],
    "configuration": ["configuration", "config", "settings", "baseline", "hardening", "firewall"],
}


# Domain synonyms and cross-standard terminology to resolve sub-clause ambiguity
ISO_DOMAIN_SYNONYMS: dict[str, str] = {
    "7.1": "Physical security perimeters, biometric access control and CCTV monitoring of server room perimeters, physical perimeter boundaries, surveillance.",
    "7.2": "Physical entry controls, building doors, entry keycards, visitor badge reception, turnstiles.",
    "7.13": "Equipment maintenance, server hardware maintenance outsourced to certified vendor, hardware servicing.",
    "5.15": "Access control policy, role-based access control, RBAC, access restrictions.",
    "5.17": "Authentication information, user password complexity rules, secret authentication credentials, password requirements.",
    "5.24": "Incident management planning, security incident response procedure, incident reporting timelines.",
    "5.29": "Information security during disruption, business continuity, disaster recovery quarterly drills, continuity testing.",
    "6.1": "Screening, pre-employment background screening, HR security, background check verification.",
    "6.5": "Responsibilities after termination or change of employment, contractors signing confidentiality agreements upon offboarding, NDAs.",
    "6.6": "Confidentiality or non-disclosure agreements, NDAs, contractor confidentiality.",
    "8.5": "Secure authentication, password complexity, multi-factor authentication MFA, login credentials.",
    "8.8": "Management of technical vulnerabilities, automated vulnerability scanning frequency, patch management windows.",
    "8.15": "Logging, audit logging, system activity logs, event recording.",
    "8.16": "Monitoring activities, SIEM system aggregates events from firewalls and triggers alerts on abnormal behavior, network monitoring.",
    "8.22": "Web filtering, network isolation, AWS security groups isolating test environments, segmenting environments.",
    "8.24": "Use of cryptography, cryptographic key management rules, encryption algorithms, data encryption at rest and in transit.",
    "8.25": "Secure development life cycle, developers receive secure coding certification, SDLC guidelines.",
    "8.28": "Secure coding, developers review pull requests and verify code security before merging, peer code review.",
    "8.31": "Separation of development, test and production environments, AWS security groups isolation.",
    "8.32": "Change management, system administrators use Git repositories to track infrastructure-as-code version changes, PR approvals.",
}
