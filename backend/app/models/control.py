from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    control_type = Column(SAEnum(ControlType), nullable=False)
    effectiveness = Column(SAEnum(ControlEffectiveness), nullable=False)
    status = Column(SAEnum(ControlStatus), default=ControlStatus.planned)
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    creator = relationship("User", foreign_keys=[created_by])
    risk_mappings = relationship("RiskControlMapping", back_populates="control")


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
