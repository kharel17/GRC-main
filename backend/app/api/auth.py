from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
import hashlib
import secrets
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app import schemas, models
from app.config import settings
from app.api import deps
from app.utils import security
from app.utils.emails import send_reset_password_email
from app.utils.google_auth import verify_google_token
from app.services import auth_service, totp_service
from app.api.auth_helpers import get_token_hash, issue_user_tokens
from app.api.auth_2fa import router_2fa

router = APIRouter()

# Mount 2FA sub-router at /2fa prefix so existing paths are preserved:
#   e.g. /api/v1/auth/2fa/verify-login, /api/v1/auth/2fa/setup, etc.
router.include_router(router_2fa, prefix="/2fa", tags=["2fa"])

# Backward-compatible wrapper kept for internal use and patching
async def _issue_user_tokens(response: Response, db: AsyncSession, user: models.User) -> dict:
    return await issue_user_tokens(response, db, user)

@router.post("/login", dependencies=[Depends(deps.rate_limit(limit=5, window=60))])
async def login_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    Supports both JSON payloads and application/x-www-form-urlencoded forms.
    """
    content_type = request.headers.get("content-type", "")
    username = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username") or body.get("email")
            password = body.get("password")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )
    else:
        try:
            form = await request.form()
            username = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid form data",
            )

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    user = await auth_service.authenticate_user(
        db, email=str(username), password=str(password)
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Check 2FA requirements
    is_mandatory = totp_service.is_2fa_mandatory_for_role(user.role)
    if user.totp_enabled or is_mandatory:
        two_fa_token = security.create_2fa_challenge_token(
            subject=user.id, email=user.email, role=user.role.value if user.role else "admin"
        )
        return {
            "mfa_required": True,
            "mfa_setup_required": not user.totp_enabled,
            "two_fa_token": two_fa_token,
            "message": "2FA verification required"
        }

    return await _issue_user_tokens(response, db, user)


class GoogleLoginRequest(BaseModel):
    credential: str


@router.post("/google", dependencies=[Depends(deps.rate_limit(limit=10, window=60))])
async def login_google(
    body: GoogleLoginRequest,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Direct Google OAuth 2.0 login.
    Verifies Google ID token, retrieves or provisions local user in PostgreSQL,
    and returns standard local JWT access/refresh tokens.
    """
    if not body.credential or not body.credential.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token credential is required",
        )

    try:
        claims = verify_google_token(body.credential)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
        )

    if not claims.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email is not verified",
        )

    email = claims["email"].lower().strip()

    # Query local user
    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalar_one_or_none()

    if user:
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        # Update missing full_name if available
        if not user.full_name and claims.get("full_name"):
            user.full_name = claims["full_name"]
            await db.commit()
            await db.refresh(user)
    else:
        # Auto-provision new user with recommended fallback organization logic
        org = await db.scalar(
            select(models.Organization).where(models.Organization.name == "Platform Team")
        )
        if not org:
            org = await db.scalar(
                select(models.Organization).order_by(models.Organization.created_at.asc())
            )

        user = models.User(
            id=uuid.uuid4(),
            email=email,
            full_name=claims.get("full_name") or email.split("@")[0],
            hashed_password="GOOGLE_OAUTH",
            role=models.UserRole.analyst,
            is_active=True,
            invitation_status="active",
            organization_id=org.id if org else None,
            organization_name=org.name if org else None,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return await _issue_user_tokens(response, db, user)


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    try:
        payload = security.decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        token_version = payload.get("version")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Check token in DB
    token_hash = get_token_hash(token)
    result = await db.execute(
        select(models.RefreshToken).where(models.RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalars().first()
    
    # Reuse detection: If token not in DB but was valid JWT, it might be a reused/stolen token
    if not db_token:
        # Revoke all tokens for this user as a safety measure
        await db.execute(
            delete(models.RefreshToken).where(models.RefreshToken.user_id == user_id)
        )
        # Increment user token version to invalidate all current JWTs
        user = await db.get(models.User, user_id)
        if user:
            user.token_version += 1
            db.add(user)
        await db.commit()
        
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        raise HTTPException(status_code=401, detail="Token reuse detected. All sessions revoked.")

    user = await db.get(models.User, user_id)
    if not user or not user.is_active or user.token_version != token_version:
        await db.delete(db_token)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or token version")

    # Rotate tokens: Invalidate old, issue new Access + Refresh
    await db.delete(db_token)
    
    new_access_token = security.create_access_token(user.id, token_version=user.token_version)
    new_refresh_token = security.create_refresh_token(user.id, token_version=user.token_version)
    
    new_db_token = models.RefreshToken(
        token_hash=get_token_hash(new_refresh_token),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    db.add(new_db_token)
    await db.commit()
    
    response.set_cookie(key="access_token", value=new_access_token, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", path="/")
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax", path="/")
    
    return {
        "message": "Token refreshed",
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(deps.get_db)):
    token = request.cookies.get("refresh_token")
    if token:
        token_hash = get_token_hash(token)
        await db.execute(delete(models.RefreshToken).where(models.RefreshToken.token_hash == token_hash))
        await db.commit()
    
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}

@router.get("/verify-invite")
async def verify_invite_token(
    token: str,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Verify an invitation token before accepting."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(models.User).where(
            models.User.invitation_token_hash == token_hash,
            models.User.invitation_status == "pending"
        )
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or already used invitation token")

    if user.invitation_expires_at and user.invitation_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitation token has expired")

    # Resolve org auth_provider
    auth_provider_value = "any"
    if user.organization_id:
        org_result = await db.execute(
            select(models.Organization).where(models.Organization.id == user.organization_id)
        )
        org = org_result.scalars().first()
        if org and hasattr(org, 'auth_provider') and org.auth_provider:
            auth_provider_value = str(org.auth_provider.value) if hasattr(org.auth_provider, 'value') else str(org.auth_provider)

    return {
        "valid": True,
        "email": user.email,
        "full_name": user.full_name,
        "organization_name": user.organization_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role or "user"),
        "auth_provider": auth_provider_value,
    }

@router.post("/accept-invite")
async def accept_invite(
    body: schemas.user.UserAcceptInvite,
    response: Response,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Accept an invitation using a secure token, set password, and activate account.
    """
    # 1. Verify token
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    result = await db.execute(
        select(models.User).where(
            models.User.invitation_token_hash == token_hash,
            models.User.invitation_status == "pending"
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or already used invitation token")
    
    if user.invitation_expires_at and user.invitation_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitation token has expired")

    # 2. Resolve org auth_provider to determine if SSO-only
    org_auth_provider = "any"
    if user.organization_id:
        org_result = await db.execute(
            select(models.Organization).where(models.Organization.id == user.organization_id)
        )
        org = org_result.scalars().first()
        if org and hasattr(org, 'auth_provider') and org.auth_provider:
            org_auth_provider = str(org.auth_provider.value) if hasattr(org.auth_provider, 'value') else str(org.auth_provider)

    # 3. Set password — auto-generate for SSO-only orgs, require for standard orgs
    if body.password:
        user.hashed_password = security.get_password_hash(body.password)
    elif org_auth_provider != "any":
        # SSO-only org: generate a random unusable password hash
        random_password = secrets.token_urlsafe(32)
        user.hashed_password = security.get_password_hash(random_password)
    else:
        raise HTTPException(status_code=400, detail="Password is required for standard authentication organizations")
    user.invitation_status = "active"
    user.invitation_token_hash = None
    user.invitation_expires_at = None
    user.is_active = True
    
    db.add(user)
    await db.commit()

    # 3. Check 2FA requirement
    is_mandatory = totp_service.is_2fa_mandatory_for_role(user.role)
    if user.totp_enabled or is_mandatory:
        two_fa_token = security.create_2fa_challenge_token(
            subject=user.id, email=user.email, role=user.role.value if hasattr(user.role, "value") else str(user.role or "admin")
        )
        return {
            "message": "Account activated. 2FA setup required.",
            "mfa_required": True,
            "mfa_setup_required": not user.totp_enabled,
            "two_fa_token": two_fa_token,
        }

    return await issue_user_tokens(response, db, user)

@router.post("/forgot-password", dependencies=[Depends(deps.rate_limit(limit=3, window=60))])
async def forgot_password(
    body: schemas.user.ForgotPassword,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Send a password reset email.
    """
    result = await db.execute(select(models.User).where(models.User.email == body.email))
    user = result.scalars().first()
    
    if not user:
        # For security, don't reveal if user exists. Just return 200.
        return {"message": "If an account exists for this email, you will receive a reset link shortly."}

    # Generate token
    token = secrets.token_urlsafe(32)
    user.reset_token_hash = hashlib.sha256(token.encode()).hexdigest()
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    db.add(user)
    await db.commit()
    
    await send_reset_password_email(email_to=user.email, token=token, full_name=user.full_name, db=db)
    
    return {"message": "If an account exists for this email, you will receive a reset link shortly."}

@router.post("/reset-password", dependencies=[Depends(deps.rate_limit(limit=3, window=60))])
async def reset_password(
    body: schemas.user.ResetPassword,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Reset password using a secure token.
    """
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    result = await db.execute(
        select(models.User).where(
            models.User.reset_token_hash == token_hash
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    if user.reset_token_expires_at and user.reset_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    # Validate complexity
    if not security.validate_password_strength(body.password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    # Update password
    user.hashed_password = security.get_password_hash(body.password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    
    # Optional: Invalidate all sessions on password change
    user.token_version += 1
    await db.execute(
        delete(models.RefreshToken).where(models.RefreshToken.user_id == user.id)
    )
    
    db.add(user)
    await db.commit()
    
    return {"message": "Password updated successfully"}

@router.post("/register", response_model=schemas.User)
async def register_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.superadmin])),
) -> Any:
    """
    Create new user (superadmin only).
    Normal user creation goes through the invitation flow.
    """
    # Check if user exists
    from sqlalchemy import select
    result = await db.execute(select(models.User).where(models.User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = await auth_service.create_user(db=db, user_in=user_in)
    return user

@router.get("/me", response_model=schemas.User)
def read_users_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user
