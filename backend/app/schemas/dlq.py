from typing import Any

from pydantic import BaseModel, Field


class DlqEntry(BaseModel):
    message_id: str
    payload: dict[str, Any]


class DlqReplayRequest(BaseModel):
    message_ids: list[str] = Field(..., min_length=1)
    approver_id: str
    reason_code: str
    delete_after: bool = True
