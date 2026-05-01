"""
Core: infra
Phase: none
Stage: F29
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.calendar_event import CalendarEvent
from app.models.chat import ChatSession
from app.models.error_book import ErrorRecord
from app.models.focus import FocusSession
from app.models.notification import Notification
from app.models.notification_interaction import NotificationInteraction
from app.models.plan import Plan
from app.models.task import Task
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.achievement import UserAchievement

router = APIRouter()

_EXPORT_RATE_LIMIT_SECONDS = 60


def _to_dict(obj: Any, exclude_fields: set[str] | None = None) -> dict[str, Any]:
    """Convert SQLAlchemy model instance to a serialisable dict."""
    exclude = exclude_fields or set()
    result: dict[str, Any] = {}
    for column in obj.__table__.columns:
        if column.name in exclude:
            continue
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif hasattr(value, "hex"):
            value = str(value)
        result[column.name] = value
    return result


@router.get("/me/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all user data as a ZIP file containing JSON files per data category."""
    uid = current_user.id
    now = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    # Simple per-user rate limit: use Redis if available, otherwise skip
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        if redis:
            rl_key = f"export_rate_limit:{uid}"
            if await redis.exists(rl_key):
                raise HTTPException(status_code=429, detail="请稍后再试，数据导出请求过于频繁")
            await redis.setex(rl_key, _EXPORT_RATE_LIMIT_SECONDS, "1")
    except HTTPException:
        raise
    except Exception:
        pass  # Non-critical — allow export without Redis

    async def _query(model: Any, user_field: str = "user_id") -> list[dict[str, Any]]:
        rows = (
            await db.execute(
                select(model).where(getattr(model, user_field) == uid)
            )
        ).scalars().all()
        return [_to_dict(r) for r in rows]

    profile_data: dict[str, Any] = {}
    for column in current_user.__table__.columns:
        if column.name in {"password_hash"}:
            continue
        value = getattr(current_user, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif hasattr(value, "hex"):
            value = str(value)
        profile_data[column.name] = value

    datasets: dict[str, Any] = {
        "profile": profile_data,
        "plans": await _query(Plan),
        "tasks": await _query(Task),
        "error_book": await _query(ErrorRecord),
        "focus_sessions": await _query(FocusSession),
        "calendar_events": await _query(CalendarEvent),
        "chat_sessions": await _query(ChatSession),
        "achievements": await _query(UserAchievement),
        "notifications": await _query(Notification),
        "notification_interactions": await _query(NotificationInteraction),
    }
    try:
        datasets["user_settings"] = await _query(UserSettings)
    except Exception:
        pass  # Table may not exist in all deployments

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in datasets.items():
            zf.writestr(
                f"sparkle_export_{now}/{name}.json",
                json.dumps(data, ensure_ascii=False, indent=2),
            )
    buf.seek(0)

    filename = f"sparkle_data_export_{now}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
