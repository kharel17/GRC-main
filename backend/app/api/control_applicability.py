from typing import Any, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
from pathlib import Path
from app import schemas, models
from app.api import deps
from app.services.control_applicability_service import (
    initialize_control_applicability_for_framework,
)
from app.utils.notifications import notify

router = APIRouter()


# ── Load ISO 27001 controls from JSON ─────────────────────
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


# ── Response Models ────────────────────────────────────────
class SoAEntry(BaseModel):
    control_annex: str
    control_title: str
    control_description: str
    clause_id: str
    is_applicable: bool
    status: str
    justification: Optional[str] = None
    responsible_id: Optional[str] = None
    responsible_name: Optional[str] = None
    evidence_count: int = 0
    notes: Optional[str] = None


class SoAResponse(BaseModel):
    organization_name: str
    total_controls: int
    applicable_controls: int
    implemented_controls: int
    in_progress_controls: int
    not_started_controls: int
    not_applicable_controls: int
    compliance_percentage: float
    entries: List[SoAEntry]


class ComplianceScoreResponse(BaseModel):
    total_controls: int
    applicable_controls: int
    implemented: int
    in_progress: int
    not_started: int
    not_applicable: int
    compliance_percentage: float
    by_clause: dict  # clause_id -> {total, implemented, percentage}


class InitializeFrameworkRequest(BaseModel):
    framework_id: str


# ── GET /control-applicability ─────────────────────────────
@router.get("/", response_model=List[schemas.ControlApplicabilityResponse])
async def list_control_applicability(
    db: AsyncSession = Depends(deps.get_db),
    organization_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """List all control applicability records for the current user's organization."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    query = select(models.ControlApplicability).where(
        models.ControlApplicability.organization_id == org_id
    )
    if status:
        query = query.where(models.ControlApplicability.status == status)
    
    result = await db.execute(query)
    return result.scalars().all()


# ── POST /control-applicability/initialize ─────────────────
@router.post("/initialize", response_model=dict)
async def initialize_control_applicability(
    *,
    db: AsyncSession = Depends(deps.get_db),
    bulk_in: schemas.ControlApplicabilityBulkCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin])),
) -> Any:
    """
    Initialize all 93 ISO 27001 controls for an organization.
    Creates ControlApplicability records for every control.
    Optionally accepts overrides for specific controls.
    """
    try:
        result = await initialize_control_applicability_for_framework(
            db=db,
            organization_id=bulk_in.organization_id,
            framework_id=bulk_in.framework_id or "iso27001",
            overrides=bulk_in.overrides,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        **result,
        "message": (
            f"Initialized {result['initialized_count']} {result['framework_name']} "
            f"control applicability records"
        ),
    }


@router.post("/initialize-framework", response_model=dict)
async def initialize_framework_for_current_org(
    *,
    db: AsyncSession = Depends(deps.get_db),
    body: InitializeFrameworkRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Initialize a framework for the current user's organization."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="No organization associated with this user")

    try:
        result = await initialize_control_applicability_for_framework(
            db=db,
            organization_id=current_user.organization_id,
            framework_id=body.framework_id,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        **result,
        "message": (
            f"Initialized {result['initialized_count']} {result['framework_name']} "
            f"control applicability records"
        ),
    }


# ── GET /control-applicability/annex/{annex} ───────────────
@router.get("/annex/{annex}", response_model=schemas.ControlApplicabilityResponse)
async def get_control_applicability_by_annex(
    annex: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Get applicability record by annex ID (e.g. '5.1' or 'A.5.1'). Scoped to current user's org."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    clean_annex = annex.replace("Annex ", "").replace("A.", "").strip()

    result = await db.execute(
        select(models.ControlApplicability)
        .where(models.ControlApplicability.organization_id == org_id)
        .where(
            (models.ControlApplicability.control_annex == annex) |
            (models.ControlApplicability.control_annex == clean_annex) |
            (models.ControlApplicability.control_annex == f"A.{clean_annex}")
        )
    )
    ca = result.scalars().first()
    if not ca:
        raise HTTPException(status_code=404, detail=f"Control applicability for annex {annex} not found")

    return ca


# ── GET /control-applicability/{ca_id} ────────────────────
@router.get("/{ca_id}", response_model=schemas.ControlApplicabilityResponse)
async def get_control_applicability_by_id(
    ca_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Get a single control applicability record by UUID or Annex ID. Scoped to current user's org."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    # Try UUID lookup first
    try:
        from uuid import UUID as PyUUID
        ca_uuid = PyUUID(ca_id)
        result = await db.execute(
            select(models.ControlApplicability)
            .where(models.ControlApplicability.id == ca_uuid)
            .where(models.ControlApplicability.organization_id == org_id)
        )
        ca = result.scalars().first()
        if ca:
            return ca
    except ValueError:
        pass

    # Fallback to annex lookup
    clean_annex = ca_id.replace("Annex ", "").replace("A.", "").strip()
    result = await db.execute(
        select(models.ControlApplicability)
        .where(models.ControlApplicability.organization_id == org_id)
        .where(
            (models.ControlApplicability.control_annex == ca_id) |
            (models.ControlApplicability.control_annex == clean_annex) |
            (models.ControlApplicability.control_annex == f"A.{clean_annex}")
        )
    )
    ca = result.scalars().first()
    if not ca:
        raise HTTPException(status_code=404, detail="Control applicability record not found")

    return ca


# ── GET /control-applicability/soa ─────────────────────────
@router.get("/soa", response_model=SoAResponse)
async def get_statement_of_applicability(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate the Statement of Applicability (SoA).
    Combines ISO 27001 control definitions with per-organization applicability data.
    Scoped to current user's organization.
    """
    from app.services.compliance_service import compliance_service

    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    # Fetch org for name display
    org_result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = org_result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="No organization configured")
    
    # Use compliance service to get SOA data
    entries_data = await compliance_service.get_soa(db, org_id)
    
    # Calculate counters from entries
    counters = {"implemented": 0, "in_progress": 0, "not_started": 0, "not_applicable": 0}
    for entry in entries_data:
        status = entry["status"]
        if status in counters:
            counters[status] += 1
    
    total = len(entries_data)
    applicable = total - counters["not_applicable"]
    compliance_pct = round((counters["implemented"] / applicable * 100), 1) if applicable > 0 else 0
    
    return SoAResponse(
        organization_name=org.name,
        total_controls=total,
        applicable_controls=applicable,
        implemented_controls=counters["implemented"],
        in_progress_controls=counters["in_progress"],
        not_started_controls=counters["not_started"],
        not_applicable_controls=counters["not_applicable"],
        compliance_percentage=compliance_pct,
        entries=entries_data,
    )


# ── GET /control-applicability/compliance-score ────────────
@router.get("/compliance-score", response_model=ComplianceScoreResponse)
async def get_compliance_score(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Calculate the live compliance score based on control implementation status.
    Breaks down by clause for dashboard widgets.
    Scoped to current user's organization.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

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
            by_clause[clause_id] = {"total": 0, "implemented": 0, "clause_title": ""}
            # Find clause title
            for clause in _ISO_CLAUSES:
                if clause["id"] == clause_id:
                    by_clause[clause_id]["clause_title"] = clause["title"]
                    break
        
        by_clause[clause_id]["total"] += 1
        if status == "implemented":
            by_clause[clause_id]["implemented"] += 1
    
    # Calculate percentages per clause
    for clause_id, data in by_clause.items():
        data["percentage"] = round((data["implemented"] / data["total"] * 100), 1) if data["total"] > 0 else 0
    
    total = len(_ISO_CONTROLS)
    applicable = total - counters["not_applicable"]
    compliance_pct = round((counters["implemented"] / applicable * 100), 1) if applicable > 0 else 0
    
    return ComplianceScoreResponse(
        total_controls=total,
        applicable_controls=applicable,
        implemented=counters["implemented"],
        in_progress=counters["in_progress"],
        not_started=counters["not_started"],
        not_applicable=counters["not_applicable"],
        compliance_percentage=compliance_pct,
        by_clause=by_clause,
    )
