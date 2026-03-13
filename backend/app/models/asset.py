from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from .base import Base


class AssetType(str, enum.Enum):
    data = "data"
    software = "software"
    hardware = "hardware"
    service = "service"
    personnel = "personnel"
    physical = "physical"
    server = "server"
    db = "db"
    app = "app"


class AssetClassification(str, enum.Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class AssetCriticality(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AssetStatus(str, enum.Enum):
    active = "active"
    decommissioned = "decommissioned"
    under_review = "under_review"


class CIAValue(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Asset(Base):
    """
    Critical information assets for Step 2 — Asset Identification.
    Maps to ISO 27001 Control 5.9 (Inventory of information and other associated assets).
    """
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(SAEnum(AssetType), nullable=False)
    classification = Column(SAEnum(AssetClassification), default=AssetClassification.internal)
    criticality = Column(SAEnum(AssetCriticality), default=AssetCriticality.medium)
    location = Column(String, nullable=True)
    status = Column(SAEnum(AssetStatus), default=AssetStatus.active)

    # CIA Values for ISO 27001 Risk Assessment
    confidentiality = Column(SAEnum(CIAValue), default=CIAValue.medium)
    integrity = Column(SAEnum(CIAValue), default=CIAValue.medium)
    availability = Column(SAEnum(CIAValue), default=CIAValue.medium)

    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="assets")
    owner = relationship("User", foreign_keys=[owner_id])
    risks = relationship("Risk", back_populates="asset")
    
    # Many-to-many with risks
    related_risks = relationship(
        "Risk",
        secondary="asset_risk_mapping",
        lazy="selectin"
    )
