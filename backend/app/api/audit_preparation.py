"""
Audit Preparation API — Export audit artifacts (Step 8).

Endpoints:
- /audit-preparation/soa — Statement of Applicability
- /audit-preparation/risk-register — Full risk register
- /audit-preparation/evidence-inventory — Evidence inventory with control mapping
- /audit-preparation/compliance-report — Full compliance report
"""
from typing import Any, List, Optional
from datetime import datetime
import json
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models
from app.api import deps
from app.services import audit_service
from app.services.gap_analysis_service import generate_gap_report
from fastapi.responses import Response

router = APIRouter()

# Load ISO data
_CONTROLS_PATH = Path(__file__).resolve().parents[2] / "data" / "iso27001-controls.json"
_ISO_CONTROLS = []
_ISO_CLAUSES = []
if _CONTROLS_PATH.exists():
    with open(_CONTROLS_PATH, "r", encoding="utf-8") as f:
        _data = json.load(f)
    _ISO_CONTROLS = _data.get("controls", [])
    _ISO_CLAUSES = _data.get("clauses", [])


# ── Response Models ──────────────────────────────────────
class RiskRegisterEntry(BaseModel):
    id: str
    title: str
    description: str
    category: str
    likelihood: int
    impact: int
    risk_score: int
    status: str
    owner: Optional[str] = None


class RiskRegisterResponse(BaseModel):
    organization_name: str
    generated_at: str
    total_risks: int
    risks: List[RiskRegisterEntry]
    summary: dict


class EvidenceInventoryEntry(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    file_name: str
    file_type: Optional[str] = None
    uploaded_by: Optional[str] = None
    verified: bool
    verified_by: Optional[str] = None
    related_to: str
    created_at: str


class EvidenceInventoryResponse(BaseModel):
    organization_name: str
    generated_at: str
    total_evidence: int
    verified_count: int
    unverified_count: int
    evidence: List[EvidenceInventoryEntry]


class ComplianceReportResponse(BaseModel):
    organization_name: str
    generated_at: str
    compliance_percentage: float
    total_controls: int
    applicable_controls: int
    implemented: int
    in_progress: int
    not_started: int
    not_applicable: int
    gap_summary: dict
    by_clause: List[dict]


# ── GET /audit-preparation/risk-register ─────────────────
@router.get("/risk-register", response_model=RiskRegisterResponse)
async def get_risk_register(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Export the full risk register for audit preparation. Org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    org_result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = org_result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="No organization configured")
    
    # Get all risks for this org
    risk_result = await db.execute(
        select(models.Risk).where(models.Risk.organization_id == org_id)
    )
    risks = risk_result.scalars().all()
    
    # Get risk categories for display
    cat_result = await db.execute(select(models.RiskCategory))
    categories = {str(c.id): c.name for c in cat_result.scalars().all()}
    
    # Get users for owner names
    user_result = await db.execute(select(models.User))
    users = {str(u.id): u.full_name for u in user_result.scalars().all()}
    
    entries = []
    for r in risks:
        entries.append(RiskRegisterEntry(
            id=str(r.id),
            title=r.title,
            description=r.description,
            category=categories.get(str(r.category_id), "Unknown"),
            likelihood=r.likelihood,
            impact=r.impact,
            risk_score=r.risk_score,
            status=r.status.value if hasattr(r.status, 'value') else str(r.status),
            owner=users.get(str(r.owner_id)),
        ))
    
    # Summary counts
    summary = {
        "by_status": {},
        "by_category": {},
        "high_risk_count": sum(1 for r in risks if r.risk_score >= 15),
        "medium_risk_count": sum(1 for r in risks if 6 <= r.risk_score < 15),
        "low_risk_count": sum(1 for r in risks if r.risk_score < 6),
    }
    for r in risks:
        status = r.status.value if hasattr(r.status, 'value') else str(r.status)
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        cat_name = categories.get(str(r.category_id), "Unknown")
        summary["by_category"][cat_name] = summary["by_category"].get(cat_name, 0) + 1
    
    return RiskRegisterResponse(
        organization_name=org.name,
        generated_at=datetime.utcnow().isoformat(),
        total_risks=len(entries),
        risks=entries,
        summary=summary,
    )


# ── GET /audit-preparation/evidence-inventory ────────────
@router.get("/evidence-inventory", response_model=EvidenceInventoryResponse)
async def get_evidence_inventory(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Export the complete evidence inventory for audit preparation. Org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    org_result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = org_result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="No organization configured")
    
    evidence_result = await db.execute(
        select(models.Evidence).where(models.Evidence.organization_id == org_id)
    )
    evidence_list = evidence_result.scalars().all()
    
    user_result = await db.execute(select(models.User))
    users = {str(u.id): u.full_name for u in user_result.scalars().all()}
    
    entries = []
    verified_count = 0
    for e in evidence_list:
        is_verified = bool(e.verified)
        if is_verified:
            verified_count += 1
        
        entries.append(EvidenceInventoryEntry(
            id=str(e.id),
            title=e.title,
            description=e.description,
            file_name=e.file_name,
            file_type=e.file_type,
            uploaded_by=users.get(str(e.uploaded_by)),
            verified=is_verified,
            verified_by=users.get(str(e.verified_by)) if e.verified_by else None,
            related_to=e.related_to.value if hasattr(e.related_to, 'value') else str(e.related_to),
            created_at=e.created_at.isoformat() if e.created_at else "",
        ))
    
    return EvidenceInventoryResponse(
        organization_name=org.name,
        generated_at=datetime.utcnow().isoformat(),
        total_evidence=len(entries),
        verified_count=verified_count,
        unverified_count=len(entries) - verified_count,
        evidence=entries,
    )


# ── GET /audit-preparation/compliance-report ─────────────
@router.get("/compliance-report", response_model=ComplianceReportResponse)
async def get_compliance_report(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Generate a full compliance report combining control status, gaps, and evidence. Org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    org_result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = org_result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="No organization configured")
    
    # Get control applicability
    ca_result = await db.execute(
        select(models.ControlApplicability)
        .where(models.ControlApplicability.organization_id == org_id)
    )
    ca_records = {ca.control_annex: ca for ca in ca_result.scalars().all()}
    
    counters = {"implemented": 0, "in_progress": 0, "not_started": 0, "not_applicable": 0}
    by_clause = {}
    
    for ctrl in _ISO_CONTROLS:
        annex = ctrl["id"]
        clause_id = ctrl["clauseId"]
        ca = ca_records.get(annex)
        status = ca.status.value if ca else "not_started"
        
        if status in counters:
            counters[status] += 1
        
        if clause_id not in by_clause:
            clause_title = ""
            for c in _ISO_CLAUSES:
                if c["id"] == clause_id:
                    clause_title = c["title"]
                    break
            by_clause[clause_id] = {
                "clause_id": clause_id,
                "clause_title": clause_title,
                "total": 0,
                "implemented": 0,
                "in_progress": 0,
                "not_started": 0,
                "not_applicable": 0,
            }
        
        by_clause[clause_id]["total"] += 1
        if status in by_clause[clause_id]:
            by_clause[clause_id][status] += 1
    
    # Calculate percentages per clause
    clause_list = []
    for clause_id, data in by_clause.items():
        applicable = data["total"] - data["not_applicable"]
        data["percentage"] = round((data["implemented"] / applicable * 100), 1) if applicable > 0 else 0
        clause_list.append(data)
    clause_list.sort(key=lambda c: int(c["clause_id"]))
    
    # Gap summary
    gap_report = None
    try:
        gap_report = await generate_gap_report(db, org_id)
    except Exception:
        pass
    
    gap_summary = {}
    if gap_report:
        gap_summary = gap_report.to_dict().get("summary", {})
        gap_summary["total_gaps"] = len(gap_report.gaps)
    
    total = len(_ISO_CONTROLS)
    applicable = total - counters["not_applicable"]
    compliance_pct = round((counters["implemented"] / applicable * 100), 1) if applicable > 0 else 0
    
    return ComplianceReportResponse(
        organization_name=org.name,
        generated_at=datetime.utcnow().isoformat(),
        compliance_percentage=compliance_pct,
        total_controls=total,
        applicable_controls=applicable,
        implemented=counters["implemented"],
        in_progress=counters["in_progress"],
        not_started=counters["not_started"],
        not_applicable=counters["not_applicable"],
        gap_summary=gap_summary,
        by_clause=clause_list,
    )


@router.get("/soa/export/")
async def export_soa(
    format: str = Query("pdf", description="Export format (pdf or csv)"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Export ISO 27001 Statement of Applicability (SoA) as PDF or CSV. Org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    report_bytes = await audit_service.export_soa_report(db, org_id, format=format)
    
    media_type = "application/pdf" if format == "pdf" else "text/csv"
    filename = f"ISO27001_SoA_{org.name.replace(' ', '_')}.{format}"
    
    return Response(
        content=report_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/risk-register/export/")
async def export_risks(
    format: str = Query("pdf", description="Export format (pdf or csv)"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Export the corporate Risk Register as PDF or CSV. Org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    report_bytes = await audit_service.export_risk_register(db, org_id, format=format)
    
    media_type = "application/pdf" if format == "pdf" else "text/csv"
    filename = f"Risk_Register_{org.name.replace(' ', '_')}.{format}"
    
    return Response(
        content=report_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/readiness")
async def get_readiness(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Get weighted readiness score using audit service. Org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return await audit_service.get_readiness_score(db, org_id)


@router.get("/export/")
async def export_report(
    format: str = Query("pdf", description="Export format (pdf or csv)"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Export ISO 27001 readiness report as PDF or CSV. Org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    report_bytes = await audit_service.export_audit_report(db, org_id, format=format)
    
    media_type = "application/pdf" if format == "pdf" else "text/csv"
    filename = f"ISO27001_Readiness_{org.name.replace(' ', '_')}.{format}"
    
    return Response(
        content=report_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
