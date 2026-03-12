
import asyncio
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock
from app.services.audit_service import get_readiness_score, export_audit_report
from app.services.gap_analysis_service import GapReport, GapItem

async def verify_logic():
    print("--- Verifying ISO 27001 Readiness Logic ---")
    
    # Mock DB
    db = AsyncMock()
    org_id = uuid4()
    
    # Mock Gap Report
    mock_report = GapReport(
        total_controls=114,
        applicable_controls=100,
        implemented=20,
        gaps=[
            GapItem(
                control_annex="A.5.1",
                control_title="Policies for information security",
                clause_id="5",
                severity="critical",
                current_status="not_started",
                reason="Missing policy"
            ),
            GapItem(
                control_annex="A.8.1",
                control_title="User endpoint devices",
                clause_id="8",
                severity="high",
                current_status="not_started",
                reason="No MDM"
            )
        ],
        compliance_percentage=20.0
    )
    
    # We need to mock generate_gap_report which is imported in audit_service
    from unittest.mock import patch
    
    with patch("app.services.audit_service.generate_gap_report", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_report
        # Test 1: Readiness Score
        print("\nTesting: get_readiness_score")
        score = await get_readiness_score(db, org_id)
        print(f"Compliance %: {score['compliance_percentage']}%")
        print(f"Weighted Readiness: {score['weighted_readiness']}%")
        
        # Test 2: PDF Export
        print("\nTesting: export_audit_report (PDF)")
        # Mock organization result
        mock_org = MagicMock()
        mock_org.name = "Test Org"
        
        # db.execute returns a result object
        mock_result = MagicMock()
        mock_result.scalar.return_value = mock_org
        db.execute = AsyncMock(return_value=mock_result)
        
        pdf_bytes = await export_audit_report(db, org_id, format="pdf")
        print(f"PDF Generated: {len(pdf_bytes)} bytes")
    
    with open("ISO27001_Test_Report.pdf", "wb") as f:
        f.seek(0)
        f.write(pdf_bytes)
    
    print("\nSUCCESS: Verification script completed.")

if __name__ == "__main__":
    asyncio.run(verify_logic())
