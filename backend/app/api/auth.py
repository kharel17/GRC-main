from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import hashlib
from app import schemas, models
from app.api import deps
from app.utils import security
from app.services import auth_service
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
    
    # Create tokens with current user version
    access_token = security.create_access_token(
        user.id, token_version=user.token_version,
        email=user.email, role=user.role.value if user.role else None,
    )
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
    
    return {"message": "Successfully logged in", "access_token": access_token, "token_type": "bearer"}

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
    
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}

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
    
    if user.invitation_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invitation token has expired")

    # 2. Update user
    user.hashed_password = security.get_password_hash(body.password)
    user.invitation_status = "active"
    user.invitation_token_hash = None
    user.invitation_expires_at = None
    user.is_active = True
    
    db.add(user)
    await db.flush()

    # 3. Create tokens and log in
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
        key="access_token", value=access_token, httponly=True,
        secure=settings.ENVIRONMENT == "production", samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=settings.ENVIRONMENT == "production", samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"message": "Invitation accepted and logged in", "access_token": access_token}

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
    return current_user
