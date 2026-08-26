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
import uuid
import httpx
import json
from jose import jwk
from collections import defaultdict
import time

logger = logging.getLogger("grc.deps")

# Simple in-memory rate limiting
# In a real production environment with multiple workers/instances, 
# this should be moved to Redis or a middleware.
login_attempts = defaultdict(list)

def rate_limit(limit: int, window: int):
    """
    Simple rate limiter dependency.
    limit: max attempts
    window: time window in seconds
    """
    def dependency(request: Request):
        client_ip = request.client.host
        now = time.time()
        
        # Clean up old attempts
        login_attempts[client_ip] = [t for t in login_attempts[client_ip] if now - t < window]
        
        if len(login_attempts[client_ip]) >= limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later."
            )
        
        login_attempts[client_ip].append(now)
        return True
    return dependency

# Support both cookie and Bearer header auth
reusable_oauth2_cookie = APIKeyCookie(name="access_token", auto_error=False)
reusable_oauth2_header = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

JWKS_URL = f"https://{settings.SUPABASE_PROJECT_ID if hasattr(settings, 'SUPABASE_PROJECT_ID') else 'htgojajcceunavgchrgc'}.supabase.co/auth/v1/.well-known/jwks.json"

# Cache the JWKS at module level (fetched once on startup)
_jwks_cache = None

async def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(JWKS_URL)
                _jwks_cache = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from {JWKS_URL}: {e}")
            return None
    return _jwks_cache

async def verify_supabase_token(token: str) -> dict:
    # Get the kid from token header
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg", "HS256")
    except Exception as e:
        logger.error(f"Could not read JWT header: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )
    
    # If no kid, try legacy HS256 with secret
    if not kid:
        logger.debug("No kid in header, trying legacy HS256 decode")
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
    
    # Get JWKS and find matching key
    jwks = await get_jwks()
    if not jwks:
        # Fallback to legacy secret if JWKS fetch failed
        logger.warning("JWKS not available, falling back to legacy HS256")
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
    
    # Find the key matching the kid
    matching_key = None
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            matching_key = key
            break
    
    # If no kid match found, try legacy HS256 with secret
    if matching_key is None:
        logger.warning(f"No matching key for kid: {kid}, falling back to legacy HS256")
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
    
    # Verify with the matched JWK
    try:
        public_key = jwk.construct(matching_key)
        return jwt.decode(
            token,
            public_key,
            algorithms=[alg],
            options={"verify_aud": False}
        )
    except Exception as e:
        logger.error(f"JWKS decode attempt failed: {e}")
        # Final fallback attempt with HS256
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )

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
        payload = await verify_supabase_token(token)
        logger.debug("JWT verified via verify_supabase_token")
    except Exception as e:
        last_error = e
        # --- Fallback: Internal SECRET_KEY ---
        logger.warning(f"Supabase verification failed: {e}. Trying internal SECRET_KEY...")
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256"],
                options={"verify_aud": False}
            )
            logger.debug("JWT decoded via internal SECRET_KEY")
        except JWTError as inner_e:
            last_error = inner_e
            logger.error(f"All JWT decode attempts failed. Last error: {inner_e}")

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
        # Platform team (Super Admins)
        "bcolorc17@gmail.com": models.UserRole.superadmin,
        "grchelios@gmail.com": models.UserRole.superadmin,
        "grcacc55@gmail.com": models.UserRole.superadmin,
    }

    # Step 1: Check platform team / seed override
    if email in ROLE_OVERRIDE_MAP:
        from sqlalchemy import select
        # Ensure Platform organization exists
        platform_org_res = await db.execute(select(models.Organization).where(models.Organization.name == "Platform Team"))
        platform_org = platform_org_res.scalar_one_or_none()
        
        if not platform_org:
            platform_org = models.Organization(
                id=uuid.uuid4(),
                name="Platform Team",
                onboarding_completed=True,
                ticket_settings={
                    "severity_threshold": "medium",
                    "suppression_window_hours": 24,
                    "auto_escalation_enabled": True,
                    "sla_config": {
                        "critical": 24,
                        "high": 48,
                        "medium": 120,
                        "low": 240
                    }
                }
            )
            db.add(platform_org)
            try:
                await db.flush()
            except Exception:
                await db.rollback()
                platform_org_res = await db.execute(select(models.Organization).where(models.Organization.name == "Platform Team"))
                platform_org = platform_org_res.scalar_one_or_none()

        if not user_orm:
            new_user = models.User(
                id=user_id,
                email=email,
                full_name=payload.get("user_metadata", {}).get("full_name", email.split('@')[0] if email else "Unknown"),
                hashed_password="SUPABASE_AUTH",
                role=ROLE_OVERRIDE_MAP[email],
                is_active=True,
                invitation_status='active',
                organization_id=platform_org.id,
                organization_name=platform_org.name
            )
            db.add(new_user)
            try:
                await db.commit()
                await db.refresh(new_user)
                user_orm = new_user
                logger.info(f"Auto-provisioned override user: {email} with org: Platform Team")
            except Exception as e:
                await db.rollback()
                # Check if a concurrent request already created the user
                user_res = await db.execute(select(models.User).where(models.User.email == email))
                user_orm = user_res.scalar_one_or_none()
                if not user_orm:
                    import traceback
                    logger.error(traceback.format_exc())
                    raise HTTPException(status_code=500, detail=f"Error creating override user profile: {str(e)}")
        elif not user_orm.organization_id:
            # Fix existing platform user missing org (ONLY if they have none)
            user_orm.organization_id = platform_org.id
            user_orm.organization_name = platform_org.name
            user_orm.role = ROLE_OVERRIDE_MAP[email]
            await db.commit()
            await db.refresh(user_orm)
            logger.info(f"Fixed missing organization for existing platform user: {email}")
        
        # Ensure role is always admin for platform team even if org isn't changed
        if user_orm.role != ROLE_OVERRIDE_MAP[email]:
            user_orm.role = ROLE_OVERRIDE_MAP[email]
            await db.commit()
            await db.refresh(user_orm)

        return user_orm

    from sqlalchemy import select
    user_result = await db.execute(select(models.User).where(models.User.email == email))
    user_by_email = user_result.scalar_one_or_none()
    
    # Associate Supabase ID with existing allowed email if first login
    if user_by_email and not user_orm and user_by_email.id != user_id:
        user_by_email.id = user_id # Align IDs
    
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

    # Step 5: Check if time-boxed audit access window has expired
    from datetime import datetime
    if user_orm.access_expires_at and datetime.utcnow() > user_orm.access_expires_at:
        logger.warning(f"Blocked login attempt for expired auditor account: {email}")
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ACCESS_EXPIRED",
                "message": "Your audit access window has expired. Please contact your organization administrator to renew access."
            }
        )

    # Step 6: If user pending -> activate them
    if user_orm.invitation_status == 'pending':
        user_orm.invitation_status = 'active'
        try:
            await db.commit()
            logger.info(f"Activated pending user: {email}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error activating user: {e}")

    # Load permission profile if assigned
    if user_orm.permission_profile_id and not user_orm.permission_profile:
        user_orm.permission_profile = await db.get(models.PermissionProfile, user_orm.permission_profile_id)

    # Set organization context for RLS
    from app.database import org_id_var
    from sqlalchemy import text
    org_id_var.set(user_orm.organization_id)
    if user_orm.organization_id:
        await db.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": str(user_orm.organization_id)}
        )

    return user_orm





class RoleChecker:
    def __init__(self, allowed_roles: list[models.UserRole], permission_key: Optional[str] = None):
        self.allowed_roles = [str(role.value) if hasattr(role, 'value') else str(role) for role in allowed_roles]
        self.permission_key = permission_key

    def __call__(self, user: models.User = Depends(get_current_user)):
        user_role_str = str(user.role.value) if hasattr(user.role, 'value') else str(user.role)

        # 1. Check if base role is in allowed roles
        if user_role_str in self.allowed_roles:
            return user

        # 2. If user has a custom permission profile with the specific nav permission granted
        if self.permission_key and user.permission_profile and user.permission_profile.nav_permissions:
            if user.permission_profile.nav_permissions.get(self.permission_key) is True:
                logger.info(f"Access granted via Custom Permission Profile ({self.permission_key}) for {user.email}")
                return user

        logger.warning(f"Access Denied: {user.email} (role: {user_role_str}) requires one of {self.allowed_roles} or profile permission '{self.permission_key}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user_role_str}' does not have access to this resource",
        )


def enforce_non_auditor_write(current_user: models.User = Depends(get_current_user)):
    """
    Guard to enforce that 'auditor' role accounts cannot perform write/mutation operations
    (creating, editing, deleting risks, assets, controls, evidence).
    """
    user_role_str = str(current_user.role.value) if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role_str == "auditor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditor accounts have read-only access and cannot modify platform data."
        )
    return current_user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user