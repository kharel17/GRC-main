"""
Gap Analysis API — Identify missing/weak ISO 27001 controls (Step 5).
"""
from typing import Any, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models
from app.api import deps
from app.services.gap_analysis_service import generate_gap_report, create_tickets_from_gaps

router = APIRouter()


class GapReportResponse(BaseModel):
    total_controls: int
    applicable_controls: int
    implemented: int
    total_gaps: int
    compliance_percentage: float
    gaps: List[dict]
    summary: dict


class CreateTicketsRequest(BaseModel):
    gap_annexes: Optional[List[str]] = None  # None = auto-select critical+high
    max_tickets: int = 20


class CreateTicketsResponse(BaseModel):
    created_count: int
    tickets: List[dict]


@router.get("/", response_model=GapReportResponse)
async def get_gap_analysis(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate a comprehensive gap analysis report.
    Scoped to current user's organization.
    
    Combines:
    - Control applicability status
    - AI evidence analysis
    - Document analysis results
    
    Returns missing controls, weak controls, and priority fixes.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")
    
    report = await generate_gap_report(db, org_id)
    return report.to_dict()


@router.post("/create-tickets", response_model=CreateTicketsResponse)
async def create_tickets_from_gap_analysis(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: CreateTicketsRequest,
    current_user: models.User = Depends(deps.RoleChecker([
        models.UserRole.admin, models.UserRole.manager
    ])),
) -> Any:
    """
    Create remediation tickets from gap findings (Step 6 integration).
    Scoped to current user's organization.
    
    By default creates tickets for all critical and high severity gaps.
    Optionally specify specific control annexes to create tickets for.
    Skips controls that already have active tickets.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")
    
    tickets = await create_tickets_from_gaps(
        db=db,
        organization_id=org_id,
        created_by=current_user,
        gap_annexes=request.gap_annexes,
        max_tickets=request.max_tickets,
    )
    
    return CreateTicketsResponse(
        created_count=len(tickets),
        tickets=tickets,
    )
