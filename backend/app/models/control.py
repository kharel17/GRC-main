from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Text, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from typing import Optional
from .base import Base

class ControlType(str, enum.Enum):
    preventive = "preventive"
    detective = "detective"
    corrective = "corrective"

class ControlEffectiveness(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class ControlStatus(str, enum.Enum):
    planned = "planned"
    implemented = "implemented"
    under_review = "under_review"


class Control(Base):
    __tablename__ = "controls"
    __table_args__ = (
        Index("ix_controls_org_framework_ctrl", "organization_id", "framework_control_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    control_type: Mapped[ControlType] = mapped_column(SAEnum(ControlType), nullable=False)
    effectiveness: Mapped[ControlEffectiveness] = mapped_column(SAEnum(ControlEffectiveness), nullable=False)
    status: Mapped[ControlStatus] = mapped_column(SAEnum(ControlStatus), default=ControlStatus.planned)
    
    linked_risk_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("risks.id"), nullable=True)
    
    # Audit Provenance & Assessment Flags
    source: Mapped[Optional[str]] = mapped_column(String, default="manual", server_default="manual", nullable=True)
    source_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_analyses.id", ondelete="SET NULL"), nullable=True
    )
    assessment_status: Mapped[str] = mapped_column(
        String, default="human_verified", server_default="human_verified", nullable=False
    )

    # Relational Framework Links
    framework_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frameworks.id", ondelete="SET NULL"), nullable=True
    )
    framework_control_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("framework_controls.id", ondelete="SET NULL"), nullable=True
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    creator = relationship("User", foreign_keys=[created_by])
    organization = relationship("Organization")
    risk_mappings = relationship("RiskControlMapping", back_populates="control")
    framework = relationship("Framework", foreign_keys=[framework_id])
    framework_control = relationship("FrameworkControl", foreign_keys=[framework_control_id])
    source_document = relationship("DocumentAnalysis", foreign_keys=[source_document_id])


class RiskControlMapping(Base):
    __tablename__ = "risk_control_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_id = Column(UUID(as_uuid=True), ForeignKey("risks.id"), nullable=False)
    control_id = Column(UUID(as_uuid=True), ForeignKey("controls.id"), nullable=True)
    framework_control_id = Column(UUID(as_uuid=True), ForeignKey("framework_controls.id"), nullable=True)
    
    residual_likelihood = Column(Integer, nullable=True)
    residual_impact = Column(Integer, nullable=True)
    residual_risk_score = Column(Integer, nullable=True)
    
    mapped_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    mapped_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    risk = relationship("Risk", backref="control_mappings")
    control = relationship("Control", back_populates="risk_mappings")
    mapper = relationship("User", foreign_keys=[mapped_by])
