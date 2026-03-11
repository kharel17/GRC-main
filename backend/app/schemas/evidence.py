from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from app.models.evidence import EvidenceRelatedTo


class EvidenceBase(BaseModel):
    title: str
    description: Optional[str] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    related_to: EvidenceRelatedTo
    related_id: UUID


class EvidenceCreate(EvidenceBase):
    uploaded_by: UUID


class EvidenceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    verified: Optional[bool] = None
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None


class EvidenceStatusUpdate(BaseModel):
    """Body for PATCH /evidence/{id}/status"""
    status: str  # "active", "expired", "rejected"
    review_notes: Optional[str] = None
    valid_until: Optional[datetime] = None


class EvidenceInDBBase(EvidenceBase):
    id: UUID
    uploaded_by: UUID
    uploaded_at: datetime
    verified: bool
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    status: Optional[str] = None
    valid_until: Optional[datetime] = None
    ai_category: Optional[str] = None
    ai_analyzed: Optional[bool] = None

    class Config:
        from_attributes = True


class Evidence(EvidenceInDBBase):
    pass
