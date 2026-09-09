"""
Unit tests for Direct Google OAuth 2.0 verification and /api/v1/auth/google endpoint.
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, Response
from app.utils.google_auth import verify_google_token
from app.api.auth import login_google, GoogleLoginRequest
from app import models


def test_verify_google_token_valid():
    fake_claims = {
        "email": "test.user@example.com",
        "name": "Test User",
        "sub": "google-sub-123456",
        "email_verified": True,
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=fake_claims):
        claims = verify_google_token("dummy-valid-token")
        assert claims["email"] == "test.user@example.com"
        assert claims["full_name"] == "Test User"
        assert claims["google_id"] == "google-sub-123456"
        assert claims["email_verified"] is True


def test_verify_google_token_invalid():
    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=Exception("Expired token")):
        with pytest.raises(ValueError, match="Invalid Google ID token"):
            verify_google_token("dummy-expired-token")


@pytest.mark.anyio
async def test_login_google_unverified_email():
    unverified_claims = {
        "email": "unverified@example.com",
        "full_name": "Unverified User",
        "google_id": "google-sub-000",
        "email_verified": False,
    }
    with patch("app.api.auth.verify_google_token", return_value=unverified_claims):
        req = GoogleLoginRequest(credential="unverified-cred")
        mock_response = MagicMock(spec=Response)
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await login_google(req, mock_response, mock_db)
        assert exc_info.value.status_code == 400
        assert "not verified" in exc_info.value.detail


@pytest.mark.anyio
async def test_login_google_auto_provision_new_user():
    verified_claims = {
        "email": "new.user@example.com",
        "full_name": "New Google User",
        "google_id": "google-sub-999",
        "email_verified": True,
    }

    # Setup mock db and organizations
    mock_db = AsyncMock()
    # User does not exist
    user_scalar_result = MagicMock()
    user_scalar_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = user_scalar_result

    # Organization fallback
    dummy_org = models.Organization(
        id=uuid.uuid4(),
        name="Platform Team",
        compliance_frameworks={},
    )
    mock_db.scalar.return_value = dummy_org

    with patch("app.api.auth.verify_google_token", return_value=verified_claims):
        with patch("app.api.auth._issue_user_tokens", new_callable=AsyncMock) as mock_issue:
            mock_issue.return_value = {
                "message": "Successfully logged in",
                "access_token": "mock-jwt-token",
                "token_type": "bearer",
                "user": {"email": "new.user@example.com", "role": "analyst"},
            }

            req = GoogleLoginRequest(credential="valid-google-credential")
            mock_response = MagicMock(spec=Response)

            result = await login_google(req, mock_response, mock_db)

            assert result["access_token"] == "mock-jwt-token"
            assert result["user"]["email"] == "new.user@example.com"
            # Verify user was added to DB with GOOGLE_OAUTH password placeholder
            assert mock_db.add.called
            added_user = mock_db.add.call_args[0][0]
            assert added_user.email == "new.user@example.com"
            assert added_user.hashed_password == "GOOGLE_OAUTH"
            assert added_user.role == models.UserRole.analyst


@pytest.mark.anyio
async def test_login_google_existing_user():
    verified_claims = {
        "email": "existing@example.com",
        "full_name": "Existing User Updated Name",
        "google_id": "google-sub-111",
        "email_verified": True,
    }

    existing_user = models.User(
        id=uuid.uuid4(),
        email="existing@example.com",
        full_name="",
        hashed_password="GOOGLE_OAUTH",
        role=models.UserRole.analyst,
        is_active=True,
    )

    mock_db = AsyncMock()
    user_scalar_result = MagicMock()
    user_scalar_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = user_scalar_result

    with patch("app.api.auth.verify_google_token", return_value=verified_claims):
        with patch("app.api.auth._issue_user_tokens", new_callable=AsyncMock) as mock_issue:
            mock_issue.return_value = {
                "message": "Successfully logged in",
                "access_token": "mock-existing-jwt",
                "token_type": "bearer",
                "user": {"email": "existing@example.com", "role": "analyst"},
            }

            req = GoogleLoginRequest(credential="valid-google-credential")
            mock_response = MagicMock(spec=Response)

            result = await login_google(req, mock_response, mock_db)

            assert result["access_token"] == "mock-existing-jwt"
            assert existing_user.full_name == "Existing User Updated Name"
