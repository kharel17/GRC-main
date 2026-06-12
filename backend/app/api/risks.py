from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update
from app import schemas, models
from app.models.risk import Risk
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType
from app.utils.notifications import notify

router = APIRouter()

@router.get("/categories/", response_model=List[schemas.RiskCategory])
async def get_risk_categories(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve risk categories.
    """
    result = await db.execute(select(models.RiskCategory))
    return result.scalars().all()

@router.get("/", response_model=List[schemas.Risk])
async def read_risks(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve risks. Scoped to current user's organization.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    # Use selectinload to eagerly load the category relationship
    result = await db.execute(
        select(models.Risk)
        .where(models.Risk.organization_id == org_id)
        .options(selectinload(models.Risk.category), selectinload(models.Risk.owner))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/", response_model=schemas.Risk, status_code=200)
async def create_risk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    risk_in: schemas.RiskCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Create new risk.
    """
    # Check for duplicate in last 10 seconds (catches retry duplicates)
    from datetime import datetime, timedelta
    import logging
    logger = logging.getLogger("app.api.risks")
    
    recent_cutoff = datetime.utcnow() - timedelta(seconds=10)
    
    # Check if a risk with same title and creator was created very recently
    result = await db.execute(
        select(models.Risk).where(
            models.Risk.title == risk_in.title,
            models.Risk.created_by == current_user.id,
            models.Risk.created_at >= recent_cutoff
        )
    )
    duplicate = result.scalars().first()
    
    if duplicate:
        logger.warning(f"Duplicate risk creation prevented: {risk_in.title}")
        return duplicate

    # 1. Build risk object
    risk_data = risk_in.model_dump()
    
    # Explicitly convert strings to UUID objects and handle defaults
    owner_id = risk_data.get('owner_id')
    category_id = risk_data.get('category_id')
    asset_id = risk_data.get('asset_id')

    # Convert to UUID if present and a string, otherwise preserve the Pydantic-parsed UUID object
    risk_data['owner_id'] = UUID(owner_id) if isinstance(owner_id, str) and owner_id else (owner_id or current_user.id)
    risk_data['category_id'] = UUID(category_id) if isinstance(category_id, str) and category_id else category_id
    risk_data['asset_id'] = UUID(asset_id) if isinstance(asset_id, str) and asset_id else asset_id
    
    # Double check likelihood/impact for risk_score calculation safety
    likelihood = risk_data.get('likelihood', 1)
    impact = risk_data.get('impact', 1)
    risk_data['risk_score'] = likelihood * impact

    risk = models.Risk(
        **risk_data,
        created_by=current_user.id,
        organization_id=current_user.organization_id
    )
    db.add(risk)
    
    # 2. Flush to get the risk.id without committing
    await db.flush()
    
    # 3. Add audit log to the same transaction
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.created,
        entity_type=AuditEntityType.risk,
        entity_id=risk.id,
        entity_name=risk.title,
        new_values=risk_in.model_dump(mode='json'),
        description=f"Risk created: {risk.title}"
    )
    
    # 4. Flush to DB
    await db.flush()
    await db.refresh(risk)

    # 5. Notifications
    # Notify owner
    if risk.owner_id:
        await notify(
            db=db,
            user_id=str(risk.owner_id),
            title="New risk assigned to you",
            message=f"New risk assigned to you: {risk.title} Score: {risk.risk_score}",
            entity_type="risk",
            entity_id=str(risk.id),
            link_url=f"/dashboard/risks/{risk.id}",
            notification_type="RISK_ASSIGNMENT"
        )
    
    # 5. Refresh and load relationships for serialization
    # We must eagerly load category because schemas.Risk expects it
    # and lazy-loading will fail after commit/refresh on an async session
    await db.commit()

    # 6. Trigger Ticket Evaluation Logic
    from app.services.risk_trigger_service import RiskTriggerService
    await RiskTriggerService.evaluate_and_trigger(db, risk.id)
    
    # Re-fetch for final serialization
    result = await db.execute(
        select(models.Risk)
        .options(selectinload(models.Risk.category), selectinload(models.Risk.owner))
        .where(models.Risk.id == risk.id)
    )
    risk = result.scalar_one()
    
    return risk

@router.get("/{id}/", response_model=schemas.Risk)
async def read_risk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str, # Using str, UUID conversion handled by Pydantic/SQLAlchemy usually
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get risk by ID. Scoped to current user's organization.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Risk)
        .where(models.Risk.id == id)
        .where(models.Risk.organization_id == org_id)
        .options(selectinload(models.Risk.category), selectinload(models.Risk.owner))
    )
    risk = result.scalars().first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    return risk

@router.put("/{id}/", response_model=schemas.Risk)
async def update_risk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    risk_in: schemas.RiskUpdate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Update an existing risk. Scoped to current user's organization.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Risk)
        .where(models.Risk.id == id)
        .where(models.Risk.organization_id == org_id)
        .options(selectinload(models.Risk.category), selectinload(models.Risk.owner))
    )
    risk = result.scalars().first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    # 1. Build risk object
    print("DEBUG: update_risk payload:", risk_in.model_dump(exclude_unset=True))
    old_values = {}
    update_data = risk_in.model_dump(exclude_unset=True)
    
    # Handle empty strings from frontend
    if 'category_id' in update_data and not update_data['category_id']:
        update_data['category_id'] = None
    if 'owner_id' in update_data and not update_data['owner_id']:
        update_data['owner_id'] = None
    if 'asset_id' in update_data and not update_data['asset_id']:
        update_data['asset_id'] = None

    for field, value in update_data.items():
        old_values[field] = getattr(risk, field)
        setattr(risk, field, value)

    await db.commit()
    await db.refresh(risk)

    # Reload with category
    result = await db.execute(
        select(models.Risk)
        .where(models.Risk.id == id)
        .options(selectinload(models.Risk.category))
    )
    risk = result.scalars().first()

    # Audit log
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.updated,
        entity_type=AuditEntityType.risk,
        entity_id=risk.id,
        entity_name=risk.title,
        old_values=old_values,
        new_values=update_data,
        description=f"Risk updated: {risk.title}"
    )
    await db.commit()

    # Trigger Ticket Evaluation Logic
    from app.services.risk_trigger_service import RiskTriggerService
    await RiskTriggerService.evaluate_and_trigger(db, risk.id)

    return risk


# ── Risk-Control Mapping ──────────────────────────────────

from app.models.control import RiskControlMapping, Control

@router.get("/{id}/controls/", response_model=list[schemas.RiskControlMappingOut])
async def get_risk_controls(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get all controls mapped to a risk. Scoped to current user's organization.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    # Verify the risk belongs to the user's org
    risk_check = await db.execute(
        select(models.Risk.id).where(models.Risk.id == id, models.Risk.organization_id == org_id)
    )
    if not risk_check.scalars().first():
        raise HTTPException(status_code=404, detail="Risk not found")

    result = await db.execute(
        select(RiskControlMapping)
        .where(RiskControlMapping.risk_id == id)
        .options(selectinload(RiskControlMapping.control))
    )
    mappings = result.scalars().all()
    out = []
    for m in mappings:
        out.append(schemas.RiskControlMappingOut(
            id=str(m.id),
            risk_id=str(m.risk_id),
            control_id=str(m.control_id),
            control_title=m.control.title if m.control else None,
            control_status=m.control.status.value if m.control else None,
            residual_likelihood=m.residual_likelihood,
            residual_impact=m.residual_impact,
            residual_risk_score=m.residual_risk_score,
            mapped_at=str(m.mapped_at) if m.mapped_at else None,
        ))
    return out

@router.post("/{id}/controls/", response_model=schemas.RiskControlMappingOut)
async def map_control_to_risk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    body: schemas.RiskControlMappingCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager, models.UserRole.analyst])),
) -> Any:
    """
    Map a control to a risk.
    """
    # Verify risk exists and belongs to user's org
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    risk_result = await db.execute(
        select(models.Risk).where(models.Risk.id == id, models.Risk.organization_id == org_id)
    )
    risk = risk_result.scalars().first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    # Verify control exists and belongs to user's org
    ctrl_result = await db.execute(
        select(Control).where(Control.id == body.control_id, Control.organization_id == org_id)
    )
    ctrl = ctrl_result.scalars().first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Control not found")

    mapping = RiskControlMapping(
        risk_id=id,
        control_id=body.control_id,
        mapped_by=current_user.id,
    )
    db.add(mapping)
    await db.flush()

    # Audit
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.created,
        entity_type=AuditEntityType.risk,
        entity_id=risk.id,
        entity_name=risk.title,
        new_values={"control_id": str(body.control_id), "control_title": ctrl.title},
        description=f"Control '{ctrl.title}' mapped to Risk '{risk.title}'"
    )

    # Auto-update risk status based on control mapping
    if risk and risk.status != models.RiskStatus.accepted:
        # If control is high effectiveness or implemented -> mark risk as mitigated
        if (
            ctrl.effectiveness == models.ControlEffectiveness.high
            or ctrl.status == models.ControlStatus.implemented
        ):
            risk.status = models.RiskStatus.mitigated
        # If risk was just identified -> move to assessed
        elif risk.status == models.RiskStatus.identified:
            risk.status = models.RiskStatus.assessed

    await db.commit()
    await db.refresh(mapping)

    return schemas.RiskControlMappingOut(
        id=str(mapping.id),
        risk_id=str(mapping.risk_id),
        control_id=str(mapping.control_id),
        control_title=ctrl.title,
        control_status=ctrl.status.value if ctrl.status else None,
        residual_likelihood=mapping.residual_likelihood,
        residual_impact=mapping.residual_impact,
        residual_risk_score=mapping.residual_risk_score,
        mapped_at=str(mapping.mapped_at) if mapping.mapped_at else None,
    )

@router.delete("/{id}", status_code=204)
async def delete_risk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
):
    """
    Delete a risk. Scoped to current user's organization.
    Only strictly for Admin and Manager.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Risk)
        .where(models.Risk.id == id)
        .where(models.Risk.organization_id == org_id)
        .options(selectinload(models.Risk.category), selectinload(models.Risk.owner))
    )
    risk = result.scalars().first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    
    # 1. Audit log BEFORE deletion
    # Once deleted, we can't reliably load relationships for validation
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.deleted,
        entity_type=AuditEntityType.risk,
        entity_id=risk.id,
        entity_name=risk.title,
        old_values=schemas.Risk.model_validate(risk).model_dump(mode='json'),
        description=f"Risk deleted: {risk.title}"
    )

    # 2. Delete many-to-many mappings (RiskControlMapping)
    from sqlalchemy import delete, update
    await db.execute(
        delete(RiskControlMapping).where(RiskControlMapping.risk_id == id)
    )

    # 3. Unlink direct control associations (if any)
    await db.execute(
        update(models.Control)
        .where(models.Control.linked_risk_id == id)
        .values(linked_risk_id=None)
    )
    
    # 4. Delete the risk itself
    await db.delete(risk)
    
    await db.commit()
    return None
