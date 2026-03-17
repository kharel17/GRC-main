from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services.risk_service import recheck_risk_status
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
    try:
        result = await db.execute(
            select(models.Control)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=schemas.Control, status_code=200)
async def create_control(
    *,
    db: AsyncSession = Depends(deps.get_db),
    control_in: schemas.ControlCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    # 1. Build control object
    print("DEBUG: create_control payload:", control_in.model_dump())
    control_data = control_in.model_dump()
    control_data['owner_id'] = control_data.get('owner_id') or current_user.id
    
    control = models.Control(
        **control_data,
        created_by=current_user.id
    )
    db.add(control)
    await db.flush() # Get generated ID
    
    # 2. Audit log
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
    
    # 3. Final commit
    await db.commit()
    await db.refresh(control)
    
    return control

@router.get("/{id}", response_model=schemas.Control)
async def read_control(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    result = await db.execute(
        select(models.Control).where(models.Control.id == id)
    )
    control = result.scalars().first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return control

@router.put("/{id}", response_model=schemas.Control)
async def update_control(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    control_in: schemas.ControlUpdate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    result = await db.execute(
        select(models.Control).where(models.Control.id == id)
    )
    control = result.scalars().first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")

    old_values = {}
    update_data = control_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        old_values[field] = getattr(control, field)
        setattr(control, field, value)

    await db.commit()
    await db.refresh(control)

    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.updated,
        entity_type=AuditEntityType.control,
        entity_id=control.id,
        entity_name=control.title,
        old_values=old_values,
        new_values=update_data,
        description=f"Control updated: {control.title}"
    )
    await db.commit()

    return control


@router.delete("/{id}", status_code=204)
async def delete_control(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
):
    """
    Delete a control.
    Only strictly for Admin and Manager.
    """
    result = await db.execute(select(models.Control).where(models.Control.id == id))
    control = result.scalars().first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    
    # Capture linked risks before deletion (Bug 2)
    risk_mapping_result = await db.execute(
        select(models.RiskControlMapping.risk_id).where(models.RiskControlMapping.control_id == id)
    )
    linked_risk_ids = risk_mapping_result.scalars().all()
    
    # 1. Delete mappings first
    await db.execute(
        models.RiskControlMapping.__table__.delete().where(models.RiskControlMapping.control_id == id)
    )
    
    # 2. Delete control
    await db.delete(control)
    
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.deleted,
        entity_type=AuditEntityType.control,
        entity_id=control.id,
        entity_name=control.title,
        old_values=schemas.Control.model_validate(control).model_dump(mode='json'),
        description=f"Control deleted: {control.title}"
    )
    
    await db.commit()

    # 3. Recheck risks (Bug 2)
    for r_id in linked_risk_ids:
        await recheck_risk_status(str(r_id), db)
