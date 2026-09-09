from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base
import enum
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB

class UserRole(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    analyst = "analyst"
    manager = "manager"
    control_owner = "control_owner"
    risk_owner = "risk_owner"
    compliance_officer = "compliance_officer"
    department_manager = "department_manager"
    executive = "executive"
    auditor = "auditor"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.admin)
    department: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_acting_admin: Mapped[int] = mapped_column(Integer, server_default='0', default=0)
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    permission_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("permission_profiles.id"), nullable=True)
    access_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True) # Used for time-boxed auditor guest windows

    # Invitation System
    invitation_status: Mapped[str] = mapped_column(String, default="pending", nullable=False) # pending, active, deactivated
    invitation_token_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    invitation_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Password Reset System
    reset_token_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # TOTP 2FA System
    totp_secret: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default='false')
    totp_backup_codes: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    organization_name: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Used during onboarding

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    risks_owned = relationship("Risk", foreign_keys="Risk.owner_id", back_populates="owner")
    risks_created = relationship("Risk", foreign_keys="Risk.created_by", back_populates="creator")
    tickets_assigned = relationship("Ticket", foreign_keys="Ticket.assigned_to_id", back_populates="assignee")
    audit_logs = relationship("AuditLog", back_populates="user")
    organization = relationship("Organization", foreign_keys=[organization_id])
    permission_profile = relationship("PermissionProfile", back_populates="users", foreign_keys=[permission_profile_id])
    
    manager = relationship("User", remote_side=[id], foreign_keys=[manager_id], back_populates="subordinates")
    subordinates = relationship("User", back_populates="manager", foreign_keys=[manager_id])
    
    invited_by_user = relationship("User", remote_side=[id], foreign_keys=[invited_by], back_populates="invites_sent")
    invites_sent = relationship("User", back_populates="invited_by_user", foreign_keys=[invited_by])
