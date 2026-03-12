from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType

router = APIRouter()

@router.get("/", response_model=List[schemas.Risk])
async def read_risks(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve risks.
    """
    # Use selectinload to eagerly load the category relationship
    result = await db.execute(
        select(models.Risk)
        .options(selectinload(models.Risk.category))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/", response_model=schemas.Risk)
async def create_risk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    risk_in: schemas.RiskCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Create new risk.
    """
    risk = models.Risk(
        **risk_in.model_dump(),
        created_by=current_user.id
    )
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    
    # Reload with category for response schema
    # Or just return risk, category will be null in response if not loaded, schema allows Optional
    
    # Log Audit
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
    await db.commit()
    
    return risk

@router.get("/{id}", response_model=schemas.Risk)
async def read_risk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str, # Using str, UUID conversion handled by Pydantic/SQLAlchemy usually
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get risk by ID.
    """
    # Cast to UUID if needed, but standard library handles it often
    result = await db.execute(
        select(models.Risk)
        .where(models.Risk.id == id)
        .options(selectinload(models.Risk.category))
    )
    risk = result.scalars().first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")
    return risk

@router.put("/{id}", response_model=schemas.Risk)
async def update_risk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    risk_in: schemas.RiskUpdate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Update an existing risk.
    """
    result = await db.execute(
        select(models.Risk)
        .where(models.Risk.id == id)
        .options(selectinload(models.Risk.category))
    )
    risk = result.scalars().first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    old_values = {}
    update_data = risk_in.model_dump(exclude_unset=True)
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

    return risk


# ── Risk-Control Mapping ──────────────────────────────────

from app.models.control import RiskControlMapping, Control

@router.get("/{id}/controls", response_model=list[schemas.RiskControlMappingOut])
async def get_risk_controls(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get all controls mapped to a risk.
    """
    result = await db.execute(
        select(RiskControlMapping)
        .where(RiskControlMapping.risk_id == id)
        .options(selectinload(RiskControlMapping.control))
    )
    mappings = result.scalars().all()
    out = []
    for m in mappings:
        out.append(RiskControlMappingOut(
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

@router.post("/{id}/controls", response_model=schemas.RiskControlMappingOut)
async def map_control_to_risk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: str,
    body: schemas.RiskControlMappingCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Map a control to a risk.
    """
    # Verify risk exists
    risk_result = await db.execute(select(models.Risk).where(models.Risk.id == id))
    risk = risk_result.scalars().first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    # Verify control exists
    ctrl_result = await db.execute(select(Control).where(Control.id == body.control_id))
    ctrl = ctrl_result.scalars().first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Control not found")

    mapping = RiskControlMapping(
        risk_id=id,
        control_id=body.control_id,
        mapped_by=current_user.id,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)

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
    await db.commit()

    return RiskControlMappingOut(
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
