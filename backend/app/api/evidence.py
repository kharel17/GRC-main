"""
Evidence Engine API endpoints.

Handles file upload to Supabase Storage, metadata CRUD,
status verification workflow, and expiry tracking.
"""
from typing import Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType
from app.models.evidence import EvidenceStatus, EvidenceRelatedTo
from app.config import settings

from app.services.ai_service import ai_service, extract_text_from_pdf
from app.utils.notifications import notify
import httpx
import logging

logger = logging.getLogger("grc.evidence")

async def analyze_evidence_background(
    evidence_id: str,
    file_url: str,
    file_name: str,
    organization_id: str = None,
):
    """
    Background task: runs AI analysis on uploaded 
    evidence and updates the evidence record.
    Called automatically after every evidence upload.
    """
    from app.database import SessionLocal
    from sqlalchemy import select
    from datetime import datetime
    import httpx
    
    async with SessionLocal() as db:
        # Set RLS context for background session so queries aren't filtered out
        if organization_id:
            from sqlalchemy import text as _text
            await db.execute(
                _text("SELECT set_config('app.org_id', :org_id, true)"),
                {"org_id": organization_id}
            )
        try:
            # Get evidence record
            result = await db.execute(
                select(models.Evidence).where(
                    models.Evidence.id == evidence_id
                )
            )
            evidence = result.scalar_one_or_none()
            if not evidence:
                return
            
            # Fetch file content from URL
            file_content = None
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(file_url)
                    if resp.status_code == 200:
                        file_content = resp.content
            except Exception as e:
                logger.error(f"Failed to fetch evidence file for analysis: {e}")
            
            # Run AI analysis using available AIService methods
            analysis = None
            if file_content and file_name.lower().endswith(".pdf"):
                analysis = await ai_service.analyze_evidence_qdrant(extract_text_from_pdf(file_content))
            elif file_content:
                # Try as text
                try:
                    text = file_content.decode("utf-8", errors="ignore")
                    analysis = await ai_service.analyze_evidence_qdrant(text)
                except Exception:
                    analysis = await ai_service.analyze_evidence_qdrant(f"Metadata analysis for {file_name}")
            else:
                # Fallback to metadata analysis
                analysis = await ai_service.analyze_evidence_qdrant(f"Metadata analysis for {file_name}")
            
            # Store results back to evidence record
            evidence.ai_analyzed = True
            evidence.ai_analyzed_at = datetime.utcnow()
            
            if analysis:
                evidence.ai_summary = getattr(analysis, 'summary', None) or str(analysis)
                evidence.ai_category = getattr(analysis, 'category', None)
                
                # Update status based on top match confidence
                if analysis.matched_controls:
                    top_match = analysis.matched_controls[0]
                    confidence = top_match.confidence / 100.0 # ai_service uses 0-100 range
                    
                    if confidence >= 0.7:
                        evidence.status = models.evidence.EvidenceStatus.verified
                    elif confidence >= 0.4:
                        evidence.status = models.evidence.EvidenceStatus.pending
                    else:
                        evidence.status = models.evidence.EvidenceStatus.rejected
            
            await db.commit()
            await db.refresh(evidence)

            # ── Notifications ──────────────────────────────────────────────────
            if analysis and analysis.matched_controls:
                top_match = analysis.matched_controls[0]
                confidence = top_match.confidence # 0-100 range from ai_service
                iso_clause = top_match.clause_id
                
                if confidence >= 80:
                    # Verified
                    await notify(
                        db=db,
                        user_id=evidence.uploaded_by,
                        title="Evidence verified",
                        message=f"✅ Evidence verified: {evidence.file_name} scored {confidence}% for {iso_clause}",
                        entity_type="evidence",
                        entity_id=evidence.id,
                        link_url="/dashboard/evidence",
                        notification_type="EVIDENCE_VERIFIED"
                    )
                elif confidence < 50:
                    # Rejected
                    await notify(
                        db=db,
                        user_id=evidence.uploaded_by,
                        title="Evidence rejected",
                        message=f"❌ Evidence rejected: {evidence.file_name} only scored {confidence}% Please upload better proof",
                        entity_type="evidence",
                        entity_id=evidence.id,
                        link_url="/dashboard/evidence",
                        notification_type="EVIDENCE_REJECTED"
                    )
                else:
                    # Needs review (50-80%)
                    # 1. Notify Control Owner
                    if evidence.related_to == models.evidence.EvidenceRelatedTo.control:
                        ctrl_res = await db.execute(
                            select(models.Control).where(models.Control.id == evidence.related_id)
                        )
                        control = ctrl_res.scalar_one_or_none()
                        if control and control.owner_id:
                            # Notify Control Owner
                            await notify(
                                db=db,
                                user_id=control.owner_id,
                                title="Evidence needs review",
                                message=f"⚠️ Evidence needs review: {evidence.file_name} scored {confidence}% Manual review required",
                                entity_type="evidence",
                                entity_id=evidence.id,
                                link_url="/dashboard/evidence",
                                notification_type="EVIDENCE_REVIEW_REQUIRED"
                            )
                            
                            # Notify Manager
                            owner_res = await db.execute(
                                select(models.User).where(models.User.id == control.owner_id)
                            )
                            owner = owner_res.scalar_one_or_none()
                            if owner and owner.manager_id:
                                await notify(
                                    db=db,
                                    user_id=owner.manager_id,
                                    title="Evidence needs review",
                                    message=f"⚠️ Evidence needs review: {evidence.file_name} scored {confidence}% Manual review required",
                                    entity_type="evidence",
                                    entity_id=evidence.id,
                                    link_url="/dashboard/evidence",
                                    notification_type="EVIDENCE_REVIEW_REQUIRED"
                                )
            
        except Exception as e:
            logger.error(f"AI analysis failed for evidence {evidence_id}: {e}")

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
            # Bug 5: Propagate 409 Conflict (duplicate filename) as a distinct error
            if resp.status_code == 409:
                raise HTTPException(
                    status_code=409,
                    detail="A file with this name already exists. Please rename the file and try again."
                )
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
    related_uuid: UUID
    raw_uuid_valid = False
    try:
        related_uuid = UUID(related_id)
        raw_uuid_valid = True
    except ValueError:
        pass

    if not raw_uuid_valid:
        if related_to_enum != EvidenceRelatedTo.control:
            raise HTTPException(status_code=422, detail="related_id must be a valid UUID for non-control types")
        # Try to resolve annex string → control UUID
        from app.models.control_applicability import ControlApplicability
        org_id = current_user.organization_id
        ca_result = await db.execute(
            select(ControlApplicability).where(
                ControlApplicability.annex_id == related_id,
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
            public_url = await _upload_to_supabase_storage(file, storage_path)
        except HTTPException as upload_exc:
            # Bug 5: Re-map Supabase 409 (duplicate object) to a clear user-facing error
            if upload_exc.status_code == 409 or "already exists" in str(upload_exc.detail).lower():
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

        # Queue AI analysis as background task
        background_tasks.add_task(
            analyze_evidence_background,
            evidence_id=str(evidence.id),
            file_url=evidence.file_url,
            file_name=evidence.file_name,
            organization_id=str(current_user.organization_id) if current_user.organization_id else None,
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
    related_id: Optional[UUID] = Query(None, description="Filter by control or risk ID"),
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
    import os
    from urllib.parse import urlparse

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
            headers = {
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "apikey": settings.SUPABASE_SERVICE_KEY,
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

    now = datetime.utcnow()
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
