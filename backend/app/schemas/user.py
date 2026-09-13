from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID
from app.models.user import UserRole

# Shared properties
class UserBase(BaseModel):
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
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

from .permission_profile import PermissionProfileResponse

class UserInDBBase(UserBase):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    permission_profile_id: Optional[UUID] = None
    permission_profile: Optional[PermissionProfileResponse] = None
    access_expires_at: Optional[datetime] = None
    totp_enabled: Optional[bool] = False
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
    password: Optional[str] = None  # Optional for SSO-only organizations

# Schema for requesting a password reset
class ForgotPassword(BaseModel):
    email: EmailStr

# Schema for resetting password with a token
class ResetPassword(BaseModel):
    token: str
    password: str

# ── 2FA Schemas ───────────────────────────────────────────────
class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str
    provisioning_uri: str

class TOTPVerifyRequest(BaseModel):
    code: str

class TOTPLoginVerifyRequest(BaseModel):
    two_fa_token: str
    code: str

class TOTPDisableRequest(BaseModel):
    code: str
    password: Optional[str] = None

class TOTPStatusResponse(BaseModel):
    totp_enabled: bool
    is_mandatory: bool
    has_backup_codes: bool
