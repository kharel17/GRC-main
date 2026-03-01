import pyotp
import qrcode
import io
import base64
from app.config import settings

def generate_totp_secret() -> str:
    """Generate a random base32 TOTP secret."""
    return pyotp.random_base32()

def get_totp_uri(secret: str, email: str) -> str:
    """Get the provisioning URI for a TOTP secret."""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=settings.PROJECT_NAME
    )

def verify_totp_token(secret: str, token: str) -> bool:
    """Verify a TOTP token against a secret."""
    if not secret or not token:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(token)

def generate_qr_code_base64(uri: str) -> str:
    """Generate a base64 encoded QR code image from a URI."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()
