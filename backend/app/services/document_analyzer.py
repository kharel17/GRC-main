"""
Document Analysis Pipeline Functions.

Extracted from ai_service.py – provides the canonical async document analysis
entry point and security practice extraction used by the ingestion pipeline
and API routes.
"""

import logging

from typing import Optional

from app.services.ai_models import (
    CATEGORY_KEYWORDS,
)

logger = logging.getLogger("grc.ai")


async def _run_document_analysis_async(
    text: str,
    org_id: Optional[str] = None,
    current_doc_id: Optional[str] = None,
) -> dict:
    """Async Qdrant-backed document analysis pipeline.

    This is the canonical entry point for the ingestion pipeline and all API
    routes. It uses Qdrant as the primary source of truth for control
    similarity and falls back to the in-memory path when Qdrant is offline.

    Returns a dict with the same schema as the legacy ``_run_document_analysis``.
    """
    # Lazy import to avoid circular dependency with ai_service singleton
    from app.services.ai_service import ai_service

    if not ai_service.is_ready:
        ai_service.initialize()

    category = ai_service._categorize(text)
    evidence_result = await ai_service.analyze_evidence_qdrant(
        text,
        top_n=93,
        threshold=0.30,
        org_id=org_id,
        current_doc_id=current_doc_id,
    )

    implemented = []
    weak_matches = []

    for match in evidence_result.matched_controls:
        item = {
            "control_annex": match.annex,
            "title": match.title,
            "confidence": match.confidence,
            "clause_id": match.clause_id,
        }
        if match.confidence >= 50:
            implemented.append(item)
        elif match.confidence >= 30:
            weak_matches.append(item)

    # Sort for deterministic output — confidence descending, annex ascending on ties
    implemented.sort(key=lambda x: (-x["confidence"], x["control_annex"]))
    weak_matches.sort(key=lambda x: (-x["confidence"], x["control_annex"]))

    matched_annexes = {m.annex for m in evidence_result.matched_controls}
    missing = []
    for ctrl in ai_service._controls:
        if ctrl["annex"] not in matched_annexes:
            missing.append({
                "control_annex": ctrl["annex"],
                "title": ctrl["title"],
                "reason": "No reference found in document",
            })

    practices = _extract_security_practices(text)

    return {
        "document_category": category,
        "summary": evidence_result.summary,
        "implemented_controls": implemented,
        "weak_matches": weak_matches,
        "missing_controls": missing,
        "security_practices": practices,
        "total_controls_checked": len(ai_service._controls),
        "strong_matches": len(implemented),
        "weak_match_count": len(weak_matches),
        "missing_count": len(missing),
    }


def _extract_security_practices(text: str) -> list[dict]:
    """Extract security practices by scanning for key phrases."""
    text_lower = text.lower()
    
    practice_patterns = {
        "Multi-factor authentication": (["mfa", "multi-factor", "two-factor", "2fa"], ["5.17", "8.5"]),
        "Access control policy": (["access control", "role-based access", "rbac", "least privilege"], ["5.15", "5.18", "8.2"]),
        "Data encryption": (["encryption", "encrypted", "aes", "tls", "ssl", "cryptograph"], ["8.24"]),
        "Security awareness training": (["security training", "awareness program", "security awareness"], ["6.3"]),
        "Incident response": (["incident response", "incident management", "security incident"], ["5.24", "5.25", "5.26"]),
        "Backup procedures": (["backup", "data backup", "recovery point"], ["8.13"]),
        "Change management": (["change management", "change control", "change request"], ["8.32"]),
        "Vulnerability management": (["vulnerability scan", "penetration test", "vulnerability management"], ["8.8"]),
        "Network security": (["firewall", "network segmentation", "intrusion detection", "ids", "ips"], ["8.20", "8.21", "8.22"]),
        "Logging and monitoring": (["audit log", "event log", "monitoring", "siem"], ["8.15", "8.16"]),
        "Password policy": (["password policy", "password complexity", "password rotation"], ["5.17"]),
        "Data classification": (["data classification", "information classification", "labeling"], ["5.12", "5.13"]),
        "Business continuity": (["business continuity", "disaster recovery", "bcp", "drp"], ["5.29", "5.30"]),
        "Secure development": (["secure development", "sdlc", "secure coding", "code review"], ["8.25", "8.28"]),
        "Supplier management": (["vendor management", "supplier assessment", "third-party"], ["5.19", "5.20", "5.21"]),
    }
    
    found_practices = []
    for practice_name, (keywords, related_controls) in practice_patterns.items():
        if any(kw in text_lower for kw in keywords):
            found_practices.append({
                "practice": practice_name,
                "related_controls": related_controls,
            })
    
    return found_practices
