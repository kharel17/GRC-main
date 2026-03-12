from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from .base import Base

class TicketActivityType(str, enum.Enum):
    status_change = "status_change"
    priority_change = "priority_change"
    assignment_change = "assignment_change"
    escalation = "escalation"
    resolution = "resolution"
    comment_added = "comment_added"
    sla_missed = "sla_missed"
    other = "other"

class TicketActivity(Base):
    __tablename__ = "ticket_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # User who performed action (None if system)
    
    activity_type = Column(SAEnum(TicketActivityType), nullable=False)
    
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("Ticket", back_populates="activities")
    user = relationship("User")
