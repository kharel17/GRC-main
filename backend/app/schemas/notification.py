from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID

class NotificationBase(BaseModel):
    message: str
    type: str
    ticket_id: Optional[UUID] = None

class NotificationCreate(NotificationBase):
    user_id: UUID

class Notification(NotificationBase):
    id: UUID
    user_id: UUID
    is_read: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
