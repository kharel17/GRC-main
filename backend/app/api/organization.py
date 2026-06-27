from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps

router = APIRouter()


@router.get("/", response_model=schemas.OrganizationResponse)
async def get_organization(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """Get the current user's organization."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="No organization configured. Please set up your organization first.")
    return org


@router.post("/", response_model=schemas.OrganizationResponse)
async def create_organization(
    *,
    db: AsyncSession = Depends(deps.get_db),
    org_in: schemas.OrganizationCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin])),
) -> Any:
    """Create organization (admin only). Returns 409 if user already belongs to an org."""
    # Guard: prevent creating a second org for a user who already has one
    if current_user.organization_id:
        raise HTTPException(
            status_code=409,
            detail="User already belongs to an organization. Use PUT /organization/ to update."
        )

    org_data = org_in.model_dump()
    # model column 'employee_count' is String, schema sends Optional[int] — cast safely
    if org_data.get("employee_count") is not None:
        org_data["employee_count"] = str(org_data["employee_count"])

    org = models.Organization(**org_data)
    db.add(org)
    await db.flush()

    # Associate the creating user with the new organization
    current_user.organization_id = org.id
    db.add(current_user)

    await db.commit()
    await db.refresh(org)
    return org


@router.put("/", response_model=schemas.OrganizationResponse)
async def update_organization(
    *,
    db: AsyncSession = Depends(deps.get_db),
    org_in: schemas.OrganizationUpdate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin])),
) -> Any:
    """Update organization details (admin only). Scoped to current user's org."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="No organization found. Create one first.")
    
    update_data = org_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    
    # Log the action
    from app.services import audit_service
    from app.models.audit_log import AuditAction, AuditEntityType
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.updated,
        entity_type=AuditEntityType.user, # Organization doesn't have its own type in AuditEntityType enum yet, using user or compliance
        entity_id=org.id,
        entity_name=org.name,
        description="Updated organization profile and ISO context",
        auto_commit=False
    )

    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org
