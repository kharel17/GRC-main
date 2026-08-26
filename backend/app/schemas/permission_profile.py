from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict
from uuid import UUID

class PermissionProfileBase(BaseModel):
    name: str
    description: Optional[str] = None
    nav_permissions: Dict[str, bool] = {}

class PermissionProfileCreate(PermissionProfileBase):
    pass

class PermissionProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nav_permissions: Optional[Dict[str, bool]] = None

class PermissionProfileResponse(PermissionProfileBase):
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserProfileAssignRequest(BaseModel):
    user_id: UUID
    permission_profile_id: Optional[UUID] = None
