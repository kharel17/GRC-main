import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionLocal
from app.services.email_queue import enqueue_email

logger = logging.getLogger("grc.emails")


async def send_invitation_email(
    email_to: str,
    token: str,
    full_name: str,
    org_name: str,
    role: str = "Member",
    auth_provider: str = "any",
    db: Optional[AsyncSession] = None,
):
    """
    Enqueue an invitation email job into the transactional email queue.
    """
    invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={token}"
    subject = f"Invitation to join {org_name} on {settings.PROJECT_NAME}"

    template_data = {
        "full_name": full_name,
        "organization_name": org_name,
        "role": role,
        "invite_url": invite_url,
        "expires_hours": 168,  # 7 days
        "auth_provider": auth_provider,
    }

    if db is not None:
        await enqueue_email(
            db=db,
            recipient=email_to,
            template_name="invitation.html",
            template_data=template_data,
            subject=subject,
        )
    else:
        async with SessionLocal() as session:
            await enqueue_email(
                db=session,
                recipient=email_to,
                template_name="invitation.html",
                template_data=template_data,
                subject=subject,
            )

    logger.info(f"Enqueued invitation email for {email_to}")


async def send_reset_password_email(
    email_to: str,
    token: str,
    full_name: str = "User",
    db: Optional[AsyncSession] = None,
):
    """
    Enqueue a password reset email job into the transactional email queue.
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = f"Password Reset Request - {settings.PROJECT_NAME}"

    template_data = {
        "full_name": full_name,
        "reset_url": reset_url,
        "expires_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
    }

    if db is not None:
        await enqueue_email(
            db=db,
            recipient=email_to,
            template_name="password_reset.html",
            template_data=template_data,
            subject=subject,
        )
    else:
        async with SessionLocal() as session:
            await enqueue_email(
                db=session,
                recipient=email_to,
                template_name="password_reset.html",
                template_data=template_data,
                subject=subject,
            )

    logger.info(f"Enqueued password reset email for {email_to}")
