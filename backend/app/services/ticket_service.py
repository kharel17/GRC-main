from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update
from app import models, schemas
from app.models.ticket import TicketStatus, TicketPriority
from app.models.ticket_activity import TicketActivityType
from app.services.notification_service import NotificationService
import uuid

class TicketService:
    @staticmethod
    def calculate_priority(risk_score: int) -> TicketPriority:
        """Maps a 0-100 risk score to a TicketPriority."""
        if risk_score >= 85:
            return TicketPriority.critical
        elif risk_score >= 65:
            return TicketPriority.high
        elif risk_score >= 40:
            return TicketPriority.medium
        return TicketPriority.low

    @staticmethod
    async def process_ai_finding(
        db: AsyncSession,
        finding_text: str,
        current_user_id: uuid.UUID,
        control_id: Optional[uuid.UUID] = None,
        risk_id: Optional[uuid.UUID] = None,
        source_audit_log_id: Optional[uuid.UUID] = None
    ) -> models.Ticket:
        """
        Processes an AI finding: ISO mapping, weighting, repeat check, and tiered assignment.
        """
        # 1. ISO Mapping & Weighting (Surgical Extraction Simulation)
        # Geminis extraction would produce these specific fields
        iso_clause = "A.18.1.1" # Example default: Compliance with legal/contractual requirements
        risk_score = 50 
        
        lower_text = finding_text.lower()
        if "critical" in lower_text or "vulnerability" in lower_text:
            iso_clause = "A.12.6.1"
            risk_score = 95
        elif "password" in lower_text or "mfa" in lower_text:
            iso_clause = "A.9.2.1"
            risk_score = 85
        elif "encryption" in lower_text or "tls" in lower_text:
            iso_clause = "A.10.1.1"
            risk_score = 70
        elif "policy" in lower_text:
            iso_clause = "A.5.1.1"
            risk_score = 30
        
        # 2. Criticality Mapping
        base_priority = TicketService.calculate_priority(risk_score)

        # 3. Repeat Check (Last 90 days) - State Agnostic
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        repeat_query = await db.execute(
            select(models.Ticket)
            .where(models.Ticket.iso_clause == iso_clause)
            .where(models.Ticket.created_at >= ninety_days_ago)
            .order_by(models.Ticket.created_at.desc())
            .limit(1)
        )
        previous_ticket = repeat_query.scalars().first()
        is_repeat = previous_ticket is not None
        previous_ticket_id = previous_ticket.id if previous_ticket else None

        # 4. Assignee Determination & SLA
        # We need to find users with specific roles
        async def get_user_by_role(role: models.UserRole) -> Optional[models.User]:
            res = await db.execute(select(models.User).where(models.User.role == role).limit(1))
            return res.scalars().first()

        l1_admin = await get_user_by_role(models.UserRole.admin)
        l2_manager = await get_user_by_role(models.UserRole.manager)
        l3_analyst = await get_user_by_role(models.UserRole.analyst)

        # Default fallback
        assigned_to = l3_analyst or l1_admin
        priority = base_priority
        sla_hours = 0

        if not is_repeat:
            if base_priority == TicketPriority.critical:
                assigned_to = l1_admin
                sla_hours = 24
            elif base_priority == TicketPriority.high:
                assigned_to = l2_manager
                sla_hours = 48
            elif base_priority == TicketPriority.medium:
                assigned_to = l3_analyst
                sla_hours = 72
            else:
                assigned_to = l3_analyst
                sla_hours = 24 * 7
        else:
            # Repeat logic
            if base_priority == TicketPriority.critical:
                assigned_to = l1_admin # "L1 Urgent"
                sla_hours = 24
            elif base_priority == TicketPriority.high:
                assigned_to = l1_admin
                sla_hours = 24
            elif base_priority == TicketPriority.medium:
                assigned_to = l2_manager
                sla_hours = 48
            else:
                assigned_to = l2_manager
                sla_hours = 72

        # 5. Create the Ticket
        ticket_create = schemas.TicketCreate(
            title=f"AI Finding: {iso_clause} - {'REPEAT' if is_repeat else 'NEW'}",
            description=finding_text,
            priority=priority,
            category=models.ticket.TicketCategory.security_incident,
            source_audit_log_id=source_audit_log_id or uuid.uuid4(),
            assigned_to_id=assigned_to.id if assigned_to else current_user_id,
            assigned_to_role=assigned_to.role.value if assigned_to else "analyst",
            due_date=datetime.utcnow() + timedelta(hours=sla_hours),
            status_updated_at=datetime.utcnow(),
            is_repeat_finding=is_repeat,
            iso_clause=iso_clause,
            risk_score=risk_score,
            previous_ticket_id=previous_ticket_id
        )

        ticket = await TicketService.create_ticket(db, ticket_create, current_user_id)
        
        # 6. Audit Repeat Finding if applicable
        if is_repeat:
            activity = models.TicketActivity(
                ticket_id=ticket.id,
                user_id=None, # System
                activity_type=TicketActivityType.other,
                description="REPEAT_FINDING_FLAGGED: This ISO clause was flagged within the last 90 days."
            )
            db.add(activity)
            await db.commit()

        return ticket

    @staticmethod
    async def create_ticket(
        db: AsyncSession, 
        ticket_in: schemas.TicketCreate, 
        current_user_id: uuid.UUID
    ) -> models.Ticket:
        """
        Create a new ticket and log the activity.
        """
        # Calculate SLA if not provided
        due_date = ticket_in.due_date
        if not due_date:
            due_date = TicketService.calculate_sla_due_date(ticket_in.priority)

        ticket = models.Ticket(
            **ticket_in.model_dump(exclude={"due_date"}),
            due_date=due_date,
            created_by=current_user_id
        )
        
        db.add(ticket)
        await db.flush() # Get ID and other defaults
        
        # Log activity
        activity = models.TicketActivity(
            ticket_id=ticket.id,
            user_id=current_user_id,
            activity_type=TicketActivityType.other,
            new_value=TicketStatus.open,
            description=f"Ticket created by {current_user_id}"
        )
        db.add(activity)
        
        await db.commit()
        await db.refresh(ticket)
        
        # Notify assignee
        if ticket.assigned_to_id:
            await NotificationService.create_notification(
                db=db,
                user_id=ticket.assigned_to_id,
                message=f"New ticket assigned: {ticket.title}",
                type="ASSIGNMENT",
                ticket_id=ticket.id
            )
            
        return ticket

    @staticmethod
    def calculate_sla_due_date(priority: TicketPriority) -> datetime:
        """
        Calculate SLA due date based on priority.
        """
        now = datetime.utcnow()
        if priority == TicketPriority.critical:
            return now + timedelta(hours=24)
        elif priority == TicketPriority.high:
            return now + timedelta(hours=48)
        elif priority == TicketPriority.medium:
            return now + timedelta(hours=72)
        else: # low
            return now + timedelta(days=7)

    @staticmethod
    async def validate_action_permissions(
        db: AsyncSession,
        ticket: models.Ticket,
        user: models.User,
        action: str
    ) -> bool:
        """
        Validates if a user can perform a specific action on a ticket based on GRC roles.
        """
        role = user.role
        user_id = user.id

        if role == models.UserRole.admin:
            return True # Admin can do everything

        if role == models.UserRole.manager:
            # Manager can act on tickets assigned to them or their subordinates
            if ticket.assigned_to_id == user_id:
                return True
            
            # Check team (subordinates)
            sub_res = await db.execute(
                select(models.User).where(models.User.manager_id == user_id)
            )
            sub_ids = [u.id for u in sub_res.scalars().all()]
            if ticket.assigned_to_id in sub_ids:
                return True
            
            # Managers cannot CLOSE tickets (only Admin)
            if action == "close":
                return False
                
            return False

        if role == models.UserRole.analyst:
            # Analysts can only act on their own tickets
            if ticket.assigned_to_id != user_id:
                return False
            
            # Analysts can only RESOLVE or add comments
            allowed_actions = ["resolve", "comment"]
            return action in allowed_actions

        return False

    @staticmethod
    async def set_pending_evidence(
        db: AsyncSession,
        ticket_id: uuid.UUID,
        current_user: models.User,
        comment_text: str
    ) -> models.Ticket:
        """
        Sets ticket to PENDING_EVIDENCE. Only L1/L2 can trigger this on others' tickets.
        """
        result = await db.execute(
            select(models.Ticket).where(models.Ticket.id == ticket_id)
        )
        ticket = result.scalars().first()
        if not ticket:
            raise ValueError("Ticket not found")

        # Permission check: Only L1/L2, and cannot request from self (spec rule)
        if current_user.role not in [models.UserRole.admin, models.UserRole.manager]:
             raise PermissionError("Only Managers/Admins can request evidence")
        
        if ticket.assigned_to_id == current_user.id and current_user.role != models.UserRole.admin:
            raise PermissionError("Cannot set PENDING_EVIDENCE on your own ticket (Managers/Analysts)")

        ticket.status = TicketStatus.pending_evidence
        ticket.status_updated_at = datetime.utcnow()
        ticket.due_date = datetime.utcnow() + timedelta(hours=72) # SLA Reset to +72h
        
        # Mandatory comment
        activity = models.TicketActivity(
            ticket_id=ticket.id,
            user_id=current_user.id,
            activity_type=TicketActivityType.other,
            new_value=TicketStatus.pending_evidence,
            description=f"Evidence requested: {comment_text}"
        )
        db.add(activity)
        
        # Add a real comment too
        comment = models.TicketComment(
            ticket_id=ticket.id,
            author_id=current_user.id,
            text=f"[EVIDENCE REQUESTED] {comment_text}"
        )
        db.add(comment)

        await db.commit()
        await db.refresh(ticket)

        # Notify assignee of evidence request
        await NotificationService.create_notification(
            db=db,
            user_id=ticket.assigned_to_id,
            message=f"Action Required: Evidence requested for ticket {ticket.id}",
            type="EVIDENCE_REQUEST",
            ticket_id=ticket.id
        )

        return ticket

    @staticmethod
    async def update_ticket(
        db: AsyncSession, 
        ticket_id: uuid.UUID, 
        ticket_in: schemas.TicketUpdate, 
        current_user_id: uuid.UUID
    ) -> Optional[models.Ticket]:
        """
        Update a ticket and log changes.
        """
        result = await db.execute(
            select(models.Ticket).where(models.Ticket.id == ticket_id)
        )
        ticket = result.scalars().first()
        if not ticket:
            return None

        # Permission check
        res = await db.execute(select(models.User).where(models.User.id == current_user_id))
        user = res.scalars().first()
        if not await TicketService.validate_action_permissions(db, ticket, user, "update"):
            raise PermissionError("You do not have permission to update this ticket")

        update_data = ticket_in.model_dump(exclude_unset=True)
        
        # Track changes for activity log
        for field, new_value in update_data.items():
            old_value = getattr(ticket, field)
            if old_value != new_value:
                activity_type = TicketActivityType.other
                if field == "status":
                    activity_type = TicketActivityType.status_change
                    ticket.status_updated_at = datetime.utcnow()
                elif field == "priority":
                    activity_type = TicketActivityType.priority_change
                elif field == "assigned_to_id":
                    activity_type = TicketActivityType.assignment_change
                
                activity = models.TicketActivity(
                    ticket_id=ticket.id,
                    user_id=current_user_id,
                    activity_type=activity_type,
                    old_value=str(old_value),
                    new_value=str(new_value),
                    description=f"Field {field} changed"
                )
                db.add(activity)
                setattr(ticket, field, new_value)

        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def escalate_ticket(
        db: AsyncSession, 
        ticket_id: uuid.UUID, 
        escalated_to_id: uuid.UUID, 
        current_user_id: Optional[uuid.UUID],
        reason: Optional[str] = None
    ) -> Optional[models.Ticket]:
        """
        Escalate a ticket.
        """
        result = await db.execute(
            select(models.Ticket).where(models.Ticket.id == ticket_id)
        )
        ticket = result.scalars().first()
        if not ticket:
            return None

        # Permission check (Special case: Analyst cannot toggle auto-escalation)
        res = await db.execute(select(models.User).where(models.User.id == current_user_id))
        user = res.scalars().first()
        if not await TicketService.validate_action_permissions(db, ticket, user, "escalate"):
            raise PermissionError("You do not have permission to escalate this ticket")

        # Manual Escalation Guards (Spec Section 4) - Bypass for System Auto-Escalation
        if current_user_id is not None:
             if ticket.is_auto_escalation_enabled:
                  raise ValueError("Disable auto-escalation toggle first")
             
             if not reason or len(reason) < 10:
                  raise ValueError("Reason must be at least 10 characters")
             
        # Check if assignee is already L1
        assignee_role = ticket.assigned_to_role
        if assignee_role == "admin":
             raise ValueError("Already at highest authority level")

        old_id = ticket.assigned_to_id
        ticket.status = TicketStatus.escalated
        ticket.status_updated_at = datetime.utcnow()
        ticket.escalated_to_id = escalated_to_id
        ticket.escalation_level += 1
        ticket.escalated_at = datetime.utcnow()
        
        # Log activity
        activity = models.TicketActivity(
            ticket_id=ticket.id,
            user_id=current_user_id,
            activity_type=TicketActivityType.escalation,
            old_value=str(old_id),
            new_value=str(escalated_to_id),
            description=reason or "Ticket escalated"
        )
        db.add(activity)
        
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        
        # Notify new assignee
        await NotificationService.create_notification(
            db=db,
            user_id=escalated_to_id,
            message=f"Ticket Escalated: You have been assigned ticket {ticket.id}",
            type="ESCALATION",
            ticket_id=ticket.id
        )
        
        return ticket

    @staticmethod
    async def resolve_ticket(
        db: AsyncSession, 
        ticket_id: uuid.UUID, 
        current_user_id: Optional[uuid.UUID],
        resolution_notes: Optional[str] = None
    ) -> Optional[models.Ticket]:
        """
        Resolve a ticket.
        """
        result = await db.execute(
            select(models.Ticket).where(models.Ticket.id == ticket_id)
        )
        ticket = result.scalars().first()
        if not ticket:
            return None

        # Permission check
        res = await db.execute(select(models.User).where(models.User.id == current_user_id))
        user = res.scalars().first()
        if not await TicketService.validate_action_permissions(db, ticket, user, "resolve"):
            raise PermissionError("You do not have permission to resolve this ticket")

        ticket.status = TicketStatus.resolved
        ticket.status_updated_at = datetime.utcnow()
        ticket.resolved_at = datetime.utcnow()
        
        # Log activity
        activity = models.TicketActivity(
            ticket_id=ticket.id,
            user_id=current_user_id,
            activity_type=TicketActivityType.resolution,
            new_value=TicketStatus.resolved,
            description=resolution_notes or "Ticket resolved"
        )
        db.add(activity)
        
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def get_supervisor(db: AsyncSession, user: models.User) -> Optional[uuid.UUID]:
        """
        Supervisor Fallback: manager_id -> is_acting_admin=1 -> L1 Fallback.
        """
        # 1. Direct Manager
        if user.manager_id:
            return user.manager_id
            
        # 2. Acting Admin
        acting_admin_res = await db.execute(
            select(models.User).where(models.User.is_acting_admin == 1).limit(1)
        )
        acting_admin = acting_admin_res.scalars().first()
        if acting_admin:
            return acting_admin.id
            
        # 3. L1 Fallback (Admin)
        admin_res = await db.execute(
            select(models.User).where(models.User.role == models.UserRole.admin).limit(1)
        )
        admin = admin_res.scalars().first()
        if admin:
            return admin.id
            
        return None

    @staticmethod
    async def check_slas(db: AsyncSession):
        """
        Check for tickets that have passed their due date and auto-escalate if enabled.
        Strictly follows GRC Supervisor Fallback and L1 Hard Stop rules.
        """
        now = datetime.utcnow()
        result = await db.execute(
            select(models.Ticket)
            .where(models.Ticket.status.in_([
                TicketStatus.open, 
                TicketStatus.in_review, 
                TicketStatus.escalated, 
                TicketStatus.pending_evidence,
                TicketStatus.pending_l2_review,
                TicketStatus.pending_l1_signoff,
                TicketStatus.rejected
            ]))
            .where(models.Ticket.is_auto_escalation_enabled == True)
        )
        all_potential_overdue = result.scalars().all()
        
        for ticket in all_potential_overdue:
            try:
                is_overdue = False
                
                # Special logic for PENDING_EVIDENCE: 72h from status_updated_at
                if ticket.status == TicketStatus.pending_evidence:
                    if ticket.status_updated_at and (now - ticket.status_updated_at) > timedelta(hours=72):
                        is_overdue = True
                else:
                    # Standard SLA logic
                    if ticket.due_date and ticket.due_date < now:
                        is_overdue = True
                
                if not is_overdue:
                    continue

                assignee_result = await db.execute(
                    select(models.User).where(models.User.id == ticket.assigned_to_id)
                )
                assignee = assignee_result.scalars().first()
                
                if not assignee:
                    continue

                # Section 4 Logic: L1 Hard Stop (Including Acting Admin)
                if assignee.role == models.UserRole.admin or assignee.is_acting_admin == 1:
                    # Mark OVERDUE (Audit: OVERDUE_AT_ADMIN), notify Admin. Do not reassign.
                    sla_activity = models.TicketActivity(
                        ticket_id=ticket.id,
                        user_id=None,
                        activity_type=TicketActivityType.sla_missed,
                        description=f"OVERDUE_AT_L1: SLA missed at {ticket.due_date if ticket.status != TicketStatus.pending_evidence else '72h timeout'}. Assignee is L1/Acting Admin (Final Authority)."
                    )
                    db.add(sla_activity)
                    
                    # Notify Admin for Hard Stop
                    await NotificationService.create_notification(
                        db=db,
                        user_id=assignee.id,
                        message=f"Critical: Ticket {ticket.id} is OVERDUE at L1 level.",
                        type="OVERDUE_CRITICAL",
                        ticket_id=ticket.id
                    )
                    continue

                # Supervisor Fallback
                supervisor_id = await TicketService.get_supervisor(db, assignee)
                
                if supervisor_id:
                    # Reassign: Set status ESCALATED, write AUTO_ESCALATED to audit
                    await TicketService.escalate_ticket(
                        db=db,
                        ticket_id=ticket.id,
                        escalated_to_id=supervisor_id,
                        current_user_id=None, # System action
                        reason="AUTO_ESCALATED due to SLA miss"
                    )
                    
                    # Also log SLA miss specifically
                    sla_activity = models.TicketActivity(
                        ticket_id=ticket.id,
                        user_id=None,
                        activity_type=TicketActivityType.sla_missed,
                        description=f"SLA missed at {ticket.due_date}. Auto-escalated to supervisor {supervisor_id}."
                    )
                    db.add(sla_activity)
                else:
                    # Fallback if no supervisor found at all
                    sla_activity = models.TicketActivity(
                        ticket_id=ticket.id,
                        user_id=None,
                        activity_type=TicketActivityType.sla_missed,
                        description=f"SLA missed at {ticket.due_date} but no supervisor target found."
                    )
                    db.add(sla_activity)
            except Exception as e:
                # Log error for this specific ticket and continue to next
                from app.worker import logger
                logger.error(f"Failed to process SLA for ticket {ticket.id}: {e}")
                continue
        
        if all_potential_overdue:
            await db.commit()
