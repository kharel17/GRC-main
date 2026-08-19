import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from app.config import settings

logger = logging.getLogger("grc.emails")

async def send_invitation_email(email_to: str, token: str, full_name: str, org_name: str):
    """
    Sends an invitation email with a link to accept the invite.
    Uses SMTP settings from configuration.
    """
    if not settings.SMTP_HOST:
        logger.warning(f"SMTP_HOST not configured. Could not send email to {email_to}")
        logger.info(f"INVITATION TOKEN for {email_to}: {token}")
        return

    invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={token}"
    
    subject = f"Invitation to join {org_name} on GRC Platform"
    body = f"""
    Hello {full_name},

    You have been invited to join {org_name} on the GRC Platform.

    To accept your invitation and set your password, please click the link below:
    {invite_url}

    This link will expire in 7 days.

    Best regards,
    The GRC Team
    """

    message = MIMEMultipart()
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = email_to
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        # Standard smtplib is blocking; in production, this should be moved to a background task
        # or use aiosmtplib. For now, we use a simple implementation.
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_PASSWORD:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        logger.info(f"Invitation email successfully sent to {email_to}")
    except Exception as e:
        logger.error(f"Failed to send email to {email_to}: {e}")
        # Log the token so it can be manually retrieved in development
        logger.info(f"INVITATION TOKEN for {email_to}: {token}")

async def send_reset_password_email(email_to: str, token: str):
    """
    Sends a password reset email with a link.
    """
    if not settings.SMTP_HOST:
        logger.warning(f"SMTP_HOST not configured. Could not send reset email to {email_to}")
        logger.info(f"RESET TOKEN for {email_to}: {token}")
        return

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    subject = "Password Reset Request - GRC Platform"
    body = f"""
    Hello,

    We received a request to reset your password for the GRC Platform.

    To set a new password, please click the link below:
    {reset_url}

    This link will expire in 24 hours.

    If you did not request this, please ignore this email.

    Best regards,
    The GRC Team
    """

    message = MIMEMultipart()
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = email_to
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_PASSWORD:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        logger.info(f"Reset password email successfully sent to {email_to}")
    except Exception as e:
        logger.error(f"Failed to send reset email to {email_to}: {e}")
        logger.info(f"RESET TOKEN for {email_to}: {token}")
