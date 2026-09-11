"""
Unit tests for Role Hardening, Boundary Protections, Defect Remediations and Permission Checks.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.organization import OrganizationSize
from app.models.control import Control, ControlStatus, ControlEffectiveness
from app.models.risk import Risk, RiskStatus
from app.schemas.organization import OrganizationUpdate, OrganizationCreate
from app.api.users import delete_user, update_user_role, read_user_by_id
from app.api.risks import create_risk, map_control_to_risk
from app.api.tickets import create_ticket
from app.schemas.risk import RiskControlMappingCreate


def test_organization_size_normalization():
    """Verify that OrganizationCreate and OrganizationUpdate normalize size to lowercase."""
    org_in = OrganizationUpdate(size="Large")
    assert org_in.size == "large"

    org_in2 = OrganizationUpdate(size=" ENTERPRISE ")
    assert org_in2.size == "enterprise"

    org_in3 = OrganizationCreate(name="Acme Corp", size="Small")
    assert org_in3.size == "small"


@pytest.mark.anyio
async def test_non_superadmin_cannot_delete_superadmin():
    """Tenant admin or manager attempting to delete/deactivate a superadmin gets 403 Forbidden."""
    admin_caller = MagicMock(spec=User)
    admin_caller.id = uuid.uuid4()
    admin_caller.role = UserRole.admin
    admin_caller.organization_id = uuid.uuid4()

    target_superadmin = MagicMock(spec=User)
    target_superadmin.id = uuid.uuid4()
    target_superadmin.role = UserRole.superadmin
    target_superadmin.organization_id = admin_caller.organization_id
    target_superadmin.email = "superadmin@platform.internal"

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = target_superadmin
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await delete_user(str(target_superadmin.id), mock_db, admin_caller)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Superadmin" in exc_info.value.detail


@pytest.mark.anyio
async def test_non_superadmin_cannot_modify_superadmin_role():
    """Tenant admin attempting to modify a superadmin gets 403 Forbidden."""
    admin_caller = MagicMock(spec=User)
    admin_caller.id = uuid.uuid4()
    admin_caller.role = UserRole.admin
    admin_caller.organization_id = uuid.uuid4()

    target_superadmin = MagicMock(spec=User)
    target_superadmin.id = uuid.uuid4()
    target_superadmin.role = UserRole.superadmin
    target_superadmin.organization_id = admin_caller.organization_id

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = target_superadmin
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await update_user_role(str(target_superadmin.id), {"role": "analyst"}, mock_db, admin_caller)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Superadmin" in exc_info.value.detail


@pytest.mark.anyio
async def test_non_superadmin_cannot_escalate_to_superadmin():
    """Tenant admin attempting to escalate a user to superadmin gets 403 Forbidden."""
    admin_caller = MagicMock(spec=User)
    admin_caller.id = uuid.uuid4()
    admin_caller.role = UserRole.admin
    admin_caller.organization_id = uuid.uuid4()

    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await update_user_role(str(uuid.uuid4()), {"role": "superadmin"}, mock_db, admin_caller)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "superadmin role" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_non_superadmin_read_user_by_id_masks_superadmin():
    """Tenant admin requesting a superadmin by ID gets 404 Not Found."""
    admin_caller = MagicMock(spec=User)
    admin_caller.id = uuid.uuid4()
    admin_caller.role = UserRole.admin
    admin_caller.organization_id = uuid.uuid4()

    target_superadmin = MagicMock(spec=User)
    target_superadmin.id = uuid.uuid4()
    target_superadmin.role = UserRole.superadmin
    target_superadmin.organization_id = admin_caller.organization_id

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = target_superadmin
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await read_user_by_id(str(target_superadmin.id), mock_db, admin_caller)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_risk_mitigation_requires_implemented_control():
    """
    A mapped control with status='planned' (even if high effectiveness)
    must NOT mark the risk as mitigated. It should only transition to assessed.
    """
    caller = MagicMock(spec=User)
    caller.id = uuid.uuid4()
    caller.role = UserRole.admin
    caller.organization_id = uuid.uuid4()

    risk = Risk(
        id=uuid.uuid4(),
        title="Sample Risk",
        status=RiskStatus.identified,
        organization_id=caller.organization_id,
    )

    planned_ctrl = Control(
        id=uuid.uuid4(),
        title="Sample Planned Control",
        status=ControlStatus.planned,
        effectiveness=ControlEffectiveness.high, # High effectiveness but merely planned!
        organization_id=caller.organization_id,
    )

    mock_db = AsyncMock()
    async def fake_refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()
    mock_db.refresh.side_effect = fake_refresh

    mock_res_risk = MagicMock()
    mock_res_risk.scalars.return_value.first.return_value = risk
    mock_res_planned_ctrl = MagicMock()
    mock_res_planned_ctrl.scalars.return_value.first.return_value = planned_ctrl

    mock_db.execute.side_effect = [mock_res_risk, mock_res_planned_ctrl]

    body = RiskControlMappingCreate(control_id=planned_ctrl.id)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.services.audit_service.log_action", AsyncMock())
        await map_control_to_risk(id=str(risk.id), body=body, db=mock_db, current_user=caller)

    # Risk must NOT be mitigated; it must be assessed
    assert risk.status == RiskStatus.assessed
    assert risk.status != RiskStatus.mitigated

    # Now verify with implemented control:
    implemented_ctrl = Control(
        id=uuid.uuid4(),
        title="Implemented Control",
        status=ControlStatus.implemented,
        effectiveness=ControlEffectiveness.medium,
        organization_id=caller.organization_id,
    )
    mock_res_impl_ctrl = MagicMock()
    mock_res_impl_ctrl.scalars.return_value.first.return_value = implemented_ctrl
    mock_db.execute.side_effect = [mock_res_risk, mock_res_impl_ctrl]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.services.audit_service.log_action", AsyncMock())
        await map_control_to_risk(id=str(risk.id), body=body, db=mock_db, current_user=caller)

    assert risk.status == RiskStatus.mitigated


def test_analyst_permissions_in_role_checkers():
    """Verify endpoint signatures and dependencies grant analyst creation rights."""
    from app.api.risks import router as risks_router
    from app.api.tickets import router as tickets_router

    # Find the POST / route on risks_router
    risk_post_route = next(r for r in risks_router.routes if r.path == "/" and "POST" in r.methods)
    ticket_post_route = next(r for r in tickets_router.routes if r.path == "/" and "POST" in r.methods)

    # Check dependencies of the route handlers (FastAPI Dependant.dependencies contain Dependant objects whose callable is in .call)
    risk_role_checkers = [
        getattr(d.call, "allowed_roles", []) for d in risk_post_route.dependant.dependencies
    ]
    assert any(UserRole.analyst in roles for roles in risk_role_checkers)

    ticket_role_checkers = [
        getattr(d.call, "allowed_roles", []) for d in ticket_post_route.dependant.dependencies
    ]
    assert any(UserRole.analyst in roles for roles in ticket_role_checkers)
