from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.tool_history_service import ToolHistoryService

router = APIRouter(prefix="/tool-history", tags=["tool-history"])


class ClientToolHistoryCreate(BaseModel):
    tool_name: Literal["breathing", "calculator"]
    used_at: datetime | None = None
    surface: str | None = Field(default=None, max_length=50)
    success: bool = True
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    rounds_completed: int | None = Field(default=None, ge=0, le=10000)
    pattern: str | None = Field(default=None, max_length=80)
    complexity: Literal["simple", "medium", "complex"] | None = None
    completed_from_background: bool | None = None


class ClientToolHistoryResponse(BaseModel):
    id: int
    tool_name: str
    success: bool
    used_at: datetime | None


def _to_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


@router.post("/client-events", response_model=ClientToolHistoryResponse)
async def record_client_tool_history(
    payload: ClientToolHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    used_at = _to_utc_naive(payload.used_at) or datetime.now(UTC).replace(tzinfo=None)
    context_snapshot = {
        "used_at": used_at.isoformat(),
        "surface": payload.surface,
    }
    input_args: dict[str, object] = {"used_at": used_at.isoformat()}

    if payload.tool_name == "breathing":
        context_snapshot.update(
            {
                "duration_minutes": payload.duration_minutes,
                "rounds_completed": payload.rounds_completed,
                "pattern": payload.pattern,
                "completed_from_background": payload.completed_from_background,
            }
        )
        input_args.update(
            {
                "duration_minutes": payload.duration_minutes,
                "pattern": payload.pattern,
            }
        )
        output_summary = "breathing exercise completed"
    else:
        context_snapshot["complexity"] = payload.complexity or "simple"
        input_args["complexity"] = payload.complexity or "simple"
        output_summary = f"calculator expression evaluated ({payload.complexity or 'simple'})"

    history = await ToolHistoryService(db).record_tool_execution(
        user_id=current_user.id,
        tool_name=payload.tool_name,
        success=payload.success,
        tool_category="wellbeing" if payload.tool_name == "breathing" else "calculation",
        context_snapshot=context_snapshot,
        input_args=input_args,
        output_summary=output_summary,
    )
    history.created_at = used_at
    await db.commit()
    await db.refresh(history)

    return ClientToolHistoryResponse(
        id=history.id,
        tool_name=history.tool_name,
        success=history.success,
        used_at=history.created_at,
    )
