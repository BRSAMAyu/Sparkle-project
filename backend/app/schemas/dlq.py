from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DlqEntry(BaseModel):
    message_id: str
    payload: Dict[str, Any]


class DlqReplayRequest(BaseModel):
    message_ids: List[str] = Field(..., min_length=1)
    approver_id: str
    reason_code: str
    delete_after: bool = True
