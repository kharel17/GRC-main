from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app import models
from app.api import deps
from app.services.dashboard_service import dashboard_service

router = APIRouter()

@router.get("/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Returns an aggregated summary for the main dashboard.
    """
    return await dashboard_service.get_dashboard_summary(db, current_user.organization_id)
