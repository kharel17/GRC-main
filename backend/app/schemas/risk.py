from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from app.models.risk import RiskStatus

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
    category_id: UUID
    likelihood: int
    impact: int
    risk_score: int
    status: RiskStatus = RiskStatus.identified
    owner_id: UUID

class RiskCreate(RiskBase):
    pass

class RiskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    likelihood: Optional[int] = None
    impact: Optional[int] = None
    risk_score: Optional[int] = None
    status: Optional[RiskStatus] = None
    owner_id: Optional[UUID] = None

class RiskInDBBase(RiskBase):
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Risk(RiskInDBBase):
    category: Optional[RiskCategory] = None

# Risk-Control Mapping
class RiskControlMappingOut(BaseModel):
    id: UUID
    risk_id: UUID
    control_id: UUID
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
