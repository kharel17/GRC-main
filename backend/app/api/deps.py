from typing import Generator, Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyCookie
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas
from app.config import settings
from app.database import get_db
import logging

logger = logging.getLogger("grc.deps")

# Support both cookie and Bearer header auth
reusable_oauth2_cookie = APIKeyCookie(name="access_token", auto_error=False)
reusable_oauth2_header = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cookie_token: str = Depends(reusable_oauth2_cookie),
    header_token: str = Depends(reusable_oauth2_header),
) -> models.User:
    """
    Validates the JWT token from header or cookie and returns the user.
    Auto-provisions users from Supabase if they don't exist locally.
    """
    token = header_token or cookie_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if token.startswith("Bearer "):
        token = token[7:].strip()

    payload = None
    last_error = None

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        logger.debug(f"JWT header alg: {alg}")
    except Exception as e:
        logger.error(f"Could not read JWT header: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )

    # --- Attempt 1: Supabase secret, HS256 ---
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        logger.debug("JWT decoded via Supabase HS256")
    except JWTError as e:
        last_error = e
        logger.debug(f"HS256 decode failed: {e}")

    # --- Attempt 2: ES256 with PEM wrapping ---
    if payload is None and alg == "ES256":
        key = settings.SUPABASE_JWT_SECRET
        keys_to_try = [key]
        if not key.startswith("-----BEGIN"):
            keys_to_try.insert(0, f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----")
        for k in keys_to_try:
            try:
                payload = jwt.decode(
                    token, k, algorithms=["ES256"], options={"verify_aud": False}
                )
                logger.debug("JWT decoded via ES256")
                break
            except JWTError as e:
                last_error = e
                logger.debug(f"ES256 decode attempt failed: {e}")

    # --- Attempt 3: Internal SECRET_KEY fallback ---
    if payload is None:
        logger.warning("Supabase decode failed. Trying internal SECRET_KEY...")
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256"],
                options={"verify_aud": False}
            )
            logger.debug("JWT decoded via internal SECRET_KEY")
        except JWTError as e:
            last_error = e
            logger.error(f"All JWT decode attempts failed. Last error: {e}")

    if payload is None:
        # Return 401 (not 403) — the token is unreadable, not a permissions issue
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials. Token decode failed: {last_error}",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing required 'sub' claim",
        )

    # --- Load or auto-provision user ---
    user_orm = await db.get(models.User, user_id)

    if not user_orm:
        email = payload.get("email", "")
        role_str = payload.get("user_metadata", {}).get("role", "admin")

        DEV_ROLE_MAP = {
            "alice@company.com": models.UserRole.admin,
            "carol@company.com": models.UserRole.manager,
            "bob@company.com": models.UserRole.analyst,
        }

        try:
            role_enum = models.UserRole(role_str)
        except ValueError:
            role_enum = models.UserRole.admin

        if email in DEV_ROLE_MAP:
            role_enum = DEV_ROLE_MAP[email]
        else:
            from sqlalchemy import select, func
            try:
                user_count_query = await db.execute(select(func.count()).select_from(models.User))
                user_count = user_count_query.scalar_one()
                if user_count == 0:
                    role_enum = models.UserRole.admin
            except Exception as e:
                logger.error(f"Error checking user count: {e}")

        new_user = models.User(
            id=user_id,
            email=email,
            full_name=payload.get("user_metadata", {}).get("full_name", email.split('@')[0] if email else "Unknown"),
            hashed_password="SUPABASE_AUTH",
            role=role_enum,
            is_active=True
        )
        db.add(new_user)
        try:
            await db.commit()
            await db.refresh(new_user)
            user_orm = new_user
            logger.info(f"Auto-provisioned new user: {email} with role: {role_enum}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error auto-provisioning user: {e}")
            raise HTTPException(status_code=500, detail="Error creating user profile")

    # --- Temporary global admin override (remove when roles are stable) ---
    if user_orm.role != models.UserRole.admin:
        logger.info(f"Applying temporary admin override for: {user_orm.email}")
        user_orm.role = models.UserRole.admin

    return user_orm


class RoleChecker:
    def __init__(self, allowed_roles: list[models.UserRole]):
        self.allowed_roles = [str(role.value) if hasattr(role, 'value') else str(role) for role in allowed_roles]

    def __call__(self, user: models.User = Depends(get_current_user)):
        user_role_str = str(user.role.value) if hasattr(user.role, 'value') else str(user.role)

        logger.debug(f"Checking access: User role '{user_role_str}' vs Allowed roles {self.allowed_roles}")

        if user_role_str not in self.allowed_roles:
            logger.warning(f"Access Denied: {user.email} (role: {user_role_str}) requires one of {self.allowed_roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role_str}' does not have access to this resource",
            )
        return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user