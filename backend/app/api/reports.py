from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Any, Optional, List
from pydantic import BaseModel
import datetime
import os
from jinja2 import Environment, FileSystemLoader

from app.api import deps
from app import models
from app.services.pdf_service import build_pdf_response

router = APIRouter()

class CustomReportConfig(BaseModel):
    title: Optional[str] = "Custom GRC Report"
    date_range: Optional[str] = "all_time"  # last_7_days, last_30_days, last_quarter, last_year, all_time
    framework: Optional[str] = "all"
    include_risks: bool = True
    include_controls: bool = True
    include_compliance: bool = True
    include_tickets: bool = False
    include_audit_logs: bool = False

@router.get("/")
async def list_reports(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """List available report types."""
    return [
        {"id": "risk-summary", "title": "Risk Summary Report", "description": "Overview of all risks and their scores"},
        {"id": "compliance-status", "title": "Compliance Status Report", "description": "Current compliance posture across frameworks"},
    ]

# Setup Jinja2 Environment pointing to the templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

@router.post("/custom/export", response_class=HTMLResponse)
async def export_custom_report(
    config: CustomReportConfig,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin])),
) -> Any:
    """Generate a custom combined report based on selected sections."""
    import datetime as dt
    
    print(f"DEBUG: Generating custom report '{config.title}' for user {current_user.email}")
    generated_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_by = current_user.full_name or current_user.email

    # Calculate date filter
    now = dt.datetime.now()
    date_filter = None
    if config.date_range == "last_7_days":
        date_filter = now - dt.timedelta(days=7)
    elif config.date_range == "last_30_days":
        date_filter = now - dt.timedelta(days=30)
    elif config.date_range == "last_quarter":
        date_filter = now - dt.timedelta(days=90)
    elif config.date_range == "last_year":
        date_filter = now - dt.timedelta(days=365)

    # Executive Summary data
    exec_summary = {
        "total_risks": 0,
        "high_risks": 0,
        "total_controls": 0,
        "implemented_controls": 0,
        "compliance_score": 0,
        "open_tickets": 0,
    }

    risks_data = []
    if config.include_risks:
        try:
            stmt = select(models.Risk).options(
                selectinload(models.Risk.category),
                selectinload(models.Risk.owner)
            )
            if date_filter:
                stmt = stmt.where(models.Risk.created_at >= date_filter)
            result = await db.execute(stmt)
            risks = result.scalars().all()
            exec_summary["total_risks"] = len(risks)
            exec_summary["high_risks"] = sum(1 for r in risks if (r.risk_score or 0) >= 15)
            for r in risks:
                risks_data.append({
                    "title": r.title or "Untitled Risk",
                    "category": r.category.name if r.category else "Unknown",
                    "score": r.risk_score or 0,
                    "status": (r.status.value if r.status else "open").capitalize(),
                    "owner": r.owner.full_name if r.owner else "Unassigned",
                })
        except Exception as e:
            print(f"ERROR fetching risks: {e}")

    controls_data = []
    if config.include_controls:
        try:
            stmt = select(models.Control).options(selectinload(models.Control.owner))
            result = await db.execute(stmt)
            controls = result.scalars().all()
            exec_summary["total_controls"] = len(controls)
            exec_summary["implemented_controls"] = sum(1 for c in controls if c.status and c.status.value == 'implemented')
            for c in controls:
                controls_data.append({
                    "code": c.id.hex[:8].upper() if hasattr(c, 'id') and c.id else 'N/A',
                    "title": c.title or "Untitled Control",
                    "status": (c.status.value if c.status else "planned").capitalize(),
                    "owner": c.owner.full_name if c.owner else "Unassigned",
                })
        except Exception as e:
            print(f"ERROR fetching controls: {e}")

    compliance_data = []
    compliance_percentage = 0
    if config.include_compliance:
        try:
            result = await db.execute(select(models.ComplianceItem))
            items = result.scalars().all()
            total = len(items)
            compliant = sum(1 for i in items if i.status and i.status.value == 'compliant')
            compliance_percentage = int((compliant / total) * 100) if total > 0 else 0
            exec_summary["compliance_score"] = compliance_percentage
            for i in items:
                compliance_data.append({
                    "req_id": i.requirement_id or "N/A",
                    "title": i.title or "Untitled Requirement",
                    "status": (i.status.value if i.status else "not_started").replace('_', ' ').capitalize(),
                    "due_date": i.due_date.strftime("%Y-%m-%d") if i.due_date else "None",
                })
        except Exception as e:
            print(f"ERROR fetching compliance: {e}")

    tickets_data = []
    if config.include_tickets:
        try:
            stmt = select(models.Ticket).options(selectinload(models.Ticket.assignee))
            if date_filter:
                stmt = stmt.where(models.Ticket.created_at >= date_filter)
            result = await db.execute(stmt)
            tickets = result.scalars().all()
            exec_summary["open_tickets"] = sum(1 for t in tickets if t.status and t.status.value != 'closed')
            for t in tickets:
                tickets_data.append({
                    "title": t.title or "Untitled Ticket",
                    "status": (t.status.value if t.status else "open").capitalize(),
                    "priority": (t.priority.value if t.priority else "medium").capitalize(),
                    "assignee": t.assignee.full_name if t.assignee else "Unassigned",
                    "due_date": t.due_date.strftime("%Y-%m-%d") if t.due_date else "None",
                })
        except Exception as e:
            print(f"ERROR fetching tickets: {e}")

    audit_data = []
    if config.include_audit_logs:
        try:
            stmt = select(models.AuditLog).options(selectinload(models.AuditLog.user)).order_by(models.AuditLog.timestamp.desc()).limit(100)
            if date_filter:
                stmt = stmt.where(models.AuditLog.timestamp >= date_filter)
            result = await db.execute(stmt)
            logs = result.scalars().all()
            for log in logs:
                audit_data.append({
                    "action": (log.action.value if log.action else "updated").capitalize(),
                    "entity": (log.entity_type.value if log.entity_type else "system").capitalize(),
                    "user": log.user.full_name if log.user else "System",
                    "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "N/A",
                    "details": log.description or "",
                })
        except Exception as e:
            print(f"ERROR fetching audit logs: {e}")

    try:
        template = env.get_template("custom_report.html")
        html_content = template.render(
            report_title=config.title,
            generated_date=generated_date,
            generated_by=generated_by,
            date_range=(config.date_range or "all_time").replace("_", " ").title(),
            framework=(config.framework or "all").upper(),
            exec_summary=exec_summary,
            include_risks=config.include_risks,
            risks=risks_data,
            include_controls=config.include_controls,
            controls=controls_data,
            include_compliance=config.include_compliance,
            compliance_items=compliance_data,
            compliance_percentage=compliance_percentage,
            include_tickets=config.include_tickets,
            tickets=tickets_data,
            include_audit_logs=config.include_audit_logs,
            audit_logs=audit_data,
        )
        print("DEBUG: Template rendered successfully")
        return HTMLResponse(content=html_content)
    except Exception as e:
        print(f"FATAL ERROR during template rendering: {e}")
        raise HTTPException(status_code=500, detail=f"Report rendering failed: {str(e)}")

@router.get("/{report_type}/export")
async def export_report(
    report_type: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate a PDF report based on the requested report type.
    """
    generated_by = current_user.full_name or current_user.email
    
    if report_type == "risk-summary":
        result = await db.execute(
            select(models.Risk)
            .options(selectinload(models.Risk.category))
            .options(selectinload(models.Risk.owner))
        )
        risks_data = result.scalars().all()
        
        headers = ["#", "Risk Title", "Category", "Score", "Status", "Owner"]
        rows = []
        for idx, r in enumerate(risks_data, start=1):
            rows.append([
                idx,
                r.title or "Untitled",
                r.category.name if r.category else "Unknown",
                r.risk_score or 0,
                (r.status.value if r.status else "open").capitalize(),
                r.owner.full_name if r.owner else "Unassigned"
            ])
            
        pdf_bytes = build_pdf_response("Risk Summary Report", generated_by, headers, rows, [10, 60, 35, 15, 30, 40])
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report_type}.pdf"})
        
    elif report_type == "compliance-status":
        result = await db.execute(
            select(models.ComplianceItem)
            .options(selectinload(models.ComplianceItem.owner))
        )
        items_data = result.scalars().all()
        
        headers = ["Req ID", "Requirement Title", "Status", "Due Date", "Owner"]
        rows = []
        for i in items_data:
            rows.append([
                i.requirement_id or "N/A",
                i.title or "Untitled",
                (i.status.value if i.status else "not_started").replace('_', ' ').capitalize(),
                i.due_date.strftime("%Y-%m-%d") if i.due_date else "None",
                i.owner.full_name if i.owner else "Unassigned"
            ])

        pdf_bytes = build_pdf_response("Compliance Status Report", generated_by, headers, rows, [25, 75, 30, 25, 35])
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report_type}.pdf"})
        
    elif report_type == "control-effectiveness":
        result = await db.execute(
            select(models.ControlApplicability)
            .options(
                selectinload(models.ControlApplicability.responsible),
                selectinload(models.ControlApplicability.framework_control),
            )
            .where(models.ControlApplicability.organization_id == current_user.organization_id)
            .order_by(models.ControlApplicability.control_annex)
        )
        ca_records = result.scalars().all()

        headers = ["Annex", "Control Title", "Status", "Applicable", "Owner", "Updated"]
        rows = []
        for c in ca_records:
            ctrl_title = (c.framework_control.title if c.framework_control else None) or c.notes or c.control_annex
            rows.append([
                c.control_annex,
                ctrl_title,
                (c.status.value if c.status else "not_started").replace("_", " ").title(),
                "Yes" if c.is_applicable else "No",
                c.responsible.full_name if c.responsible else "Unassigned",
                c.updated_at.strftime("%Y-%m-%d") if c.updated_at else "N/A",
            ])

        pdf_bytes = build_pdf_response("Control Effectiveness Report", generated_by, headers, rows, [20, 70, 30, 20, 30, 20])
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report_type}.pdf"})

    elif report_type == "audit-trail":
        stmt = (
            select(models.AuditLog)
            .options(selectinload(models.AuditLog.user))
            .order_by(models.AuditLog.timestamp.desc())
            .limit(500)
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()

        headers = ["Timestamp", "User", "Action", "Entity", "Description"]
        rows = []
        for log in logs:
            rows.append([
                log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "N/A",
                log.user.full_name if log.user else "System",
                (log.action.value if log.action else "updated").capitalize(),
                (log.entity_type.value if log.entity_type else "").replace("_", " ").title(),
                log.description or ""
            ])

        pdf_bytes = build_pdf_response("Audit Trail Export", generated_by, headers, rows, [30, 35, 25, 30, 70])
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report_type}.pdf"})

    elif report_type == "evidence-inventory":
        result = await db.execute(
            select(models.Evidence)
            .options(
                selectinload(models.Evidence.uploader),
                selectinload(models.Evidence.verifier),
            )
            .where(models.Evidence.organization_id == current_user.organization_id)
            .order_by(models.Evidence.uploaded_at.desc())
        )
        evidence_records = result.scalars().all()

        headers = ["Title", "File Name", "Type", "Status", "Uploaded By", "Date"]
        rows = []
        for e in evidence_records:
            rows.append([
                e.title or "Untitled",
                e.file_name or "—",
                (e.file_type or "unknown").upper(),
                (e.status.value if e.status else "pending").capitalize(),
                e.uploader.full_name if e.uploader else "Unknown",
                e.uploaded_at.strftime("%Y-%m-%d") if e.uploaded_at else "N/A"
            ])

        pdf_bytes = build_pdf_response("Evidence Inventory", generated_by, headers, rows, [40, 45, 20, 25, 35, 25])
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report_type}.pdf"})

    elif report_type == "trend-analysis":
        result = await db.execute(
            select(models.Risk)
            .options(
                selectinload(models.Risk.category),
                selectinload(models.Risk.owner),
            )
            .where(models.Risk.organization_id == current_user.organization_id)
            .order_by(models.Risk.created_at.asc())
        )
        risks = result.scalars().all()

        headers = ["#", "Risk Title", "Category", "Likelihood", "Impact", "Score", "Status"]
        rows = []
        for idx, r in enumerate(risks, start=1):
            rows.append([
                idx,
                r.title or "Untitled",
                r.category.name if r.category else "Uncategorized",
                r.likelihood or 0,
                r.impact or 0,
                r.risk_score or 0,
                (r.status.value if r.status else "identified").capitalize()
            ])

        pdf_bytes = build_pdf_response("Risk Trend & Distribution Report", generated_by, headers, rows, [10, 60, 40, 20, 20, 20, 20])
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={report_type}.pdf"})

    else:
        raise HTTPException(status_code=404, detail=f"Report type '{report_type}' is not supported.")
