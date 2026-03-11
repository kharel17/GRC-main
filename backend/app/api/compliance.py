from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType

router = APIRouter()

@router.get("/", response_model=List[schemas.ComplianceItem])
async def read_compliance_items(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    result = await db.execute(
        select(models.ComplianceItem)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

from pydantic import BaseModel

class ComplianceStats(BaseModel):
    totalControls: int
    implementedControls: int
    inProgressControls: int
    notStartedControls: int
    notApplicableControls: int
    complianceScore: int

@router.get("/stats", response_model=ComplianceStats)
async def get_compliance_stats(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    # Basic mock stats for now, real implementation would count actual controls
    return ComplianceStats(
        totalControls=114,
        implementedControls=45,
        inProgressControls=20,
        notStartedControls=40,
        notApplicableControls=9,
        complianceScore=42
    )

@router.post("/", response_model=schemas.ComplianceItem)
async def create_compliance_item(
    *,
    db: AsyncSession = Depends(deps.get_db),
    item_in: schemas.ComplianceItemCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.analyst])),
) -> Any:
    item = models.ComplianceItem(
        **item_in.model_dump()
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.created,
        entity_type=AuditEntityType.compliance_item,
        entity_id=item.id,
        entity_name=item.title,
        new_values=item_in.model_dump(mode='json', exclude={'due_date'}), # date serialization handled by pydantic json mode usually
        description=f"Compliance item created: {item.title}"
    )
    await db.commit()
    return item
