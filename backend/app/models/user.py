from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base
import enum
import uuid
from sqlalchemy.dialects.postgresql import UUID

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.admin)
    department = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    token_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_acting_admin = Column(Integer, server_default='0', default=0)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    # Invitation System
    invitation_status = Column(String, default="pending", nullable=False) # pending, active, deactivated
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invited_at = Column(DateTime, nullable=True)
    organization_name = Column(String, nullable=True) # Used during onboarding

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    risks_owned = relationship("Risk", foreign_keys="Risk.owner_id", back_populates="owner")
    risks_created = relationship("Risk", foreign_keys="Risk.created_by", back_populates="creator")
    tickets_assigned = relationship("Ticket", foreign_keys="Ticket.assigned_to_id", back_populates="assignee")
    audit_logs = relationship("AuditLog", back_populates="user")
    organization = relationship("Organization", foreign_keys=[organization_id])
    
    manager = relationship("User", remote_side=[id], foreign_keys=[manager_id], back_populates="subordinates")
    subordinates = relationship("User", back_populates="manager", foreign_keys=[manager_id])
    
    invited_by_user = relationship("User", remote_side=[id], foreign_keys=[invited_by], back_populates="invites_sent")
    invites_sent = relationship("User", back_populates="invited_by_user", foreign_keys=[invited_by])
