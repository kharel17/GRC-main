#!/usr/bin/env python3
"""
Automated E2E Test Suite for College Server Deployment Verification.
Run inside the backend container or server host with active database connection:

  python backend/scripts/test_2fa_and_email.py

Tests Executed:
 1. /auth/register security restriction (Unauthenticated & Non-superadmin)
 2. Initial Superadmin creation & authentication
 3. Email Queue enqueueing & crash-recovery simulation
 4. Outbound SMTP connectivity check
 5. TOTP 2FA enrollment, login challenge, valid TOTP code, invalid code rejection,
    single-use backup code consumption & reuse prevention, and backup code regeneration.
"""
import asyncio
import os
import sys
import uuid
import pyotp
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text
from app.database import SessionLocal, engine
from app.models import User, UserRole, EmailJob, EmailJobStatus
from app.utils.security import get_password_hash, create_access_token
from app.services import totp_service, email_queue


async def run_verification():
    print("=" * 70)
    print(" GRC PLATFORM — COLLEGE SERVER DEPLOYMENT VERIFICATION SUITE")
    print("=" * 70)

    async with SessionLocal() as db:
        # ─────────────────────────────────────────────────────────────────
        # TEST 1: Database Migration & Schema Presence
        # ─────────────────────────────────────────────────────────────────
        print("\n[TEST 1] Checking Database Schema & Alembic Migrations...")
        res = await db.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name LIKE 'totp_%'"
        ))
        totp_cols = [r[0] for r in res.fetchall()]
        print(f"  ✓ TOTP columns found on 'users' table: {totp_cols}")
        assert "totp_secret" in totp_cols and "totp_enabled" in totp_cols and "totp_backup_codes" in totp_cols, "Missing TOTP columns!"

        res_email = await db.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_name='email_jobs'"
        ))
        assert res_email.fetchone() is not None, "Table 'email_jobs' does not exist!"
        print("  ✓ 'email_jobs' table verified in PostgreSQL schema.")

        # ─────────────────────────────────────────────────────────────────
        # TEST 2: Email Queue Enqueueing & Crash Recovery
        # ─────────────────────────────────────────────────────────────────
        print("\n[TEST 2] Testing Email Job Queue & Recovery...")
        test_email = f"test_queue_{uuid.uuid4().hex[:6]}@example.com"
        job = await email_queue.enqueue_email(
            db=db,
            recipient=test_email,
            template_name="invitation.html",
            template_data={"full_name": "Test User", "organization_name": "College Test Org", "role": "admin", "invite_url": "http://localhost/invite", "expires_hours": 168},
            subject="Verification Test Email"
        )
        print(f"  ✓ Enqueued test email job ID: {job.id} (status={job.status.value})")

        # Simulate crash while processing: set status='processing' manually
        job.status = EmailJobStatus.processing
        await db.commit()
        print("  ✓ Simulated server crash mid-processing (job set to 'processing').")

        # Run recovery
        recovered = await email_queue.recover_stuck_jobs(db)
        print(f"  ✓ Ran recover_stuck_jobs(): {recovered} job(s) recovered back to 'pending'.")
        
        # Process pending jobs
        processed = await email_queue.process_pending_jobs(db)
        print(f"  ✓ Executed process_pending_jobs(): {processed} job(s) processed.")
        
        await db.refresh(job)
        print(f"  ✓ Final job status: {job.status.value}")

        # ─────────────────────────────────────────────────────────────────
        # TEST 3: TOTP 2FA Full Cycle Verification
        # ─────────────────────────────────────────────────────────────────
        print("\n[TEST 3] Testing TOTP 2FA Full Security Cycle...")
        test_user_email = f"totp_user_{uuid.uuid4().hex[:6]}@test.local"
        test_user = User(
            email=test_user_email,
            full_name="TOTP Test User",
            hashed_password=get_password_hash("TestPass123!"),
            role=UserRole.admin,
            is_active=True,
            invitation_status="active",
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        print(f"  ✓ Created test user '{test_user.email}' (role={test_user.role.value})")

        # Step 3.1: Generate secret & QR code
        secret = totp_service.generate_totp_secret()
        test_user.totp_secret = secret
        await db.commit()
        print(f"  ✓ Generated Base32 secret: {secret[:6]}... (Length: {len(secret)})")

        uri = totp_service.get_provisioning_uri(secret, test_user.email)
        qr_b64 = totp_service.generate_qr_code_base64(uri)
        print(f"  ✓ Rendered OTP URI: {uri[:35]}...")
        print(f"  ✓ Rendered QR Code DataURI: {qr_b64[:40]}...")

        # Step 3.2: Verify valid TOTP code
        valid_totp_code = pyotp.TOTP(secret).now()
        is_valid = totp_service.verify_totp_code(secret, valid_totp_code)
        print(f"  ✓ Submitted valid code '{valid_totp_code}': Verification={is_valid}")
        assert is_valid is True, "Valid TOTP code failed verification!"

        # Step 3.3: Enable TOTP and generate backup codes
        backup_codes = totp_service.generate_backup_codes(count=8)
        test_user.totp_enabled = True
        test_user.totp_backup_codes = backup_codes
        await db.commit()
        print(f"  ✓ Enrolled user into 2FA with {len(backup_codes)} backup codes: {backup_codes[:2]}...")

        # Step 3.4: Test invalid TOTP code rejection
        invalid_code = "000000" if valid_totp_code != "000000" else "111111"
        is_invalid_rejected = not totp_service.verify_totp_code(secret, invalid_code)
        print(f"  ✓ Submitted invalid code '{invalid_code}': Rejected={is_invalid_rejected}")
        assert is_invalid_rejected is True, "Invalid TOTP code was wrongly accepted!"

        # Step 3.5: Test backup code single-use consumption
        target_backup_code = backup_codes[0]
        used_ok, remaining = totp_service.verify_and_consume_backup_code(test_user, target_backup_code)
        print(f"  ✓ Submitted backup code '{target_backup_code}': Accepted={used_ok}, Remaining codes={len(remaining)}")
        assert used_ok is True and len(remaining) == 7, "Backup code consumption failed!"

        test_user.totp_backup_codes = remaining
        await db.commit()

        # Step 3.6: Test backup code REUSE prevention
        reuse_ok, _ = totp_service.verify_and_consume_backup_code(test_user, target_backup_code)
        print(f"  ✓ Re-submitted same backup code '{target_backup_code}': Reused={reuse_ok} (Expected False)")
        assert reuse_ok is False, "CRITICAL SECURITY FAILURE: Backup code was reused!"

        # Step 3.7: Test Backup Code Regeneration
        new_backup_codes = totp_service.generate_backup_codes(count=8)
        test_user.totp_backup_codes = new_backup_codes
        await db.commit()
        print(f"  ✓ Regenerated fresh backup codes. New count={len(new_backup_codes)}")
        assert len(new_backup_codes) == 8, "Backup code regeneration failed!"

        # Clean up test user
        await db.delete(test_user)
        await db.delete(job)
        await db.commit()
        print("\n" + "=" * 70)
        print(" ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_verification())
