"""
Evidence Engine API endpoints.

Handles file upload to Supabase Storage, metadata CRUD,
status verification workflow, and expiry tracking.
"""
from typing import Any, List, Optional
from datetime import datetime, timedelta, timezone
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType
from app.models.evidence import EvidenceStatus, EvidenceRelatedTo
from app.config import settings

from app.services.evidence_analysis import (
    analyze_evidence_background,
    upload_to_supabase_storage,
    derive_file_type,
    SUPABASE_STORAGE_URL,
    BUCKET_NAME,
)
from app.utils.notifications import notify
import httpx
import logging

logger = logging.getLogger("grc.evidence")

router = APIRouter()


# ── POST  /api/v1/evidence  ───────────────────────────────

@router.post("/", response_model=schemas.Evidence)
async def create_evidence(
    *,
    db: AsyncSession = Depends(deps.get_db),
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(deps.get_current_active_user),
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

    # Bug 4: If related_to=control and related_id is an annex string (e.g. "5.1"),
    # look up the ControlApplicability by annex to find its real UUID.
    related_uuid: Optional[UUID] = None
    try:
        related_uuid = UUID(related_id)
    except ValueError:
        pass

    if related_uuid is None:
        if related_to_enum != EvidenceRelatedTo.control:
            raise HTTPException(status_code=422, detail="related_id must be a valid UUID for non-control types")
        # Try to resolve annex string → control UUID
        from app.models.control_applicability import ControlApplicability
        org_id = current_user.organization_id
        ca_result = await db.execute(
            select(ControlApplicability).where(
                ControlApplicability.control_annex == related_id,
                ControlApplicability.organization_id == org_id,
            )
        )
        ca = ca_result.scalar_one_or_none()
        if not ca:
            raise HTTPException(
                status_code=422,
                detail=f"No control found with annex '{related_id}' in your organization"
            )
        related_uuid = ca.id

    assert related_uuid is not None

    try:
        # Validate file size (10 MB)
        MAX_SIZE = 10 * 1024 * 1024
        contents = await file.read()
        if len(contents) > MAX_SIZE:
            raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")
        await file.seek(0)  # reset for the upload helper

        # Build storage path:  {user_id}/{related_id}/{filename}
        storage_path = f"{current_user.id}/{related_uuid}/{file.filename}"

        # Upload to Supabase Storage — raises 502 on generic error, or 409 on duplicate
        try:
            public_url = await upload_to_supabase_storage(file, storage_path)
        except HTTPException as upload_exc:
            # Bug 5: Re-map Supabase 409 (duplicate object) to a clear user-facing error
            if upload_exc.status_code == 409 or (isinstance(upload_exc.detail, str) and "already exists" in upload_exc.detail.lower()):
                raise HTTPException(
                    status_code=409,
                    detail="A file with this name already exists. Please rename the file and try again."
                )
            raise

        # Persist metadata row
        evidence = models.Evidence(
            title=title,
            description=description,
            file_url=public_url,
            file_name=file.filename,
            file_type=derive_file_type(file.filename or ""),
            file_size=len(contents),
            status=EvidenceStatus.pending,
            related_to=related_to_enum,
            related_id=related_uuid,
            uploaded_by=current_user.id,
            uploaded_at=datetime.now(timezone.utc).replace(tzinfo=None),
            organization_id=current_user.organization_id,
        )
        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)

        # Queue AI analysis as background task
        org_id_str = str(current_user.organization_id) if current_user.organization_id else ""
        background_tasks.add_task(
            analyze_evidence_background,
            evidence_id=str(evidence.id),
            file_url=evidence.file_url or "",
            file_name=evidence.file_name or "",
            organization_id=org_id_str,
        )

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
                "related_id": str(related_uuid),
            },
            description=f"Evidence uploaded: {evidence.title}",
        )

        # Trigger instant notification to uploader
        await notify(
            db=db,
            user_id=str(current_user.id),
            title="Evidence Uploaded",
            message=f"Evidence '{evidence.file_name}' uploaded successfully. AI analysis in progress.",
            entity_type="evidence",
            entity_id=str(evidence.id),
            link_url="/dashboard/evidence",
            notification_type="EVIDENCE_UPLOADED",
        )
        await db.commit()

        return evidence
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        logger.error(f"EVIDENCE UPLOAD CRASH: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ── GET  /api/v1/evidence  ────────────────────────────────

@router.get("/", response_model=List[schemas.Evidence])
async def read_evidence(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    related_id: Optional[str] = Query(None, description="Filter by control or risk ID"),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Return evidence list, optionally filtered by related_id. Role-scoped and org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    query = select(models.Evidence).where(
        models.Evidence.organization_id == org_id
    )

    if related_id:
        target_uuid = None
        try:
            target_uuid = uuid.UUID(related_id)
        except (ValueError, TypeError):
            pass

        if not target_uuid:
            # Check FrameworkControl by code (e.g., "5.1", "A.5.1") or title
            fc_stmt = select(models.FrameworkControl.id).where(
                (models.FrameworkControl.code.ilike(f"%{related_id}%")) |
                (models.FrameworkControl.title.ilike(f"%{related_id}%"))
            )
            fc_res = await db.execute(fc_stmt)
            target_uuid = fc_res.scalar_one_or_none()

        if not target_uuid:
            # Check Control by title
            ctrl_stmt = select(models.Control.id).where(
                models.Control.title.ilike(f"%{related_id}%")
            )
            ctrl_res = await db.execute(ctrl_stmt)
            target_uuid = ctrl_res.scalar_one_or_none()

        if target_uuid:
            query = query.where(models.Evidence.related_id == target_uuid)
        else:
            # Check if related_id matches any EvidenceControlMatch control_id (e.g. "5.15")
            ecm_stmt = select(models.EvidenceControlMatch.evidence_id).where(
                models.EvidenceControlMatch.control_id.ilike(f"%{related_id}%")
            )
            ecm_res = await db.execute(ecm_stmt)
            matched_evidence_ids = ecm_res.scalars().all()
            if matched_evidence_ids:
                query = query.where(models.Evidence.id.in_(matched_evidence_ids))
            else:
                return []
    
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
    """Verify, reject, or set evidence under review. Admin/Manager only. Org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Evidence)
        .where(models.Evidence.id == evidence_id)
        .where(models.Evidence.organization_id == org_id)
    )
    evidence = result.scalars().first()
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
    if new_status == EvidenceStatus.verified:
        evidence.verified = True
        evidence.verified_by = current_user.id
        evidence.verified_at = datetime.now(timezone.utc)

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


@router.delete("/{evidence_id}")
async def delete_evidence(
    evidence_id: UUID,
    current_user: models.User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Delete evidence.
    Admins and Managers can delete any evidence.
    Analysts can only delete evidence they uploaded.
    """
    from app.services import audit_service
    from app.models.audit_log import AuditAction, AuditEntityType

    # 1. Find evidence in DB (scoped to org)
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Evidence)
        .where(models.Evidence.id == evidence_id)
        .where(models.Evidence.organization_id == org_id)
    )
    evidence = result.scalars().first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # 2. Check permission
    # If not admin/manager, check if owner
    user_role_str = str(current_user.role.value) if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role_str not in ['admin', 'superadmin', 'manager']:
        if str(evidence.uploaded_by) != str(current_user.id):
            raise HTTPException(
                status_code=403, 
                detail="You do not have permission to delete this evidence (can only delete your own)"
            )

    # 3. Securely handle file deletion (attempt only)
    try:
        if evidence.file_url and BUCKET_NAME and BUCKET_NAME in evidence.file_url:
            service_key = settings.SUPABASE_SERVICE_KEY or ""
            headers: dict[str, str] = {
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
            }
            parts = evidence.file_url.split(f"/{BUCKET_NAME}/")
            if len(parts) > 1:
                storage_path = parts[1]
                delete_url = f"{SUPABASE_STORAGE_URL}/object/{BUCKET_NAME}/{storage_path}"
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.delete(delete_url, headers=headers)
    except Exception as e:
        logger.warning(f"Storage object deletion failed for evidence {evidence_id}: {e}")

    # 4. Log action
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.deleted,
        entity_type=AuditEntityType.evidence,
        entity_id=evidence.id,
        entity_name=evidence.title,
        old_values={"title": evidence.title, "file_url": evidence.file_url},
        description=f"Evidence deleted: {evidence.title}"
    )

    # 5. Delete DB record
    await db.delete(evidence)
    await db.commit()

    return {"success": True, "message": "Evidence deleted successfully"}


# ── GET  /api/v1/evidence/expiring  ──────────────────────

@router.get("/expiring", response_model=List[schemas.Evidence])
async def get_expiring_evidence(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    days: int = Query(30, description="Window in days"),
) -> Any:
    """Return evidence expiring within the given window (default 30 days). Org-scoped."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)

    query = (
        select(models.Evidence)
        .where(models.Evidence.organization_id == org_id)
        .where(models.Evidence.valid_until.isnot(None))
        .where(models.Evidence.valid_until <= cutoff)
        .where(models.Evidence.valid_until >= now)
        .order_by(models.Evidence.valid_until.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()
