from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from pydantic import BaseModel

from app.api.deps import get_current_user, get_db
from app.models.notification import Notification
from app.models.user import User

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    ticket_id: Optional[UUID] = None
    message: str
    type: str
    is_read: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadRequest(BaseModel):
    notification_ids: Optional[List[UUID]] = None  # None = mark all


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return count of unread notifications for the current user."""
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read == 0,
        )
    )
    count = result.scalar() or 0
    return UnreadCountResponse(unread_count=count)


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user, newest first."""
    query = select(Notification).where(
        Notification.user_id == current_user.id
    )
    if unread_only:
        query = query.where(Notification.is_read == 0)

    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/mark-read", response_model=dict)
async def mark_notifications_read(
    body: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark specific notifications (or all) as read for current user."""
    query = (
        update(Notification)
        .where(Notification.user_id == current_user.id)
        .values(is_read=1)
    )
    if body.notification_ids:
        query = query.where(Notification.id.in_(body.notification_ids))

    await db.execute(query)
    await db.commit()
    return {"success": True, "message": "Notifications marked as read"}


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single notification belonging to the current user."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()
    return {"success": True, "message": "Notification deleted"}