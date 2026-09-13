import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.models.organization import AuthProvider, Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from app.api.invitations import InviteAdminRequest
from app.schemas.user import UserAcceptInvite
from app.api.auth import verify_invite_token, accept_invite


def test_auth_provider_schema_normalization():
    # Valid values
    org1 = OrganizationCreate(name="Acme Corp", auth_provider="any")
    assert org1.auth_provider == "any"

    org2 = OrganizationCreate(name="Acme Corp", auth_provider="MICROSOFT")
    assert org2.auth_provider == "microsoft"

    org3 = OrganizationCreate(name="Acme Corp", auth_provider="Google")
    assert org3.auth_provider == "google"

    # Default value is 'any'
    org_default = OrganizationCreate(name="Default Corp")
    assert org_default.auth_provider == "any"

    # Invalid value raises ValueError
    with pytest.raises(ValueError, match="auth_provider must be one of"):
        OrganizationCreate(name="Invalid Corp", auth_provider="saml_okta")


def test_invite_admin_request_auth_provider():
    req1 = InviteAdminRequest(
        email="admin@acme.com",
        full_name="Acme Admin",
        organization_name="Acme Corp",
        auth_provider="microsoft"
    )
    assert req1.auth_provider == "microsoft"

    # Default
    req_def = InviteAdminRequest(
        email="admin@acme.com",
        full_name="Acme Admin",
        organization_name="Acme Corp"
    )
    assert req_def.auth_provider == "any"


def test_user_accept_invite_schema_optional_password():
    # Password optional for SSO
    req_sso = UserAcceptInvite(token="test-sso-token")
    assert req_sso.token == "test-sso-token"
    assert req_sso.password is None

    # Password provided for password-based setup
    req_pwd = UserAcceptInvite(token="test-pwd-token", password="SecurePassword123!")
    assert req_pwd.password == "SecurePassword123!"


@pytest.mark.anyio
async def test_verify_invite_token_returns_auth_provider():
    db = AsyncMock()
    mock_org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_user.email = "invited@company.com"
    mock_user.full_name = "Invited User"
    mock_user.role = "admin"
    mock_user.organization_name = "Contoso Ltd"
    mock_user.organization_id = mock_org_id
    mock_user.invitation_expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    mock_user.is_active = True

    mock_org = MagicMock(spec=Organization)
    mock_org.name = "Contoso Ltd"
    mock_org.auth_provider = AuthProvider.microsoft

    # Mock DB query for user and org
    user_result = MagicMock()
    user_result.scalars().first.return_value = mock_user

    org_result = MagicMock()
    org_result.scalars().first.return_value = mock_org

    db.execute.side_effect = [user_result, org_result]

    res = await verify_invite_token(token="sample-raw-token", db=db)
    assert res["valid"] is True
    assert res["email"] == "invited@company.com"
    assert res["organization_name"] == "Contoso Ltd"
    assert res["auth_provider"] == "microsoft"


@pytest.mark.anyio
async def test_accept_invite_sso_auto_generates_password():
    db = AsyncMock()
    mock_org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_user.email = "sso-user@enterprise.com"
    mock_user.role = "admin"
    mock_user.organization_name = "Enterprise Corp"
    mock_user.organization_id = mock_org_id
    mock_user.invitation_expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    mock_user.hashed_password = None

    mock_org = MagicMock(spec=Organization)
    mock_org.auth_provider = AuthProvider.microsoft

    user_result = MagicMock()
    user_result.scalars().first.return_value = mock_user

    org_result = MagicMock()
    org_result.scalars().first.return_value = mock_org

    db.execute.side_effect = [user_result, org_result]

    with patch("app.api.auth.security.create_access_token", return_value="fake-jwt-token"):
        req = UserAcceptInvite(token="sso-token")  # no password provided
        res = await accept_invite(body=req, response=MagicMock(), db=db)

        assert ("access_token" in res) or (res.get("mfa_required") is True)
        # User hashed_password should be generated and set
        assert mock_user.hashed_password is not None
        assert mock_user.invitation_token_hash is None


@pytest.mark.anyio
async def test_accept_invite_any_org_requires_password_if_omitted():
    db = AsyncMock()
    mock_org_id = uuid.uuid4()

    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_user.email = "user@generic.com"
    mock_user.organization_id = mock_org_id
    mock_user.invitation_expires_at = datetime.now(timezone.utc) + timedelta(days=1)

    mock_org = MagicMock(spec=Organization)
    mock_org.auth_provider = AuthProvider.any

    user_result = MagicMock()
    user_result.scalars().first.return_value = mock_user

    org_result = MagicMock()
    org_result.scalars().first.return_value = mock_org

    db.execute.side_effect = [user_result, org_result]

    req = UserAcceptInvite(token="generic-token")  # no password provided for 'any' org
    with pytest.raises(HTTPException) as exc_info:
        await accept_invite(body=req, response=MagicMock(), db=db)

    assert exc_info.value.status_code == 400
    assert "Password is required" in exc_info.value.detail
