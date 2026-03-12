from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
from app.config import settings
from app.database import get_db
import logging
logger = logging.getLogger("grc.deps")

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
    # Debug: strip Bearer if improperly passed (unlikely but safe)
    if token.startswith("Bearer "):
        token = token[7:].strip()
        
    try:
        # Debug: extract header to see what's in there
        try:
            from jose import jwt as jose_jwt
            header = jose_jwt.get_unverified_header(token)
            logger.info(f"JWT Header: {header}")
        except Exception as e:
            logger.warning(f"Could not extract token header: {e}")
            
        # Try decoding with Supabase secret first
        try:
            # Broaden algorithms to avoid "alg not allowed" errors
            allowed_algs = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
            payload = jwt.decode(
                token, 
                settings.SUPABASE_JWT_SECRET, 
                algorithms=allowed_algs,
                options={"verify_aud": False}
            )
        except JWTError as e:
            # Fallback: Try with app's internal SECRET_KEY
            logger.info(f"Supabase decode failed ({e}), trying internal secret...")
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
        
        user_id = payload.get("sub")
        if not user_id:
            logger.error("Token structure invalid: no 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure",
            )
            
    except (JWTError, ValidationError) as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Could not validate credentials: {str(e)}",
        )
    
    # Check if user exists in our local database
    user_orm = await db.get(models.User, user_id)
    
    if not user_orm:
        # Auto-provision user on first Supabase login
        # Extract email from app_metadata or user_metadata if available
        email = payload.get("email", "")
        role_str = payload.get("user_metadata", {}).get("role", "admin")
        
        # Dev seed accounts only - do not use in production
        DEV_ROLE_MAP = {
            "alice@company.com": models.UserRole.admin,
            "carol@company.com": models.UserRole.manager,
            "bob@company.com": models.UserRole.analyst,
        }

        try:
            role_enum = models.UserRole(role_str)
        except ValueError:
            role_enum = models.UserRole.admin

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
         
    # Aggressively enforce admin role if requested (temporary global admin mode)
    if user_orm and user_orm.role != models.UserRole.admin:
        # Check if we should override or just return. 
        # Requirement: "Everyone who logs in is an admin"
        user_orm.role = models.UserRole.admin
        db.add(user_orm)
        try:
            await db.commit()
            await db.refresh(user_orm)
        except Exception:
            await db.rollback()
            
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
