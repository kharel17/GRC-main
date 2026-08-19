"""
Onboarding endpoints for the GRC Platform.
Handles organization setup after an admin accepts their invitation.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app import models
from app.database import get_db
from app.api.deps import get_current_user
from app.services.control_applicability_service import (
    initialize_control_applicability_for_framework,
    normalize_framework_selection,
)
import logging

logger = logging.getLogger("grc.onboarding")

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────

class OnboardingCompleteRequest(BaseModel):
    organization_name: str
    industry: str
    employee_count: str
    infrastructure: str
    data_types: str
    compliance_frameworks: Optional[List[str]] = None

class OnboardingStatusResponse(BaseModel):
    completed: bool

# ── 1. POST /complete ─────────────────────────────────────────

@router.post("/complete")
async def complete_onboarding(
    body: OnboardingCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Complete the onboarding process by filling in organization details.
    Only callable once per organization. Only admin can complete onboarding.
    """
    user_role = str(current_user.role.value) if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can complete onboarding")

    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="No organization associated with this user")

    org = await db.get(models.Organization, current_user.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if org.onboarding_completed:
        raise HTTPException(status_code=400, detail="Onboarding already completed for this organization")

    try:
        selected_frameworks = normalize_framework_selection(body.compliance_frameworks)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Update organization
    org.name = body.organization_name
    org.industry = body.industry
    org.employee_count = body.employee_count
    org.infrastructure = body.infrastructure
    org.data_types = body.data_types
    org.compliance_frameworks = selected_frameworks
    org.onboarding_completed = True

    # Also update user's organization_name
    current_user.organization_name = body.organization_name

    try:
        init_results = []
        for framework_id in selected_frameworks:
            init_results.append(
                await initialize_control_applicability_for_framework(
                    db=db,
                    organization_id=org.id,
                    framework_id=framework_id,
                    register_with_organization=False,
                )
            )

        await db.commit()
        logger.info(
            "Onboarding completed for org %s with frameworks %s initialized: %s",
            body.organization_name,
            selected_frameworks,
            init_results,
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing onboarding: {e}")
        raise HTTPException(status_code=500, detail="Error completing onboarding")

    return {"success": True, "frameworks": selected_frameworks, "initialization": init_results}


# ── 2. GET /status ────────────────────────────────────────────

@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Check if the current user's organization has completed onboarding.
    """
    if not current_user.organization_id:
        return OnboardingStatusResponse(completed=False)

    org = await db.get(models.Organization, current_user.organization_id)
    if not org:
        return OnboardingStatusResponse(completed=False)

    return OnboardingStatusResponse(completed=bool(org.onboarding_completed))
