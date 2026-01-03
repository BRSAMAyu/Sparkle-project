from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime
from app.models.base import BaseModel

class EventOutbox(BaseModel):
    __tablename__ = "outbox_events"

    topic = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default='pending', index=True)
    processed_at = Column(DateTime, nullable=True)
    error = Column(String, nullable=True)

    # id, created_at, updated_at, deleted_at are inherited from BaseModel
    # BaseModel provides UUID id and auto created_at/updated_at
