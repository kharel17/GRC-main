from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID
from app.models.user import UserRole

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = UserRole.admin
    department: Optional[str] = None
    is_active: Optional[bool] = True
    manager_id: Optional[UUID] = None
    is_acting_admin: Optional[int] = 0
    access_expires_at: Optional[datetime] = None

# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    full_name: str
    password: str

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None

from .permission_profile import PermissionProfileResponse

class UserInDBBase(UserBase):
    id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    permission_profile_id: Optional[UUID] = None
    permission_profile: Optional[PermissionProfileResponse] = None
    access_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Additional properties to return via API
class User(UserInDBBase):
    pass

# Additional properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str

# Schema for accepting an invitation
class UserAcceptInvite(BaseModel):
    token: str
    password: str

# Schema for requesting a password reset
class ForgotPassword(BaseModel):
    email: EmailStr

# Schema for resetting password with a token
class ResetPassword(BaseModel):
    token: str
    password: str
