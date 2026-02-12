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
    uploaded_by: UUID

class EvidenceCreate(EvidenceBase):
    pass

class EvidenceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    verified: Optional[bool] = None
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None

class EvidenceInDBBase(EvidenceBase):
    id: UUID
    uploaded_at: datetime
    verified: bool
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Evidence(EvidenceInDBBase):
    pass
