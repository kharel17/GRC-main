from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from app.models.control import ControlType, ControlEffectiveness, ControlStatus

class ControlBase(BaseModel):
    title: str
    description: str
    control_type: ControlType
    effectiveness: ControlEffectiveness
    status: ControlStatus = ControlStatus.planned
    owner_id: str

class ControlCreate(ControlBase):
    pass

class ControlUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    control_type: Optional[ControlType] = None
    effectiveness: Optional[ControlEffectiveness] = None
    status: Optional[ControlStatus] = None
    owner_id: Optional[str] = None

class ControlInDBBase(ControlBase):
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Control(ControlInDBBase):
    pass
