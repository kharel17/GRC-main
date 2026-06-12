from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Any, List
from app.api import deps
from app.models.user import User, UserRole
from app import schemas
import bcrypt
import uuid

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
    await db.commit()
