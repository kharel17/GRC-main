"""
AI API Endpoints – Exposes the AI service to the frontend.

Endpoints:
  POST /ai/analyze-evidence   → Analyze evidence text, return matched controls
  POST /ai/suggest-risk       → Suggest risk scores from a description
  GET  /ai/compliance-gaps    → Identify controls with no evidence coverage
  GET  /ai/status             → AI service health check
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
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
        model_name=ai_service.MODEL_NAME,
        controls_loaded=len(ai_service._controls),
        is_ready=ai_service.is_ready,
    )


@router.post("/analyze-evidence", response_model=EvidenceAnalysisResponse)
async def analyze_evidence(
    request: EvidenceAnalysisRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Analyze evidence text and return matched ISO 27001 controls.

    The AI compares the text semantically against all 93 ISO 27001 controls
    and returns the top matches with confidence scores.
    """
    if not ai_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="AI service is not initialized. Please wait for model loading."
        )

    try:
        result = ai_service.analyze_evidence(
            text=request.text,
            top_n=request.top_n,
            threshold=request.threshold,
        )
        return EvidenceAnalysisResponse(
            category=result.category,
            matched_controls=[
                ControlMatchResponse(**m.to_dict())
                for m in result.matched_controls
            ],
            summary=result.summary,
        )
    except Exception as e:
        logger.error(f"Evidence analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/suggest-risk", response_model=RiskSuggestionResponse)
async def suggest_risk(
    request: RiskSuggestionRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Analyze a risk description and suggest likelihood/impact scores.
    Also returns related ISO 27001 controls that could mitigate the risk.
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
        # Fetch all evidence descriptions from DB
        result = await db.execute(select(models.Evidence))
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
        gaps = ai_service.get_compliance_gaps(evidence_texts)
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
