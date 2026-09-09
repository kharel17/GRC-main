from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Text, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum
from .base import Base


class OrganizationSize(str, enum.Enum):
    small = "small"           # 1-50 employees
    medium = "medium"         # 51-250 employees
    large = "large"           # 251-1000 employees
    enterprise = "enterprise" # 1000+ employees


from typing import Optional, List, Any
from sqlalchemy.orm import relationship, Mapped, mapped_column

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    size: Mapped[Optional[OrganizationSize]] = mapped_column(SAEnum(OrganizationSize), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    employee_count: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Range e.g. "1-50"
    
    # Onboarding Details
    infrastructure: Mapped[Optional[str]] = mapped_column(String, nullable=True) # AWS, Azure, On-premise, etc.
    data_types: Mapped[Optional[str]] = mapped_column(String, nullable=True) # PII, Financial, etc.
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Detailed risk levels per risk type
    risk_appetite: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    
    # Milestone for compliance
    compliance_target_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Framework linkage
    framework_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("frameworks.id"), nullable=True)
    isms_scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Compliance frameworks the org is targeting (e.g. ["ISO 27001", "SOC2", "GDPR"])
    compliance_frameworks: Mapped[Any] = mapped_column(JSONB, default=list, nullable=False)

    # Ticket triggering and escalation settings
    ticket_settings: Mapped[Any] = mapped_column(JSONB, default={
        "severity_threshold": "medium",
        "suppression_window_hours": 24,
        "auto_escalation_enabled": True,
        "sla_config": {
            "critical": 24,
            "high": 48,
            "medium": 120, # 5 days
            "low": 240     # 10 days
        }
    }, nullable=False)

    primary_contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    primary_contact = relationship("User", foreign_keys=[primary_contact_id])
    framework = relationship("Framework", back_populates="organizations")
    assets = relationship("Asset", back_populates="organization", cascade="all, delete-orphan")
    control_applicabilities = relationship("ControlApplicability", back_populates="organization", cascade="all, delete-orphan")
