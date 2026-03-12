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
