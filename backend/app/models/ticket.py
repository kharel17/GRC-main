from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from .base import Base

class TicketPriority(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"

class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    escalated = "escalated"
    resolved = "resolved"
    closed = "closed"

class TicketCategory(str, enum.Enum):
    risk_identified = "risk_identified"
    risk_mitigated = "risk_mitigated"
    compliance_gap = "compliance_gap"
    security_incident = "security_incident"
    audit_finding = "audit_finding"
    policy_violation = "policy_violation"

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(SAEnum(TicketPriority), nullable=False)
    status = Column(SAEnum(TicketStatus), default=TicketStatus.open)
    category = Column(SAEnum(TicketCategory), nullable=False)
    
    source_audit_log_id = Column(UUID(as_uuid=True), ForeignKey("audit_logs.id"), nullable=False)
    
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to_role = Column(String, nullable=False)
    
    escalated_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    escalated_to_role = Column(String, nullable=True)
    escalation_level = Column(Integer, default=1)
    
    related_risk_id = Column(UUID(as_uuid=True), ForeignKey("risks.id"), nullable=True)
    related_entity_type = Column(String, nullable=True)
    related_entity_id = Column(UUID(as_uuid=True), nullable=True)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    escalated_at = Column(DateTime, nullable=True)

    # Relationships
    assignee = relationship("User", foreign_keys=[assigned_to_id], back_populates="tickets_assigned")
    source_audit_log = relationship("AuditLog", back_populates="tickets")
    related_risk = relationship("Risk", back_populates="tickets")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")

class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="comments")
