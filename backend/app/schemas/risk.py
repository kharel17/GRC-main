from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from app.models.risk import RiskStatus
from pydantic import BaseModel, ConfigDict, computed_field
from pydantic.alias_generators import to_camel

# Risk Category
class RiskCategoryBase(BaseModel):
    name: str
    description: str
    color: str

class RiskCategoryCreate(RiskCategoryBase):
    pass

class RiskCategory(RiskCategoryBase):
    id: UUID
    
    class Config:
        from_attributes = True

# Risk
class RiskBase(BaseModel):
    title: str
    description: str
    category_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    threat: Optional[str] = None
    vulnerability: Optional[str] = None
    likelihood: int
    impact: int
    risk_score: int
    status: RiskStatus = RiskStatus.identified
    owner_id: Optional[UUID] = None

class RiskCreate(RiskBase):
    pass

class RiskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    asset_id: Optional[UUID] = None
    threat: Optional[str] = None
    vulnerability: Optional[str] = None
    likelihood: Optional[int] = None
    impact: Optional[int] = None
    risk_score: Optional[int] = None
    status: Optional[RiskStatus] = None
    owner_id: Optional[UUID] = None
    category_id: Optional[UUID] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class RiskInDBBase(RiskBase):
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    organization_id: UUID
    category_id: Optional[UUID] = None
    category: Optional[RiskCategory] = None

    @computed_field
    def category_name(self) -> Optional[str]:
        return self.category.name if self.category else "Uncategorized"

    @computed_field
    def owner_name(self) -> str:
        owner = getattr(self, "owner", None)
        return owner.full_name if owner else "Unassigned"

    @computed_field
    def score(self) -> int:
        return self.risk_score

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

class Risk(RiskInDBBase):
    pass

# Risk-Control Mapping
class RiskControlMappingOut(BaseModel):
    id: UUID
    risk_id: UUID
    control_id: Optional[UUID] = None
    framework_control_id: Optional[UUID] = None
    control_title: Optional[str] = None
    control_status: Optional[str] = None
    residual_likelihood: Optional[int] = None
    residual_impact: Optional[int] = None
    residual_risk_score: Optional[int] = None
    mapped_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RiskControlMappingCreate(BaseModel):
    control_id: UUID
