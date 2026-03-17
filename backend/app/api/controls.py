from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType
from app.utils.notifications import notify

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
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.analyst])),
) -> Any:
    # 1. Build control object
    control = models.Control(
        title=control_in.title,
        description=control_in.description,
        control_type=control_in.control_type,
        effectiveness=control_in.effectiveness,
        status=control_in.status,
        owner_id=control_in.owner_id or current_user.id,
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
    
    # 4. Notifications
    # Notify owner
    if control.owner_id:
        await notify(
            db=db,
            user_id=control.owner_id,
            title="New control assigned to you",
            message=f"New control assigned to you: {control.title}",
            entity_type="control",
            entity_id=control.id,
            link_url=f"/dashboard/controls/{control.id}",
            notification_type="CONTROL_ASSIGNMENT"
        )
    
    # Notify admin if implemented
    if control.status == models.ControlStatus.implemented:
        admin_res = await db.execute(
            select(models.User).where(models.User.role == models.UserRole.admin)
        )
        admins = admin_res.scalars().all()
        for admin in admins:
            await notify(
                db=db,
                user_id=admin.id,
                title="Control implemented",
                message=f"✅ Control implemented: {control.title}",
                entity_type="control",
                entity_id=control.id,
                link_url=f"/dashboard/controls/{control.id}",
                notification_type="CONTROL_IMPLEMENTED"
            )
    
    return control

@router.get("/{id}/", response_model=schemas.Control)
async def read_control(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    result = await db.execute(
        select(models.Control).where(models.Control.id == id)
    )
    control = result.scalars().first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return control

@router.put("/{id}/", response_model=schemas.Control)
async def update_control(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    control_in: schemas.ControlUpdate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.analyst])),
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

    # Audit log
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

    # 4. Notifications for status change to implemented
    if (
        "status" in update_data 
        and update_data["status"] == models.ControlStatus.implemented 
        and old_values.get("status") != models.ControlStatus.implemented
    ):
        admin_res = await db.execute(
            select(models.User).where(models.User.role == models.UserRole.admin)
        )
        admins = admin_res.scalars().all()
        for admin in admins:
            await notify(
                db=db,
                user_id=admin.id,
                title="Control implemented",
                message=f"✅ Control implemented: {control.title}",
                entity_type="control",
                entity_id=control.id,
                link_url=f"/dashboard/controls/{control.id}",
                notification_type="CONTROL_IMPLEMENTED"
            )

    return control

@router.patch("/{id}/", response_model=schemas.Control)
async def patch_control(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    control_in: schemas.ControlUpdate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.analyst, models.UserRole.manager])),
) -> Any:
    """
    Partial update for a control. 
    Commonly used to change owner_id or status without sending full body.
    """
    import logging
    logger = logging.getLogger("grc.controls")
    
    result = await db.execute(
        select(models.Control).where(models.Control.id == id)
    )
    control = result.scalars().first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")

    update_data = control_in.model_dump(exclude_unset=True)
    logger.info(f"PATCH control {id} with data: {update_data}")

    old_values = {}
    for field, value in update_data.items():
        old_values[field] = getattr(control, field)
        setattr(control, field, value)

    await db.commit()
    await db.refresh(control)

    # Audit log
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.updated,
        entity_type=AuditEntityType.control,
        entity_id=control.id,
        entity_name=control.title,
        old_values=old_values,
        new_values=update_data,
        description=f"Control partially updated: {control.title}"
    )
    await db.commit()

    return control
