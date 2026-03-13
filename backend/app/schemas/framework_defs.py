from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class FrameworkControlBase(BaseModel):
    code: str
    title: str
    description: str
    category: Optional[str] = None

class FrameworkControlCreate(FrameworkControlBase):
    framework_id: UUID

class FrameworkControlResponse(FrameworkControlBase):
    id: UUID
    framework_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FrameworkBase(BaseModel):
    name: str
    version: str
    description: Optional[str] = None

class FrameworkCreate(FrameworkBase):
    pass

class FrameworkUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None

class FrameworkResponse(FrameworkBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FrameworkDetailResponse(FrameworkResponse):
    controls: List[FrameworkControlResponse] = []
