from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update
from app import models, schemas
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory
from app.services.ticket_service import TicketService
import uuid

class RiskTriggerService:
    @staticmethod
    async def evaluate_and_trigger(db: AsyncSession, risk_id: uuid.UUID) -> Optional[models.Ticket]:
        """
        Main entry point to evaluate a risk and trigger ticket creation or update.
        """
        # 1. Fetch Risk with relationships
        result = await db.execute(
            select(models.Risk)
            .where(models.Risk.id == risk_id)
            .options(
                selectinload(models.Risk.asset),
                selectinload(models.Risk.organization)
            )
        )
        risk = result.scalars().first()
        if not risk:
            return None

        # 2. Get threshold (default to Medium if not set in Org settings)
        threshold = TicketPriority.medium
        if risk.organization and risk.organization.ticket_settings:
            threshold_val = risk.organization.ticket_settings.get("severity_threshold", "medium")
            threshold = TicketPriority(threshold_val)

        # 3. Map risk score/likelihood+impact to Priority
        # (Assuming risk.risk_score exists or we calculate it)
        priority = TicketService.calculate_priority(risk.risk_score)

        # 4. Check if above threshold
        priority_map = {
            TicketPriority.low: 0,
            TicketPriority.medium: 1,
            TicketPriority.high: 2,
            TicketPriority.critical: 3
        }
        
        if priority_map[priority] < priority_map[threshold]:
            return None

        # 5. Check for duplicates/existing open tickets
        # Suppression window logic: don't create new if open ticket exists for this exact risk
        existing_ticket_query = await db.execute(
            select(models.Ticket)
            .where(models.Ticket.related_risk_id == risk_id)
            .where(models.Ticket.status.in_([
                TicketStatus.open, 
                TicketStatus.in_review, 
                TicketStatus.escalated,
                TicketStatus.pending_evidence
            ]))
            .order_by(models.Ticket.created_at.desc())
            .limit(1)
        )
        existing_ticket = existing_ticket_query.scalars().first()

        if existing_ticket:
            # Update priority if it increased
            if priority_map[priority] > priority_map[existing_ticket.priority]:
                existing_ticket.priority = priority
                # Re-calculate due date based on new priority
                existing_ticket.due_date = existing_ticket.created_at + timedelta(
                    hours=RiskTriggerService._get_sla_hours(risk.organization, priority)
                )
                db.add(existing_ticket)
                await db.commit()
            return existing_ticket

        # 6. Determine Assignee (Asset Owner -> Dept Manager -> Admin)
        assignee_id = await RiskTriggerService._determine_assignee(db, risk)

        # 7. Calculate SLA
        sla_hours = RiskTriggerService._get_sla_hours(risk.organization, priority)
        due_date = datetime.utcnow() + timedelta(hours=sla_hours)

        # 8. Create Ticket
        ticket_in = schemas.TicketCreate(
            title=f"Actionable Risk: {risk.title}",
            description=risk.description,
            priority=priority,
            category=TicketCategory.risk_identified,
            source_audit_log_id=uuid.uuid4(), # System generated
            assigned_to_id=assignee_id,
            assigned_to_role="owner", # Default role label for this flow
            related_risk_id=risk.id,
            due_date=due_date,
            created_by=risk.created_by,
            organization_id=risk.organization_id
        )

        ticket = await TicketService.create_ticket(db, ticket_in, risk.created_by)
        return ticket

    @staticmethod
    async def _determine_assignee(db: AsyncSession, risk: models.Risk) -> uuid.UUID:
        """
        Assignment Hierarchy: Asset Owner -> System Admin
        """
        # 1. Asset Owner
        if risk.asset and risk.asset.owner_id:
            return risk.asset.owner_id
        
        # 2. Risk Owner (Historical fallback)
        if risk.owner_id:
            return risk.owner_id

        # 3. System Admin fallback (scoped to same org as the risk)
        admin_query = select(models.User).where(models.User.role == models.UserRole.admin)
        if risk.organization_id:
            admin_query = admin_query.where(models.User.organization_id == risk.organization_id)
        admin_res = await db.execute(admin_query.limit(1))
        admin = admin_res.scalars().first()
        if admin:
            return admin.id
            
        return risk.created_by # Absolute fallback

    @staticmethod
    def _get_sla_hours(organization: models.Organization, priority: TicketPriority) -> int:
        """
        Get SLA hours from org settings or defaults.
        """
        defaults = {
            TicketPriority.critical: 24,
            TicketPriority.high: 48,
            TicketPriority.medium: 120, # 5 days
            TicketPriority.low: 240     # 10 days
        }
        
        if organization and organization.ticket_settings:
            sla_config = organization.ticket_settings.get("sla_config", {})
            return sla_config.get(priority.value, defaults[priority])
            
        return defaults[priority]
