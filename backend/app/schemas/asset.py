from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


class AssetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    asset_type: str  # data, software, hardware, service, personnel, physical, server, db, app
    classification: str = "internal"  # public, internal, confidential, restricted
    criticality: str = "medium"  # low, medium, high, critical
    location: Optional[str] = None
    owner_id: UUID
    organization_id: UUID


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    asset_type: Optional[str] = None
    classification: Optional[str] = None
    criticality: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None  # active, decommissioned, under_review
    owner_id: Optional[UUID] = None


class AssetRiskLinkRequest(BaseModel):
    risk_ids: List[UUID]


class AssetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    asset_type: str
    classification: str
    criticality: str
    location: Optional[str] = None
    status: str
    owner_id: UUID
    related_risks: List[UUID] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("related_risks", mode="before")
    @classmethod
    def extract_risk_ids(cls, v: Any) -> List[UUID]:
        if isinstance(v, list) and v and not isinstance(v[0], UUID):
            return [getattr(r, "id", r) for r in v]
        return v

    model_config = {"from_attributes": True}
