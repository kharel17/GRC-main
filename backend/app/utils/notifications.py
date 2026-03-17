from sqlalchemy.ext.asyncio import AsyncSession
from app.services.notification_service import NotificationService
import uuid

async def notify(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    entity_type: str,
    entity_id: str,
    link_url: str,
    notification_type: str
):
    """
    Creates a notification record in the database using NotificationService.
    """
    u_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    e_id = uuid.UUID(entity_id) if isinstance(entity_id, str) and entity_id else entity_id
    
    return await NotificationService.create_notification(
        db=db,
        user_id=u_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link_url=link_url,
        entity_type=entity_type,
        entity_id=e_id
    )
