from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update
from app import models, schemas
from app.models.ticket import TicketStatus, TicketPriority
from app.models.ticket_activity import TicketActivityType
from app.services.notification_service import NotificationService
from app.utils.notifications import notify
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
        Processes a security finding using deterministic rule-based heuristics:
        keyword-to-ISO clause mapping, risk weighting, repeat checks, and tiered assignment.
        Note: This method uses keyword matching rules, not a live generative LLM call.
        """
        # 1. Deterministic Rule-Based Keyword-to-ISO Mapping & Weighting
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

        # First, get the current user's organization_id for org-scoped queries
        user_result = await db.execute(select(models.User).where(models.User.id == current_user_id))
        current_user = user_result.scalars().first()
        user_org_id = current_user.organization_id if current_user else None

        # 3. Repeat Check (Last 90 days) — Org-Scoped
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        repeat_stmt = (
            select(models.Ticket)
            .where(models.Ticket.iso_clause == iso_clause)
            .where(models.Ticket.created_at >= ninety_days_ago)
        )
        if user_org_id:
            repeat_stmt = repeat_stmt.where(models.Ticket.organization_id == user_org_id)

        repeat_query = await db.execute(
            repeat_stmt.order_by(models.Ticket.created_at.desc()).limit(1)
        )
        previous_ticket = repeat_query.scalars().first()
        is_repeat = previous_ticket is not None
        previous_ticket_id = previous_ticket.id if previous_ticket else None

        # 4. Assignee Determination & SLA
        async def get_user_by_role(role: models.UserRole) -> Optional[models.User]:
            query = select(models.User).where(models.User.role == role)
            if user_org_id:
                query = query.where(models.User.organization_id == user_org_id)
            res = await db.execute(query.limit(1))
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

        # 5. Create/Update the Risk (Triggers Evaluation)
        from app.services.risk_trigger_service import RiskTriggerService
        
        # Check if risk already exists for this specific control/asset (safely handle None)
        target_asset_id = risk_id or control_id
        risk = None
        if target_asset_id is not None:
            rq = select(models.Risk).where(models.Risk.asset_id == target_asset_id)
            if user_org_id:
                rq = rq.where(models.Risk.organization_id == user_org_id)
            risk_res = await db.execute(rq.limit(1))
            risk = risk_res.scalars().first()
        
        if not risk:
            # Create Risk first
            risk = models.Risk(
                title=f"AI Identified Risk: {iso_clause}",
                description=finding_text,
                likelihood=max(1, risk_score // 20),
                impact=max(1, risk_score // 20),
                risk_score=risk_score,
                status=models.RiskStatus.identified,
                organization_id=user_org_id,
                asset_id=target_asset_id,
                created_by=current_user_id,
                owner_id=current_user_id
            )
            db.add(risk)
            await db.flush()
        else:
            # Update Risk
            risk.risk_score = risk_score
            risk.description = finding_text
            db.add(risk)
            await db.flush()

        # 6. Trigger Ticket Evaluation (Centralized Logic)
        ticket = await RiskTriggerService.evaluate_and_trigger(db, risk.id)
        
        # 7. Audit Repeat Finding if applicable
        if is_repeat and ticket:
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
            await notify(
                db=db,
                user_id=ticket.assigned_to_id,
                title="New ticket assigned",
                message=f"New ticket assigned: {ticket.title}",
                entity_type="ticket",
                entity_id=ticket.id,
                link_url=f"/dashboard/tickets/{ticket.id}",
                notification_type="ASSIGNMENT"
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

        # Notify assignee of evidence request if assigned
        if ticket.assigned_to_id:
            await notify(
                db=db,
                user_id=ticket.assigned_to_id,
                title="Evidence requested",
                message=f"📎 Evidence requested: {ticket.title} - {comment_text}",
                entity_type="ticket",
                entity_id=ticket.id,
                link_url=f"/dashboard/tickets/{ticket.id}",
                notification_type="EVIDENCE_REQUEST"
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
             # Rule: Must disable auto-escalation toggle first
             if ticket.is_auto_escalation_enabled:
                  raise ValueError("Disable auto-escalation toggle first. (Prevents system from re-evaluating manually escalated tickets)")
             
             # Rule: Reason is mandatory and >= 10 chars
             if not reason or len(reason) < 10:
                  raise ValueError("Reason for manual escalation must be at least 10 characters")
             
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
        await notify(
            db=db,
            user_id=escalated_to_id,
            title="Ticket escalated to you",
            message=f"Ticket escalated to you: {ticket.title} - requires immediate attention",
            entity_type="ticket",
            entity_id=ticket.id,
            link_url=f"/dashboard/tickets/{ticket.id}",
            notification_type="ESCALATION"
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
        Strictly follows GRC Supervisor Fallback and L1 Hard Stop rules across all organizations.
        """
        from sqlalchemy import text
        now = datetime.utcnow()

        # Query all active organization IDs to set RLS context per organization
        org_result = await db.execute(select(models.Organization.id))
        org_ids = org_result.scalars().all()

        for org_id in org_ids:
            # Set RLS session context for current organization
            await db.execute(
                text("SELECT set_config('app.org_id', :org_id, true)"),
                {"org_id": str(org_id)}
            )

            result = await db.execute(
                select(models.Ticket)
                .where(models.Ticket.organization_id == org_id)
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
                    await notify(
                        db=db,
                        user_id=assignee.id,
                        title="OVERDUE",
                        message=f"🚨 OVERDUE: {ticket.title} - Requires your immediate action",
                        entity_type="ticket",
                        entity_id=ticket.id,
                        link_url=f"/dashboard/tickets/{ticket.id}",
                        notification_type="OVERDUE_CRITICAL"
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
