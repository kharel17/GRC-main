from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Any, List
from app.api import deps
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog, AuditAction, AuditEntityType
from app.models.auth import RefreshToken
from app import schemas
import bcrypt
import uuid
from sqlalchemy import delete

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
async def read_users(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve users (active only, scoped to organization)."""
    stmt = (
        select(User)
        .where(User.is_active == True)
        .where(User.organization_id == current_user.organization_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


@router.get("/{user_id}", response_model=schemas.User)
async def read_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get a specific user by id (scoped to organization)."""
    stmt = select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found in your organization")

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


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.RoleChecker([UserRole.admin])),
) -> None:
    """
    Soft-delete a user (admin only). 
    Sets is_active to False to move from management list while preserving historical data.
    Cannot delete yourself.
    """

    # Prevent self-deletion
    if str(current_user.id) == str(user_id):
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account"
        )

    stmt = select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found in your organization")

    # Soft delete: deactivation
    user.is_active = False
    user.organization_id = None # Clear org scoping on deactivation
    user.invitation_status = 'deactivated'
    
    # REVOKE ALL SESSIONS
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    user.token_version += 1 # Invalidate all current JWTs
    
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
    current_user: User = Depends(deps.RoleChecker([UserRole.admin])),
) -> Any:
    """Update a user's role (admin only, scoped to organization)."""
    new_role = role_data.get("role")
    if not new_role:
        raise HTTPException(status_code=400, detail="Missing 'role' field in request body")

    try:
        role_enum = UserRole(new_role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: '{new_role}'")

    stmt = select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found in your organization")

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
