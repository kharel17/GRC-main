from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType

router = APIRouter()


@router.get("/", response_model=List[schemas.AssetResponse])
async def list_assets(
    type: Optional[str] = Query(None, description="Filter by asset type"),
    classification: Optional[str] = Query(None, description="Filter by classification"),
    criticality: Optional[str] = Query(None, description="Filter by criticality"),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """List all assets with optional filtering."""
    query = select(models.Asset).where(models.Asset.status != models.AssetStatus.decommissioned)
    
    if type:
        query = query.where(models.Asset.type == type)
    if classification:
        query = query.where(models.Asset.classification == classification)
    if criticality:
        query = query.where(models.Asset.criticality == criticality)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=schemas.AssetResponse, status_code=200)
async def create_asset(
    *,
    db: AsyncSession = Depends(deps.get_db),
    asset_in: schemas.AssetCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """Create a new asset."""
    asset = models.Asset(**asset_in.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    await audit_service.log_action(
        db=db,
        user=current_user,
        action=AuditAction.created,
        entity_type=AuditEntityType.control,  # Using 'control' as closest fit; can extend enum later
        entity_id=asset.id,
        entity_name=asset.name,
        description=f"Asset created: {asset.name} ({asset.type.value})"
    )
    await db.commit()
    return asset


@router.get("/{asset_id}", response_model=schemas.AssetResponse)
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Get asset details."""
    result = await db.execute(select(models.Asset).where(models.Asset.id == asset_id))
    asset = result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/{asset_id}", response_model=schemas.AssetResponse)
async def update_asset(
    asset_id: str,
    *,
    db: AsyncSession = Depends(deps.get_db),
    asset_in: schemas.AssetUpdate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.analyst])),
) -> Any:
    """Update an asset."""
    result = await db.execute(select(models.Asset).where(models.Asset.id == asset_id))
    asset = result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    update_data = asset_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/{asset_id}")
async def decommission_asset(
    asset_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin])),
) -> Any:
    """Decommission an asset (soft delete — sets status to decommissioned)."""
    result = await db.execute(select(models.Asset).where(models.Asset.id == asset_id))
    asset = result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    asset.status = models.AssetStatus.decommissioned
    db.add(asset)
    await db.commit()
    return {"message": f"Asset '{asset.name}' has been decommissioned"}


@router.post("/{asset_id}/risks", response_model=schemas.AssetResponse)
async def link_risks_to_asset(
    asset_id: str,
    link_in: schemas.AssetRiskLinkRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """Link one or more risks to an asset."""
    from app.models.asset_risk import AssetRiskMapping
    
    result = await db.execute(select(models.Asset).where(models.Asset.id == asset_id))
    asset = result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Simple implementation: insert into mapping table
    for risk_id in link_in.risk_ids:
        # Check if already exists
        mapping_result = await db.execute(
            select(AssetRiskMapping).where(
                AssetRiskMapping.asset_id == asset.id,
                AssetRiskMapping.risk_id == risk_id
            )
        )
        if not mapping_result.scalars().first():
            db.add(AssetRiskMapping(asset_id=asset.id, risk_id=risk_id))
    
    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/{asset_id}/risks/{risk_id}", response_model=schemas.AssetResponse)
async def unlink_risk_from_asset(
    asset_id: str,
    risk_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """Unlink a risk from an asset."""
    from app.models.asset_risk import AssetRiskMapping
    from sqlalchemy import delete
    
    result = await db.execute(select(models.Asset).where(models.Asset.id == asset_id))
    asset = result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    await db.execute(
        delete(AssetRiskMapping).where(
            AssetRiskMapping.asset_id == asset.id,
            AssetRiskMapping.risk_id == risk_id
        )
    )
    await db.commit()
    await db.refresh(asset)
    return asset
