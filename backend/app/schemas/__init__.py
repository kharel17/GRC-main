from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from .token import Token, TokenPayload, Message
from .user import User, UserCreate, UserUpdate
from .risk import Risk, RiskCreate, RiskUpdate, RiskCategory, RiskCategoryCreate, RiskControlMappingOut, RiskControlMappingCreate
from .control import Control, ControlCreate, ControlUpdate
from .compliance import ComplianceItem, ComplianceItemCreate, ComplianceItemUpdate
from .evidence import Evidence, EvidenceCreate, EvidenceUpdate, EvidenceStatusUpdate
from .audit_log import AuditLog, AuditLogCreate
from .ticket import (
    Ticket, TicketCreate, TicketUpdate, TicketComment, TicketCommentCreate, 
    AITicketCreate, TicketActivity, TicketResolution, EvidenceRequest
)
from .notification import Notification, NotificationCreate
from .organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from .asset import AssetCreate, AssetUpdate, AssetResponse, AssetRiskLinkRequest
from .control_applicability import (
    ControlApplicabilityCreate,
    ControlApplicabilityUpdate,
    ControlApplicabilityResponse,
    ControlApplicabilityBulkCreate,
)

class FrameworkControlBase(BaseModel):
    code: str
    title: str
    description: str
    category: Optional[str] = None

class FrameworkControlCreate(FrameworkControlBase):
    framework_id: UUID

class FrameworkControlResponse(FrameworkControlBase):
    id: UUID
    framework_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FrameworkBase(BaseModel):
    name: str
    version: str
    description: Optional[str] = None

class FrameworkCreate(FrameworkBase):
    pass

class FrameworkUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None

class FrameworkResponse(FrameworkBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FrameworkDetailResponse(FrameworkResponse):
    controls: List[FrameworkControlResponse] = []
from .document_analysis import DocumentAnalysisResponse, DocumentAnalysisSummary
from .permission_profile import (
    PermissionProfileBase,
    PermissionProfileCreate,
    PermissionProfileUpdate,
    PermissionProfileResponse,
    UserProfileAssignRequest,
)
