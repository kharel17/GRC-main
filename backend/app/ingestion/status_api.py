"""
Ingestion Status API — Provides job progress polling endpoints.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app import models
from app.ingestion.job_queue import get_job_status, JobStatus

router = APIRouter()

@router.get("/jobs/{analysis_id}")
async def get_ingestion_job_status(
    analysis_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Get detailed progress status of an ongoing or completed document ingestion job.
    Returns current processing step, progress percentage (0-100), chunk count, and any error message.
    """
    job_status = await get_job_status(db, analysis_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    return job_status
