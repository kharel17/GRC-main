"""
Google OAuth 2.0 ID Token Verification Utility.

Verifies Google ID tokens received from the frontend client against
Google's public certificates and the configured GOOGLE_CLIENT_ID.
"""

from typing import Any, Dict
from google.oauth2 import id_token
from google.auth.transport import requests
from app.config import settings


def verify_google_token(token: str) -> Dict[str, Any]:
    """
    Verifies Google ID token against GOOGLE_CLIENT_ID and extracts user claims.

    Args:
        token: Raw JWT ID token string from Google Sign-In.

    Returns:
        dict: Extracted claims including email, full_name, google_id, email_verified.

    Raises:
        ValueError: If token signature, audience, or issuer is invalid or expired.
    """
    try:
        # If GOOGLE_CLIENT_ID is set, verify against it; otherwise pass None to skip audience check in mock/dev
        client_id = settings.GOOGLE_CLIENT_ID.strip() if settings.GOOGLE_CLIENT_ID else None
        
        id_info = id_token.verify_oauth2_token(
            token, requests.Request(), client_id
        )
        return {
            "email": id_info.get("email"),
            "full_name": id_info.get("name", ""),
            "google_id": id_info.get("sub"),
            "email_verified": id_info.get("email_verified", False),
        }
    except Exception as e:
        raise ValueError(f"Invalid Google ID token: {str(e)}")
