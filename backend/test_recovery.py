"""
Restart recovery test for job_queue.
Tests that recover_pending_jobs() correctly re-enqueues jobs whose
queued_payload is persisted in the DocumentAnalysis JSONB column.
"""
import asyncio
import base64
import uuid

from app.ingestion.job_queue import recover_pending_jobs, _dispatch_queue
from app import models


async def test_recovery():
    from app.database import SessionLocal
    from sqlalchemy import select

    fake_aid = uuid.uuid4()
    fake_oid = uuid.uuid4()
    fake_bytes = b'fake-file-bytes-for-recovery-test'
    fake_payload = {
        "analysis_id": str(fake_aid),
        "file_bytes_b64": base64.b64encode(fake_bytes).decode(),
        "filename": "recovery_test.pdf",
        "organization_id": str(fake_oid),
        "queued_at": "2026-08-10T09:00:00",
    }

    async with SessionLocal() as db:
        # Try inserting a fake DocumentAnalysis row in processing state
        # with queued_payload in analysis_result (as enqueue_ingestion_job would write)
        row = models.DocumentAnalysis(
            id=fake_aid,
            organization_id=fake_oid,
            file_name="recovery_test.pdf",
            file_type="pdf",
            uploaded_by=fake_oid,  # FK may fail without a real user row
            status=models.DocumentAnalysisStatus.processing,
            analysis_result={
                "processing_step": "queued",
                "progress": 0,
                "queued_payload": fake_payload,
            },
        )
        db.add(row)
        try:
            await db.commit()
            print(f"[INSERT OK] analysis_id={fake_aid}")
            insert_ok = True
        except Exception as e:
            await db.rollback()
            print(f"[INSERT FAILED — FK constraint] {e}")
            print("Testing recover_pending_jobs() against existing real rows instead...")
            insert_ok = False

        # Clear in-memory queue, then call recover
        _dispatch_queue.clear()
        count_before = len(_dispatch_queue)
        count = await recover_pending_jobs(db)
        count_after = len(_dispatch_queue)

        print(f"\nrecover_pending_jobs() returned: {count}")
        print(f"_dispatch_queue size — before={count_before}, after={count_after}")

        if insert_ok and count_after > 0:
            recovered = _dispatch_queue[-1]
            filename = recovered.get("filename")
            aid = recovered.get("analysis_id")
            has_bytes = bool(recovered.get("file_bytes_b64"))
            decoded = base64.b64decode(recovered["file_bytes_b64"])
            bytes_match = decoded == fake_bytes

            print(f"Recovered filename: {filename}")
            print(f"Recovered analysis_id: {aid}")
            print(f"file_bytes_b64 present: {has_bytes}")
            print(f"Decoded bytes match original: {bytes_match}")

            if filename == "recovery_test.pdf" and str(aid) == str(fake_aid) and bytes_match:
                print("\n[PASS] recovery_test.pdf recovered correctly from DB — bytes intact")
            else:
                print("\n[FAIL] Recovered payload mismatch")

            # Cleanup
            await db.delete(row)
            await db.commit()
            print("[CLEANUP] Test row deleted from DB")

        elif not insert_ok:
            print("Cannot fully verify without insertable row — FK constraint prevents isolated test")
            print("recover_pending_jobs() scan executed without error ✓")
        else:
            print("[FAIL] Queue did not grow after recovery (count increased but queue empty?)")


if __name__ == "__main__":
    asyncio.run(test_recovery())
