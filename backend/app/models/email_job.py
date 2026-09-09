import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class EmailJobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    sent = "sent"
    failed = "failed"
    dead = "dead"


class EmailJob(Base):
    __tablename__ = "email_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient = Column(String, nullable=False, index=True)
    template_name = Column(String, nullable=False)
    template_data = Column(JSONB, nullable=False, default={})
    subject = Column(String, nullable=False)

    status = Column(
        SAEnum(EmailJobStatus, name="emailjobstatus"),
        default=EmailJobStatus.pending,
        nullable=False,
        index=True,
    )
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    next_retry_at = Column(DateTime, nullable=True, index=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    sent_at = Column(DateTime, nullable=True)
