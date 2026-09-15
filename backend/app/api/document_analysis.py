"""
Document Analysis API — Upload and AI-analyze security documentation (Step 3).
"""
from typing import Any, List
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app import schemas, models
from app.api import deps
from app.services.ai_service import ai_service, _run_document_analysis_async, _extract_security_practices
from app.services.file_service import file_storage
import logging
import json

logger = logging.getLogger("grc.document_analysis")
router = APIRouter()


@router.get("/", response_model=List[schemas.DocumentAnalysisResponse])
async def list_document_analyses(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """List all document analyses with full findings."""
    result = await db.execute(
        select(models.DocumentAnalysis)
        .order_by(models.DocumentAnalysis.created_at.desc())
        .offset(skip).limit(limit)
    )
    analyses = result.scalars().all()
    return analyses


@router.get("/{analysis_id}", response_model=schemas.DocumentAnalysisResponse)
async def get_document_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Get full document analysis details including AI findings."""
    result = await db.execute(
        select(models.DocumentAnalysis).where(models.DocumentAnalysis.id == analysis_id)
    )
    analysis = result.scalars().first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Document analysis not found")
    return analysis


from app.ingestion.job_queue import init_job_record, enqueue_ingestion_job

@router.post("/upload", response_model=schemas.DocumentAnalysisResponse)
async def upload_and_analyze_document(
    file: UploadFile = File(...),
    organization_id: str = Form(None),
    link_as_evidence: bool = Form(False),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Upload a document (PDF/DOCX) and trigger durable pgqueuer background AI ingestion & analysis pipeline.
    
    The pipeline runs asynchronously via durable Postgres job queue:
    - Extract text page-by-page (PyMuPDF + Tesseract OCR fallback)
    - Structural + recursive token chunking (~400 tokens)
    - Vector embedding & control mapping
    
    Returns 202 Accepted status with initial analysis record. Progress can be polled via /api/v1/ingestion/jobs/{analysis_id}.
    """
    target_org_id = organization_id or str(current_user.organization_id)
    if not target_org_id:
        raise HTTPException(status_code=400, detail="User not associated with an organization")

    try:
        org_uuid = uuid.UUID(str(target_org_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid organization ID format")

    filename = file.filename or "uploaded_document"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"

    # Validate file type
    allowed_types = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if file.content_type not in allowed_types and not filename.lower().endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported")
    
    # Read file bytes
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    # Store the file
    file_key = await file_storage.upload(file_bytes, filename, file.content_type or "application/octet-stream")
    file_url = await file_storage.get_download_url(file_key)
    
    # Create evidence record if requested
    evidence_id = None
    if link_as_evidence:
        evidence = models.Evidence(
            title=f"Document: {filename}",
            description=f"AI-analyzed security document: {filename}",
            file_url=file_url,
            file_name=filename,
            file_type=ext,
            file_size=len(file_bytes),
            related_to=models.EvidenceRelatedTo.compliance_item,
            related_id=uuid.uuid4(),
            uploaded_by=current_user.id,
            organization_id=org_uuid,
        )
        db.add(evidence)
        await db.flush()
        evidence_id = evidence.id
    
    # Create DocumentAnalysis record
    doc_analysis = models.DocumentAnalysis(
        organization_id=org_uuid,
        file_name=filename,
        file_url=file_url,
        file_size=len(file_bytes),
        file_type=ext,
        uploaded_by=current_user.id,
        status=models.DocumentAnalysisStatus.processing,
        evidence_id=evidence_id,
    )
    db.add(doc_analysis)
    await db.flush()
    
    # Initialize job tracking record
    await init_job_record(db, doc_analysis)
    await db.commit()
    await db.refresh(doc_analysis)

    # Queue ingestion pipeline — payload is durably persisted to DB before dispatch.
    await enqueue_ingestion_job(
        analysis_id=doc_analysis.id,
        file_bytes=file_bytes,
        filename=filename,
        organization_id=doc_analysis.organization_id,
        db=db,
    )

    return doc_analysis



@router.post("/{analysis_id}/reanalyze", response_model=schemas.DocumentAnalysisResponse)
async def reanalyze_document(
    analysis_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """Re-run AI analysis on a previously uploaded document."""
    result = await db.execute(
        select(models.DocumentAnalysis).where(models.DocumentAnalysis.id == analysis_id)
    )
    doc_analysis = result.scalars().first()
    if not doc_analysis:
        raise HTTPException(status_code=404, detail="Document analysis not found")
    
    if not doc_analysis.extracted_text:
        raise HTTPException(status_code=422, detail="No extracted text available for re-analysis")
    
    doc_analysis.status = models.DocumentAnalysisStatus.processing
    await db.flush()
    
    try:
        extracted_text_val: str = doc_analysis.extracted_text or ""
        analysis_result = await _run_document_analysis_async(
            extracted_text_val,
            org_id=str(doc_analysis.organization_id) if doc_analysis.organization_id else None,
            current_doc_id=str(doc_analysis.id),
        )
        
        doc_analysis.status = models.DocumentAnalysisStatus.completed
        doc_analysis.document_category = analysis_result.get("document_category", "general")
        doc_analysis.analysis_result = analysis_result
        doc_analysis.implemented_controls = analysis_result.get("implemented_controls", [])
        doc_analysis.missing_controls = analysis_result.get("missing_controls", [])
        doc_analysis.security_practices = analysis_result.get("security_practices", [])
        doc_analysis.analyzed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
    except Exception as e:
        logger.error(f"Re-analysis failed: {e}")
        doc_analysis.status = models.DocumentAnalysisStatus.failed
        doc_analysis.analysis_result = {"error": f"Re-analysis failed: {str(e)}"}
    
    await db.commit()
    await db.refresh(doc_analysis)
    return doc_analysis


@router.get("/{analysis_id}/remediations/preview", response_model=List[schemas.RemediationCandidate])
async def preview_remediations(
    analysis_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Preview candidate risks and controls for identified document gaps before registration."""
    # 1. Fetch document analysis (scoped to current user's organization)
    result = await db.execute(
        select(models.DocumentAnalysis).where(
            models.DocumentAnalysis.id == analysis_id,
            models.DocumentAnalysis.organization_id == current_user.organization_id,
        )
    )
    analysis = result.scalars().first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Document analysis not found")

    missing_controls = analysis.missing_controls or []
    if not missing_controls:
        return []

    # 2. Dynamically fetch frameworks accessible to this tenant (system or tenant-owned)
    fw_result = await db.execute(
        select(models.Framework).where(
            or_(
                models.Framework.organization_id == current_user.organization_id,
                models.Framework.organization_id.is_(None),
            )
        )
    )
    frameworks = fw_result.scalars().all()
    framework_ids = [f.id for f in frameworks]
    framework_map = {f.id: f.name for f in frameworks}

    # 3. Dynamically fetch framework controls for these frameworks
    fc_result = await db.execute(
        select(models.FrameworkControl)
        .where(models.FrameworkControl.framework_id.in_(framework_ids))
        .options(selectinload(models.FrameworkControl.framework))
    )
    framework_controls = fc_result.scalars().all()

    # Index by normalized code and normalized title
    def normalize_code(val: str) -> str:
        s = val.lower().strip()
        if s.startswith("a."):
            s = s[2:]
        return s.strip()

    fc_by_code: dict[str, models.FrameworkControl] = {}
    fc_by_title: dict[str, models.FrameworkControl] = {}
    for fc in framework_controls:
        fc_by_code[normalize_code(fc.code)] = fc
        fc_by_title[fc.title.strip().lower()] = fc

    # 4. Check existing controls in user's organization for duplicate detection
    ctrl_result = await db.execute(
        select(models.Control).where(
            models.Control.organization_id == current_user.organization_id
        )
    )
    existing_controls = ctrl_result.scalars().all()
    registered_fc_ids = {c.framework_control_id for c in existing_controls if c.framework_control_id}
    registered_titles = {c.title.strip().lower() for c in existing_controls if c.title}

    # 5. Synthesize candidates
    candidates: List[schemas.RemediationCandidate] = []
    for idx, gap in enumerate(missing_controls):
        if not isinstance(gap, dict):
            continue

        raw_annex = str(gap.get("control_annex") or gap.get("annex") or gap.get("code") or "")
        gap_title = str(gap.get("title") or "Required Security Control")
        gap_reason = gap.get("reason")

        norm_code = normalize_code(raw_annex)
        matched_fc = fc_by_code.get(norm_code) or fc_by_title.get(gap_title.strip().lower())

        is_registered = False
        if matched_fc and matched_fc.id in registered_fc_ids:
            is_registered = True
        elif gap_title.strip().lower() in registered_titles:
            is_registered = True

        fw_name = "Standard Framework"
        fw_id = None
        fc_id = None
        fc_description = None

        if matched_fc:
            fw_id = matched_fc.framework_id
            fc_id = matched_fc.id
            fw_name = matched_fc.framework.name if matched_fc.framework else framework_map.get(matched_fc.framework_id, "Standard")
            fc_description = matched_fc.description

        display_annex = raw_annex if raw_annex else (matched_fc.code if matched_fc else "GAP")

        candidate = schemas.RemediationCandidate(
            candidate_id=f"cand-{idx}-{uuid.uuid4().hex[:8]}",
            gap_title=gap_title,
            gap_annex=display_annex,
            gap_reason=gap_reason,
            framework_id=fw_id,
            framework_name=fw_name,
            framework_control_id=fc_id,
            suggested_risk_title=f"Absence of {gap_title} Control",
            suggested_risk_description=(
                f"Document gap analysis identified missing coverage for {display_annex} ({gap_title}). "
                f"{gap_reason or 'No mitigating policy or operational control was discovered in the uploaded documentation.'}"
            ),
            suggested_risk_likelihood=3,
            suggested_risk_impact=3,
            suggested_control_title=f"Implement {gap_title} Control",
            suggested_control_description=(
                fc_description
                or f"Establish formal policies, technical procedures, and operational safeguards to fulfill {gap_title} requirements."
            ),
            control_type="preventive",
            owner_id=current_user.id,
            assessment_status="ai_suggested",
            already_registered=is_registered,
        )
        candidates.append(candidate)

    return candidates


@router.post("/{analysis_id}/remediations/commit", response_model=schemas.CommitRemediationResponse)
async def commit_remediations(
    analysis_id: str,
    payload: schemas.CommitRemediationRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Commit approved remediation items to Risk and Control registers inside an atomic transaction.
    If any insert fails, the entire batch rolls back cleanly.
    """
    result = await db.execute(
        select(models.DocumentAnalysis).where(
            models.DocumentAnalysis.id == analysis_id,
            models.DocumentAnalysis.organization_id == current_user.organization_id,
        )
    )
    analysis = result.scalars().first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Document analysis not found")

    if not payload.items:
        return schemas.CommitRemediationResponse(
            success=True,
            committed_count=0,
            created_risk_ids=[],
            created_control_ids=[],
        )

    # Commit any existing read transaction before beginning the atomic batch block
    if db.in_transaction():
        await db.commit()

    created_risk_ids: List[uuid.UUID] = []
    created_control_ids: List[uuid.UUID] = []

    async with db.begin():
        for item in payload.items:
            # 1. Insert Risk
            risk_id = uuid.uuid4()
            risk = models.Risk(
                id=risk_id,
                title=item.risk_title,
                description=item.risk_description,
                likelihood=item.likelihood,
                impact=item.impact,
                risk_score=item.likelihood * item.impact,
                status=models.RiskStatus.identified,
                organization_id=current_user.organization_id,
                owner_id=item.owner_id or current_user.id,
                created_by=current_user.id,
                source="ai_gap_remediation",
                source_document_id=analysis.id,
                assessment_status="ai_suggested",
            )
            db.add(risk)
            await db.flush()
            created_risk_ids.append(risk_id)

            # 2. Insert Control
            control_id = uuid.uuid4()
            try:
                c_type = models.ControlType(item.control_type)
            except Exception:
                c_type = models.ControlType.preventive

            control = models.Control(
                id=control_id,
                title=item.control_title,
                description=item.control_description,
                control_type=c_type,
                effectiveness=models.ControlEffectiveness.low,
                status=models.ControlStatus.planned,
                organization_id=current_user.organization_id,
                owner_id=item.owner_id or current_user.id,
                created_by=current_user.id,
                source="ai_gap_remediation",
                source_document_id=analysis.id,
                assessment_status="ai_suggested",
                framework_id=item.framework_id,
                framework_control_id=item.framework_control_id,
            )
            db.add(control)
            await db.flush()
            created_control_ids.append(control_id)

            # 3. Insert RiskControlMapping
            mapping = models.RiskControlMapping(
                id=uuid.uuid4(),
                risk_id=risk_id,
                control_id=control_id,
                framework_control_id=item.framework_control_id,
                mapped_by=current_user.id,
            )
            db.add(mapping)

    return schemas.CommitRemediationResponse(
        success=True,
        committed_count=len(payload.items),
        created_risk_ids=created_risk_ids,
        created_control_ids=created_control_ids,
    )


def _extract_security_practices(text: str) -> list[dict]:
    """Extract security practices by scanning for key phrases."""
    text_lower = text.lower()
    
    practice_patterns = {
        "Multi-factor authentication": (["mfa", "multi-factor", "two-factor", "2fa"], ["5.17", "8.5"]),
        "Access control policy": (["access control", "role-based access", "rbac", "least privilege"], ["5.15", "5.18", "8.2"]),
        "Data encryption": (["encryption", "encrypted", "aes", "tls", "ssl", "cryptograph"], ["8.24"]),
        "Security awareness training": (["security training", "awareness program", "security awareness"], ["6.3"]),
        "Incident response": (["incident response", "incident management", "security incident"], ["5.24", "5.25", "5.26"]),
        "Backup procedures": (["backup", "data backup", "recovery point"], ["8.13"]),
        "Change management": (["change management", "change control", "change request"], ["8.32"]),
        "Vulnerability management": (["vulnerability scan", "penetration test", "vulnerability management"], ["8.8"]),
        "Network security": (["firewall", "network segmentation", "intrusion detection", "ids", "ips"], ["8.20", "8.21", "8.22"]),
        "Logging and monitoring": (["audit log", "event log", "monitoring", "siem"], ["8.15", "8.16"]),
        "Password policy": (["password policy", "password complexity", "password rotation"], ["5.17"]),
        "Data classification": (["data classification", "information classification", "labeling"], ["5.12", "5.13"]),
        "Business continuity": (["business continuity", "disaster recovery", "bcp", "drp"], ["5.29", "5.30"]),
        "Secure development": (["secure development", "sdlc", "secure coding", "code review"], ["8.25", "8.28"]),
        "Supplier management": (["vendor management", "supplier assessment", "third-party"], ["5.19", "5.20", "5.21"]),
    }
    
    found_practices = []
    for practice_name, (keywords, related_controls) in practice_patterns.items():
        if any(kw in text_lower for kw in keywords):
            found_practices.append({
                "practice": practice_name,
                "related_controls": related_controls,
            })
    
    return found_practices
