"""
Gap Analysis Service — Aggregates evidence, document analyses, and control data
to identify missing/weak controls and generate remediation tickets.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import models
from app.models.control_applicability import ControlImplementationStatus
from app.services.ai_service import ai_service

logger = logging.getLogger("grc.gap_analysis")

# Load ISO controls
_CONTROLS_PATH = Path(__file__).resolve().parents[2] / "data" / "iso27001-controls.json"
_ISO_CONTROLS: list[dict] = []
_ISO_CLAUSES: list[dict] = []

def _load_controls():
    global _ISO_CONTROLS, _ISO_CLAUSES
    if not _ISO_CONTROLS and _CONTROLS_PATH.exists():
        with open(_CONTROLS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _ISO_CONTROLS = data.get("controls", [])
        _ISO_CLAUSES = data.get("clauses", [])
_load_controls()

# Control lookup by annex ID
_CONTROLS_BY_ID = {c["id"]: c for c in _ISO_CONTROLS}


class GapItem:
    """Represents a single compliance gap under the 3-tier compliance model."""
    def __init__(
        self,
        control_annex: str,
        control_title: str,
        clause_id: str,
        severity: str,
        reason: str,
        compliance_state: str = "no_policy",  # satisfied, policy_evidence_mismatch, policy_too_vague, no_policy, no_evidence
        policy_title: Optional[str] = None,
        policy_excerpt: Optional[str] = None,
        policy_confidence: float = 0.0,
        mapping_status: str = "suggested",    # confirmed, manually_edited, suggested
        is_policy_confirmed: bool = True,
        mismatch_details: Optional[dict] = None,
        framework_control_id: Optional[UUID] = None,
        best_evidence_score: float = 0.0,
        current_status: str = "not_started",
    ):
        self.control_annex = control_annex
        self.control_title = control_title
        self.clause_id = clause_id
        self.severity = severity  # critical, high, medium, low
        self.reason = reason
        self.compliance_state = compliance_state
        self.policy_title = policy_title
        self.policy_excerpt = policy_excerpt
        self.policy_confidence = policy_confidence
        self.mapping_status = mapping_status
        self.is_policy_confirmed = is_policy_confirmed
        self.mismatch_details = mismatch_details
        self.framework_control_id = framework_control_id
        self.best_evidence_score = best_evidence_score
        self.current_status = current_status

    def to_dict(self) -> dict:
        return {
            "control_annex": self.control_annex,
            "control_title": self.control_title,
            "clause_id": self.clause_id,
            "severity": self.severity,
            "reason": self.reason,
            "compliance_state": self.compliance_state,
            "policy_title": self.policy_title,
            "policy_excerpt": self.policy_excerpt,
            "policy_confidence": self.policy_confidence,
            "mapping_status": self.mapping_status,
            "is_policy_confirmed": self.is_policy_confirmed,
            "mismatch_details": self.mismatch_details,
            "framework_control_id": str(self.framework_control_id) if self.framework_control_id else None,
            "best_evidence_score": self.best_evidence_score,
            "current_status": self.current_status,
        }


class GapReport:
    """Full gap analysis report with 3-tier governance metrics."""
    def __init__(self, total_controls: int, applicable_controls: int,
                 implemented: int, partially_implemented: int, missing: int,
                 gaps: list[GapItem], compliance_percentage: float):
        self.total_controls = total_controls
        self.applicable_controls = applicable_controls
        self.implemented = implemented
        self.partially_implemented = partially_implemented
        self.missing = missing
        self.gaps = gaps
        self.compliance_percentage = compliance_percentage

    def to_dict(self) -> dict:
        return {
            "total_controls": self.total_controls,
            "applicable_controls": self.applicable_controls,
            "implemented": self.implemented,
            "partially_implemented": self.partially_implemented,
            "missing": self.missing,
            "total_gaps": len(self.gaps),
            "compliance_percentage": self.compliance_percentage,
            "gaps": [g.to_dict() for g in self.gaps],
            "summary": {
                "critical": sum(1 for g in self.gaps if g.severity == "critical"),
                "high": sum(1 for g in self.gaps if g.severity == "high"),
                "medium": sum(1 for g in self.gaps if g.severity == "medium"),
                "low": sum(1 for g in self.gaps if g.severity == "low"),
                "no_policy": sum(1 for g in self.gaps if g.compliance_state == "no_policy"),
                "policy_evidence_mismatch": sum(1 for g in self.gaps if g.compliance_state == "policy_evidence_mismatch"),
                "policy_too_vague": sum(1 for g in self.gaps if g.compliance_state == "policy_too_vague"),
                "no_evidence": sum(1 for g in self.gaps if g.compliance_state == "no_evidence"),
                "satisfied": sum(1 for g in self.gaps if g.compliance_state == "satisfied"),
                "unconfirmed_policy_mappings": sum(1 for g in self.gaps if not g.is_policy_confirmed and g.policy_title is not None),
            },
        }


def _classify_severity(status: str, has_evidence: bool, criticality_multiplier: float = 1.0) -> str:
    """Classify gap severity based on implementation status, evidence, and asset criticality."""
    # Base severity mapping
    severity_order = ["low", "medium", "high", "critical"]
    base_idx = 0

    if status == "not_started" and not has_evidence:
        base_idx = 3 # critical
    elif status == "not_started" and has_evidence:
        base_idx = 2 # high
    elif status == "in_progress" and not has_evidence:
        base_idx = 2 # high
    elif status == "in_progress" and has_evidence:
        base_idx = 1 # medium
    else:
        base_idx = 0 # low

    # Adjust based on criticality multiplier
    # e.g. medium (1) * 1.5 -> high (2)
    new_idx = min(int(base_idx * criticality_multiplier), 3)
    return severity_order[new_idx]


async def generate_gap_report(db: AsyncSession, organization_id: UUID) -> GapReport:
    """
    Generate a comprehensive gap analysis report for an organization.
    
    Combines:
    - ControlApplicability records (what's tracked)
    - Evidence analysis (what's documented)
    - Document analysis results (what the AI found)
    """
    # 1. Get all applicability records
    ca_result = await db.execute(
        select(models.ControlApplicability)
        .where(models.ControlApplicability.organization_id == organization_id)
    )
    ca_records = {ca.control_annex: ca for ca in ca_result.scalars().all()}

    # 2. Get all evidence texts for AI gap detection
    evidence_result = await db.execute(
        select(models.Evidence)
        .where(models.Evidence.organization_id == organization_id)
    )
    evidence_list = evidence_result.scalars().all()
    evidence_texts = [
        f"{e.title}. {e.description}" for e in evidence_list 
        if e.title and e.description
    ]

    # 3. Get AI-based gap scores (which controls lack evidence coverage)
    ai_gaps = {}
    if ai_service.is_ready and evidence_texts:
        try:
            raw_gaps = await ai_service.get_compliance_gaps(evidence_texts, threshold=0.40)
            ai_gaps = {g["annex"]: g.get("best_match_score", 0) for g in raw_gaps}
        except Exception as e:
            logger.warning(f"AI gap analysis failed: {e}")

    # 4. Get document analysis results (differentiating internal_policy vs evidence)
    doc_result = await db.execute(
        select(models.DocumentAnalysis)
        .where(
            models.DocumentAnalysis.organization_id == organization_id,
            models.DocumentAnalysis.status == "completed",
        )
    )
    doc_analyses = doc_result.scalars().all()
    
    # Separate policies vs evidence documents
    policy_docs = [d for d in doc_analyses if getattr(d, "source_type", "evidence") in ("internal_policy", "policy")]
    evidence_docs = [d for d in doc_analyses if getattr(d, "source_type", "evidence") == "evidence"]
    org_has_policies = len(policy_docs) > 0

    # Build control-to-policy mapping aggregating all contributing chunks across policy docs
    policy_map: dict[str, dict] = {}
    for doc in policy_docs:
        mappings = doc.policy_control_mappings or []
        for m in mappings:
            annex = m.get("control_annex") or m.get("annex", "")
            status = m.get("mapping_status", "suggested")
            if not annex or status == "rejected":
                continue
            chunks = m.get("policy_chunks", [])
            conf = float(m.get("composite_confidence") or m.get("confidence", 0.0))
            is_confirmed = status in ("confirmed", "manually_edited")

            if annex not in policy_map:
                policy_map[annex] = {
                    "doc_id": doc.id,
                    "title": doc.file_name,
                    "mapping_status": status,
                    "is_confirmed": is_confirmed,
                    "confidence": conf,
                    "policy_chunks": list(chunks),
                    "text_snippets": [c.get("excerpt", "") for c in chunks] if chunks else ([doc.extracted_text[:400]] if doc.extracted_text else []),
                }
            else:
                # If existing mapping is unconfirmed and this one is confirmed, upgrade authority
                if is_confirmed and not policy_map[annex]["is_confirmed"]:
                    policy_map[annex]["mapping_status"] = status
                    policy_map[annex]["is_confirmed"] = True
                    policy_map[annex]["title"] = doc.file_name
                # Accumulate contributing chunks across policy docs
                if chunks:
                    policy_map[annex]["policy_chunks"].extend(chunks)
                    policy_map[annex]["text_snippets"].extend([c.get("excerpt", "") for c in chunks])
                policy_map[annex]["confidence"] = max(policy_map[annex]["confidence"], conf)

    # Build control-to-evidence mapping
    evidence_doc_map: dict[str, dict] = {}
    for doc in evidence_docs:
        controls = doc.implemented_controls or []
        for m in controls:
            annex = m.get("control_annex") or m.get("annex", "")
            conf = float(m.get("confidence", 0.0))
            if annex and (annex not in evidence_doc_map or conf > evidence_doc_map[annex]["confidence"]):
                evidence_doc_map[annex] = {
                    "doc_id": doc.id,
                    "title": doc.file_name,
                    "confidence": conf,
                    "excerpt": m.get("excerpt") or (doc.extracted_text[:400] if doc.extracted_text else ""),
                    "text": doc.extracted_text or "",
                }

    # 5. Get Assets and their risk mappings for criticality weighting
    assets_result = await db.execute(
        select(models.Asset)
        .where(models.Asset.organization_id == organization_id)
    )
    assets_list = assets_result.scalars().all()
    
    # Criticality mapping
    CRITICALITY_MAP = {
        models.AssetCriticality.low: 1.0,
        models.AssetCriticality.medium: 1.2,
        models.AssetCriticality.high: 1.5,
        models.AssetCriticality.critical: 2.0
    }

    control_criticality = {} # annex -> multiplier
    
    rc_result = await db.execute(
        select(models.RiskControlMapping, models.FrameworkControl.code)
        .join(models.FrameworkControl, models.RiskControlMapping.framework_control_id == models.FrameworkControl.id)
        .join(models.Risk, models.RiskControlMapping.risk_id == models.Risk.id)
        .where(models.Risk.organization_id == organization_id)
    )
    risk_controls = rc_result.all()
    
    for asset in assets_list:
        multiplier = CRITICALITY_MAP.get(asset.criticality, 1.2)
        for risk in asset.related_risks:
            for rc, annex in risk_controls:
                if rc.risk_id == risk.id and annex:
                    control_criticality[annex] = max(control_criticality.get(annex, 1.0), multiplier)

    # 6. Fetch FrameworkControl IDs to link them properly
    from app.models.framework_control import FrameworkControl
    fw_controls_res = await db.execute(select(FrameworkControl))
    all_fw_controls = fw_controls_res.scalars().all()
    fw_id_map = {c.code: c.id for c in all_fw_controls}

    # 7. Build gap report
    gaps = []
    implemented_count = 0
    partial_count = 0
    missing_count = 0
    applicable_count = 0

    for ctrl in _ISO_CONTROLS:
        annex = ctrl["id"]
        ca = ca_records.get(annex)
        
        # Skip not-applicable controls
        if ca and not ca.is_applicable:
            continue
        
        applicable_count += 1
        status = ca.status.value if ca else "not_started"
        
        # Determine policy & evidence presence
        policy_info = policy_map.get(annex)
        evidence_info = evidence_doc_map.get(annex)
        has_generic_evidence = (annex not in ai_gaps) or (evidence_info is not None)
        best_score = ai_gaps.get(annex, 100.0 if has_generic_evidence else 0.0)

        # 4-State Classification
        compliance_state = "no_policy"
        mismatch_details = None
        reason = ""
        is_policy_confirmed = policy_info.get("is_confirmed", False) if policy_info else False
        mapping_status = policy_info.get("mapping_status", "suggested") if policy_info else "suggested"

        if not org_has_policies:
            # Legacy / Graceful Fallback mode when org has not uploaded policies yet
            if has_generic_evidence:
                compliance_state = "satisfied"
                reason = "Evidence satisfies framework control requirement (legacy framework-only mode; no internal policies uploaded)."
            else:
                compliance_state = "no_evidence"
                reason = "Control has not been implemented and no supporting evidence was found."
        else:
            if not policy_info:
                # State 1: No internal policy addresses this control
                compliance_state = "no_policy"
                if has_generic_evidence:
                    reason = "Evidence exists, but no internal company policy governs or mandates this control."
                else:
                    reason = "No internal company policy document covers this control requirement."
            elif not has_generic_evidence:
                # State: Policy exists, but zero evidence
                compliance_state = "no_evidence"
                unconf_flag = " [Unconfirmed Mapping]" if not is_policy_confirmed else ""
                reason = f"Internal policy '{policy_info['title']}'{unconf_flag} exists, but no operational evidence was found to prove execution."
            else:
                # Multi-chunk Policy vs Evidence alignment evaluation
                policy_text_input = policy_info.get("text_snippets", [])
                evidence_text = evidence_info.get("text", "") if evidence_info else "\n\n".join(evidence_texts)
                
                alignment = ai_service.evaluate_policy_evidence_alignment(
                    policy_text=policy_text_input,
                    evidence_text=evidence_text,
                    control_title=ctrl["title"],
                    control_annex=annex,
                )
                
                compliance_state = alignment.get("compliance_state", "satisfied" if alignment.get("is_aligned") else "policy_evidence_mismatch")
                unconf_notice = " (Note: Based on unconfirmed AI policy mapping)" if not is_policy_confirmed else ""
                
                if compliance_state == "satisfied":
                    reason = f"Evidence satisfies internal policy '{policy_info['title']}' requirements for {ctrl['title']}.{unconf_notice}"
                elif compliance_state == "policy_too_vague":
                    mismatch_details = alignment
                    reason = f"Policy Too Vague: {alignment.get('mismatch_reason')}{unconf_notice}"
                else:
                    compliance_state = "policy_evidence_mismatch"
                    mismatch_details = alignment
                    reason = f"Policy-Evidence Mismatch: {alignment.get('mismatch_reason', 'Evidence does not satisfy internal policy rules.')}{unconf_notice}"

        # Classify implementation numbers
        if compliance_state == "satisfied" or status == "implemented":
            implemented_count += 1
            if status != "implemented" and compliance_state != "satisfied":
                pass
            else:
                continue
        elif status == "in_progress":
            partial_count += 1
        else:
            missing_count += 1

        # Determine severity
        severity = _classify_severity(
            status, 
            has_generic_evidence,
            control_criticality.get(annex, 1.0)
        )
        if compliance_state in ("policy_evidence_mismatch", "policy_too_vague"):
            severity = "high" if severity in ("low", "medium") else severity

        first_chunk_excerpt = policy_info["policy_chunks"][0].get("excerpt") if policy_info and policy_info.get("policy_chunks") else (policy_info.get("text_snippets", [""])[0] if policy_info else None)

        gaps.append(GapItem(
            control_annex=annex,
            control_title=ctrl["title"],
            clause_id=ctrl["clauseId"],
            severity=severity,
            reason=reason,
            compliance_state=compliance_state,
            policy_title=policy_info["title"] if policy_info else None,
            policy_excerpt=first_chunk_excerpt,
            policy_confidence=policy_info["confidence"] if policy_info else 0.0,
            mapping_status=mapping_status,
            is_policy_confirmed=is_policy_confirmed,
            mismatch_details=mismatch_details,
            framework_control_id=fw_id_map.get(annex),
            best_evidence_score=best_score,
            current_status=status,
        ))

    # Sort gaps by severity (critical first)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps.sort(key=lambda g: severity_order.get(g.severity, 99))

    compliance_pct = 0.0
    if applicable_count > 0:
        compliance_pct = int((implemented_count / applicable_count * 1000)) / 10.0

    return GapReport(
        total_controls=len(_ISO_CONTROLS),
        applicable_controls=applicable_count,
        implemented=implemented_count,
        partially_implemented=partial_count,
        missing=missing_count,
        gaps=gaps,
        compliance_percentage=compliance_pct,
    )


async def create_tickets_from_gaps(
    db: AsyncSession,
    organization_id: UUID,
    created_by: models.User,
    gap_annexes: Optional[list[str]] = None,
    max_tickets: int = 20,
) -> list[dict]:
    """
    Create remediation tickets from gap findings.
    
    Args:
        gap_annexes: Specific control annexes to create tickets for.
                     If None, creates tickets for all critical+high gaps.
        max_tickets: Maximum number of tickets to create in one batch.
    """
    from app.services import audit_service
    from app.models.audit_log import AuditAction, AuditEntityType
    from app.models.ticket import TicketPriority, TicketStatus, TicketCategory

    report = await generate_gap_report(db, organization_id)
    
    # Filter gaps
    if gap_annexes:
        target_gaps = [g for g in report.gaps if g.control_annex in gap_annexes]
    else:
        target_gaps = [g for g in report.gaps if g.severity in ("critical", "high")]
    
    target_gaps = target_gaps[:max_tickets]
    
    created_tickets = []
    
    for gap in target_gaps:
        # Check if ticket already exists for this control
        existing = await db.execute(
            select(models.Ticket).where(
                models.Ticket.organization_id == organization_id,
                models.Ticket.title.contains(gap.control_annex),
                models.Ticket.status.notin_([
                    TicketStatus.resolved,
                    TicketStatus.closed,
                ]),
            )
        )
        if existing.scalars().first():
            continue  # Skip — active ticket already exists

        # Map severity to ticket priority
        priority_map = {
            "critical": TicketPriority.critical,
            "high": TicketPriority.high,
            "medium": TicketPriority.medium,
            "low": TicketPriority.low,
        }
        
        # Create audit log first (required FK for ticket)
        audit_log = await audit_service.log_action(
            db=db,
            user=created_by,
            action=AuditAction.created,
            entity_type=AuditEntityType.compliance_item,
            entity_id=organization_id,
            entity_name=f"Gap: {gap.control_annex}",
            description=f"Gap analysis ticket created for control {gap.control_annex}: {gap.control_title}",
        )
        await db.flush()
        
        ticket = models.Ticket(
            title=f"[{gap.control_annex}] {gap.control_title} — Gap Remediation",
            description=(
                f"**Gap Analysis Finding**\n\n"
                f"**Control:** {gap.control_annex} — {gap.control_title}\n"
                f"**Severity:** {gap.severity.upper()}\n"
                f"**Current Status:** {gap.current_status}\n"
                f"**Reason:** {gap.reason}\n\n"
                f"**Required Action:** Implement this control and upload supporting evidence."
            ),
            priority=priority_map.get(gap.severity, TicketPriority.medium),
            status=TicketStatus.open,
            category=TicketCategory.compliance_gap,
            source_audit_log_id=audit_log.id,
            assigned_to_id=created_by.id,
            assigned_to_role="Analyst",
            organization_id=organization_id,
            created_by=created_by.id,
            framework_control_id=gap.framework_control_id,
        )
        db.add(ticket)
        await db.flush()
        
        created_tickets.append({
            "ticket_id": str(ticket.id),
            "control_annex": gap.control_annex,
            "control_title": gap.control_title,
            "severity": gap.severity,
            "priority": ticket.priority.value,
        })
    
    await db.commit()
    
    logger.info(f"Created {len(created_tickets)} remediation tickets from gap analysis")
    return created_tickets
