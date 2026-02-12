from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
from app.models.audit_log import AuditAction, AuditEntityType
from uuid import UUID

async def log_action(
    db: AsyncSession,
    user: models.User,
    action: AuditAction,
    entity_type: AuditEntityType,
    entity_id: UUID,
    entity_name: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None
) -> models.AuditLog:
    
    audit_log = models.AuditLog(
        user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        old_values=old_values,
        new_values=new_values,
        description=description,
        ip_address=ip_address
    )
    db.add(audit_log)
    # We do not commit here assuming this is part of a larger transaction or will be committed by the caller
    # But usually audit logs should be committed. 
    # If the main action fails, we might not want to log it? Or log failure?
    # For now, let's assume successful actions are logged.
    return audit_log
