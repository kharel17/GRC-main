from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class Framework(Base):
    __tablename__ = "frameworks"
    __table_args__ = (
        UniqueConstraint("name", "organization_id", name="uq_framework_name_org"),
        Index("uq_framework_system_name", "name", unique=True, postgresql_where=Column("organization_id").is_(None)),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    controls = relationship("FrameworkControl", back_populates="framework", cascade="all, delete-orphan")
    organizations = relationship("Organization", back_populates="framework", foreign_keys="[Organization.framework_id]")
    organization = relationship("Organization", foreign_keys=[organization_id])
    applicabilities = relationship("ControlApplicability", back_populates="framework")
