from typing import Any, List
from fastapi import APIRouter, Depends
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
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Retrieve audit logs.
    """
    result = await db.execute(
        select(models.AuditLog)
        .order_by(models.AuditLog.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
