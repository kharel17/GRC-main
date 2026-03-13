from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class FrameworkControl(Base):
    __tablename__ = "framework_controls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    framework_id = Column(UUID(as_uuid=True), ForeignKey("frameworks.id"), nullable=False)
    
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=True) # e.g., "Organizational", "People"
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    framework = relationship("Framework", back_populates="controls")
    applicabilities = relationship("ControlApplicability", back_populates="framework_control")
