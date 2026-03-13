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

    # --- Load user from DB ---
    user_orm = await db.get(models.User, user_id)
    email = payload.get("email", "")

    ROLE_OVERRIDE_MAP = {
        # Seed accounts (local dev only)
        "alice@company.com":   models.UserRole.admin,
        "carol@company.com":   models.UserRole.manager,
        "bob@company.com":     models.UserRole.analyst,
        # Platform team (all environments)
        "bcolorc17@gmail.com": models.UserRole.admin,
        "grchelios@gmail.com": models.UserRole.admin,
    }

    # Step 1: Check platform team / seed override
    if email in ROLE_OVERRIDE_MAP:
        if not user_orm:
            new_user = models.User(
                id=user_id,
                email=email,
                full_name=payload.get("user_metadata", {}).get("full_name", email.split('@')[0] if email else "Unknown"),
                hashed_password="SUPABASE_AUTH",
                role=ROLE_OVERRIDE_MAP[email],
                is_active=True,
                invitation_status='active'
            )
            db.add(new_user)
            try:
                await db.commit()
                await db.refresh(new_user)
                user_orm = new_user
                logger.info(f"Auto-provisioned override user: {email} with role: {ROLE_OVERRIDE_MAP[email]}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Error auto-provisioning override user: {e}")
                raise HTTPException(status_code=500, detail="Error creating override user profile")
        return user_orm

    from sqlalchemy import select
    user_result = await db.execute(select(models.User).where(models.User.email == email))
    user_by_email = user_result.scalar_one_or_none()
    
    # Associate Supabase ID with existing allowed email if first login
    if user_by_email and not user_orm and user_by_email.id != user_id:
        user_by_email.id = user_id # Align IDs (might need handling based on current schema constraints, but usually Supabase matches or overrides id)
        # Instead of replacing ID directly, let's just use the email matched user.
        # Ideally, invitation creates the user with a temporary ID or matches email during OAuth
        # Since Supabase handles the actual UUID creation during auth/signup, 
        # let's assume the DB record ID needs to be synchronized or we look it up by email.
    
    # We will strictly look up by email for the invitation system to ensure we catch invited users.
    if not user_orm and user_by_email:
        user_orm = user_by_email
        # Optional: sync the ID if it differs
        if str(user_orm.id) != user_id:
             logger.warning(f"User ID mismatch for {email}. Supabase: {user_id}, DB: {user_orm.id}")

    # Step 3: If user not found -> BLOCK
    if not user_orm:
        logger.warning(f"Blocked unauthorized login attempt for email: {email}")
        raise HTTPException(
            status_code=403,
            detail={
                "code": "NOT_INVITED",
                "message": "You have not been invited to this platform. Please contact your administrator."
            }
        )

    # Step 4: If user deactivated -> BLOCK
    if user_orm.invitation_status == 'deactivated':
        logger.warning(f"Blocked login attempt for deactivated user: {email}")
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ACCOUNT_DEACTIVATED",
                "message": "Your account has been deactivated. Please contact your administrator."
            }
        )

    # Step 5: If user pending -> activate them
    if user_orm.invitation_status == 'pending':
        user_orm.invitation_status = 'active'
        try:
            await db.commit()
            logger.info(f"Activated pending user: {email}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error activating user: {e}")

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