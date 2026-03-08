from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType

router = APIRouter()

@router.get("/", response_model=List[schemas.Evidence])
async def read_evidence(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    result = await db.execute(
        select(models.Evidence)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/", response_model=schemas.Evidence)
async def create_evidence(
    *,
    db: AsyncSession = Depends(deps.get_db),
    evidence_in: schemas.EvidenceCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.analyst])),
) -> Any:
    evidence = models.Evidence(
        **evidence_in.model_dump()
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.created,
        entity_type=AuditEntityType.evidence,
        entity_id=evidence.id,
        entity_name=evidence.title,
        new_values=evidence_in.model_dump(mode='json'),
        description=f"Evidence uploaded: {evidence.title}"
    )
    await db.commit()
    return evidence
