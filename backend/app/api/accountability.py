from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PendingCommitmentOut(BaseModel):
    id: str
    summary: str
    due_at: datetime
    subject_type: str = Field(default="commitment")
    evidence_token: str | None = None
    resolved_at: datetime | None = None


class PendingCommitmentListOut(BaseModel):
    items: list[PendingCommitmentOut] = Field(default_factory=list)
