from __future__ import annotations
from datetime import datetime
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict


class NotificationBase(BaseModel):
    title: str
    content: str
    type: str = "fragmented_time"
    data: dict[str, Any] | None = None

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    is_read: bool | None = None

class NotificationResponse(NotificationBase):
    id: UUID4
    user_id: UUID4
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
