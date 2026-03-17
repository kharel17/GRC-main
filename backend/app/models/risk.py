from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("risk_categories.id"), nullable=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    
    threat = Column(Text, nullable=True)
    vulnerability = Column(Text, nullable=True)
    
    likelihood = Column(Integer, nullable=False)
    impact = Column(Integer, nullable=False)
    risk_score = Column(Integer, nullable=False)
    status = Column(SAEnum(RiskStatus), default=RiskStatus.identified)
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("RiskCategory", foreign_keys=[category_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    asset = relationship("Asset", back_populates="risks")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="risks_owned")
    creator = relationship("User", foreign_keys=[created_by], back_populates="risks_created")
    tickets = relationship("Ticket", back_populates="related_risk")

    @property
    def score(self) -> int:
        return self.risk_score
        
    @property
    def owner_name(self) -> Optional[str]:
        return self.owner.full_name if getattr(self, "owner", None) else None


