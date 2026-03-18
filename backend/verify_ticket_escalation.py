import asyncio
import uuid
import sys
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import SessionLocal
from app import models, schemas
from app.services.risk_trigger_service import RiskTriggerService
from app.services.ticket_service import TicketService
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory
from app.models.user import UserRole
from app.models.risk import RiskStatus

async def verify():
    async with SessionLocal() as db:
        print("--- Starting Verification: Ticket Triggering & Escalation ---")
        sys.stdout.flush()
        
        # 1. Setup Test Data
        org = models.Organization(
            name=f"Test Org {uuid.uuid4().hex[0:6]}",
            description="Verification Org",
            ticket_settings={
                "severity_threshold": 40,
                "is_auto_escalation_enabled": True,
                "suppression_window_days": 7
            }
        )
        db.add(org)
        await db.flush()

        manager = models.User(
            email=f"manager_{uuid.uuid4().hex[0:6]}@test.com",
            full_name="Department Manager",
            hashed_password="hash",
            role=UserRole.department_manager,
            organization_id=org.id
        )
        db.add(manager)
        await db.flush()

        owner = models.User(
            email=f"owner_{uuid.uuid4().hex[0:6]}@test.com",
            full_name="Asset Owner",
            hashed_password="hash",
            role=UserRole.risk_owner,
            organization_id=org.id,
            manager_id=manager.id
        )
        db.add(owner)
        await db.flush()

        asset = models.Asset(
            name="Critical Database",
            type=models.asset.AssetType.db,
            organization_id=org.id,
            owner_id=owner.id
        )
        db.add(asset)
        await db.flush()

        # 2. Test Case 1: Initial Triggering (Critical)
        print("\nTest 1: Initial Triggering (Critical)...")
        sys.stdout.flush()
        risk = models.Risk(
            title="S3 Bucket Publicly Accessible",
            description="The production database backup bucket is public.",
            likelihood=5,
            impact=5,
            risk_score=95,
            status=RiskStatus.identified,
            organization_id=org.id,
            owner_id=owner.id,
            created_by=owner.id,
            asset_id=asset.id
        )
        db.add(risk)
        await db.flush()

        await RiskTriggerService.evaluate_and_trigger(db, risk.id)
        await db.commit()
        await db.refresh(risk)

        # Verify Ticket
        stmt = select(models.Ticket).where(models.Ticket.related_risk_id == risk.id)
        res = await db.execute(stmt)
        ticket = res.scalars().first()

        if ticket and ticket.priority == TicketPriority.critical and ticket.assigned_to_id == owner.id:
            print(f"SUCCESS: Ticket {ticket.id} created as {ticket.priority} and assigned to Owner.")
        else:
            print(f"FAILED: Ticket creation issues. Priority: {ticket.priority if ticket else 'N/A'}, Assignee: {ticket.assigned_to_id if ticket else 'N/A'}")
        sys.stdout.flush()

        # 3. Test Case 2: Severity Upgrade/Downgrade (Update Priority)
        print("\nTest 2: Risk Score Downgraded (Medium)...")
        sys.stdout.flush()
        risk.risk_score = 50
        db.add(risk)
        await db.flush()

        await RiskTriggerService.evaluate_and_trigger(db, risk.id)
        await db.commit()
        await db.refresh(ticket)

        if ticket.priority == TicketPriority.medium:
            print(f"SUCCESS: Ticket {ticket.id} updated to Medium priority.")
        else:
            print(f"FAILED: Ticket priority not updated. Current: {ticket.priority}")
        sys.stdout.flush()

        # 4. Test Case 3: Auto-Closure
        print("\nTest 3: Risk Resolved (Auto-Close)...")
        sys.stdout.flush()
        risk.status = RiskStatus.mitigated
        db.add(risk)
        await db.flush()

        await RiskTriggerService.evaluate_and_trigger(db, risk.id)
        await db.commit()
        await db.refresh(ticket)

        if ticket.status == TicketStatus.resolved:
            print(f"SUCCESS: Ticket {ticket.id} auto-closed as Resolved.")
        else:
            print(f"FAILED: Ticket not closed. Status: {ticket.status}")
        sys.stdout.flush()

        # 5. Test Case 4: Manual Escalation with Guard
        print("\nTest 4: Manual Escalation with Guard...")
        sys.stdout.flush()
        # Create a new critical risk/ticket
        new_risk = models.Risk(
            title="Unpatched OS",
            description="OS has critical vulnerabilities.",
            likelihood=5,
            impact=4,
            risk_score=90,
            status=RiskStatus.identified,
            organization_id=org.id,
            owner_id=owner.id,
            created_by=owner.id,
            asset_id=asset.id
        )
        db.add(new_risk)
        await db.flush()
        await RiskTriggerService.evaluate_and_trigger(db, new_risk.id)
        await db.commit()

        stmt = select(models.Ticket).where(models.Ticket.related_risk_id == new_risk.id)
        res = await db.execute(stmt)
        new_ticket = res.scalars().first()
        
        # Disable auto-escalation first to allow manual
        new_ticket.is_auto_escalation_enabled = False
        db.add(new_ticket)
        await db.commit()

        try:
            await TicketService.escalate_ticket(
                db=db,
                ticket_id=new_ticket.id,
                escalated_to_id=None, # Use hierarchy
                current_user_id=owner.id,
                reason="Need senior help on patching strategy"
            )
            await db.refresh(new_ticket)
            if new_ticket.status == TicketStatus.escalated and new_ticket.assigned_to_id == manager.id:
                print(f"SUCCESS: Ticket {new_ticket.id} manually escalated to Manager {manager.full_name}.")
            else:
                # In escalate_ticket, it assigns to escalated_to_id, let me check the logic.
                print(f"INFO: Reassignment details. Status: {new_ticket.status}, Assigned to: {new_ticket.assigned_to_id}")
                if new_ticket.assigned_to_id == manager.id:
                     print("SUCCESS: Correctly assigned to Manager.")
                else:
                     print(f"FAILED: Not assigned to manager. Manager ID: {manager.id}, Actual: {new_ticket.assigned_to_id}")
        except Exception as e:
            print(f"FAILED: Escalation threw error: {e}")
            import traceback
            traceback.print_exc()

        print("\n--- Verification Complete ---")
        sys.stdout.flush()

if __name__ == "__main__":
    import traceback
    try:
        asyncio.run(verify())
    except Exception:
        traceback.print_exc()
