"""
Reflection Summary API

Aggregates task-level reflection data for the daily reflection summary view.
Reuses existing task_feedbacks.reflection_payload data — no new tables needed.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.models.task_feedback import TaskFeedback

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.utcnow()


@router.get("/summary")
async def get_reflection_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return a timeline of recent task reflections with aggregated stats."""
    cutoff = _utcnow() - timedelta(days=days)

    result = await db.execute(
        select(TaskFeedback)
        .where(
            TaskFeedback.user_id == user_id,
            TaskFeedback.reflection_payload.isnot(None),
            TaskFeedback.created_at >= cutoff,
        )
        .order_by(desc(TaskFeedback.created_at))
    )
    feedbacks = result.scalars().all()

    timeline: list[dict[str, Any]] = []
    theme_counts: dict[str, int] = {}
    total = 0

    for fb in feedbacks:
        payload = fb.reflection_payload or {}
        entry = {
            "feedback_id": str(fb.id),
            "task_id": str(fb.task_id) if fb.task_id else None,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
            "completion_quality": fb.completion_quality,
            "payload": payload,
        }
        timeline.append(entry)

        # Extract themes from payload (free-text answers)
        for key in ("highlights", "challenges", "tomorrow_intention", "stuck_points", "what_helped", "what_would_change"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                theme_counts[value.strip()[:80]] = theme_counts.get(value.strip()[:80], 0) + 1

        total += 1

    # Top themes (most frequent reflection topics)
    top_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Mood trend from completion_quality
    quality_scores = [
        fb.completion_quality
        for fb in feedbacks
        if fb.completion_quality is not None
    ]
    avg_mood = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else None

    return {
        "total_reflections": total,
        "days": days,
        "avg_mood": avg_mood,
        "top_themes": [{"theme": t, "count": c} for t, c in top_themes],
        "timeline": timeline,
    }
