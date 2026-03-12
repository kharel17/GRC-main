import asyncio
import logging
from app.database import SessionLocal
from app.services.ticket_service import TicketService

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grc.worker")

async def sla_worker(cron_secret: str):
    """
    Background worker that periodically checks for SLA misses and triggers auto-escalation.
    Validates x-cron-secret for security.
    """
    if cron_secret != settings.CRON_SECRET:
        logger.error("Invalid cron secret provided. SLA Worker exiting.")
        return

    logger.info("SLA Worker started with valid secret.")
    while True:
        try:
            async with SessionLocal() as db:
                logger.info("Checking SLAs...")
                await TicketService.check_slas(db)
        except Exception as e:
            logger.error(f"Error in SLA Worker: {e}")
        
        # Check every hour
        await asyncio.sleep(3600)

if __name__ == "__main__":
    from app.config import settings
    asyncio.run(sla_worker(settings.CRON_SECRET))
