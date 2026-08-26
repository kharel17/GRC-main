from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from app.api import deps
from app import models, schemas
from app.models.user import UserRole
import uuid

from app.models.audit_log import AuditLog, AuditAction, AuditEntityType

router = APIRouter()

@router.get("/", response_model=List[schemas.PermissionProfileResponse])
async def list_permission_profiles(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    List all custom permission profiles for the user's organization.
    Available to admin, manager, compliance_officer, and auditor.
    """
    if not current_user.organization_id:
        return []
    
    result = await db.execute(
        select(models.PermissionProfile).where(
            models.PermissionProfile.organization_id == current_user.organization_id
        ).order_by(models.PermissionProfile.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=schemas.PermissionProfileResponse)
async def create_permission_profile(
    profile_in: schemas.PermissionProfileCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([UserRole.admin])),
) -> Any:
    """
    Create a new custom permission profile (Tenant Admin only).
    """
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not associated with an organization")

    # Check for duplicate profile name in the same org
    existing = await db.execute(
        select(models.PermissionProfile).where(
            models.PermissionProfile.organization_id == current_user.organization_id,
            models.PermissionProfile.name == profile_in.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"A profile named '{profile_in.name}' already exists in your organization.")

    profile = models.PermissionProfile(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        name=profile_in.name,
        description=profile_in.description,
        nav_permissions=profile_in.nav_permissions,
    )
    db.add(profile)

    # Audit log
    audit_log = AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=AuditAction.created,
        entity_type=AuditEntityType.setting,
        entity_id=profile.id,
        entity_name=profile.name,
        description=f"Created custom permission profile '{profile.name}' with {len(profile.nav_permissions)} features enabled."
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.put("/{profile_id}", response_model=schemas.PermissionProfileResponse)
async def update_permission_profile(
    profile_id: UUID,
    profile_in: schemas.PermissionProfileUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([UserRole.admin])),
) -> Any:
    """
    Update an existing custom permission profile (Tenant Admin only).
    """
    result = await db.execute(
        select(models.PermissionProfile).where(
            models.PermissionProfile.id == profile_id,
            models.PermissionProfile.organization_id == current_user.organization_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Permission profile not found")

    if profile_in.name is not None:
        profile.name = profile_in.name
    if profile_in.description is not None:
        profile.description = profile_in.description
    if profile_in.nav_permissions is not None:
        profile.nav_permissions = profile_in.nav_permissions

    db.add(profile)

    # Audit log
    audit_log = AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=AuditAction.updated,
        entity_type=AuditEntityType.setting,
        entity_id=profile.id,
        entity_name=profile.name,
        description=f"Updated custom permission profile '{profile.name}'."
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/{profile_id}")
async def delete_permission_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([UserRole.admin])),
) -> Any:
    """
    Delete a custom permission profile. Unassigns any users linked to it first.
    """
    result = await db.execute(
        select(models.PermissionProfile).where(
            models.PermissionProfile.id == profile_id,
            models.PermissionProfile.organization_id == current_user.organization_id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Permission profile not found")

    # Unlink any users currently assigned to this profile
    users_res = await db.execute(
        select(models.User).where(models.User.permission_profile_id == profile_id)
    )
    assigned_users = users_res.scalars().all()
    for u in assigned_users:
        u.permission_profile_id = None
        db.add(u)

    await db.delete(profile)

    # Audit log
    audit_log = AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=AuditAction.deleted,
        entity_type=AuditEntityType.setting,
        entity_id=profile.id,
        entity_name=profile.name,
        description=f"Deleted custom permission profile '{profile.name}'. {len(assigned_users)} users reverted to standard role permissions."
    )
    db.add(audit_log)

    await db.commit()
    return {"success": True, "message": "Permission profile deleted successfully"}


@router.post("/assign")
async def assign_permission_profile_to_user(
    assign_in: schemas.UserProfileAssignRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([UserRole.admin])),
) -> Any:
    """
    Assign or unassign a custom permission profile to an organization user (Tenant Admin only).
    """
    user_res = await db.execute(
        select(models.User).where(
            models.User.id == assign_in.user_id,
            models.User.organization_id == current_user.organization_id,
        )
    )
    target_user = user_res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found in your organization")

    profile_name = "None (Standard Defaults)"
    if assign_in.permission_profile_id:
        profile_res = await db.execute(
            select(models.PermissionProfile).where(
                models.PermissionProfile.id == assign_in.permission_profile_id,
                models.PermissionProfile.organization_id == current_user.organization_id,
            )
        )
        profile = profile_res.scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=404, detail="Permission profile not found in your organization")
        target_user.permission_profile_id = assign_in.permission_profile_id
        profile_name = profile.name
    else:
        target_user.permission_profile_id = None

    db.add(target_user)

    # Audit log
    audit_log = AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=AuditAction.updated,
        entity_type=AuditEntityType.user,
        entity_id=target_user.id,
        entity_name=target_user.email,
        description=f"Assigned permission profile '{profile_name}' to {target_user.email} by {current_user.email}."
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(target_user)
    return {"success": True, "message": "User permission profile updated successfully"}
