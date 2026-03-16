"""
Evidence Engine API endpoints.

Handles file upload to Supabase Storage, metadata CRUD,
status verification workflow, and expiry tracking.
"""
from typing import Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType
from app.models.evidence import EvidenceStatus, EvidenceRelatedTo
from app.config import settings

import httpx
import logging

logger = logging.getLogger("grc.evidence")

router = APIRouter()

# ── Supabase Storage helpers ───────────────────────────────

SUPABASE_STORAGE_URL = f"{settings.SUPABASE_URL}/storage/v1"
BUCKET_NAME = settings.SUPABASE_BUCKET_NAME  # from .env: SUPABASE_BUCKET_NAME=evidence


async def _upload_to_supabase_storage(
    file: UploadFile,
    storage_path: str,
) -> str:
    """Upload a file to Supabase Storage and return the public URL."""
    file_bytes = await file.read()

    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_KEY,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        # Upload the file
        upload_url = f"{SUPABASE_STORAGE_URL}/object/{BUCKET_NAME}/{storage_path}"
        resp = await client.post(
            upload_url,
            headers={
                **headers,
                "Content-Type": file.content_type or "application/octet-stream",
            },
            content=file_bytes,
        )

        if resp.status_code not in (200, 201):
            logger.error(f"Supabase upload failed: {resp.status_code} {resp.text}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to upload file to storage: {resp.text}",
            )

    # Build the public URL
    public_url = f"{SUPABASE_STORAGE_URL}/object/public/{BUCKET_NAME}/{storage_path}"
    return public_url


def _derive_file_type(filename: str) -> str:
    """Return a short file-type label from the filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    mapping = {
        "pdf": "pdf",
        "png": "image",
        "jpg": "image",
        "jpeg": "image",
        "docx": "doc",
        "doc": "doc",
        "csv": "csv",
        "xlsx": "spreadsheet",
        "xls": "spreadsheet",
    }
    return mapping.get(ext, ext)


# ── POST  /api/v1/evidence  ───────────────────────────────

@router.post("/", response_model=schemas.Evidence)
async def create_evidence(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.analyst])),
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    related_to: str = Form(...),  # "control" or "risk"
    related_id: str = Form(...),  # UUID as string
) -> Any:
    """Upload evidence file to Supabase Storage and persist metadata."""

    # Validate related_to enum
    try:
        related_to_enum = EvidenceRelatedTo(related_to)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"related_to must be one of: {[e.value for e in EvidenceRelatedTo]}",
        )

    # Validate related_id as UUID
    try:
        related_uuid = UUID(related_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="related_id must be a valid UUID")

    try:
        # Validate file size (10 MB)
        MAX_SIZE = 10 * 1024 * 1024
        contents = await file.read()
        if len(contents) > MAX_SIZE:
            raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")
        await file.seek(0)  # reset for the upload helper

        # Build storage path:  {user_id}/{related_id}/{filename}
        storage_path = f"{current_user.id}/{related_uuid}/{file.filename}"

        # Upload to Supabase Storage
        public_url = await _upload_to_supabase_storage(file, storage_path)

        # Persist metadata row
        evidence = models.Evidence(
            title=title,
            description=description,
            file_url=public_url,
            file_name=file.filename,
            file_type=_derive_file_type(file.filename or ""),
            file_size=len(contents),
            status=EvidenceStatus.pending,
            related_to=related_to_enum,
            related_id=related_uuid,
            uploaded_by=current_user.id,
            uploaded_at=datetime.utcnow(),
            organization_id=current_user.organization_id,
        )
        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)

        # Audit log
        await audit_service.log_action(
            db=db,
            user=current_user,
            action=AuditAction.created,
            entity_type=AuditEntityType.evidence,
            entity_id=evidence.id,
            entity_name=evidence.title,
            new_values={
                "file_name": file.filename,
                "related_to": related_to,
                "related_id": related_id,
            },
            description=f"Evidence uploaded: {evidence.title}",
        )
        await db.commit()

        return evidence
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        logger.error(f"EVIDENCE UPLOAD CRASH: {error_msg}")
        raise HTTPException(status_code=500, detail=f"DEBUG CRASH: {str(e)}\n\n{error_msg}")


# ── GET  /api/v1/evidence  ────────────────────────────────

@router.get("/", response_model=List[schemas.Evidence])
async def read_evidence(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    related_id: Optional[UUID] = Query(None, description="Filter by control or risk ID"),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Return evidence list, optionally filtered by related_id. Role-scoped."""
    query = select(models.Evidence)

    if related_id:
        query = query.where(models.Evidence.related_id == related_id)
    
    # Section 6: Evidence Filtering (RBAC)
    if current_user.role == models.UserRole.analyst:
        # Analyst only sees evidence they uploaded (Spec rule: Filter controls to owner_id)
        query = query.where(models.Evidence.uploaded_by == current_user.id)
    elif current_user.role == models.UserRole.manager:
        # Manager sees their own and team's evidence
        sub_query = select(models.User.id).where(models.User.manager_id == current_user.id)
        sub_res = await db.execute(sub_query)
        sub_ids = [uid for uid in sub_res.scalars().all()]
        query = query.where(
            (models.Evidence.uploaded_by == current_user.id) | 
            (models.Evidence.uploaded_by.in_(sub_ids))
        )

    query = query.order_by(models.Evidence.uploaded_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# ── PATCH  /api/v1/evidence/{id}/status  ──────────────────

@router.patch("/{evidence_id}/status", response_model=schemas.Evidence)
async def update_evidence_status(
    evidence_id: UUID,
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(
        deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])
    ),
    status_in: schemas.EvidenceStatusUpdate,
) -> Any:
    """Verify, reject, or set evidence under review. Admin/Manager only."""
    evidence = await db.get(models.Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Map incoming status string to the model enum
    try:
        new_status = EvidenceStatus(status_in.status)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of: {[e.value for e in EvidenceStatus]}",
        )

    old_status = evidence.status.value if evidence.status else None

    evidence.status = new_status

    if status_in.valid_until is not None:
        evidence.valid_until = status_in.valid_until

    # Mark as verified if applicable
    if new_status == EvidenceStatus.active:
        evidence.verified = True
        evidence.verified_by = current_user.id
        evidence.verified_at = datetime.utcnow()

    # Audit log
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.updated,
        entity_type=AuditEntityType.evidence,
        entity_id=evidence.id,
        entity_name=evidence.title,
        old_values={"status": old_status},
        new_values={
            "status": new_status.value,
            "valid_until": str(status_in.valid_until) if status_in.valid_until else None,
        },
        description=f"Evidence status changed from {old_status} to {new_status.value}",
    )

    await db.commit()
    await db.refresh(evidence)
    return evidence


# ── GET  /api/v1/evidence/expiring  ──────────────────────

@router.get("/expiring", response_model=List[schemas.Evidence])
async def get_expiring_evidence(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    days: int = Query(30, description="Window in days"),
) -> Any:
    """Return evidence expiring within the given window (default 30 days)."""
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days)

    query = (
        select(models.Evidence)
        .where(models.Evidence.valid_until.isnot(None))
        .where(models.Evidence.valid_until <= cutoff)
        .where(models.Evidence.valid_until >= now)
        .order_by(models.Evidence.valid_until.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()
