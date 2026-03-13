import asyncio
import os
import sys
from uuid import UUID
from datetime import datetime
from sqlalchemy import select

# Add the current directory to sys.path to resolve 'app' correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.services.gap_analysis_service import generate_gap_report, create_tickets_from_gaps
from app.services.evidence_service import EvidenceService
from app.models.organization import Organization
from app.models.user import User
from app.models.evidence import Evidence, EvidenceStatus, EvidenceRelatedTo
from app.models.ticket import Ticket, TicketStatus
from app.models.control_applicability import ControlApplicability, ControlImplementationStatus

async def run_consolidated_verification():
    """
    Consolidated verification for GRC Engine Phases 3-7:
    - Gap Analysis
    - Automated Ticketing
    - Evidence Verification Workflow
    """
    print("=== GRC ENGINE CONSOLIDATED VERIFICATION ===")
    
    async with SessionLocal() as db:
        try:
            # 1. Environment Check
            res = await db.execute(select(Organization).limit(1))
            org = res.scalar()
            if not org:
                print("Error: No Organization found. Please seed the database first.")
                return

            u_res = await db.execute(select(User).limit(1))
            admin = u_res.scalar()
            
            print(f"Target Org: {org.name}")
            print(f"Target User: {admin.email}")

            # 2. Gap Analysis & Ticketing (Phases 3, 5, 6)
            print("\n[Phase 3/5/6] Testing Gap Analysis & Ticketing...")
            report = await generate_gap_report(db, org.id)
            print(f"Found {len(report.gaps)} gaps.")
            
            # Target a specific control for testing (e.g., 5.1)
            target_annex = '5.1'
            target_gap = next((g for g in report.gaps if g.control_annex == target_annex), report.gaps[0])
            print(f"Testing with Control: {target_gap.control_annex}")

            tickets_data = await create_tickets_from_gaps(
                db=db,
                organization_id=org.id,
                created_by=admin,
                gap_annexes=[target_gap.control_annex]
            )
            
            if tickets_data:
                ticket_id = tickets_data[0]['ticket_id']
                t_res = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
                ticket = t_res.scalar()
                print(f"SUCCESS: Created Ticket '{ticket.title}'")
            else:
                # Check if one already exists
                t_res = await db.execute(select(Ticket).where(
                    Ticket.organization_id == org.id,
                    Ticket.status != TicketStatus.resolved,
                    Ticket.title.like(f"%{target_gap.control_annex}%")
                ).limit(1))
                ticket = t_res.scalar()
                if ticket:
                    print(f"INFO: Using existing Ticket '{ticket.title}'")
                else:
                    print("FAILED: No ticket created and no existing ticket found.")
                    return

            # 3. Evidence Verification Workflow (Phase 7)
            print("\n[Phase 7] Testing Evidence Verification Workflow...")
            
            # Find Control Applicability
            ca_res = await db.execute(select(ControlApplicability).where(
                ControlApplicability.organization_id == org.id,
                ControlApplicability.control_annex == target_gap.control_annex
            ))
            ca = ca_res.scalar()
            
            # Upload Evidence
            evidence = Evidence(
                title=f"Verification Evidence - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                description="Consolidated verification test evidence.",
                file_name="test_evidence.pdf",
                status=EvidenceStatus.pending,
                organization_id=org.id,
                related_to=EvidenceRelatedTo.compliance_item,
                related_id=ca.id,
                uploaded_by=admin.id
            )
            db.add(evidence)
            await db.commit()
            await db.refresh(evidence)
            print(f"SUCCESS: Uploaded Evidence '{evidence.title}'")

            # Verify Evidence
            print("Verifying evidence via EvidenceService...")
            await EvidenceService.verify_evidence(
                db=db,
                evidence_id=evidence.id,
                verifier=admin,
                status=EvidenceStatus.verified,
                notes="Consolidated test run."
            )

            # 4. Final Validation
            await db.refresh(ca)
            # Fetch ticket again to see if it's resolved
            t_res = await db.execute(select(Ticket).where(Ticket.id == ticket.id))
            ticket = t_res.scalar()

            print("\n=== FINAL RESULTS ===")
            print(f"Evidence Status: {evidence.status}")
            print(f"Control Status: {ca.status}")
            print(f"Ticket Status: {ticket.status}")

            if ca.status == ControlImplementationStatus.implemented and ticket.status == TicketStatus.resolved:
                print("\nCONSOLIDATED ENGINE VERIFICATION COMPLETED SUCCESSFULLY!")
            else:
                print("\nCONSOLIDATED ENGINE VERIFICATION FAILED.")

        except Exception as e:
            print(f"\nVerification encountered an error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_consolidated_verification())
