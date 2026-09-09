import asyncio
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionLocal
from app.models.email_job import EmailJob, EmailJobStatus

logger = logging.getLogger("grc.email_queue")

# Initialize Jinja2 environment for HTML email templates
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"
template_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True
)

async def enqueue_email(
    db: AsyncSession,
    recipient: str,
    template_name: str,
    template_data: Dict[str, Any],
    subject: str,
) -> EmailJob:
    """
    Enqueue an email job into the transactional email_jobs table.
    """
    job = EmailJob(
        recipient=recipient,
        template_name=template_name,
        template_data=template_data,
        subject=subject,
        status=EmailJobStatus.pending,
        attempts=0,
        max_attempts=5,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info(f"Enqueued email job {job.id} to {recipient} (template: {template_name})")
    return job

def render_email_template(template_name: str, template_data: Dict[str, Any]) -> str:
    """Render Jinja2 HTML email template."""
    template = template_env.get_template(template_name)
    data = {"project_name": settings.PROJECT_NAME, **template_data}
    return template.render(**data)

async def _send_smtp_email(recipient: str, subject: str, html_content: str) -> None:
    """
    Send HTML email via SMTP using aiosmtplib.
    If SMTP_HOST is not configured, log email content for development.
    """
    if not settings.SMTP_HOST or not settings.EMAILS_FROM_EMAIL:
        logger.info(
            f"[DEV EMAIL LOG] SMTP not configured. Simulating email send:\n"
            f"  To: {recipient}\n"
            f"  Subject: {subject}\n"
            f"  HTML Length: {len(html_content)} chars"
        )
        return

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    try:
        import aiosmtplib
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True if settings.SMTP_PORT == 587 else False,
            use_tls=True if settings.SMTP_PORT == 465 else False,
            timeout=15,
        )
        logger.info(f"Successfully sent SMTP email to {recipient}")
    except ImportError:
        import smtplib
        def sync_send():
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                if settings.SMTP_PORT == 587:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        await asyncio.to_thread(sync_send)
        logger.info(f"Successfully sent SMTP email to {recipient} (via smtplib fallback)")

async def process_pending_jobs(db: AsyncSession) -> int:
    """
    Fetch and process pending or retryable failed email jobs.
    """
    now = datetime.utcnow()
    stmt = (
        select(EmailJob)
        .where(
            or_(
                EmailJob.status == EmailJobStatus.pending,
                and_(
                    EmailJob.status == EmailJobStatus.failed,
                    EmailJob.next_retry_at <= now,
                    EmailJob.attempts < EmailJob.max_attempts,
                ),
            )
        )
        .limit(20)
    )

    result = await db.execute(stmt)
    jobs = result.scalars().all()

    if not jobs:
        return 0

    processed_count = 0
    for job in jobs:
        job.status = EmailJobStatus.processing
        job.updated_at = now
        await db.commit()

        try:
            html = render_email_template(job.template_name, job.template_data)
            await _send_smtp_email(job.recipient, job.subject, html)

            job.status = EmailJobStatus.sent
            job.sent_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            job.last_error = None
            await db.commit()
            processed_count += 1
        except Exception as exc:
            job.attempts += 1
            job.last_error = str(exc)
            job.updated_at = datetime.utcnow()

            if job.attempts >= job.max_attempts:
                job.status = EmailJobStatus.dead
                logger.error(f"Email job {job.id} marked DEAD after {job.attempts} attempts. Error: {exc}")
            else:
                job.status = EmailJobStatus.failed
                backoff_seconds = (2 ** job.attempts) * 60
                job.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
                logger.warning(f"Email job {job.id} failed (attempt {job.attempts}/{job.max_attempts}). Retrying in {backoff_seconds}s. Error: {exc}")

            await db.commit()

    return processed_count

async def recover_stuck_jobs(db: AsyncSession) -> int:
    """Reset jobs stuck in 'processing' state back to 'pending' on startup."""
    stmt = select(EmailJob).where(EmailJob.status == EmailJobStatus.processing)
    result = await db.execute(stmt)
    stuck_jobs = result.scalars().all()
    count = len(stuck_jobs)
    for job in stuck_jobs:
        job.status = EmailJobStatus.pending
        job.updated_at = datetime.utcnow()
    if count > 0:
        await db.commit()
        logger.info(f"Recovered {count} stuck email job(s) -> set to pending")
    return count

_worker_task: Optional[asyncio.Task] = None

async def email_worker_loop():
    """Background worker loop processing email jobs every 10 seconds."""
    logger.info("Starting email queue worker loop...")
    while True:
        try:
            async with SessionLocal() as db:
                await process_pending_jobs(db)
        except asyncio.CancelledError:
            logger.info("Email worker loop cancelled.")
            break
        except Exception as exc:
            logger.error(f"Error in email worker loop: {exc}", exc_info=True)

        await asyncio.sleep(10)

def start_email_worker():
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(email_worker_loop())
        logger.info("Email worker task launched.")

def stop_email_worker():
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        logger.info("Email worker task cancellation requested.")
