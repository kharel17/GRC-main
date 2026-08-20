from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[schemas.AuditLog])
async def read_audit_logs(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.RoleChecker([
        models.UserRole.admin, models.UserRole.compliance_officer, models.UserRole.auditor
    ], permission_key="audit_log")),
) -> Any:
    """
    Retrieve audit logs. Scoped to the current user's organization
    by joining on the User table to restrict to same-org users.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.AuditLog)
        .join(models.User, models.AuditLog.user_id == models.User.id)
        .where(models.User.organization_id == org_id)
        .order_by(models.AuditLog.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
