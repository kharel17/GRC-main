"""
Policies API Router.
Provides endpoints for automated policy synthesis and starter policy generation.
"""
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.database import get_db
from app.api import deps
from app.services.policy_generator import generate_starter_policies

router = APIRouter()


class GenerateStarterPoliciesRequest(BaseModel):
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    industry: Optional[str] = None
    infrastructure: Optional[str] = None
    data_types: Optional[str] = None


@router.post("/generate-starter")
async def generate_starter_policies_endpoint(
    body: Optional[GenerateStarterPoliciesRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate the 3 baseline security policies (Access Control, Incident Management, Data Protection),
    persist them as DocumentAnalysis records in PostgreSQL, and index them into Qdrant vector store.
    """
    target_org_id = (body and body.organization_id) or current_user.organization_id
    if not target_org_id:
        raise HTTPException(status_code=400, detail="User is not associated with an organization")

    if isinstance(target_org_id, str):
        try:
            target_org_id = UUID(target_org_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid organization ID format")

    org = await db.get(models.Organization, target_org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_name = str((body and body.organization_name) or org.name or "Organization")
    industry = str((body and body.industry) or org.industry or "Technology")
    infrastructure = str((body and body.infrastructure) or org.infrastructure or "Cloud Infrastructure")
    data_types = str((body and body.data_types) or org.data_types or "Confidential Business Data")

    try:
        policies = await generate_starter_policies(
            db=db,
            organization_id=org.id,
            user_id=current_user.id,
            org_name=org_name,
            industry=industry,
            infrastructure=infrastructure,
            data_types=data_types,
        )
        return {
            "success": True,
            "message": f"Successfully generated and indexed {len(policies)} starter policies",
            "policies": policies,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate starter policies: {str(e)}")
