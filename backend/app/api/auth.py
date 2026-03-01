from datetime import datetime, timedelta
from typing import Any, Optional
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import hashlib
from app import schemas, models
from app.api import deps
from app.utils import security
from app.services import auth_service, mfa_service
from app.config import settings

router = APIRouter()

def get_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

@router.post("/login")
async def login_access_token(
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await auth_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    if user.mfa_enabled:
        # Return a temporary session for MFA verification
        mfa_token = security.create_access_token(
            user.id, 
            expires_delta=timedelta(minutes=5),
            token_version=user.token_version,
            additional_data={"mfa_pending": True}
        )
        return {
            "mfa_required": True,
            "mfa_token": mfa_token,
            "email": user.email
        }
    
    # Standard login for users without MFA
    access_token = security.create_access_token(user.id, token_version=user.token_version)
    refresh_token = security.create_refresh_token(user.id, token_version=user.token_version)
    
    # Store refresh token hash in DB
    db_refresh_token = models.RefreshToken(
        token_hash=get_token_hash(refresh_token),
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    db.add(db_refresh_token)
    await db.commit()
    
    # Set httpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"message": "Successfully logged in", "mfa_required": False}

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
        expires_at=datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    db.add(new_db_token)
    await db.commit()
    
    response.set_cookie(key="access_token", value=new_access_token, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax")
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax")
    
    return {"message": "Token refreshed"}

@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(deps.get_db)):
    token = request.cookies.get("refresh_token")
    if token:
        token_hash = get_token_hash(token)
        await db.execute(delete(models.RefreshToken).where(models.RefreshToken.token_hash == token_hash))
        await db.commit()
    
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}

@router.post("/register", response_model=schemas.User)
async def register_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Create new user.
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
@router.post("/mfa/setup")
async def setup_mfa(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """Generate MFA secret and QR code for the current user."""
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled")
    
    secret = mfa_service.generate_totp_secret()
    current_user.totp_secret = secret
    db.add(current_user)
    await db.commit()
    
    uri = mfa_service.get_totp_uri(secret, current_user.email)
    qr_code = mfa_service.generate_qr_code_base64(uri)
    
    return {
        "secret": secret,
        "qr_code": qr_code
    }

@router.post("/mfa/enable")
async def enable_mfa(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    mfa_in: schemas.MFAVerify = None
) -> Any:
    """Verify code and enable MFA for the user."""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="MFA setup not initiated")
    
    if not mfa_service.verify_totp_token(current_user.totp_secret, mfa_in.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    
    current_user.mfa_enabled = True
    db.add(current_user)
    await db.commit()
    return {"message": "MFA enabled successfully"}

@router.post("/mfa/verify")
async def verify_mfa_login(
    response: Response,
    mfa_in: schemas.MFALoginVerify,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """Verify MFA code during login to get final tokens."""
    try:
        payload = security.decode_token(mfa_in.mfa_token)
        if not payload.get("mfa_pending"):
            raise HTTPException(status_code=401, detail="Invalid MFA token")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA token")
    
    user = await db.get(models.User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    if not mfa_service.verify_totp_token(user.totp_secret, mfa_in.code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    # Issue real tokens
    access_token = security.create_access_token(user.id, token_version=user.token_version)
    refresh_token = security.create_refresh_token(user.id, token_version=user.token_version)
    
    db_refresh_token = models.RefreshToken(
        token_hash=get_token_hash(refresh_token),
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    db.add(db_refresh_token)
    await db.commit()
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=settings.ENVIRONMENT == "production", samesite="lax")
    
    return {"message": "Successfully authenticated with MFA"}

@router.post("/forgot-password")
async def forgot_password(
    password_in: schemas.ForgotPassword,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """Generate a password reset token and send (mock) email."""
    result = await db.execute(select(models.User).where(models.User.email == password_in.email))
    user = result.scalars().first()
    
    if not user:
        # Avoid user enumeration by returning success anyway
        return {"message": "If the email exists, a reset link has been sent."}
    
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    
    db.add(user)
    await db.commit()
    
    # In a real app, send actual email here
    print(f"DEBUG: Password reset token for {user.email}: {token}")
    
    return {
        "message": "Password reset initiated",
        "debug_token": token # For demo purposes only
    }

@router.post("/reset-password")
async def reset_password(
    reset_in: schemas.ResetPassword,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """Verify reset token and update password."""
    result = await db.execute(
        select(models.User).where(
            models.User.reset_token == reset_in.token,
            models.User.reset_token_expires > datetime.utcnow()
        )
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    user.hashed_password = security.get_password_hash(reset_in.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    # Increment token version to revoke all current sessions
    user.token_version += 1
    
    db.add(user)
    await db.commit()
    
    return {"message": "Password updated successfully"}
