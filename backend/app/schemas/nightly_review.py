from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NightlyReviewItem(BaseModel):
    type: str
    payload: Dict[str, Any]


class NightlyReviewResponse(BaseModel):
    id: UUID
    user_id: UUID
    review_date: date
    summary_text: Optional[str] = None
    todo_items: Optional[List[NightlyReviewItem]] = None
    evidence_refs: Optional[List[Dict[str, Any]]] = None
    model_version: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
