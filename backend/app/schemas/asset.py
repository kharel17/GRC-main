from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class AssetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    asset_type: str  # data, software, hardware, service, personnel, physical
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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
