from datetime import datetime
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.services.compliance_service import compliance_service
from app.models.audit_log import AuditAction, AuditEntityType

router = APIRouter()

@router.get("/", response_model=List[schemas.ComplianceItem])
async def read_compliance_items(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.ComplianceItem)
        .where(models.ComplianceItem.organization_id == org_id)
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

@router.get("/stats")
async def get_compliance_stats(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    # Use real compliance scoring logic
    stats = await compliance_service.get_compliance_score(db, current_user.organization_id)
    return {
        "totalControls": stats["total_controls"],
        "implementedControls": stats["implemented"],
        "inProgressControls": stats["in_progress"],
        "notStartedControls": stats["not_started"],
        "notApplicableControls": stats["not_applicable"],
        "complianceScore": int(stats["score"])
    }

@router.post("/", response_model=schemas.ComplianceItem)
async def create_compliance_item(
    *,
    db: AsyncSession = Depends(deps.get_db),
    item_in: schemas.ComplianceItemCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    item_data = item_in.model_dump()
    item_data['organization_id'] = org_id
    item = models.ComplianceItem(**item_data)
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
        new_values=item_in.model_dump(mode='json', exclude={'due_date'}),
        description=f"Compliance item created: {item.title}"
    )
    await db.commit()
    return item

@router.post("/recalculate")
async def recalculate_compliance(
    current_user: models.User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Recalculate compliance score based on current verified evidence.
    Available to all authenticated users.
    """
    try:
        stats = await compliance_service.get_compliance_score(db, current_user.organization_id)
        
        return {
            "score": stats["score"],
            "total_controls": stats["total_controls"],
            "verified_controls": stats["implemented"],
            "recalculated_at": datetime.utcnow()
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
