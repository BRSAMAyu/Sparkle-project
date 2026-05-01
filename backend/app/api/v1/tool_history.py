from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.tool_history_service import ToolHistoryService

router = APIRouter(prefix="/tool-history", tags=["tool-history"])


class ClientToolHistoryCreate(BaseModel):
    tool_name: Literal[
        "breathing",
        "calculator",
        "translator",
        "vocabulary_lookup",
        "notes",
        "flash_capsule",
    ]
    used_at: datetime | None = None
    surface: str | None = Field(default=None, max_length=50)
    success: bool = True
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    rounds_completed: int | None = Field(default=None, ge=0, le=10000)
    pattern: str | None = Field(default=None, max_length=80)
    complexity: Literal["simple", "medium", "complex"] | None = None
    completed_from_background: bool | None = None
    source_language: str | None = Field(default=None, max_length=16)
    target_language: str | None = Field(default=None, max_length=16)
    text_length: int | None = Field(default=None, ge=0, le=100000)
    lookup_term: str | None = Field(default=None, max_length=80)
    char_count: int | None = Field(default=None, ge=0, le=100000)
    line_count: int | None = Field(default=None, ge=0, le=10000)
    subject: str | None = Field(default=None, max_length=80)
    error_type: str | None = Field(default=None, max_length=80)
    task_id: str | None = Field(default=None, max_length=80)


class ClientToolHistoryResponse(BaseModel):
    id: int
    tool_name: str
    success: bool
    used_at: datetime | None


class ClientToolHistoryDeleteResponse(BaseModel):
    id: int
    deleted: bool


def _to_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _clean_text(value: str | None, *, max_length: int = 80) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    return cleaned[:max_length]


def _tool_category(tool_name: str) -> str:
    return {
        "breathing": "wellbeing",
        "calculator": "calculation",
        "translator": "translation",
        "vocabulary_lookup": "vocabulary",
        "notes": "notes",
        "flash_capsule": "reflection",
    }.get(tool_name, "client_tool")


def _build_context_snapshot(
    payload: ClientToolHistoryCreate, used_at: datetime
) -> tuple[dict[str, object], dict[str, object], str]:
    context_snapshot: dict[str, object] = {
        "used_at": used_at.isoformat(),
        "surface": payload.surface,
    }
    input_args: dict[str, object] = {"used_at": used_at.isoformat()}
    output_summary = "client tool completed"

    if payload.tool_name == "breathing":
        context_snapshot.update(
            {
                "duration_minutes": payload.duration_minutes,
                "rounds_completed": payload.rounds_completed,
                "pattern": _clean_text(payload.pattern),
                "completed_from_background": payload.completed_from_background,
            }
        )
        input_args.update(
            {
                "duration_minutes": payload.duration_minutes,
                "pattern": _clean_text(payload.pattern),
            }
        )
        output_summary = "breathing exercise completed"
    elif payload.tool_name == "calculator":
        context_snapshot["complexity"] = payload.complexity or "simple"
        input_args["complexity"] = payload.complexity or "simple"
        output_summary = f"calculator expression evaluated ({payload.complexity or 'simple'})"
    elif payload.tool_name == "translator":
        context_snapshot.update(
            {
                "source_language": _clean_text(payload.source_language, max_length=16) or "auto",
                "target_language": _clean_text(payload.target_language, max_length=16),
                "text_length": payload.text_length,
            }
        )
        input_args.update(
            {
                "source_language": context_snapshot["source_language"],
                "target_language": context_snapshot["target_language"],
                "text_length": payload.text_length,
            }
        )
        output_summary = "translation completed; raw text not stored"
    elif payload.tool_name == "vocabulary_lookup":
        lookup_term = _clean_text(payload.lookup_term)
        context_snapshot["lookup_term"] = lookup_term
        input_args["lookup_term"] = lookup_term
        output_summary = "vocabulary lookup completed"
    elif payload.tool_name == "notes":
        context_snapshot.update(
            {
                "char_count": payload.char_count,
                "line_count": payload.line_count,
                "task_id": _clean_text(payload.task_id),
            }
        )
        input_args.update(
            {
                "char_count": payload.char_count,
                "line_count": payload.line_count,
                "task_id": _clean_text(payload.task_id),
            }
        )
        output_summary = "quick note synced; note content not stored"
    elif payload.tool_name == "flash_capsule":
        context_snapshot.update(
            {
                "subject": _clean_text(payload.subject),
                "error_type": _clean_text(payload.error_type),
                "task_id": _clean_text(payload.task_id),
            }
        )
        input_args.update(
            {
                "subject": _clean_text(payload.subject),
                "error_type": _clean_text(payload.error_type),
                "task_id": _clean_text(payload.task_id),
            }
        )
        output_summary = "flash capsule saved; capsule text not stored in tool history"

    return context_snapshot, input_args, output_summary


@router.post("/client-events", response_model=ClientToolHistoryResponse)
async def record_client_tool_history(
    payload: ClientToolHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    used_at = _to_utc_naive(payload.used_at) or datetime.now(UTC).replace(tzinfo=None)
    context_snapshot, input_args, output_summary = _build_context_snapshot(payload, used_at)

    history = await ToolHistoryService(db).record_tool_execution(
        user_id=current_user.id,
        tool_name=payload.tool_name,
        success=payload.success,
        tool_category=_tool_category(payload.tool_name),
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


@router.delete("/client-events/{history_id}", response_model=ClientToolHistoryDeleteResponse)
async def delete_client_tool_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await ToolHistoryService(db).delete_client_context_effect(
        user_id=current_user.id,
        record_id=history_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="tool history event not found")
    await db.commit()
    return ClientToolHistoryDeleteResponse(id=history_id, deleted=True)
