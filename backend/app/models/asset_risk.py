from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

class AssetRiskMapping(Base):
    """
    Many-to-many relationship between Assets and Risks.
    Allows tracking which risks affect which specific technical assets.
    """
    __tablename__ = "asset_risk_mapping"

    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    risk_id = Column(UUID(as_uuid=True), ForeignKey("risks.id", ondelete="CASCADE"), primary_key=True)
