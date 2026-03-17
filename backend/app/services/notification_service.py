from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app import models, schemas
from uuid import UUID

class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str,
        link_url: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        ticket_id: Optional[UUID] = None
    ) -> models.Notification:
        notification = models.Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            link_url=link_url,
            entity_type=entity_type,
            entity_id=entity_id,
            ticket_id=ticket_id,
            is_read=0
        )
        db.add(notification)
        await db.flush()
        return notification

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: UUID) -> int:
        result = await db.execute(
            select(func.count(models.Notification.id))
            .where(models.Notification.user_id == user_id)
            .where(models.Notification.is_read == 0)
        )
        return result.scalar() or 0

    @staticmethod
    async def get_notifications(
        db: AsyncSession, 
        user_id: UUID, 
        limit: int = 20
    ) -> List[models.Notification]:
        result = await db.execute(
            select(models.Notification)
            .where(models.Notification.user_id == user_id)
            .order_by(models.Notification.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: UUID):
        await db.execute(
            update(models.Notification)
            .where(models.Notification.user_id == user_id)
            .where(models.Notification.is_read == 0)
            .values(is_read=1)
        )
        await db.flush()
