from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import uuid

from app import models, schemas
from app.models.evidence import EvidenceStatus
from app.models.ticket import TicketStatus
from app.models.control_applicability import ControlImplementationStatus
from app.services.audit_service import log_action, AuditAction, AuditEntityType

class EvidenceService:
    @staticmethod
    async def verify_evidence(
        db: AsyncSession,
        evidence_id: uuid.UUID,
        verifier: models.User,
        status: EvidenceStatus,
        notes: Optional[str] = None
    ) -> models.Evidence:
        """
        Verifies evidence and triggers automated status updates for linked controls and tickets.
        """
        # 1. Fetch Evidence
        res = await db.execute(
            select(models.Evidence).where(models.Evidence.id == evidence_id)
        )
        evidence = res.scalars().first()
        if not evidence:
            raise ValueError("Evidence not found")

        old_status = evidence.status
        evidence.status = status
        evidence.verified_by = verifier.id
        evidence.verified_at = datetime.utcnow()
        
        if status == EvidenceStatus.verified:
            evidence.verified = True
        else:
            evidence.verified = False

        db.add(evidence)
        
        # 2. Audit the verification
        await log_action(
            db=db,
            user=verifier,
            action=AuditAction.reviewed,
            entity_type=AuditEntityType.evidence,
            entity_id=evidence_id,
            entity_name=evidence.title,
            old_values={"status": old_status},
            new_values={"status": status},
            description=notes or f"Evidence {status.value} by {verifier.email}"
        )

        # 3. Automated Linkage (If Verified)
        if status == EvidenceStatus.verified:
            # A. Update Control Applicability
            # We assume evidence.related_to == 'compliance' or matched via AI
            # For this MVP, we look at the specific control it was uploaded for
            if evidence.related_to == models.evidence.EvidenceRelatedTo.compliance_item:
                ca_res = await db.execute(
                    select(models.ControlApplicability)
                    .where(models.ControlApplicability.id == evidence.related_id)
                )
                ca = ca_res.scalars().first()
                if ca:
                    ca.status = ControlImplementationStatus.implemented
                    ca.updated_at = datetime.utcnow()
                    db.add(ca)
                    
                    # B. Resolve Linked Ticket
                    # Search for OPEN tickets linked to this framework control
                    ticket_res = await db.execute(
                        select(models.Ticket)
                        .where(
                            models.Ticket.framework_control_id == ca.framework_control_id,
                            models.Ticket.organization_id == ca.organization_id,
                            models.Ticket.status.notin_([TicketStatus.resolved, TicketStatus.closed])
                        )
                    )
                    tickets = ticket_res.scalars().all()
                    for ticket in tickets:
                        ticket.status = TicketStatus.resolved
                        ticket.resolved_at = datetime.utcnow()
                        db.add(ticket)
                        
                        # Add activity log for ticket
                        activity = models.TicketActivity(
                            ticket_id=ticket.id,
                            user_id=verifier.id,
                            activity_type=models.ticket_activity.TicketActivityType.resolution,
                            description=f"Automated resolution: Evidence '{evidence.title}' verified."
                        )
                        db.add(activity)

        await db.commit()
        await db.refresh(evidence)
        return evidence
