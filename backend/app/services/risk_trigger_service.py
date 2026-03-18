from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app import models, schemas
from app.services.ticket_service import TicketService
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory
from app.models.risk import Risk
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class RiskTriggerService:
    @staticmethod
    async def evaluate_and_trigger(db: AsyncSession, risk_id: uuid.UUID) -> None:
        """
        Entry point after risk creation or update.
        Evaluates risk score against threshold and manages linked tickets.
        """
        # 1. Load risk with organization settings
        result = await db.execute(
            select(models.Risk)
            .where(models.Risk.id == risk_id)
        )
        risk = result.scalars().first()
        if not risk:
            return

        org_result = await db.execute(
            select(models.Organization).where(models.Organization.id == risk.organization_id)
        )
        org = org_result.scalars().first()
        if not org:
            return

        settings = org.ticket_settings or {}
        threshold = settings.get("severity_threshold", 40) # Default to Medium
        
        # 2. Handle risk resolution (mitigated or accepted often count as resolved for tickets)
        if risk.status in [models.RiskStatus.mitigated, models.RiskStatus.accepted]:
            await RiskTriggerService._close_linked_tickets(db, risk)
            return

        # 3. Check threshold
        risk_score = risk.risk_score or 0
        if risk_score < threshold:
            logger.info(f"Risk {risk.id} score {risk_score} below threshold {threshold}. No ticket triggered.")
            return

        # 4. Find assignee hierarchy
        assignee_id = await RiskTriggerService._determine_assignee(db, risk)
        
        # 5. Check for existing open tickets
        existing_ticket_stmt = (
            select(models.Ticket)
            .where(models.Ticket.related_risk_id == risk.id)
            .where(models.Ticket.status.in_([TicketStatus.open, TicketStatus.in_review, TicketStatus.escalated, TicketStatus.pending_evidence]))
        )
        existing_result = await db.execute(existing_ticket_stmt)
        existing_ticket = existing_result.scalars().first()

        if existing_ticket:
            # Update existing ticket priority/due date if risk score changed
            new_priority = TicketService.calculate_priority(risk_score)
            if existing_ticket.priority != new_priority:
                existing_ticket.priority = new_priority
                existing_ticket.due_date = TicketService.calculate_sla_due_date(new_priority)
                
                # Log activity
                activity = models.TicketActivity(
                    ticket_id=existing_ticket.id,
                    user_id=None, # System
                    activity_type=models.TicketActivityType.priority_change,
                    description=f"Ticket priority updated to {new_priority} due to risk score change to {risk_score}"
                )
                db.add(activity)
                logger.info(f"Updated existing ticket {existing_ticket.id} priority to {new_priority}")
        else:
            # Create new ticket
            await RiskTriggerService._create_ticket(db, risk, assignee_id)

        await db.commit()

    @staticmethod
    async def _determine_assignee(db: AsyncSession, risk: models.Risk) -> uuid.UUID:
        """
        Assignment Hierarchy: Asset Owner -> Dept Manager -> Admin
        """
        # 1. Asset Owner
        if risk.asset_id:
            asset_res = await db.execute(select(models.Asset).where(models.Asset.id == risk.asset_id))
            asset = asset_res.scalars().first()
            if asset and asset.owner_id:
                logger.info(f"Assigning ticket to asset owner: {asset.owner_id}")
                return asset.owner_id

        # 2. Department Manager
        # We look for a user with 'department_manager' role in the same organization
        # Or specifically the manager of the person who created the risk? 
        # Plan says "Department Manager if asset isn't linked".
        if risk.owner_id:
            owner_res = await db.execute(select(models.User).where(models.User.id == risk.owner_id))
            owner = owner_res.scalars().first()
            if owner and owner.manager_id:
                logger.info(f"Assigning ticket to owner's manager: {owner.manager_id}")
                return owner.manager_id

        # 3. System Admin Fallback
        admin_res = await db.execute(
            select(models.User).where(models.User.role == models.UserRole.admin).limit(1)
        )
        admin = admin_res.scalars().first()
        if admin:
            logger.info("Assigning ticket to fallback admin")
            return admin.id

        return risk.owner_id # Ultimate fallback

    @staticmethod
    async def _create_ticket(db: AsyncSession, risk: models.Risk, assignee_id: uuid.UUID) -> None:
        """
        Creates a new ticket linked to the risk.
        """
        priority = TicketService.calculate_priority(risk.risk_score)
        
        # Need a dummy audit log id for the model constraint
        # Or better: create a system audit log for this event
        
        ticket = models.Ticket(
            title=f"Fixing Risk: {risk.title}",
            description=f"Automated ticket created for high severity risk.\nRisk Score: {risk.risk_score}\nDescription: {risk.description}",
            priority=priority,
            status=TicketStatus.open,
            category=TicketCategory.risk_identified,
            organization_id=risk.organization_id,
            assigned_to_id=assignee_id,
            assigned_to_role="owner", # Generic placeholder
            related_risk_id=risk.id,
            risk_score=risk.risk_score,
            source_audit_log_id=None, # Optional
            created_by=risk.created_by or assignee_id,
            due_date=TicketService.calculate_sla_due_date(priority)
        )
        
        db.add(ticket)
        await db.flush()
        
        # Log activity
        activity = models.TicketActivity(
            ticket_id=ticket.id,
            user_id=None,
            activity_type=models.TicketActivityType.other,
            description="TICKET_CREATED: Automated risk-to-ticket generation triggered."
        )
        db.add(activity)
        logger.info(f"Created new ticket {ticket.id} for risk {risk.id}")

    @staticmethod
    async def _close_linked_tickets(db: AsyncSession, risk: models.Risk) -> None:
        """
        Closes any open tickets linked to a now-resolved risk.
        """
        stmt = (
            update(models.Ticket)
            .where(models.Ticket.related_risk_id == risk.id)
            .where(models.Ticket.status.in_([TicketStatus.open, TicketStatus.in_review, TicketStatus.escalated, TicketStatus.pending_evidence]))
            .values(status=TicketStatus.resolved, resolved_at=datetime.utcnow())
        )
        await db.execute(stmt)
        logger.info(f"Auto-closed tickets linked to resolved risk {risk.id}")

risk_trigger_service = RiskTriggerService()
