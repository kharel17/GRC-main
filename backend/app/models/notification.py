from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False) # e.g., 'escalation', 'deadline', 'mention'
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    ticket = relationship("Ticket")

    # Compound index for efficient polling
    __table_args__ = (
        Index("ix_notifications_user_id_is_read", "user_id", "is_read"),
    )
