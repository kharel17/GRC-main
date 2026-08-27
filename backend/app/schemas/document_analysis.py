from pydantic import BaseModel
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


class ControlMatchItem(BaseModel):
    control_annex: str
    title: str
    confidence: float
    excerpt: Optional[str] = None


class PolicyChunkItem(BaseModel):
    chunk_id: str
    section_heading: str = "General"
    page_number: int = 1
    excerpt: str
    confidence: float


class PolicyControlMappingItem(BaseModel):
    control_annex: str
    title: str
    clause_id: Optional[str] = None
    mapping_status: str = "suggested"  # suggested, confirmed, manually_edited, rejected
    confirmed_by: Optional[UUID] = None
    confirmed_at: Optional[datetime] = None
    composite_confidence: float = 0.0
    policy_chunks: List[PolicyChunkItem] = []


class PolicyMappingUpdateRequest(BaseModel):
    mappings: List[PolicyControlMappingItem]


class DocumentAnalysisResponse(BaseModel):
    id: UUID
    organization_id: UUID
    file_name: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    status: str
    document_category: Optional[str] = None
    source_type: str = "evidence"
    policy_control_mappings: Optional[List[PolicyControlMappingItem]] = None
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
    source_type: str = "evidence"
    implemented_count: int = 0
    missing_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
