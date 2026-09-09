import base64
import io
import logging
import secrets
from typing import List, Tuple
import pyotp
import qrcode

from app.config import settings
from app.models.user import UserRole, User

logger = logging.getLogger("grc.totp")

MANDATORY_2FA_ROLES = {
    UserRole.superadmin,
    UserRole.admin,
    UserRole.manager,
    UserRole.compliance_officer,
}


def is_2fa_mandatory_for_role(role: UserRole) -> bool:
    """Check if 2FA is mandatory for the given user role (Option A decision)."""
    return role in MANDATORY_2FA_ROLES


def generate_totp_secret() -> str:
    """Generate a random Base32 TOTP secret."""
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, email: str) -> str:
    """Get standard otpauth:// URI for authenticator apps."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.PROJECT_NAME)


def generate_qr_code_base64(provisioning_uri: str) -> str:
    """Generate base64 PNG data URI for the TOTP QR code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=3,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def verify_totp_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verify a 6-digit TOTP code with time drift window."""
    if not secret or not code:
        return False
    # Strip spaces or dashes users might type
    clean_code = code.replace(" ", "").replace("-", "").strip()
    totp = pyotp.TOTP(secret)
    return totp.verify(clean_code, valid_window=valid_window)


def generate_backup_codes(count: int = 8) -> List[str]:
    """Generate human-friendly 8-character backup codes."""
    codes = []
    for _ in range(count):
        part1 = secrets.token_hex(2)
        part2 = secrets.token_hex(2)
        codes.append(f"{part1}-{part2}")
    return codes


def verify_and_consume_backup_code(user: User, code: str) -> Tuple[bool, List[str]]:
    """
    Check if code exists in user's backup codes.
    If match found, consume it (remove from list) and return (True, updated_codes).
    """
    if not user.totp_backup_codes:
        return False, []

    clean_code = code.strip().lower()
    existing_codes = list(user.totp_backup_codes)

    for i, c in enumerate(existing_codes):
        if c.strip().lower() == clean_code:
            remaining_codes = existing_codes[:i] + existing_codes[i+1:]
            return True, remaining_codes

    return False, existing_codes
