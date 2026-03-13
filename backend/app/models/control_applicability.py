from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.models.base import Base


class ControlImplementationStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    implemented = "implemented"
    not_applicable = "not_applicable"


class ControlApplicability(Base):
    """
    Tracks the applicability and implementation status of each ISO 27001 control
    per organization. This is the core data behind the Statement of Applicability (SoA).
    """
    __tablename__ = "control_applicability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    framework_id = Column(UUID(as_uuid=True), ForeignKey("frameworks.id"), nullable=True)

    # References the control annex ID from iso27001-controls.json (e.g. "5.1", "8.12")
    control_annex = Column(String, nullable=False)

    # Link to the standard library control
    framework_control_id = Column(UUID(as_uuid=True), ForeignKey("framework_controls.id"), nullable=True)

    is_applicable = Column(Boolean, default=True, nullable=False)

    # Implementation status of this control for this org
    status = Column(
        SAEnum(ControlImplementationStatus),
        default=ControlImplementationStatus.not_started,
        nullable=False,
    )

    # Required justification when control is marked as not applicable
    justification = Column(Text, nullable=True)

    # Who is responsible for implementing/maintaining this control
    responsible_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="control_applicabilities")
    framework = relationship("Framework", back_populates="applicabilities")
    framework_control = relationship("FrameworkControl", back_populates="applicabilities")
    responsible = relationship("User", foreign_keys=[responsible_id])
