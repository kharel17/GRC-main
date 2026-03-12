from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, models
from app.api import deps
from app.services.notification_service import NotificationService

router = APIRouter()

@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    count = await NotificationService.get_unread_count(db, current_user.id)
    return {"count": count}

@router.get("/", response_model=List[schemas.Notification])
async def get_notifications(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    limit: int = 20
) -> Any:
    return await NotificationService.get_notifications(db, current_user.id, limit)

@router.post("/mark-all-read")
async def mark_all_read(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    await NotificationService.mark_all_read(db, current_user.id)
    return {"status": "success"}
