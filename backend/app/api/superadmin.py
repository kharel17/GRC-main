"""
Super Admin Management API Endpoints for GRCGuard Platform.
Allows platform-level Super Admins to monitor customer tenants and perform support impersonation.
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from uuid import UUID
import uuid
import datetime

from app import models, schemas
from app.api import deps
from app.config import settings
from jose import jwt

router = APIRouter()


class TenantSummary(BaseModel):
    id: UUID
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    onboarding_completed: bool
    user_count: int
    compliance_frameworks: List[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ImpersonationResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int = 15
    tenant_id: UUID
    tenant_name: str


@router.get("/organizations", response_model=List[TenantSummary])
async def list_tenants(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.superadmin])),
) -> Any:
    """
    List all onboarded organization tenants with user counts (Super Admin only).
    """
    query = select(
        models.Organization,
        func.count(models.User.id).label("user_count")
    ).outerjoin(
        models.User, models.User.organization_id == models.Organization.id
    ).group_by(models.Organization.id)

    result = await db.execute(query)
    rows = result.all()

    tenants = []
    for org, user_count in rows:
        tenants.append(
            TenantSummary(
                id=org.id,
                name=org.name,
                industry=org.industry,
                size=org.size,
                onboarding_completed=bool(org.onboarding_completed),
                user_count=user_count,
                compliance_frameworks=org.compliance_frameworks or [],
                created_at=org.created_at or datetime.datetime.utcnow(),
            )
        )
    return tenants


@router.post("/impersonate/{org_id}", response_model=ImpersonationResponse)
async def impersonate_tenant_admin(
    org_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.superadmin])),
) -> Any:
    """
    Generate a 15-minute support impersonation session token for a specific tenant (Super Admin only).
    Logs explicit dual-actor audit event for compliance tracking.
    """
    org = await db.get(models.Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Target organization not found")

    # Audit log entry for support impersonation
    audit_log = models.AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=models.AuditAction.reviewed,
        entity_type=models.AuditEntityType.organization,
        entity_id=org.id,
        entity_name=org.name,
        description=f"SUPPORT IMPERSONATION: Super Admin {current_user.email} initiated support session for Org '{org.name}' ({org.id})"
    )
    db.add(audit_log)
    await db.commit()

    # Issue short-lived support token
    expires_delta = datetime.timedelta(minutes=15)
    now = datetime.datetime.utcnow()
    payload = {
        "sub": str(current_user.id),
        "email": current_user.email,
        "org_id": str(org.id),
        "impersonated_org_id": str(org.id),
        "role": models.UserRole.admin.value,
        "exp": now + expires_delta,
        "iat": now,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    return ImpersonationResponse(
        access_token=token,
        tenant_id=org.id,
        tenant_name=org.name,
    )
