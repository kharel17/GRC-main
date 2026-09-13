from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


VALID_AUTH_PROVIDERS = ("any", "microsoft", "google")


class OrganizationCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None  # small, medium, large, enterprise
    auth_provider: Optional[str] = "any"  # any, microsoft, google
    description: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    compliance_frameworks: List[str] = Field(default_factory=list)
    primary_contact_id: Optional[UUID] = None
    framework_id: Optional[UUID] = None
    isms_scope: Optional[str] = None
    employee_count: Optional[str] = None  # Range string e.g. "1-50", "51-200"
    infrastructure: Optional[str] = None  # e.g. "AWS, Azure"
    data_types: Optional[str] = None      # e.g. "PII, Financial"
    risk_appetite: Optional[dict] = None
    compliance_target_date: Optional[datetime] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("size", mode="before")
    @classmethod
    def normalize_size(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            v_clean = v.strip().lower()
            return v_clean if v_clean else None
        return v

    @field_validator("auth_provider", mode="before")
    @classmethod
    def normalize_auth_provider(cls, v: Any) -> Optional[str]:
        if v is None:
            return "any"
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean not in VALID_AUTH_PROVIDERS:
                raise ValueError(f"auth_provider must be one of {VALID_AUTH_PROVIDERS}")
            return v_clean
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    auth_provider: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    compliance_frameworks: Optional[List[str]] = None
    primary_contact_id: Optional[UUID] = None
    framework_id: Optional[UUID] = None
    isms_scope: Optional[str] = None
    employee_count: Optional[str] = None  # Range string e.g. "1-50", "51-200"
    infrastructure: Optional[str] = None
    data_types: Optional[str] = None
    risk_appetite: Optional[dict] = None
    compliance_target_date: Optional[datetime] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("size", mode="before")
    @classmethod
    def normalize_size(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            v_clean = v.strip().lower()
            return v_clean if v_clean else None
        return v

    @field_validator("auth_provider", mode="before")
    @classmethod
    def normalize_auth_provider(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean not in VALID_AUTH_PROVIDERS:
                raise ValueError(f"auth_provider must be one of {VALID_AUTH_PROVIDERS}")
            return v_clean
        return v


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    auth_provider: str = "any"
    description: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    compliance_frameworks: List[str] = Field(default_factory=list)
    primary_contact_id: Optional[UUID] = None
    framework_id: Optional[UUID] = None
    isms_scope: Optional[str] = None
    employee_count: Optional[str] = None  # Range string e.g. "1-50", "51-200"
    infrastructure: Optional[str] = None
    data_types: Optional[str] = None
    risk_appetite: Optional[dict] = None
    compliance_target_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)
