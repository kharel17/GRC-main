"""
Postgres-backed Durable Job Queue for Async Document Ingestion.

Durability contract
-------------------
  • On enqueue:   job payload (including base64 file bytes) is written into the
                  DocumentAnalysis.analysis_result JSONB column under the key
                  "queued_payload". The record survives server restarts.
  • On startup:   recover_pending_jobs() reads all DocumentAnalysis rows still in
                  the 'processing' state and re-enqueues them so the worker picks
                  up any jobs that were interrupted.
  • On completion: update_job_progress() with step=ready/failed clears the
                   queued_payload from the JSONB to free the stored bytes.
"""
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import logging

from typing import Optional, Dict, Any, List
from uuid import UUID
import base64

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from app import models

logger = logging.getLogger("grc.ingestion.job_queue")


class IngestionStep(str, Enum):
    queued = "queued"
    extracting = "extracting"
    chunking = "chunking"
    embedding = "embedding"
    ready = "ready"
    failed = "failed"


@dataclass
class JobStatus:
    analysis_id: str
    organization_id: str
    file_name: str
    status: str
    step: str
    progress: int           # 0 to 100 percentage
    chunk_count: int
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# In-memory dispatch queue — populated from DB on startup and on enqueue.
# The DB record is the durable store; this list is only a fast delivery
# mechanism so the worker loop does not have to poll the DB on every iteration.
_dispatch_queue: List[Dict[str, Any]] = []
_worker_running: bool = False
_worker_task: Optional[asyncio.Task] = None


# ── DB helpers ────────────────────────────────────────────────────────────────

async def init_job_record(
    db: AsyncSession,
    doc_analysis: models.DocumentAnalysis
) -> None:
    """Initialize job tracking fields in DocumentAnalysis record."""
    initial_meta = {
        "processing_step": IngestionStep.queued.value,
        "progress": 0,
        "chunk_count": 0,
        "error": None,
        "queued_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    doc_analysis.status = models.DocumentAnalysisStatus.processing
    doc_analysis.analysis_result = initial_meta
    await db.flush()


async def update_job_progress(
    db: AsyncSession,
    analysis_id: UUID,
    step: IngestionStep,
    progress: int,
    chunk_count: int = 0,
    error: Optional[str] = None,
) -> None:
    """Update granular job step, progress, and error details in DB."""
    result = await db.execute(
        select(models.DocumentAnalysis).where(models.DocumentAnalysis.id == analysis_id)
    )
    doc_analysis = result.scalars().first()
    if not doc_analysis:
        return

    current_meta: Dict[str, Any] = dict(doc_analysis.analysis_result or {})
    current_meta["processing_step"] = step.value
    current_meta["progress"] = max(0, min(100, progress))
    if chunk_count > 0:
        current_meta["chunk_count"] = chunk_count
    if error:
        current_meta["error"] = error
    current_meta["updated_at"] = datetime.utcnow().isoformat()

    # Remove persisted payload once the job has reached a terminal state
    # (ready or failed) — no need to keep the file bytes in the DB any longer.
    if step in (IngestionStep.ready, IngestionStep.failed):
        current_meta.pop("queued_payload", None)

    doc_analysis.analysis_result = current_meta

    if step == IngestionStep.ready:
        doc_analysis.status = models.DocumentAnalysisStatus.completed
        doc_analysis.analyzed_at = datetime.utcnow()
    elif step == IngestionStep.failed:
        doc_analysis.status = models.DocumentAnalysisStatus.failed

    await db.commit()


async def get_job_status(
    db: AsyncSession,
    analysis_id: UUID
) -> Optional[JobStatus]:
    """Retrieve current job status for frontend polling."""
    result = await db.execute(
        select(models.DocumentAnalysis).where(models.DocumentAnalysis.id == analysis_id)
    )
    doc_analysis = result.scalars().first()
    if not doc_analysis:
        return None

    meta = doc_analysis.analysis_result or {}
    status_str = doc_analysis.status.value if hasattr(doc_analysis.status, 'value') else str(doc_analysis.status)

    return JobStatus(
        analysis_id=str(doc_analysis.id),
        organization_id=str(doc_analysis.organization_id),
        file_name=doc_analysis.file_name,
        status=status_str,
        step=meta.get("processing_step", status_str),
        progress=meta.get("progress", 0),
        chunk_count=meta.get("chunk_count", 0),
        error=meta.get("error"),
        created_at=doc_analysis.created_at.isoformat() if doc_analysis.created_at else None,
        updated_at=meta.get("updated_at"),
    )


# ── Durable Enqueue + Recovery ────────────────────────────────────────────────

async def enqueue_ingestion_job(
    analysis_id: UUID,
    file_bytes: bytes,
    filename: str,
    organization_id: UUID,
    db: Optional[AsyncSession] = None,
    source_type: str = "evidence",
) -> None:
    """
    Enqueue a document ingestion job durably.

    The full payload (including base64-encoded file bytes) is written to the
    DocumentAnalysis.analysis_result JSONB column BEFORE the job is added to
    the in-memory dispatch queue. A server restart will not lose the job —
    recover_pending_jobs() will reload it from the DB on the next startup.

    Args:
        analysis_id:      UUID of the DocumentAnalysis record already created.
        file_bytes:       Raw bytes of the uploaded document.
        filename:         Original file name.
        organization_id:  Owning organisation UUID.
        db:               Optional active DB session. If supplied, the payload
                          is persisted immediately. If None, the job is queued
                          in memory only (use only when DB is unavailable, e.g.
                          in tests).
        source_type:      "internal_policy" or "evidence".
    """
    payload: Dict[str, Any] = {
        "analysis_id": str(analysis_id),
        "file_bytes_b64": base64.b64encode(file_bytes).decode("utf-8"),
        "filename": filename,
        "organization_id": str(organization_id),
        "source_type": source_type,
        "queued_at": datetime.utcnow().isoformat(),
    }

    # ── Persist payload to DB (durability guarantee) ──────────────────────────
    if db is not None:
        try:
            result = await db.execute(
                select(models.DocumentAnalysis).where(
                    models.DocumentAnalysis.id == analysis_id
                )
            )
            doc_analysis = result.scalars().first()
            if doc_analysis is not None:
                current_meta: Dict[str, Any] = dict(doc_analysis.analysis_result or {})
                current_meta["queued_payload"] = payload
                doc_analysis.analysis_result = current_meta
                await db.commit()
                logger.info(
                    f"Job queue: Payload for analysis_id={analysis_id} persisted to DB ✓"
                )
            else:
                logger.warning(
                    f"Job queue: DocumentAnalysis {analysis_id} not found — "
                    f"payload stored in memory only (not durable)"
                )
        except Exception as exc:
            logger.error(
                f"Job queue: Failed to persist payload to DB for {analysis_id}: {exc} "
                f"— falling back to in-memory (not durable for this job)"
            )
    else:
        logger.warning(
            f"Job queue: No DB session provided for {analysis_id} — "
            f"payload stored in memory only (not durable)"
        )

    # ── Dispatch to in-memory queue for the worker loop ───────────────────────
    _dispatch_queue.append(payload)
    ensure_worker_running()
    logger.info(
        f"Job queue: Enqueued job analysis_id={analysis_id} ({filename}), "
        f"queue depth={len(_dispatch_queue)}"
    )


async def recover_pending_jobs(db: AsyncSession) -> int:
    """
    On server startup, reload any jobs that were in-flight when the server
    last stopped.

    Scans for DocumentAnalysis rows in 'processing' status whose
    analysis_result contains a 'queued_payload' key (written by
    enqueue_ingestion_job). Adds them back to the dispatch queue so the
    worker picks them up.

    Returns the number of jobs recovered.
    """
    try:
        result = await db.execute(
            select(models.DocumentAnalysis).where(
                models.DocumentAnalysis.status == models.DocumentAnalysisStatus.processing
            )
        )
        rows = result.scalars().all()
        recovered = 0
        for row in rows:
            meta = row.analysis_result or {}
            payload = meta.get("queued_payload")
            if payload and isinstance(payload, dict):
                _dispatch_queue.append(payload)
                recovered += 1
                logger.info(
                    f"Job queue: Recovered job analysis_id={row.id} ({row.file_name})"
                )
        if recovered:
            ensure_worker_running()
            logger.info(f"Job queue: {recovered} pending job(s) recovered from DB ✓")
        return recovered
    except Exception as exc:
        logger.error(f"Job queue: Failed to recover pending jobs: {exc}")
        return 0


# ── Worker Loop ───────────────────────────────────────────────────────────────

async def _worker_loop() -> None:
    """Worker loop: drains _dispatch_queue, calling process_document_job for each."""
    global _worker_running
    _worker_running = True
    logger.info("Job queue worker: started ✓")

    from app.ingestion.pipeline import process_document_job

    while _worker_running:
        if _dispatch_queue:
            job = _dispatch_queue.pop(0)
            aid = UUID(job["analysis_id"])
            oid = UUID(job["organization_id"])
            fname = job["filename"]
            fbytes = base64.b64decode(job["file_bytes_b64"].encode("utf-8"))

            logger.info(f"Job queue worker: Processing job {aid} ({fname})")
            try:
                await process_document_job(
                    analysis_id=aid,
                    file_bytes=fbytes,
                    filename=fname,
                    organization_id=oid,
                    source_type=job.get("source_type", "evidence"),
                )
            except Exception as e:
                logger.error(
                    f"Job queue worker: Job {aid} failed: {e}", exc_info=True
                )
        else:
            await asyncio.sleep(0.5)


def ensure_worker_running() -> None:
    """Ensure the queue worker asyncio task is active."""
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker_loop())
