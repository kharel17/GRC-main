from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from app.models.compliance import ComplianceStatus, CompliancePriority

class ComplianceItemBase(BaseModel):
    framework: str
    requirement_id: str
    title: str
    description: str
    status: ComplianceStatus = ComplianceStatus.not_started
    priority: CompliancePriority = CompliancePriority.medium
    due_date: Optional[datetime] = None
    owner_id: UUID

class ComplianceItemCreate(ComplianceItemBase):
    pass

class ComplianceItemUpdate(BaseModel):
    framework: Optional[str] = None
    requirement_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ComplianceStatus] = None
    priority: Optional[CompliancePriority] = None
    due_date: Optional[datetime] = None
    owner_id: Optional[UUID] = None

class ComplianceItemInDBBase(ComplianceItemBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ComplianceItem(ComplianceItemInDBBase):
    pass
