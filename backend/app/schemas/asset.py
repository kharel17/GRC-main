from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


class AssetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # data, software, hardware, service, personnel, physical, server, db, app
    classification: str = "internal"  # public, internal, confidential, restricted
    criticality: str = "medium"  # low, medium, high, critical
    location: Optional[str] = None
    confidentiality: str = "medium"  # low, medium, high
    integrity: str = "medium"
    availability: str = "medium"
    owner_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    classification: Optional[str] = None
    criticality: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None  # active, decommissioned, under_review
    confidentiality: Optional[str] = None
    integrity: Optional[str] = None
    availability: Optional[str] = None
    owner_id: Optional[UUID] = None


class AssetRiskLinkRequest(BaseModel):
    # Accept either a single risk_id OR a list of risk_ids for flexibility
    risk_id: Optional[UUID] = None
    risk_ids: Optional[List[UUID]] = None

    def get_risk_ids(self) -> List[UUID]:
        """Return a unified list of risk UUIDs regardless of which field was sent."""
        if self.risk_ids:
            return self.risk_ids
        if self.risk_id:
            return [self.risk_id]
        return []


class AssetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    type: str
    classification: str
    criticality: str
    location: Optional[str] = None
    status: str
    confidentiality: str
    integrity: str
    availability: str
    owner_id: Optional[UUID] = None  # Optional: protects against old rows with no owner
    related_risks: List[UUID] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("type", "classification", "criticality", "status",
                     "confidentiality", "integrity", "availability", mode="before")
    @classmethod
    def coerce_enum_to_str(cls, v: Any) -> str:
        """SQLAlchemy returns Python Enum objects; extract .value for JSON serialization."""
        return v.value if hasattr(v, "value") else str(v)

    @field_validator("related_risks", mode="before")
    @classmethod
    def extract_risk_ids(cls, v: Any) -> List[UUID]:
        if isinstance(v, list) and v and not isinstance(v[0], UUID):
            return [getattr(r, "id", r) for r in v]
        return v or []

    model_config = {"from_attributes": True}
