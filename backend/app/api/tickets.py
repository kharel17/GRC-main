from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select
from app import schemas, models
from app.api import deps
from app.services import audit_service
from app.models.audit_log import AuditAction, AuditEntityType
from app.models.ticket import TicketStatus
from datetime import datetime, timedelta
from app.services.ticket_service import TicketService
from app.models.control import Control

router = APIRouter()

@router.get("/", response_model=List[schemas.Ticket])
async def read_tickets(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve tickets. Scoped to current user's organization.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    # Server-side role scoping (Spec Section 3 & 6)
    query = select(models.Ticket).where(
        models.Ticket.organization_id == org_id
    ).options(
        selectinload(models.Ticket.comments).joinedload(models.TicketComment.author),
        selectinload(models.Ticket.activities),
        selectinload(models.Ticket.assignee),
        selectinload(models.Ticket.escalated_to),
        selectinload(models.Ticket.creator)
    )

    if current_user.role == models.UserRole.analyst:
        # Analyst sees only own tickets
        query = query.where(models.Ticket.assigned_to_id == current_user.id)
    elif current_user.role == models.UserRole.manager:
        # Manager sees team tickets
        sub_query = select(models.User.id).where(models.User.manager_id == current_user.id)
        sub_res = await db.execute(sub_query)
        sub_ids = [uid for uid in sub_res.scalars().all()]
        query = query.where(
            (models.Ticket.assigned_to_id == current_user.id) | 
            (models.Ticket.assigned_to_id.in_(sub_ids))
        )
    # Admin sees all within org (no additional filter)

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/", response_model=schemas.Ticket)
async def create_ticket(
    *,
    db: AsyncSession = Depends(deps.get_db),
    ticket_in: schemas.TicketCreate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Create new ticket. Org ID is injected from current user.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    # Override organization_id from user context
    ticket_data = ticket_in.model_dump()
    ticket_data['organization_id'] = org_id
    scoped_ticket_in = schemas.TicketCreate(**ticket_data)

    return await TicketService.create_ticket(
        db=db,
        ticket_in=scoped_ticket_in,
        current_user_id=current_user.id
    )

@router.post("/from-ai", response_model=schemas.Ticket)
async def create_ticket_from_ai(
    *,
    db: AsyncSession = Depends(deps.get_db),
    ai_in: schemas.AITicketCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Module A: Rule-Based Finding Ingestion
    Creates a ticket based on incoming security findings using deterministic keyword-matching
    rules for ISO clause mapping and repeat checks.
    """
    return await TicketService.process_ai_finding(
        db=db,
        finding_text=ai_in.findingsText,
        current_user_id=current_user.id,
        control_id=ai_in.controlId,
        risk_id=ai_in.riskId,
        source_audit_log_id=ai_in.source_audit_log_id
    )

@router.get("/{id}", response_model=schemas.Ticket)
async def read_ticket(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get ticket by ID. Scoped to current user's organization.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    result = await db.execute(
        select(models.Ticket)
        .where(models.Ticket.id == id)
        .where(models.Ticket.organization_id == org_id)
        .options(
            selectinload(models.Ticket.comments).joinedload(models.TicketComment.author),
            selectinload(models.Ticket.activities),
            selectinload(models.Ticket.assignee),
            selectinload(models.Ticket.escalated_to),
            selectinload(models.Ticket.creator)
        )
    )
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.put("/{id}", response_model=schemas.Ticket)
async def update_ticket(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    ticket_in: schemas.TicketUpdate,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Update a ticket.
    """
    ticket = await TicketService.update_ticket(
        db=db,
        ticket_id=id,
        ticket_in=ticket_in,
        current_user_id=current_user.id
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.patch("/{id}/", response_model=schemas.Ticket)
async def patch_ticket(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    ticket_in: schemas.TicketUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Partial update a ticket.
    """
    ticket = await TicketService.update_ticket(
        db=db,
        ticket_id=id,
        ticket_in=ticket_in,
        current_user_id=current_user.id
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.post("/{id}/escalate", response_model=schemas.Ticket)
async def escalate_ticket(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    escalated_to_id: UUID, 
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Escalate a ticket.
    """
    ticket = await TicketService.escalate_ticket(
        db=db,
        ticket_id=id,
        escalated_to_id=escalated_to_id,
        current_user_id=current_user.id
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.post("/{id}/resolve", response_model=schemas.Ticket)
async def resolve_ticket(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    resolution: schemas.TicketResolution,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Resolve a ticket.
    """
    ticket = await TicketService.resolve_ticket(
        db=db,
        ticket_id=id,
        current_user_id=current_user.id,
        resolution_notes=resolution.resolution_notes
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.post("/{id}/request-evidence", response_model=schemas.Ticket)
async def request_evidence(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    evidence_in: schemas.EvidenceRequest,
    current_user: models.User = Depends(deps.RoleChecker([models.UserRole.admin, models.UserRole.manager])),
) -> Any:
    """
    Request evidence for a ticket (Sets status to PENDING_EVIDENCE).
    """
    return await TicketService.set_pending_evidence(
        db=db,
        ticket_id=id,
        current_user=current_user,
        comment_text=evidence_in.comment_text
    )

@router.post("/{id}/comments", response_model=schemas.TicketComment)
async def create_ticket_comment(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: UUID,
    comment_in: schemas.TicketCommentCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Add a comment to a ticket.
    """
    # Verify ticket belongs to user's org
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    ticket_check = await db.execute(
        select(models.Ticket.id)
        .where(models.Ticket.id == id)
        .where(models.Ticket.organization_id == org_id)
    )
    if not ticket_check.scalars().first():
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    comment = models.TicketComment(
        ticket_id=id,
        author_id=current_user.id,
        text=comment_in.text
    )
    db.add(comment)
    
    # Log activity
    activity = models.TicketActivity(
        ticket_id=id,
        user_id=current_user.id,
        activity_type=models.ticket_activity.TicketActivityType.comment_added,
        description=f"Comment added: {comment_in.text[:50]}..."
    )
    db.add(activity)

    await db.commit()
    await db.refresh(comment)
    return comment
