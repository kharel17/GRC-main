"""
Two-Factor Authentication (2FA / TOTP) Endpoints.

Extracted from auth.py – all TOTP setup, verification, and backup code
management routes live here. Mounted under the main auth router so that
existing URL paths (e.g. /api/v1/auth/2fa/verify-login) are preserved.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas, models
from app.api import deps
from app.utils import security
from app.services import totp_service
from app.api.auth_helpers import issue_user_tokens

router_2fa = APIRouter()


@router_2fa.post("/verify-login", dependencies=[Depends(deps.rate_limit(limit=5, window=60))])
async def verify_2fa_login(
    body: schemas.user.TOTPLoginVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Verify 6-digit TOTP code or backup code during login challenge step."""
    try:
        payload = security.decode_token(body.two_fa_token)
        if payload.get("type") != "2fa_challenge":
            raise HTTPException(status_code=401, detail="Invalid 2FA challenge token type")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired 2FA challenge token")

    user = await db.get(models.User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # If TOTP is enabled, verify code or backup code
    if user.totp_enabled:
        is_valid = totp_service.verify_totp_code(user.totp_secret, body.code)
        if not is_valid:
            # Check backup codes
            is_backup_valid, remaining_codes = totp_service.verify_and_consume_backup_code(user, body.code)
            if is_backup_valid:
                user.totp_backup_codes = remaining_codes
                db.add(user)
                await db.commit()
                is_valid = True

        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid verification code")
    else:
        raise HTTPException(
            status_code=400,
            detail="2FA setup required prior to verification"
        )

    return await issue_user_tokens(response, db, user)


@router_2fa.post("/setup-login")
async def setup_2fa_during_login(
    body: schemas.user.TOTPLoginVerifyRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Generate QR code and secret for mandatory 2FA enrollment during login.
    Uses short-lived two_fa_token.
    """
    try:
        payload = security.decode_token(body.two_fa_token)
        if payload.get("type") != "2fa_challenge":
            raise HTTPException(status_code=401, detail="Invalid 2FA challenge token type")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired 2FA challenge token")

    user = await db.get(models.User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    if not user.totp_secret:
        secret = totp_service.generate_totp_secret()
        user.totp_secret = secret
        db.add(user)
        await db.commit()
    else:
        secret = user.totp_secret

    uri = totp_service.get_provisioning_uri(secret, user.email)
    qr_code = totp_service.generate_qr_code_base64(uri)

    return {
        "secret": secret,
        "qr_code": qr_code,
        "provisioning_uri": uri,
    }


@router_2fa.post("/setup", response_model=schemas.user.TOTPSetupResponse)
async def setup_2fa(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Generate TOTP secret and QR code for authenticated user enrollment."""
    secret = totp_service.generate_totp_secret()
    current_user.totp_secret = secret
    db.add(current_user)
    await db.commit()

    uri = totp_service.get_provisioning_uri(secret, current_user.email)
    qr_code = totp_service.generate_qr_code_base64(uri)

    return {
        "secret": secret,
        "qr_code": qr_code,
        "provisioning_uri": uri,
    }


@router_2fa.post("/enable")
async def enable_2fa(
    body: schemas.user.TOTPLoginVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Confirm 2FA setup with initial TOTP code during login flow.
    """
    user = None
    if body.two_fa_token:
        try:
            payload = security.decode_token(body.two_fa_token)
            if payload.get("type") == "2fa_challenge":
                user = await db.get(models.User, payload.get("sub"))
        except Exception:
            pass

    if not user:
        raise HTTPException(status_code=400, detail="Invalid 2FA challenge token or session")

    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup has not been initiated")

    is_valid = totp_service.verify_totp_code(user.totp_secret, body.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    backup_codes = totp_service.generate_backup_codes(count=8)
    user.totp_enabled = True
    user.totp_backup_codes = backup_codes
    db.add(user)
    await db.commit()

    token_result = await issue_user_tokens(response, db, user)
    token_result["backup_codes"] = backup_codes
    return token_result


@router_2fa.post("/enable-auth")
async def enable_2fa_auth(
    body: schemas.user.TOTPVerifyRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Confirm 2FA setup for currently logged-in user in Settings."""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup has not been initiated")

    is_valid = totp_service.verify_totp_code(current_user.totp_secret, body.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    backup_codes = totp_service.generate_backup_codes(count=8)
    current_user.totp_enabled = True
    current_user.totp_backup_codes = backup_codes
    db.add(current_user)
    await db.commit()

    return {"message": "2FA successfully enabled", "backup_codes": backup_codes}


@router_2fa.post("/disable")
async def disable_2fa(
    body: schemas.user.TOTPDisableRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Disable 2FA (blocked if 2FA is mandatory for user's role)."""
    if totp_service.is_2fa_mandatory_for_role(current_user.role):
        raise HTTPException(
            status_code=400,
            detail="2FA is mandatory for your administrative role and cannot be disabled."
        )

    # Verify TOTP code or password
    is_code_valid = totp_service.verify_totp_code(current_user.totp_secret, body.code)
    is_pw_valid = body.password and security.verify_password(body.password, current_user.hashed_password)

    if not is_code_valid and not is_pw_valid:
        raise HTTPException(status_code=400, detail="Invalid verification code or password")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_backup_codes = None
    db.add(current_user)
    await db.commit()

    return {"message": "2FA successfully disabled"}


@router_2fa.get("/status", response_model=schemas.user.TOTPStatusResponse)
async def get_2fa_status(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Get 2FA enrollment status for current user."""
    return {
        "totp_enabled": bool(current_user.totp_enabled),
        "is_mandatory": totp_service.is_2fa_mandatory_for_role(current_user.role),
        "has_backup_codes": bool(current_user.totp_backup_codes and len(current_user.totp_backup_codes) > 0),
    }


@router_2fa.post("/confirm")
async def confirm_2fa_alias(
    body: schemas.user.TOTPVerifyRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Alias for confirming 2FA setup matching plan route name."""
    return await enable_2fa_auth(body=body, db=db, current_user=current_user)


@router_2fa.post("/verify-2fa")
async def verify_2fa_alias(
    body: schemas.user.TOTPLoginVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """Alias for verifying 2FA challenge matching plan route name."""
    return await verify_2fa_login(body=body, response=response, db=db)


@router_2fa.post("/regenerate-codes")
async def regenerate_backup_codes(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Regenerate a fresh set of 8 backup codes for an enrolled user."""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA must be enabled to generate backup codes.")

    backup_codes = totp_service.generate_backup_codes(count=8)
    current_user.totp_backup_codes = backup_codes
    db.add(current_user)
    await db.commit()

    return {
        "message": "Backup codes successfully regenerated",
        "backup_codes": backup_codes
    }
