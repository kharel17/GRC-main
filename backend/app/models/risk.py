from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Text, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from typing import Optional
from .base import Base

class RiskStatus(str, enum.Enum):
    identified = "identified"
    assessed = "assessed"
    mitigated = "mitigated"
    accepted = "accepted"

class RiskCategory(Base):
    __tablename__ = "risk_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)
    color = Column(String, nullable=False)

class Risk(Base):
    __tablename__ = "risks"
    __table_args__ = (
        Index("ix_risks_org_source_doc", "organization_id", "source_document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("risk_categories.id"), nullable=True)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    
    threat: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vulnerability: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    likelihood: Mapped[int] = mapped_column(Integer, nullable=False)
    impact: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RiskStatus] = mapped_column(SAEnum(RiskStatus), default=RiskStatus.identified)
    
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    # Audit Provenance & Assessment Flags
    source: Mapped[Optional[str]] = mapped_column(String, default="manual", server_default="manual", nullable=True)
    source_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("document_analyses.id", ondelete="SET NULL"), nullable=True)
    assessment_status: Mapped[str] = mapped_column(String, default="human_verified", server_default="human_verified", nullable=False)

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("RiskCategory", foreign_keys=[category_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    asset = relationship("Asset", back_populates="risks")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="risks_owned")
    creator = relationship("User", foreign_keys=[created_by], back_populates="risks_created")
    tickets = relationship("Ticket", back_populates="related_risk")
    source_document = relationship("DocumentAnalysis", foreign_keys=[source_document_id])

    @property
    def score(self) -> int:
        return self.risk_score
        
    @property
    def owner_name(self) -> Optional[str]:
        return self.owner.full_name if getattr(self, "owner", None) else None
