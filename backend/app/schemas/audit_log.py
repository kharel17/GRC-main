from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, IPvAnyAddress
from uuid import UUID
from app.models.audit_log import AuditAction, AuditEntityType

class AuditLogBase(BaseModel):
    user_id: UUID
    action: AuditAction
    entity_type: AuditEntityType
    entity_id: UUID
    entity_name: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[IPvAnyAddress] = None
    description: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogInDBBase(AuditLogBase):
    id: UUID
    timestamp: datetime

    class Config:
        from_attributes = True

class AuditLog(AuditLogInDBBase):
    pass
