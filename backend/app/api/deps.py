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
        # Decode the Supabase JWT
        # Supabase uses HS256 and the JWT secret is in the dashboard
        payload = jwt.decode(
            token, 
            settings.SUPABASE_JWT_SECRET, 
            algorithms=["HS256"],
            options={"verify_aud": False} # Accept the default Supabase 'authenticated' audience
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure",
            )
            
    except (JWTError, ValidationError) as e:
        print(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # Check if user exists in our local database
    user_orm = await db.get(models.User, user_id)
    
    if not user_orm:
        # Auto-provision user on first Supabase login
        # Extract email from app_metadata or user_metadata if available
        email = payload.get("email", "")
        role_str = payload.get("user_metadata", {}).get("role", "analyst")
        
        # Dev seed accounts only - do not use in production
        DEV_ROLE_MAP = {
            "alice@company.com": models.UserRole.admin,
            "carol@company.com": models.UserRole.manager,
            "bob@company.com": models.UserRole.analyst,
        }

        try:
            role_enum = models.UserRole(role_str)
        except ValueError:
            role_enum = models.UserRole.analyst

        # 1. Check if email maps to a dev seed account
        if email in DEV_ROLE_MAP:
            role_enum = DEV_ROLE_MAP[email]
        else:
            # 2. If not a dev seed account, check if database is empty to make the first user an admin
            from sqlalchemy import select, func
            try:
                user_count_query = await db.execute(select(func.count()).select_from(models.User))
                user_count = user_count_query.scalar_one()

                if user_count == 0:
                    role_enum = models.UserRole.admin
            except Exception as e:
                print(f"Error checking user count: {e}")

        new_user = models.User(
            id=user_id,
            email=email,
            full_name=payload.get("user_metadata", {}).get("full_name", email.split('@')[0] if email else "Unknown"),
            hashed_password="SUPABASE_AUTH", # Password managed by Supabase
            role=role_enum,
            is_active=True
        )
        db.add(new_user)
        try:
            await db.commit()
            await db.refresh(new_user)
            user_orm = new_user
        except Exception as e:
            await db.rollback()
            print(f"Error auto-provisioning user: {e}")
            raise HTTPException(status_code=500, detail="Error creating user profile")
         
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
