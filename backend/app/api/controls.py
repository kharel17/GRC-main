from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType

router = APIRouter()

@router.get("/", response_model=List[schemas.Control])
async def read_controls(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    result = await db.execute(
        select(models.Control)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/", response_model=schemas.Control)
async def create_control(
    *,
    db: AsyncSession = Depends(deps.get_db),
    control_in: schemas.ControlCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    control = models.Control(
        **control_in.model_dump(),
        created_by=current_user.id
    )
    db.add(control)
    await db.commit()
    await db.refresh(control)
    
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.created,
        entity_type=AuditEntityType.control,
        entity_id=control.id,
        entity_name=control.title,
        new_values=control_in.model_dump(mode='json'),
        description=f"Control created: {control.title}"
    )
    await db.commit()
    return control
