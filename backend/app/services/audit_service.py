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


def serialize_data(data: Any) -> Any:
    """Recursively convert non-serializable objects (UUIDs, Enums, datetimes) to JSON-safe formats."""
    if isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_data(i) for i in data]
    elif isinstance(data, UUID):
        return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    elif hasattr(data, "value") and not isinstance(data, (str, int, float, bool, type(None))):
        # Handle Enum members by taking their .value
        return data.value
    return data


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

    # Convert potentially non-serializable objects to strings/primitives
    safe_old_values = serialize_data(old_values) if old_values else None
    safe_new_values = serialize_data(new_values) if new_values else None

    audit_log = models.AuditLog(
        user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        old_values=safe_old_values,
        new_values=safe_new_values,
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
    from app.services.gap_analysis_service import generate_gap_report
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
    weighted_readiness = max(0, round(float((1 - (current_debt / max_possible_debt)) * 100), 1)) if report.applicable_controls > 0 else 0
    
    return {
        "compliance_percentage": raw_pct,
        "weighted_readiness": weighted_readiness,
        "total_controls": report.total_controls,
        "applicable_controls": report.applicable_controls,
        "implemented_controls": report.implemented,
        "gap_summary": report.to_dict()["summary"]
    }


def _clean_pdf_text(text: Optional[Any]) -> str:
    """Sanitize string for FPDF standard latin-1 font rendering."""
    if text is None:
        return ""
    val = str(text)
    replacements = {
        '“': '"', '”': '"', '‘': "'", '’': "'",
        '—': '-', '–': '-', '…': '...', '•': '*', '\u200b': ''
    }
    for orig, repl in replacements.items():
        val = val.replace(orig, repl)
    return val.encode('latin-1', errors='replace').decode('latin-1')


async def export_soa_report(db: AsyncSession, organization_id: UUID, format: str = "pdf") -> bytes:
    """Export a professional Statement of Applicability (SoA) artifact."""
    ca_result = await db.execute(
        select(models.ControlApplicability)
        .where(models.ControlApplicability.organization_id == organization_id)
    )
    ca_records = {ca.control_annex: ca for ca in ca_result.scalars().all()}
    
    # Get organization info
    org_res = await db.execute(select(models.Organization).where(models.Organization.id == organization_id))
    organization = org_res.scalar()
    org_name = organization.name if organization else "Organization"

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Statement of Applicability (SoA)", org_name, datetime.utcnow().strftime('%Y-%m-%d')])
        writer.writerow([])
        writer.writerow(["Annex", "Applicable", "Status", "Justification"])
        for annex, ca in sorted(ca_records.items()):
            status_val = ca.status.value if (ca and ca.status and hasattr(ca.status, 'value')) else str(getattr(ca, 'status', 'not_started'))
            writer.writerow([annex, getattr(ca, 'applicable', True), status_val, getattr(ca, 'justification', '')])
        return output.getvalue().encode('utf-8')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 15, _clean_pdf_text("Statement of Applicability (SoA)"), ln=True, align="C")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, _clean_pdf_text(f"Organization: {org_name}"), ln=True, align="C")
    pdf.cell(0, 10, _clean_pdf_text("Scope: ISO 27001:2022"), ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("helvetica", "B", 10)
    pdf.cell(30, 8, "Annex", border=1)
    pdf.cell(30, 8, "Applicable", border=1)
    pdf.cell(40, 8, "Status", border=1)
    pdf.cell(90, 8, "Justification", border=1, ln=True)

    pdf.set_font("helvetica", "", 8)
    for annex, ca in sorted(ca_records.items()):
        is_app = getattr(ca, 'applicable', True)
        st = ca.status.value if (ca and ca.status and hasattr(ca.status, 'value')) else str(getattr(ca, 'status', 'not_started'))
        just = getattr(ca, 'justification', '') or "N/A"
        
        pdf.cell(30, 8, _clean_pdf_text(annex), border=1)
        pdf.cell(30, 8, "Yes" if is_app else "No", border=1)
        pdf.cell(40, 8, _clean_pdf_text(st.upper()), border=1)
        pdf.cell(90, 8, _clean_pdf_text(just[:60]), border=1, ln=True)

    out = pdf.output()
    return bytes(out) if isinstance(out, (bytearray, bytes)) else str(out).encode('latin-1', errors='replace')


async def export_risk_register(db: AsyncSession, organization_id: UUID, format: str = "pdf") -> bytes:
    """Export the professional Risk Register."""
    risk_result = await db.execute(
        select(models.Risk).where(models.Risk.organization_id == organization_id)
    )
    risks = risk_result.scalars().all()
    
    org_res = await db.execute(select(models.Organization).where(models.Organization.id == organization_id))
    organization = org_res.scalar()
    org_name = organization.name if organization else "Organization"

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Risk Register", org_name, datetime.utcnow().strftime('%Y-%m-%d')])
        writer.writerow([])
        writer.writerow(["ID", "Title", "Likelihood", "Impact", "Score", "Status"])
        for r in risks:
            st = r.status.value if (r.status and hasattr(r.status, 'value')) else str(r.status or 'open')
            writer.writerow([str(r.id)[:8], r.title, r.likelihood, r.impact, r.risk_score, st])
        return output.getvalue().encode('utf-8')

    pdf = FPDF()
    pdf.add_page("L") # Landscape for risk register
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 15, _clean_pdf_text("Organizational Risk Register"), ln=True, align="C")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, _clean_pdf_text(f"Organization: {org_name}"), ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("helvetica", "B", 10)
    pdf.cell(20, 10, "ID", border=1)
    pdf.cell(100, 10, "Risk Title", border=1)
    pdf.cell(30, 10, "Likelihood", border=1)
    pdf.cell(30, 10, "Impact", border=1)
    pdf.cell(30, 10, "Score", border=1)
    pdf.cell(50, 10, "Status", border=1, ln=True)

    pdf.set_font("helvetica", "", 9)
    for r in risks:
        st = r.status.value if (r.status and hasattr(r.status, 'value')) else str(r.status or 'open')
        pdf.cell(20, 10, _clean_pdf_text(str(r.id)[:8]), border=1)
        pdf.cell(100, 10, _clean_pdf_text((r.title or "")[:60]), border=1)
        pdf.cell(30, 10, str(r.likelihood or 1), border=1, align="C")
        pdf.cell(30, 10, str(r.impact or 1), border=1, align="C")
        pdf.cell(30, 10, str(r.risk_score or 1), border=1, align="C")
        pdf.cell(50, 10, _clean_pdf_text(st.upper()), border=1, ln=True)

    out = pdf.output()
    return bytes(out) if isinstance(out, (bytearray, bytes)) else str(out).encode('latin-1', errors='replace')


async def export_audit_report(db: AsyncSession, organization_id: UUID, format: str = "pdf") -> bytes:
    """
    Export a comprehensive ISO 27001 readiness report.
    Generates SoA, Risk Register, and Gap Analysis in one document.
    """
    from app.services.gap_analysis_service import generate_gap_report
    report = await generate_gap_report(db, organization_id)
    readiness = await get_readiness_score(db, organization_id)
    
    # Get organization info
    org_res = await db.execute(select(models.Organization).where(models.Organization.id == organization_id))
    organization = org_res.scalar()
    org_name = organization.name if organization else "Organization"

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ISO 27001 Readiness Report", org_name, datetime.utcnow().isoformat()])
        writer.writerow([])
        writer.writerow(["Summary"])
        writer.writerow(["Compliance %", readiness.get("compliance_percentage", 0)])
        writer.writerow(["Weighted Readiness", readiness.get("weighted_readiness", 0)])
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
    pdf.cell(0, 10, _clean_pdf_text("ISO 27001 Readiness Report"), ln=True, align="C")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, _clean_pdf_text(f"Organization: {org_name}"), ln=True, align="C")
    pdf.cell(0, 10, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}", ln=True, align="C")
    pdf.ln(10)
    
    # Summary Section
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "1. Executive Summary", ln=True)
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Compliance Percentage: {readiness.get('compliance_percentage', 0)}%", ln=True)
    pdf.cell(0, 8, f"Risk-Weighted Readiness: {readiness.get('weighted_readiness', 0)}%", ln=True)
    pdf.cell(0, 8, f"Applicable Controls: {readiness.get('applicable_controls', 0)}", ln=True)
    pdf.cell(0, 8, f"Implemented Controls: {readiness.get('implemented_controls', 0)}", ln=True)
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
        pdf.cell(30, 8, _clean_pdf_text(gap.control_annex), border=1)
        pdf.cell(90, 8, _clean_pdf_text((gap.control_title or "")[:50]), border=1)
        pdf.cell(30, 8, _clean_pdf_text((gap.severity or "").upper()), border=1)
        pdf.cell(40, 8, _clean_pdf_text(gap.current_status or "Not Started"), border=1, ln=True)
        
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 10, "Generated by GRC Platform Advanced Audit Module", align="C")
    
    out = pdf.output()
    return bytes(out) if isinstance(out, (bytearray, bytes)) else str(out).encode('latin-1', errors='replace')
