from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, UUID4

class NotificationBase(BaseModel):
    title: str
    content: str
    type: str = "fragmented_time"
    data: Optional[Dict[str, Any]] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None

class NotificationResponse(NotificationBase):
    id: UUID4
    user_id: UUID4
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True
