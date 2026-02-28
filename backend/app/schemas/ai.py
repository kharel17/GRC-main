"""Pydantic schemas for AI service request/response validation."""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Evidence Analysis
# ---------------------------------------------------------------------------

class EvidenceAnalysisRequest(BaseModel):
    """Request to analyze evidence text against ISO 27001 controls."""
    text: str = Field(..., min_length=10, description="Evidence document text content")
    top_n: int = Field(5, ge=1, le=20, description="Maximum number of control matches")
    threshold: float = Field(0.30, ge=0.0, le=1.0, description="Minimum confidence threshold (0-1)")


class ControlMatchResponse(BaseModel):
    """A single matched ISO 27001 control."""
    control_id: str
    annex: str
    title: str
    description: str
    clause_id: str
    confidence: float = Field(..., description="Confidence score 0-100%")


class EvidenceAnalysisResponse(BaseModel):
    """Full response of evidence analysis."""
    category: str
    matched_controls: list[ControlMatchResponse]
    summary: str


# ---------------------------------------------------------------------------
# Risk Suggestion
# ---------------------------------------------------------------------------

class RiskSuggestionRequest(BaseModel):
    """Request to get AI-suggested risk scores."""
    description: str = Field(..., min_length=10, description="Risk description text")


class RiskSuggestionResponse(BaseModel):
    """AI-suggested risk scoring."""
    likelihood: int = Field(..., ge=1, le=5)
    impact: int = Field(..., ge=1, le=5)
    risk_score: int = Field(..., ge=1, le=25)
    reasoning: str
    related_controls: list[str]


# ---------------------------------------------------------------------------
# Compliance Gaps
# ---------------------------------------------------------------------------

class ComplianceGapItem(BaseModel):
    """A control with no matching evidence."""
    control_id: str
    annex: str
    title: str
    best_match_score: float = Field(0.0, description="Best evidence match score 0-100%")


class ComplianceGapResponse(BaseModel):
    """List of controls missing evidence coverage."""
    total_controls: int
    covered_controls: int
    gap_controls: int
    compliance_rate: float = Field(..., description="Percentage of controls covered")
    gaps: list[ComplianceGapItem]


# ---------------------------------------------------------------------------
# AI Service Status
# ---------------------------------------------------------------------------

class AIStatusResponse(BaseModel):
    """Health check for the AI service."""
    status: str
    model_name: str
    active_engine: str = Field("local", description="Active AI engine: 'gemini' or 'local'")
    controls_loaded: int
    is_ready: bool
