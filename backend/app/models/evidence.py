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


from typing import Optional, List
from sqlalchemy.orm import relationship, Mapped, mapped_column

class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    status: Mapped[EvidenceStatus] = mapped_column(SAEnum(EvidenceStatus), default=EvidenceStatus.pending, nullable=False)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    related_to: Mapped[EvidenceRelatedTo] = mapped_column(SAEnum(EvidenceRelatedTo), nullable=False)
    related_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # AI Analysis fields
    ai_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., "policy", "procedure", "log", "certificate"
    ai_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
