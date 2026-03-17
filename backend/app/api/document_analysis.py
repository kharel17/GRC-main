"""
Document Analysis API — Upload and AI-analyze security documentation (Step 3).
"""
from typing import Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services.ai_service import ai_service, extract_text_from_pdf
from app.services.file_service import file_storage
import logging
import json

logger = logging.getLogger("grc.document_analysis")
router = APIRouter()


@router.get("/", response_model=List[schemas.DocumentAnalysisSummary])
async def list_document_analyses(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """List all document analyses."""
    result = await db.execute(
        select(models.DocumentAnalysis)
        .order_by(models.DocumentAnalysis.created_at.desc())
        .offset(skip).limit(limit)
    )
    analyses = result.scalars().all()
    
    # Build summary responses
    summaries = []
    for a in analyses:
        summaries.append(schemas.DocumentAnalysisSummary(
            id=a.id,
            file_name=a.file_name,
            status=a.status.value if hasattr(a.status, 'value') else str(a.status),
            document_category=a.document_category,
            implemented_count=len(a.implemented_controls) if a.implemented_controls else 0,
            missing_count=len(a.missing_controls) if a.missing_controls else 0,
            created_at=a.created_at,
        ))
    return summaries


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


@router.post("/upload", response_model=schemas.DocumentAnalysisResponse)
async def upload_and_analyze_document(
    file: UploadFile = File(...),
    organization_id: str = Form(None),
    link_as_evidence: bool = Form(False),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Upload a document (PDF) and trigger AI analysis.
    
    The AI will extract:
    - Implemented controls (found in the document)
    - Missing controls (expected but not found)
    - Security practices mentioned
    
    Optionally link the document as Evidence for audit purposes.
    """
    # Validate file type
    allowed_types = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if file.content_type not in allowed_types and not file.filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
    
    # Read file
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    # Store the file
    file_key = await file_storage.upload(file_bytes, file.filename, file.content_type or "application/octet-stream")
    file_url = await file_storage.get_download_url(file_key)
    
    # Create evidence record if requested
    evidence_id = None
    if link_as_evidence:
        evidence = models.Evidence(
            title=f"Document: {file.filename}",
            description=f"AI-analyzed security document: {file.filename}",
            file_url=file_url,
            file_name=file.filename,
            file_type=file.filename.rsplit(".", 1)[-1] if "." in file.filename else "unknown",
            file_size=len(file_bytes),
            related_to=models.EvidenceRelatedTo.compliance_item,
            related_id=models.uuid.uuid4(),  # placeholder — can be updated later
            uploaded_by=current_user.id,
            organization_id=organization_id,
        )
        db.add(evidence)
        await db.flush()
        evidence_id = evidence.id
    
    # Create DocumentAnalysis record in "processing" state
    doc_analysis = models.DocumentAnalysis(
        organization_id=organization_id,
        file_name=file.filename,
        file_url=file_url,
        file_size=len(file_bytes),
        file_type=file.filename.rsplit(".", 1)[-1] if "." in file.filename else "unknown",
        uploaded_by=current_user.id,
        status=models.DocumentAnalysisStatus.processing,
        evidence_id=evidence_id,
    )
    db.add(doc_analysis)
    await db.flush()
    
    # Extract text from PDF
    try:
        extracted_text = extract_text_from_pdf(file_bytes)
        if not extracted_text.strip():
            doc_analysis.status = models.DocumentAnalysisStatus.failed
            doc_analysis.analysis_result = {"error": "Could not extract text from document"}
            await db.commit()
            await db.refresh(doc_analysis)
            raise HTTPException(status_code=422, detail="Could not extract any text from the uploaded document")
        
        doc_analysis.extracted_text = extracted_text
    except HTTPException:
        raise
    except Exception as e:
        doc_analysis.status = models.DocumentAnalysisStatus.failed
        doc_analysis.analysis_result = {"error": str(e)}
        await db.commit()
        await db.refresh(doc_analysis)
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")
    
    # Run AI analysis
    try:
        analysis_result = _run_document_analysis(extracted_text)
        
        doc_analysis.status = models.DocumentAnalysisStatus.completed
        doc_analysis.document_category = analysis_result.get("document_category", "general")
        doc_analysis.analysis_result = analysis_result
        doc_analysis.implemented_controls = analysis_result.get("implemented_controls", [])
        doc_analysis.missing_controls = analysis_result.get("missing_controls", [])
        doc_analysis.security_practices = analysis_result.get("security_practices", [])
        doc_analysis.analyzed_at = datetime.utcnow()
        
    except Exception as e:
        logger.error(f"AI analysis failed for {file.filename}: {e}")
        doc_analysis.status = models.DocumentAnalysisStatus.failed
        doc_analysis.analysis_result = {"error": f"AI analysis failed: {str(e)}"}
    
    await db.commit()
    await db.refresh(doc_analysis)
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
        analysis_result = _run_document_analysis(doc_analysis.extracted_text)
        
        doc_analysis.status = models.DocumentAnalysisStatus.completed
        doc_analysis.document_category = analysis_result.get("document_category", "general")
        doc_analysis.analysis_result = analysis_result
        doc_analysis.implemented_controls = analysis_result.get("implemented_controls", [])
        doc_analysis.missing_controls = analysis_result.get("missing_controls", [])
        doc_analysis.security_practices = analysis_result.get("security_practices", [])
        doc_analysis.analyzed_at = datetime.utcnow()
        
    except Exception as e:
        logger.error(f"Re-analysis failed: {e}")
        doc_analysis.status = models.DocumentAnalysisStatus.failed
        doc_analysis.analysis_result = {"error": f"Re-analysis failed: {str(e)}"}
    
    await db.commit()
    await db.refresh(doc_analysis)
    return doc_analysis


def _run_document_analysis(text: str) -> dict:
    """
    Run AI analysis on extracted document text.
    
    Two-stage pipeline:
    1. Gemini structured extraction (primary) — extracts security practices as named items
    2. Embedding similarity (validation + fallback) — maps practices to ISO controls
    """
    if not ai_service.is_ready:
        raise RuntimeError("AI Service is not ready")
    
    # Stage 1: Categorize the document
    category = ai_service._categorize(text)
    
    # Stage 2: Use evidence analysis for control mapping
    evidence_result = ai_service.analyze_evidence(text, top_n=93, threshold=0.25)
    
    # Classify controls as implemented (strong match) vs weak
    implemented = []
    weak_matches = []
    
    for match in evidence_result.matched_controls:
        item = {
            "control_annex": match.annex,
            "title": match.title,
            "confidence": match.confidence,
            "clause_id": match.clause_id,
        }
        if match.confidence >= 50:  # ≥50% = strong match → likely implemented
            implemented.append(item)
        elif match.confidence >= 30:  # 30-49% = weak match
            weak_matches.append(item)
    
    # Identify missing controls (no match at all)
    matched_annexes = {m.annex for m in evidence_result.matched_controls}
    missing = []
    for ctrl in ai_service._controls:
        if ctrl["annex"] not in matched_annexes:
            missing.append({
                "control_annex": ctrl["annex"],
                "title": ctrl["title"],
                "reason": "No reference found in document",
            })
    
    # Extract security practices (keyword-based)
    practices = _extract_security_practices(text)
    
    return {
        "document_category": category,
        "summary": evidence_result.summary,
        "implemented_controls": implemented,
        "weak_matches": weak_matches,
        "missing_controls": missing,
        "security_practices": practices,
        "total_controls_checked": len(ai_service._controls),
        "strong_matches": len(implemented),
        "weak_match_count": len(weak_matches),
        "missing_count": len(missing),
    }


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
