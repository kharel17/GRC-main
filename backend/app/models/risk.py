from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
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

    risks = relationship("Risk", back_populates="category")

class Risk(Base):
    __tablename__ = "risks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("risk_categories.id"), nullable=False)
    likelihood = Column(Integer, nullable=False)
    impact = Column(Integer, nullable=False)
    risk_score = Column(Integer, nullable=False)
    status = Column(SAEnum(RiskStatus), default=RiskStatus.identified)
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("RiskCategory", back_populates="risks")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="risks_owned")
    creator = relationship("User", foreign_keys=[created_by], back_populates="risks_created")
    tickets = relationship("Ticket", back_populates="related_risk")
