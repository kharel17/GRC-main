from pydantic import BaseModel
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


class ControlMatchItem(BaseModel):
    control_annex: str
    title: str
    confidence: float
    excerpt: Optional[str] = None


class SecurityPracticeItem(BaseModel):
    practice: str
    related_controls: List[str] = []


class DocumentAnalysisResponse(BaseModel):
    id: UUID
    organization_id: UUID
    file_name: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    status: str
    document_category: Optional[str] = None
    analysis_result: Optional[Any] = None
    implemented_controls: Optional[List[Any]] = None
    missing_controls: Optional[List[Any]] = None
    security_practices: Optional[List[Any]] = None
    evidence_id: Optional[UUID] = None
    created_at: datetime
    analyzed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentAnalysisSummary(BaseModel):
    """Lightweight summary for list views."""
    id: UUID
    file_name: str
    status: str
    document_category: Optional[str] = None
    implemented_count: int = 0
    missing_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class RemediationCandidate(BaseModel):
    """Suggested risk & control candidate synthesized from a missing control gap."""
    candidate_id: str
    gap_title: str
    gap_annex: str
    gap_reason: Optional[str] = None
    framework_id: Optional[UUID] = None
    framework_name: Optional[str] = None
    framework_control_id: Optional[UUID] = None
    suggested_risk_title: str
    suggested_risk_description: str
    suggested_risk_likelihood: int = 3
    suggested_risk_impact: int = 3
    suggested_control_title: str
    suggested_control_description: str
    control_type: str = "preventive"
    owner_id: Optional[UUID] = None
    assessment_status: str = "ai_suggested"
    already_registered: bool = False


class CommitRemediationItem(BaseModel):
    """Approved candidate item submitted for registration."""
    candidate_id: Optional[str] = None
    framework_id: Optional[UUID] = None
    framework_control_id: Optional[UUID] = None
    risk_title: str
    risk_description: str
    likelihood: int = 3
    impact: int = 3
    control_title: str
    control_description: str
    control_type: str = "preventive"
    owner_id: Optional[UUID] = None


class CommitRemediationRequest(BaseModel):
    """Batch of approved remediation items to commit to Risk and Control registers."""
    items: List[CommitRemediationItem]


class CommitRemediationResponse(BaseModel):
    """Response confirming batch remediation registration."""
    success: bool = True
    committed_count: int
    created_risk_ids: List[UUID] = []
    created_control_ids: List[UUID] = []

