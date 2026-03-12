from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class OrganizationCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None  # small, medium, large, enterprise
    description: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    compliance_frameworks: List[str] = Field(default_factory=list)
    primary_contact_id: Optional[UUID] = None
    employee_count: Optional[int] = None
    risk_appetite: Optional[dict] = None
    compliance_target_date: Optional[datetime] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    compliance_frameworks: Optional[List[str]] = None
    primary_contact_id: Optional[UUID] = None
    employee_count: Optional[int] = None
    risk_appetite: Optional[dict] = None
    compliance_target_date: Optional[datetime] = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    compliance_frameworks: List[str] = Field(default_factory=list)
    primary_contact_id: Optional[UUID] = None
    employee_count: Optional[int] = None
    risk_appetite: Optional[dict] = None
    compliance_target_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
