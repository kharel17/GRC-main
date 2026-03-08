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

# Add PUT/DELETE as needed, keeping it minimal for now
