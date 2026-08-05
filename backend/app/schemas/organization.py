from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
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
    framework_id: Optional[UUID] = None
    isms_scope: Optional[str] = None
    employee_count: Optional[str] = None  # Range string e.g. "1-50", "51-200"
    risk_appetite: Optional[dict] = None
    compliance_target_date: Optional[datetime] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    compliance_frameworks: Optional[List[str]] = None
    primary_contact_id: Optional[UUID] = None
    framework_id: Optional[UUID] = None
    isms_scope: Optional[str] = None
    employee_count: Optional[str] = None  # Range string e.g. "1-50", "51-200"
    risk_appetite: Optional[dict] = None
    compliance_target_date: Optional[datetime] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


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
    framework_id: Optional[UUID] = None
    isms_scope: Optional[str] = None
    employee_count: Optional[str] = None  # Range string e.g. "1-50", "51-200"
    risk_appetite: Optional[dict] = None
    compliance_target_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)
