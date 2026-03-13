from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Text, Integer, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from .base import Base

class EvidenceRelatedTo(str, enum.Enum):
    risk = "risk"
    control = "control"
    compliance_item = "compliance_item"

class EvidenceStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    expired = "expired"


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    status = Column(SAEnum(EvidenceStatus), default=EvidenceStatus.pending, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    related_to = Column(SAEnum(EvidenceRelatedTo), nullable=False)
    related_id = Column(UUID(as_uuid=True), nullable=False)
    
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    verified = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # AI Analysis fields
    ai_category = Column(String, nullable=True)  # e.g., "policy", "procedure", "log", "certificate"
    ai_analyzed = Column(Boolean, default=False)
    ai_analyzed_at = Column(DateTime, nullable=True)

    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])
    verifier = relationship("User", foreign_keys=[verified_by])
    related_compliance_item = relationship("ComplianceItem", foreign_keys=[related_id], primaryjoin="and_(Evidence.related_id == ComplianceItem.id, Evidence.related_to == 'compliance_item')", viewonly=True, sync_backref=False)
    ai_control_matches = relationship("EvidenceControlMatch", back_populates="evidence", cascade="all, delete-orphan")


class EvidenceControlMatch(Base):
    """Stores AI-generated mappings between evidence and ISO 27001 controls."""
    __tablename__ = "evidence_control_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=False)
    control_id = Column(String, nullable=False)       # e.g., "5.15"
    control_title = Column(String, nullable=False)     # e.g., "Access control"
    confidence_score = Column(Integer, nullable=False)  # 0-100 percentage
    matched_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    evidence = relationship("Evidence", back_populates="ai_control_matches")
