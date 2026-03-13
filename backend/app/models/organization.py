from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Text, Integer
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


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    size = Column(SAEnum(OrganizationSize), nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    country = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    
    # Detailed risk levels per risk type
    risk_appetite = Column(JSONB, nullable=True)
    
    # Milestone for compliance
    compliance_target_date = Column(DateTime, nullable=True)

    # Framework linkage
    framework_id = Column(UUID(as_uuid=True), ForeignKey("frameworks.id"), nullable=True)
    isms_scope = Column(Text, nullable=True)

    # Compliance frameworks the org is targeting (e.g. ["ISO 27001", "SOC2", "GDPR"])
    compliance_frameworks = Column(JSONB, default=list, nullable=False)

    primary_contact_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    primary_contact = relationship("User", foreign_keys=[primary_contact_id])
    framework = relationship("Framework", back_populates="organizations")
    assets = relationship("Asset", back_populates="organization", cascade="all, delete-orphan")
    control_applicabilities = relationship("ControlApplicability", back_populates="organization", cascade="all, delete-orphan")
