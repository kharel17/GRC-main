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
    """Represents a single compliance gap."""
    def __init__(self, control_annex: str, control_title: str, clause_id: str,
                 severity: str, reason: str, best_evidence_score: float = 0.0,
                 current_status: str = "not_started"):
        self.control_annex = control_annex
        self.control_title = control_title
        self.clause_id = clause_id
        self.severity = severity  # critical, high, medium, low
        self.reason = reason
        self.best_evidence_score = best_evidence_score
        self.current_status = current_status

    def to_dict(self) -> dict:
        return {
            "control_annex": self.control_annex,
            "control_title": self.control_title,
            "clause_id": self.clause_id,
            "severity": self.severity,
            "reason": self.reason,
            "best_evidence_score": self.best_evidence_score,
            "current_status": self.current_status,
        }


class GapReport:
    """Full gap analysis report."""
    def __init__(self, total_controls: int, applicable_controls: int,
                 implemented: int, gaps: list[GapItem], 
                 compliance_percentage: float):
        self.total_controls = total_controls
        self.applicable_controls = applicable_controls
        self.implemented = implemented
        self.gaps = gaps
        self.compliance_percentage = compliance_percentage

    def to_dict(self) -> dict:
        return {
            "total_controls": self.total_controls,
            "applicable_controls": self.applicable_controls,
            "implemented": self.implemented,
            "total_gaps": len(self.gaps),
            "compliance_percentage": self.compliance_percentage,
            "gaps": [g.to_dict() for g in self.gaps],
            "summary": {
                "critical": sum(1 for g in self.gaps if g.severity == "critical"),
                "high": sum(1 for g in self.gaps if g.severity == "high"),
                "medium": sum(1 for g in self.gaps if g.severity == "medium"),
                "low": sum(1 for g in self.gaps if g.severity == "low"),
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
            raw_gaps = ai_service.get_compliance_gaps(evidence_texts, threshold=0.40)
            ai_gaps = {g["annex"]: g.get("best_match_score", 0) for g in raw_gaps}
        except Exception as e:
            logger.warning(f"AI gap analysis failed: {e}")

    # 4. Get document analysis results
    doc_result = await db.execute(
        select(models.DocumentAnalysis)
        .where(
            models.DocumentAnalysis.organization_id == organization_id,
            models.DocumentAnalysis.status == "completed",
        )
    )
    doc_analyses = doc_result.scalars().all()
    
    # Build set of controls found in document analyses
    implemented_by_docs = set()
    for doc in doc_analyses:
        if doc.implemented_controls:
            for ctrl in doc.implemented_controls:
                annex = ctrl.get("control_annex", "")
                if annex:
                    implemented_by_docs.add(annex)

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

    # Map controls to their highest asset criticality
    # For now, we look at risks associated with the control, then assets associated with the risk
    control_criticality = {} # annex -> multiplier
    
    # Get all risk-control mappings to link annex IDs to assets
    rc_result = await db.execute(
        select(models.RiskControlMapping, models.Control.control_annex)
        .join(models.Control, models.RiskControlMapping.control_id == models.Control.id)
        .where(models.Control.organization_id == organization_id)
    )
    risk_controls = rc_result.all()
    
    for asset in assets_list:
        multiplier = CRITICALITY_MAP.get(asset.criticality, 1.2)
        # Find risks associated with this asset via related_risks relationship (loaded via selectin)
        for risk in asset.related_risks:
            # Find controls associated with this risk
            for rc, annex in risk_controls:
                if rc.risk_id == risk.id and annex:
                    control_criticality[annex] = max(control_criticality.get(annex, 1.0), multiplier)

    # 6. Build gap report
    gaps = []
    implemented_count = 0
    applicable_count = 0

    for ctrl in _ISO_CONTROLS:
        annex = ctrl["id"]
        ca = ca_records.get(annex)
        
        # Skip not-applicable controls
        if ca and not ca.is_applicable:
            continue
        
        applicable_count += 1
        status = ca.status.value if ca else "not_started"
        
        if status == "implemented":
            implemented_count += 1
            continue

        # This control is a gap
        has_evidence = annex not in ai_gaps
        in_doc_analysis = annex in implemented_by_docs
        best_score = ai_gaps.get(annex, 100.0 if has_evidence else 0.0)
        
        severity = _classify_severity(
            status, 
            has_evidence or in_doc_analysis,
            control_criticality.get(annex, 1.0)
        )
        
        if status == "not_started":
            reason = "Control has not been started"
            if not has_evidence and not in_doc_analysis:
                reason += " and no supporting evidence or documentation found"
        elif status == "in_progress":
            reason = "Control is in progress but not yet fully implemented"
            if not has_evidence:
                reason += " — no supporting evidence found"
        else:
            reason = f"Control status: {status}"

        gaps.append(GapItem(
            control_annex=annex,
            control_title=ctrl["title"],
            clause_id=ctrl["clauseId"],
            severity=severity,
            reason=reason,
            best_evidence_score=best_score,
            current_status=status,
        ))

    # Sort gaps by severity (critical first)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps.sort(key=lambda g: severity_order.get(g.severity, 99))

    compliance_pct = round((implemented_count / applicable_count * 100), 1) if applicable_count > 0 else 0

    return GapReport(
        total_controls=len(_ISO_CONTROLS),
        applicable_controls=applicable_count,
        implemented=implemented_count,
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
            entity_type=AuditEntityType.compliance,
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
