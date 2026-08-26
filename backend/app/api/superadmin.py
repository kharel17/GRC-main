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


class UserSearchResult(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    role: str
    organization_name: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/users/search", response_model=List[UserSearchResult])
async def search_users(
    email: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.superadmin])),
) -> Any:
    """
    Search for users across all organizations by email (Super Admin only).
    """
    stmt = select(models.User).where(models.User.email.ilike(f"%{email}%")).limit(10)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        UserSearchResult(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=str(u.role.value) if hasattr(u.role, 'value') else str(u.role),
            organization_name=u.organization_name,
            is_active=u.is_active,
        )
        for u in users
    ]


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


class PromoteResponse(BaseModel):
    success: bool
    message: str
    user_id: UUID
    previous_role: str
    new_role: str = "superadmin"


@router.post("/promote/{user_id}", response_model=PromoteResponse)
async def promote_to_superadmin(
    user_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.superadmin])),
) -> Any:
    """
    Promote an existing user to Super Admin (Super Admin only).
    Moves them to Platform Team org, revokes old sessions via token_version bump.
    """
    target_user = await db.get(models.User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot promote yourself")

    previous_role = str(target_user.role.value) if hasattr(target_user.role, 'value') else str(target_user.role)

    if previous_role == "superadmin":
        raise HTTPException(status_code=400, detail="User is already a Super Admin")

    # Get or create Platform Team org
    platform_org_res = await db.execute(
        select(models.Organization).where(models.Organization.name == "Platform Team")
    )
    platform_org = platform_org_res.scalar_one_or_none()
    if not platform_org:
        platform_org = models.Organization(
            id=uuid.uuid4(),
            name="Platform Team",
            onboarding_completed=True,
            created_by=current_user.id,
        )
        db.add(platform_org)
        await db.flush()

    # Promote user
    target_user.role = models.UserRole.superadmin
    target_user.organization_id = platform_org.id
    target_user.organization_name = platform_org.name

    # Revoke all existing sessions by bumping token_version
    if hasattr(target_user, 'token_version') and target_user.token_version is not None:
        target_user.token_version += 1

    db.add(target_user)

    # Audit log
    audit_log = models.AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=models.AuditAction.updated,
        entity_type=models.AuditEntityType.user,
        entity_id=target_user.id,
        entity_name=target_user.email,
        description=f"SUPER ADMIN PROMOTION: {current_user.email} promoted {target_user.email} from '{previous_role}' to 'superadmin'"
    )
    db.add(audit_log)

    await db.commit()

    return PromoteResponse(
        success=True,
        message=f"{target_user.email} has been promoted to Super Admin",
        user_id=target_user.id,
        previous_role=previous_role,
    )
