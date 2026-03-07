from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
from app.config import settings
from app.database import get_db
from app.utils import security

from fastapi.security import APIKeyCookie, OAuth2PasswordBearer
from fastapi import Request

# Support both cookie and Bearer header auth
reusable_oauth2_cookie = APIKeyCookie(name="access_token", auto_error=False)
reusable_oauth2_header = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cookie_token: str = Depends(reusable_oauth2_cookie),
    header_token: str = Depends(reusable_oauth2_header),
) -> models.User:
    # Try Bearer header first, then fall back to cookie
    token = header_token or cookie_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = security.decode_token(token)
        token_data = schemas.token.TokenPayload(**payload)
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
            
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user_orm = await db.get(models.User, token_data.sub)
    if not user_orm:
         raise HTTPException(status_code=404, detail="User not found")
    
    # Check if token version matches the current user version
    if token_data.version != user_orm.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )
         
    return user_orm

class RoleChecker:
    def __init__(self, allowed_roles: list[models.UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: models.User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role} does not have access to this resource",
            )
        return user

def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
