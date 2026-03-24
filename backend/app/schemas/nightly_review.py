from __future__ import annotations
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NightlyReviewItem(BaseModel):
    type: str
    payload: dict[str, Any]


class NightlyReviewResponse(BaseModel):
    id: UUID
    user_id: UUID
    review_date: date
    summary_text: str | None = None
    todo_items: list[NightlyReviewItem] | None = None
    evidence_refs: list[dict[str, Any]] | None = None
    widget_payload: dict[str, Any] | None = None
    model_version: str | None = None
    status: str
    reviewed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NightlyReviewFeedbackRequest(BaseModel):
    action: str
    source: str | None = None
