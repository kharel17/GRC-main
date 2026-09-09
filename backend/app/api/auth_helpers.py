"""
Auth helpers – shared utilities for authentication endpoints.

Extracted from auth.py to keep the router file thin.
"""

from datetime import datetime, timedelta
import hashlib

from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.config import settings
from app.utils import security


def get_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_user_tokens(response: Response, db: AsyncSession, user: models.User) -> dict:
    """Create access + refresh tokens, persist refresh in DB, set cookies, return payload."""
    access_token = security.create_access_token(
        user.id, token_version=user.token_version,
        email=user.email, role=user.role.value if user.role else None,
    )
    refresh_token = security.create_refresh_token(user.id, token_version=user.token_version)
    
    db_refresh_token = models.RefreshToken(
        token_hash=get_token_hash(refresh_token),
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    db.add(db_refresh_token)
    await db.commit()
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        path="/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
    )
    
    user_info = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role) if user.role else "admin",
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "organization_name": user.organization_name,
    }
    return {
        "message": "Successfully logged in",
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_info,
    }
