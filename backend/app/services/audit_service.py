"""
Enhanced Audit Service for GRC Platform.

Provides comprehensive audit logging with:
- IP address capture from request context
- Extended action types (login, logout, export, file_upload)
- Auto-commit option for standalone audit events
- Structured metadata for compliance reporting
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from app import models
from app.models.audit_log import AuditAction, AuditEntityType
from uuid import UUID
import logging

logger = logging.getLogger("grc.audit")


def _get_client_ip(request: Optional[Request] = None) -> Optional[str]:
    """Extract real client IP, respecting X-Forwarded-For from reverse proxy."""
    if not request:
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


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
    request: Optional[Request] = None,
    ip_address: Optional[str] = None,
    auto_commit: bool = False,
) -> models.AuditLog:
    """
    Create an audit log entry.

    Args:
        db: Database session
        user: The user performing the action
        action: What happened (created, updated, deleted, login, etc.)
        entity_type: What type of entity was affected
        entity_id: ID of the affected entity
        entity_name: Human-readable name of the entity
        old_values: Previous state (for updates)
        new_values: New state (for creates/updates)
        description: Free-text description
        request: FastAPI request object (for IP extraction)
        ip_address: Override IP address (if not using request)
        auto_commit: If True, commit the audit log immediately
    """
    resolved_ip = ip_address or _get_client_ip(request)

    audit_log = models.AuditLog(
        user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        old_values=old_values,
        new_values=new_values,
        description=description,
        ip_address=resolved_ip,
    )
    db.add(audit_log)

    if auto_commit:
        await db.commit()
        await db.refresh(audit_log)

    logger.info(
        f"audit: {action.value} {entity_type.value}",
        extra={
            "user_id": str(user.id),
            "action": action.value,
            "entity_type": entity_type.value,
            "entity_id": str(entity_id),
            "ip": resolved_ip,
        },
    )

    return audit_log
