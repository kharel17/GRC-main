from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ControlApplicabilityCreate(BaseModel):
    organization_id: UUID
    framework_id: Optional[UUID] = None
    control_annex: str  # e.g. "5.1", "8.12"
    is_applicable: bool = True
    status: str = "not_started"  # not_started, in_progress, implemented, not_applicable
    justification: Optional[str] = None
    responsible_id: Optional[UUID] = None
    notes: Optional[str] = None


class ControlApplicabilityUpdate(BaseModel):
    is_applicable: Optional[bool] = None
    status: Optional[str] = None
    justification: Optional[str] = None
    responsible_id: Optional[UUID] = None
    notes: Optional[str] = None


class ControlApplicabilityResponse(BaseModel):
    id: UUID
    organization_id: UUID
    framework_id: Optional[UUID] = None
    control_annex: str
    is_applicable: bool
    status: str
    justification: Optional[str] = None
    responsible_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ControlApplicabilityBulkCreate(BaseModel):
    """Used to initialize all 93 controls for an organization at once."""
    organization_id: UUID
    framework_id: Optional[str] = None
    # If not provided, all 93 controls will be initialized as applicable + not_started
    overrides: Optional[dict] = None  # e.g. {"5.1": {"is_applicable": False, "justification": "..."}}
