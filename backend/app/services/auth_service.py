from datetime import timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models, schemas
from app.utils import security

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalars().first()
    if not user:
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    return user

async def create_user(db: AsyncSession, user_in: schemas.UserCreate) -> models.User:
    hashed_password = security.get_password_hash(user_in.password)
    db_user = models.User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        role=user_in.role or models.UserRole.analyst,
        department=user_in.department,
        is_active=True
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
