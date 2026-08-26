from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, delete
from typing import Any, List, Optional
from uuid import UUID
from app.api import deps
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog, AuditAction, AuditEntityType
from app.models.auth import RefreshToken
from app import schemas, models
import bcrypt
import uuid

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
async def read_users(
    db: AsyncSession = Depends(deps.get_db),
    organization_id: Optional[UUID] = Query(None, description="Superadmin filter for specific organization"),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve users with strict hierarchical role scoping:
    - Super Admin: Can view all users or filter by ?organization_id=...
    - Tenant Admin: Can view all users in their own organization.
    - Manager: Can view themselves, co-managers, and direct reports (Analyst/Owner).
    - Analyst/Other: Can view themselves and direct supervisor.
    """
    stmt = select(User).where(User.is_active == True)

    is_superadmin = (
        current_user.role == UserRole.superadmin or 
        (hasattr(current_user.role, 'value') and current_user.role.value == 'superadmin')
    )
    is_admin = (
        current_user.role == UserRole.admin or 
        (hasattr(current_user.role, 'value') and current_user.role.value == 'admin')
    )
    is_manager = (
        current_user.role in (UserRole.manager, UserRole.department_manager) or 
        (hasattr(current_user.role, 'value') and current_user.role.value in ('manager', 'department_manager'))
    )

    if is_superadmin:
        if organization_id:
            stmt = stmt.where(User.organization_id == organization_id)
        # If no organization_id supplied, superadmin sees users across all organizations
    elif is_admin:
        stmt = stmt.where(User.organization_id == current_user.organization_id)
    elif is_manager:
        # Managers see: themselves, direct reports (manager_id == current_user.id), and peer managers in same org
        stmt = stmt.where(
            User.organization_id == current_user.organization_id,
            or_(
                User.id == current_user.id,
                User.manager_id == current_user.id,
                User.role.in_([UserRole.manager, UserRole.department_manager]),
            )
        )
    else:
        # Analysts and standard staff see only themselves and their direct manager
        stmt = stmt.where(
            User.organization_id == current_user.organization_id,
            or_(
                User.id == current_user.id,
                User.id == current_user.manager_id if current_user.manager_id else False,
            )
        )

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    # Populate organization_name dynamically from Organization relation if not set on user column
    org_ids = [u.organization_id for u in users if u.organization_id]
    if org_ids:
        orgs_res = await db.execute(
            select(models.Organization).where(models.Organization.id.in_(org_ids))
        )
        org_map = {str(o.id): o.name for o in orgs_res.scalars().all()}
        for u in users:
            if u.organization_id and str(u.organization_id) in org_map:
                u.organization_name = org_map[str(u.organization_id)]
            elif not u.organization_name:
                u.organization_name = "Platform Team" if str(getattr(u.role, 'value', u.role)) == "superadmin" else "Unassigned Organization"

    return users


@router.get("/managers", response_model=List[schemas.User])
async def list_available_managers(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    List available managers in the caller's organization for report-to assignment.
    """
    stmt = (
        select(User)
        .where(User.is_active == True)
        .where(User.organization_id == current_user.organization_id)
        .where(User.role.in_([UserRole.admin, UserRole.manager, UserRole.department_manager]))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{user_id}", response_model=schemas.User)
async def read_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get a specific user by id (hierarchically scoped)."""
    is_superadmin = (
        current_user.role == UserRole.superadmin or 
        (hasattr(current_user.role, 'value') and current_user.role.value == 'superadmin')
    )
    
    if is_superadmin:
        stmt = select(User).where(User.id == user_id)
    else:
        stmt = select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
        
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: schemas.UserCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.RoleChecker([UserRole.admin])),
) -> Any:
    """Create a new user (admin only)."""

    # Check if email already exists
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists",
        )

    hashed = bcrypt.hashpw(user_in.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Create user row for the CURRENT organization
    new_user = User(
        id=uuid.uuid4(),
        **user_in.model_dump(exclude={"password"}),
        hashed_password=hashed,
        is_active=True,
        organization_id=current_user.organization_id # Force org ID
    )
    db.add(new_user)
    await db.flush()

    # Audit log
    audit_log = AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=AuditAction.created,
        entity_type=AuditEntityType.user,
        entity_id=new_user.id,
        entity_name=new_user.email,
        description=f"User created: {new_user.email}"
    )
    db.add(audit_log)
    
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.put("/me", response_model=schemas.User)
async def update_current_user_profile(
    user_in: schemas.UserUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update profile details (full_name, department) for the currently logged-in user.
    """
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.department is not None:
        current_user.department = user_in.department

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user



@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> None:
    """
    Deactivate a user and revoke all active sessions.
    - Super Admin: Can deactivate any user.
    - Tenant Admin: Can deactivate users in their organization.
    - Manager: Can only deactivate direct reports (Analyst/Owner).
    """
    is_superadmin = (
        current_user.role == UserRole.superadmin or 
        (hasattr(current_user.role, 'value') and current_user.role.value == 'superadmin')
    )
    is_admin = (
        current_user.role == UserRole.admin or 
        (hasattr(current_user.role, 'value') and current_user.role.value == 'admin')
    )
    is_manager = (
        current_user.role in (UserRole.manager, UserRole.department_manager) or 
        (hasattr(current_user.role, 'value') and current_user.role.value in ('manager', 'department_manager'))
    )

    if not (is_superadmin or is_admin or is_manager):
        raise HTTPException(status_code=403, detail="Insufficient permissions to deactivate users")

    if is_superadmin:
        stmt = select(User).where(User.id == user_id)
    else:
        stmt = select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if is_manager and user.manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Managers can only deactivate their direct reports")

    # Soft delete: deactivation
    user.is_active = False
    user.organization_id = None # Clear org scoping on deactivation
    user.invitation_status = 'deactivated'
    
    # REVOKE ALL SESSIONS
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    user.token_version = (user.token_version or 0) + 1 # Invalidate all current JWTs
    
    # Audit log
    audit_log = AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=AuditAction.deleted,
        entity_type=AuditEntityType.user,
        entity_id=user.id,
        entity_name=user.email,
        description=f"User deactivated and sessions revoked: {user.email}"
    )
    db.add(audit_log)
    
    await db.commit()


@router.patch("/{user_id}/role", response_model=schemas.User)
async def update_user_role(
    user_id: str,
    role_data: dict,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Update a user's role (admin or superadmin)."""
    is_superadmin = (
        current_user.role == UserRole.superadmin or 
        (hasattr(current_user.role, 'value') and current_user.role.value == 'superadmin')
    )
    is_admin = (
        current_user.role == UserRole.admin or 
        (hasattr(current_user.role, 'value') and current_user.role.value == 'admin')
    )

    if not (is_superadmin or is_admin):
        raise HTTPException(status_code=403, detail="Only administrators can update user roles")

    new_role = role_data.get("role")
    if not new_role:
        raise HTTPException(status_code=400, detail="Missing 'role' field in request body")

    try:
        role_enum = UserRole(new_role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: '{new_role}'")

    if is_superadmin:
        stmt = select(User).where(User.id == user_id)
    else:
        stmt = select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role_enum
    db.add(user)

    audit_log = AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=AuditAction.updated,
        entity_type=AuditEntityType.user,
        entity_id=user.id,
        entity_name=user.email,
        description=f"User role updated to {role_enum.value} for {user.email}"
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(user)
    return user
