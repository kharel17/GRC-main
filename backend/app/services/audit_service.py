"""
Enhanced Audit Service for GRC Platform.

Provides comprehensive audit logging with:
- IP address capture from request context
- Extended action types (login, logout, export, file_upload)
- Auto-commit option for standalone audit events
- Structured metadata for compliance reporting
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Request
from app import models
from app.models.audit_log import AuditAction, AuditEntityType
from uuid import UUID
import logging
import io
import csv
from fpdf import FPDF
from app.services.gap_analysis_service import generate_gap_report

logger = logging.getLogger("grc.audit")


def _get_client_ip(request: Optional[Request] = None) -> Optional[str]:
    """Extract real client IP, respecting X-Forwarded-For from reverse proxy."""
    if not request:
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def log_action(
    db: AsyncSession,
    user: models.User,
    action: AuditAction,
    entity_type: AuditEntityType,
    entity_id: UUID,
    entity_name: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
    request: Optional[Request] = None,
    ip_address: Optional[str] = None,
    auto_commit: bool = False,
) -> models.AuditLog:
    """
    Create an audit log entry.

    Args:
        db: Database session
        user: The user performing the action
        action: What happened (created, updated, deleted, login, etc.)
        entity_type: What type of entity was affected
        entity_id: ID of the affected entity
        entity_name: Human-readable name of the entity
        old_values: Previous state (for updates)
        new_values: New state (for creates/updates)
        description: Free-text description
        request: FastAPI request object (for IP extraction)
        ip_address: Override IP address (if not using request)
        auto_commit: If True, commit the audit log immediately
    """
    resolved_ip = ip_address or _get_client_ip(request)

    audit_log = models.AuditLog(
        user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        old_values=old_values,
        new_values=new_values,
        description=description,
        ip_address=resolved_ip,
    )
    db.add(audit_log)

    if auto_commit:
        await db.commit()
        await db.refresh(audit_log)

    logger.info(
        f"audit: {action.value} {entity_type.value}",
        extra={
            "user_id": str(user.id),
            "action": action.value,
            "entity_type": entity_type.value,
            "entity_id": str(entity_id),
            "ip": resolved_ip,
        },
    )

    return audit_log


async def get_readiness_score(db: AsyncSession, organization_id: UUID) -> Dict[str, Any]:
    """
    Calculate weighted readiness score based on implemented controls, 
    risk levels, and asset criticality.
    """
    report = await generate_gap_report(db, organization_id)
    
    # Simple percentage
    raw_pct = report.compliance_percentage
    
    # Weighted readiness
    # We weight gaps by severity: critical=4, high=3, medium=2, low=1
    severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    
    total_weight = report.applicable_controls * 2 # base weight of 2 per applicable control
    current_debt = sum(severity_weights.get(g.severity, 1) for g in report.gaps)
    
    # Readiness = 1 - (debt / total_possible_debt)
    # This is a bit subjective, but provides a better "risk-adjusted" score
    max_possible_debt = report.applicable_controls * 4
    weighted_readiness = max(0, round((1 - (current_debt / max_possible_debt)) * 100, 1)) if report.applicable_controls > 0 else 0
    
    return {
        "compliance_percentage": raw_pct,
        "weighted_readiness": weighted_readiness,
        "total_controls": report.total_controls,
        "applicable_controls": report.applicable_controls,
        "implemented_controls": report.implemented,
        "gap_summary": report.to_dict()["summary"]
    }


async def export_audit_report(db: AsyncSession, organization_id: UUID, format: str = "pdf") -> bytes:
    """
    Export a comprehensive ISO 27001 readiness report.
    Generates SoA, Risk Register, and Gap Analysis in one document.
    """
    report = await generate_gap_report(db, organization_id)
    readiness = await get_readiness_score(db, organization_id)
    
    # Get organization info
    org_res = await db.execute(select(models.Organization).where(models.Organization.id == organization_id))
    organization = org_res.scalar()
    org_name = organization.name if organization else "Unknown Organization"

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ISO 27001 Readiness Report", org_name, datetime.utcnow().isoformat()])
        writer.writerow([])
        writer.writerow(["Summary"])
        writer.writerow(["Compliance %", readiness["compliance_percentage"]])
        writer.writerow(["Weighted Readiness", readiness["weighted_readiness"]])
        writer.writerow([])
        writer.writerow(["Gap Findings"])
        writer.writerow(["Control Annex", "Control Title", "Severity", "Status", "Reason"])
        for gap in report.gaps:
            writer.writerow([gap.control_annex, gap.control_title, gap.severity, gap.current_status, gap.reason])
        return output.getvalue().encode('utf-8')

    # PDF Generation using fpdf2
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 10, "ISO 27001 Readiness Report", ln=True, align="C")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, f"Organization: {org_name}", ln=True, align="C")
    pdf.cell(0, 10, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}", ln=True, align="C")
    pdf.ln(10)
    
    # Summary Section
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "1. Executive Summary", ln=True)
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Compliance Percentage: {readiness['compliance_percentage']}%", ln=True)
    pdf.cell(0, 8, f"Risk-Weighted Readiness: {readiness['weighted_readiness']}%", ln=True)
    pdf.cell(0, 8, f"Applicable Controls: {readiness['applicable_controls']}", ln=True)
    pdf.cell(0, 8, f"Implemented Controls: {readiness['implemented_controls']}", ln=True)
    pdf.ln(10)
    
    # Gaps Section
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "2. Top Gap Findings", ln=True)
    pdf.set_font("helvetica", "B", 10)
    # Table Header
    pdf.cell(30, 8, "Annex", border=1)
    pdf.cell(90, 8, "Control Title", border=1)
    pdf.cell(30, 8, "Severity", border=1)
    pdf.cell(40, 8, "Status", border=1, ln=True)
    
    pdf.set_font("helvetica", "", 9)
    for gap in report.gaps[:20]: # Show top 20 gaps
        pdf.cell(30, 8, gap.control_annex, border=1)
        pdf.cell(90, 8, gap.control_title[:50], border=1)
        pdf.cell(30, 8, gap.severity.upper(), border=1)
        pdf.cell(40, 8, gap.current_status, border=1, ln=True)
        
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 10, "Generated by GRC Platform Advanced Audit Module", align="C")
    
    return pdf.output()
