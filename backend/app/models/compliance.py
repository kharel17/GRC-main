from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from .base import Base

class ComplianceStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    compliant = "compliant"
    non_compliant = "non_compliant"

class CompliancePriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class ComplianceItem(Base):
    __tablename__ = "compliance_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    framework = Column(String, nullable=False)
    requirement_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(ComplianceStatus), default=ComplianceStatus.not_started)
    priority = Column(SAEnum(CompliancePriority), default=CompliancePriority.medium)
    due_date = Column(DateTime, nullable=True)
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    evidence = relationship("Evidence", back_populates="related_compliance_item", foreign_keys="Evidence.related_id", primaryjoin="and_(Evidence.related_id==ComplianceItem.id, Evidence.related_to=='compliance_item')")
