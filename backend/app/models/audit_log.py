from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
import uuid
import enum
from .base import Base

class AuditAction(str, enum.Enum):
    created = "created"
    updated = "updated"
    deleted = "deleted"
    approved = "approved"
    rejected = "rejected"
    reviewed = "reviewed"
    login = "login"
    logout = "logout"
    export = "export"
    file_upload = "file_upload"

class AuditEntityType(str, enum.Enum):
    risk = "risk"
    control = "control"
    evidence = "evidence"
    compliance_item = "compliance_item"
    user = "user"
    ticket = "ticket"
    asset = "asset"

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(SAEnum(AuditAction), nullable=False)
    entity_type = Column(SAEnum(AuditEntityType), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    entity_name = Column(String, nullable=True)
    
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(INET, nullable=True)
    description = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    tickets = relationship("Ticket", back_populates="source_audit_log")
