from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class FrameworkControl(Base):
    __tablename__ = "framework_controls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    framework_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("frameworks.id"), nullable=False)
    
    code: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True) # e.g., "Organizational", "People"
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    framework = relationship("Framework", back_populates="controls")
    applicabilities = relationship("ControlApplicability", back_populates="framework_control")
