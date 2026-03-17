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

router = APIRouter(redirect_slashes=False)


# ─── Schemas ─────────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    ticket_id: Optional[UUID] = None
    title: Optional[str] = None
    message: str
    link_url: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    type: Optional[str] = None  # notification_type
    is_read: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    count: int


class MarkReadRequest(BaseModel):
    notification_ids: Optional[List[UUID]] = None  # None = mark all


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/unread-count/", response_model=UnreadCountResponse)
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
    return UnreadCountResponse(count=count)


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100, alias="limit"),
    size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    notification_type: Optional[str] = Query(None, alias="type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user, newest first."""
    # Use limit if provided (frontend sends ?limit=20), otherwise use size
    effective_size = limit or size
    skip = (page - 1) * effective_size
    query = select(Notification).where(
        Notification.user_id == current_user.id
    )
    if unread_only:
        query = query.where(Notification.is_read == 0)
    
    if notification_type:
        # Filter by entity_type (e.g. "ticket", "risk", "control")
        query = query.where(Notification.entity_type == notification_type)

    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(effective_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/{id}/read/", response_model=dict)
async def mark_single_read(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    await db.execute(
        update(Notification)
        .where(Notification.id == id, Notification.user_id == current_user.id)
        .values(is_read=1)
    )
    await db.commit()
    return {"success": True}


@router.patch("/mark-all-read/", response_model=dict)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for current user."""
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == 0)
        .values(is_read=1)
    )
    await db.commit()
    return {"marked": result.rowcount}


@router.delete("/{notification_id}/", response_model=dict)
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