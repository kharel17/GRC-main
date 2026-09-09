"""
Evidence Analysis & Storage Service.

Extracted from the evidence API router – handles background AI analysis
of uploaded evidence and Supabase Storage upload/helpers.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, UploadFile
import httpx

from app.config import settings
from app.models.evidence import EvidenceStatus
from app.utils.notifications import notify

logger = logging.getLogger("grc.evidence")

# ── Supabase Storage helpers ───────────────────────────────

SUPABASE_STORAGE_URL = f"{settings.SUPABASE_URL}/storage/v1"
BUCKET_NAME = settings.SUPABASE_BUCKET_NAME  # from .env: SUPABASE_BUCKET_NAME=evidence


async def upload_to_supabase_storage(
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


def derive_file_type(filename: str) -> str:
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


async def analyze_evidence_background(
    evidence_id: str,
    file_url: str,
    file_name: str,
    organization_id: Optional[str] = None,
):
    """
    Background task: runs AI analysis on uploaded 
    evidence and updates the evidence record.
    Called automatically after every evidence upload.
    """
    from app.database import SessionLocal
    from sqlalchemy import select
    from app import models
    from app.services.ai_service import ai_service, extract_text_from_pdf
    
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
            
            # Run AI analysis using available AIService methods (Two-Tier Evaluation)
            analysis = None
            if file_content and file_name.lower().endswith(".pdf"):
                analysis = await ai_service.analyze_evidence_qdrant(extract_text_from_pdf(file_content), org_id=organization_id)
            elif file_content:
                # Try as text
                try:
                    text = file_content.decode("utf-8", errors="ignore")
                    analysis = await ai_service.analyze_evidence_qdrant(text, org_id=organization_id)
                except Exception:
                    analysis = await ai_service.analyze_evidence_qdrant(f"Metadata analysis for {file_name}", org_id=organization_id)
            else:
                # Fallback to metadata analysis
                analysis = await ai_service.analyze_evidence_qdrant(f"Metadata analysis for {file_name}", org_id=organization_id)
            
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
                        evidence.status = EvidenceStatus.verified
                    elif confidence >= 0.4:
                        evidence.status = EvidenceStatus.pending
                    else:
                        evidence.status = EvidenceStatus.rejected
            
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
                        user_id=str(evidence.uploaded_by),
                        title="Evidence verified",
                        message=f"✅ Evidence verified: {evidence.file_name} scored {confidence}% for {iso_clause}",
                        entity_type="evidence",
                        entity_id=str(evidence.id),
                        link_url="/dashboard/evidence",
                        notification_type="EVIDENCE_VERIFIED"
                    )
                elif confidence < 50:
                    # Rejected
                    await notify(
                        db=db,
                        user_id=str(evidence.uploaded_by),
                        title="Evidence rejected",
                        message=f"❌ Evidence rejected: {evidence.file_name} only scored {confidence}% Please upload better proof",
                        entity_type="evidence",
                        entity_id=str(evidence.id),
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
                                user_id=str(control.owner_id),
                                title="Evidence needs review",
                                message=f"⚠️ Evidence needs review: {evidence.file_name} scored {confidence}% Manual review required",
                                entity_type="evidence",
                                entity_id=str(evidence.id),
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
                                    user_id=str(owner.manager_id),
                                    title="Evidence needs review",
                                    message=f"⚠️ Evidence needs review: {evidence.file_name} scored {confidence}% Manual review required",
                                    entity_type="evidence",
                                    entity_id=str(evidence.id),
                                    link_url="/dashboard/evidence",
                                    notification_type="EVIDENCE_REVIEW_REQUIRED"
                                )
            
        except Exception as e:
            logger.error(f"AI analysis failed for evidence {evidence_id}: {e}")
