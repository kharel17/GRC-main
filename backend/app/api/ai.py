"""
AI API Endpoints – Exposes the AI service to the frontend.

Endpoints:
  POST /ai/analyze-evidence      → Analyze evidence text, return matched controls
  POST /ai/analyze-evidence-pdf  → Upload a PDF, extract text, analyze it
  POST /ai/suggest-risk          → Suggest risk scores from a description
  GET  /ai/compliance-gaps       → Identify controls with no evidence coverage
  GET  /ai/status                → AI service health check
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.services.ai_service import ai_service
from app.schemas.ai import (
    EvidenceAnalysisRequest,
    EvidenceAnalysisResponse,
    ControlMatchResponse,
    RiskSuggestionRequest,
    RiskSuggestionResponse,
    ComplianceGapItem,
    ComplianceGapResponse,
    AIStatusResponse,
)
from app import models

logger = logging.getLogger("grc.ai")

router = APIRouter()


@router.get("/status", response_model=AIStatusResponse)
async def ai_status():
    """Check if the AI service is loaded and ready."""
    return AIStatusResponse(
        status="ready" if ai_service.is_ready else "not_initialized",
        model_name=ai_service.LOCAL_MODEL_NAME,
        active_engine=ai_service.active_engine,
    )


from app.services.orchestrator import run_grc_pipeline


@router.post("/analyze-evidence", response_model=EvidenceAnalysisResponse)
async def analyze_evidence(
    request: EvidenceAnalysisRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Analyze evidence text and return matched ISO 27001 controls via LangGraph Orchestrator.

    Executes hybrid retrieval (Dense Qdrant + BM25 + RRF + Reranker), confidence gating,
    LLM generation, and citation verification.

    Verdict gating:
      accept               → matched_controls from orchestrator's verified top chunks
      needs_review         → empty matched_controls, response flagged [NEEDS_REVIEW]
      insufficient_evidence→ empty matched_controls, response flagged [INSUFFICIENT_EVIDENCE]
    """
    if not ai_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="AI service is not initialized. Please wait for model loading."
        )

    try:
        # Invoke LangGraph Orchestrator — this is the single analysis path.
        orchestration = await run_grc_pipeline(
            query=request.text,
            org_id=str(current_user.organization_id),
        )
        verdict = orchestration.get("verdict", "insufficient_evidence")
        final_out = orchestration.get("final_output") or orchestration
        generation = final_out.get("result") or {}
        confidence_reason = (orchestration.get("confidence_decision") or {}).get(
            "reason", ""
        )

        if verdict == "accept":
            # Return the orchestrator's grounded, citation-verified controls.
            raw_implemented = generation.get("implemented_controls") or []
            # Normalise shape: cloud/self-hosted return plain strings (annex IDs);
            # local-only returns dicts with control_annex/title/confidence.
            matched: list[ControlMatchResponse] = []
            for c in raw_implemented:
                if isinstance(c, dict):
                    # LocalOnly shape: {"control_annex": "5.1", "title": "...", "confidence": 85.0}
                    matched.append(ControlMatchResponse(
                        control_id=c.get("control_annex", ""),
                        title=c.get("title", ""),
                        description=c.get("title", ""),
                        confidence=float(c.get("confidence", 1.0)),
                        excerpt=c.get("excerpt", ""),
                    ))
                elif isinstance(c, str) and c.strip():
                    # Cloud/self-hosted shape: plain annex ID string e.g. "5.1"
                    matched.append(ControlMatchResponse(
                        control_id=c.strip(),
                        title=c.strip(),
                        description="",
                        confidence=1.0,
                        excerpt="",
                    ))
                # else: skip malformed entries silently
            summary = generation.get("summary") or "[ACCEPT] High-confidence match verified."
            category = generation.get("document_category", "general")

        elif verdict == "needs_review":
            # Gate fires: return no controls — human must verify before results are trusted.
            matched = []
            summary = (
                f"[NEEDS_REVIEW] Retrieval confidence below threshold — "
                f"results require human review before use. Reason: {confidence_reason}"
            )
            category = "general"

        else:  # insufficient_evidence
            matched = []
            summary = (
                f"[INSUFFICIENT_EVIDENCE] No compliance controls could be matched "
                f"with sufficient confidence. Reason: {confidence_reason}"
            )
            category = "general"

        return EvidenceAnalysisResponse(
            category=category,
            matched_controls=matched,
            summary=summary,
        )
    except Exception as e:
        logger.error(f"Evidence analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze-evidence-pdf", response_model=EvidenceAnalysisResponse)
async def analyze_evidence_pdf(
    file: UploadFile = File(..., description="PDF file to analyze"),
    top_n: int = Query(5, ge=1, le=20),
    threshold: float = Query(0.30, ge=0.0, le=1.0),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Upload a PDF file, extract text, and analyze via LangGraph Orchestrator pipeline.
    """
    if not ai_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="AI service is not initialized. Please wait for model loading."
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf file."
        )

    try:
        file_bytes = await file.read()

        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        from app.ingestion.extractor import extract_pages_from_bytes
        pages = extract_pages_from_bytes(file_bytes, file.filename)
        extracted_text = "\n\n".join([p.text for p in pages if p.text])

        if not extracted_text:
            result = ai_service.analyze_evidence_pdf(
                file_bytes=file_bytes,
                top_n=top_n,
                threshold=threshold,
            )
            return EvidenceAnalysisResponse(
                category=result.category,
                matched_controls=[ControlMatchResponse(**m.to_dict()) for m in result.matched_controls],
                summary=result.summary,
            )

        orchestration = await run_grc_pipeline(
            query=extracted_text[:1000],
            org_id=str(current_user.organization_id),
        )
        verdict = orchestration.get("verdict", "insufficient_evidence")
        final_out = orchestration.get("final_output") or orchestration
        generation = final_out.get("result") or {}
        confidence_reason = (orchestration.get("confidence_decision") or {}).get(
            "reason", ""
        )

        if verdict == "accept":
            raw_implemented = generation.get("implemented_controls") or []
            matched: list[ControlMatchResponse] = []
            for c in raw_implemented:
                if isinstance(c, dict):
                    matched.append(ControlMatchResponse(
                        control_id=c.get("control_annex", ""),
                        title=c.get("title", ""),
                        description=c.get("title", ""),
                        confidence=float(c.get("confidence", 1.0)),
                        excerpt=c.get("excerpt", ""),
                    ))
                elif isinstance(c, str) and c.strip():
                    matched.append(ControlMatchResponse(
                        control_id=c.strip(),
                        title=c.strip(),
                        description="",
                        confidence=1.0,
                        excerpt="",
                    ))
            summary = generation.get("summary") or "[ACCEPT] High-confidence match verified."
            category = generation.get("document_category", "general")

        elif verdict == "needs_review":
            matched = []
            summary = (
                f"[NEEDS_REVIEW] Retrieval confidence below threshold — "
                f"results require human review before use. Reason: {confidence_reason}"
            )
            category = "general"

        else:  # insufficient_evidence
            matched = []
            summary = (
                f"[INSUFFICIENT_EVIDENCE] No compliance controls could be matched "
                f"with sufficient confidence. Reason: {confidence_reason}"
            )
            category = "general"

        return EvidenceAnalysisResponse(
            category=category,
            matched_controls=matched,
            summary=summary,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"PDF evidence analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/suggest-risk", response_model=RiskSuggestionResponse)
async def suggest_risk(
    request: RiskSuggestionRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Analyze a risk description and suggest likelihood/impact scores.
    Also returns related ISO 27001 controls that could mitigate the risk.

    Uses Gemini AI for intelligent scoring when available, falls back to
    embedding-based heuristics otherwise.
    """
    if not ai_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="AI service is not initialized."
        )

    try:
        result = ai_service.suggest_risk_score(request.description)
        return RiskSuggestionResponse(**result.to_dict())
    except Exception as e:
        logger.error(f"Risk suggestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestion failed: {str(e)}")


@router.get("/compliance-gaps", response_model=ComplianceGapResponse)
async def compliance_gaps(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Identify ISO 27001 controls that have no matching evidence.

    Fetches all evidence from the database, runs AI comparison,
    and returns controls that fall below the coverage threshold.
    """
    if not ai_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="AI service is not initialized."
        )

    try:
        # Fetch evidence descriptions for current_user's organization only
        result = await db.execute(
            select(models.Evidence).where(models.Evidence.organization_id == current_user.organization_id)
        )
        all_evidence = result.scalars().all()

        evidence_texts = []
        for ev in all_evidence:
            text_parts = []
            if ev.title:
                text_parts.append(ev.title)
            if ev.description:
                text_parts.append(ev.description)
            if text_parts:
                evidence_texts.append(". ".join(text_parts))

        # Run gap analysis
        gaps = await ai_service.get_compliance_gaps(evidence_texts)
        total_controls = len(ai_service._controls)
        gap_count = len(gaps)
        covered = total_controls - gap_count

        return ComplianceGapResponse(
            total_controls=total_controls,
            covered_controls=covered,
            gap_controls=gap_count,
            compliance_rate=round((covered / total_controls) * 100, 1) if total_controls > 0 else 0,
            gaps=[ComplianceGapItem(**g) for g in gaps],
        )
    except Exception as e:
        logger.error(f"Compliance gap analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gap analysis failed: {str(e)}")
