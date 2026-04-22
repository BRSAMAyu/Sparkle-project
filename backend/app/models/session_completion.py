from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String

from app.db.session import Base
from app.models.base import GUID


class SessionCompletion(Base):
    __tablename__ = "session_completions"

    session_id = Column(String(255), primary_key=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    completion_type = Column(String(64), nullable=False)
    source_event = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


Index("ix_session_completions_user_id_created_at", SessionCompletion.user_id, SessionCompletion.created_at)
