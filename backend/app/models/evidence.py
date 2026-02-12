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

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    related_to = Column(SAEnum(EvidenceRelatedTo), nullable=False)
    related_id = Column(UUID(as_uuid=True), nullable=False)
    # Ideally related_name would be dynamically fetched, but for simplicity storing it or omitting it is fine.
    # Frontend mock has relatedName, but in DB we usually query the related entity.
    
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    verified = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])
    verifier = relationship("User", foreign_keys=[verified_by])
    
    # Generic relationship handling in SQLAlchemy is complex, usually handled by separate queries or Polymorphic
    # But for now we can add specific relationships if needed, or just rely on 'related_id' queries.
    related_compliance_item = relationship("ComplianceItem", foreign_keys=[related_id], viewonly=True, sync_backref=False)
