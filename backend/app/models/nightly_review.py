"""
Nightly Review Models
Phase 2 nightly reviewer output.
"""
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class NightlyReview(BaseModel):
    __tablename__ = "nightly_reviews"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    review_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    summary_text: Mapped[str] = mapped_column(String(2000), nullable=True)
    todo_items: Mapped[Any] = mapped_column(JSON, nullable=True)
    evidence_refs: Mapped[Any] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="generated", nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user = relationship("User", backref="nightly_reviews")
