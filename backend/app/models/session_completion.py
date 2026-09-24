from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import GUID


class SessionCompletion(Base):
    __tablename__ = "session_completions"

    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    completion_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_event: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


Index("ix_session_completions_user_id_created_at", SessionCompletion.user_id, SessionCompletion.created_at)
