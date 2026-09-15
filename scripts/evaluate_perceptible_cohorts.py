#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import or_, select

from app.core.cache import cache_service  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.chat import ChatMessage, MessageRole  # noqa: E402
from app.models.task import Task, TaskStatus  # noqa: E402
from app.models.task_feedback import TaskFeedback  # noqa: E402
from app.services.system_update_service import SystemUpdateService  # noqa: E402


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _cohort_for_user(user_id: UUID | str | None) -> str | None:
    raw = str(user_id or "").strip()
    if not raw:
        return None
    bucket = int(hashlib.sha256(raw.encode("utf-8")).hexdigest(), 16) % 3
    return ("A", "B", "C")[bucket]


@dataclass
class CohortWindow:
    name: str
    start: datetime
    end: datetime


async def _distinct_users_in_window(window: CohortWindow) -> list[UUID]:
    async with AsyncSessionLocal() as db:
        seen: set[UUID] = set()
        user_ids: list[UUID] = []
        statements = [
            select(Task.user_id).where(
                or_(
                    Task.created_at >= window.start,
                    Task.completed_at >= window.start,
                )
            ),
            select(TaskFeedback.user_id).where(TaskFeedback.created_at >= window.start),
            select(ChatMessage.user_id).where(ChatMessage.created_at >= window.start),
        ]
        for stmt in statements:
            result = await db.execute(stmt)
            for user_id in result.scalars().all():
                if not user_id or user_id in seen:
                    continue
                seen.add(user_id)
                user_ids.append(user_id)
        return user_ids


async def _session_count_map(window: CohortWindow) -> dict[UUID, int]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ChatMessage.user_id, ChatMessage.session_id).where(
                ChatMessage.created_at >= window.start,
                ChatMessage.created_at < window.end,
            )
        )
        grouped: dict[UUID, set[str]] = defaultdict(set)
        for user_id, session_id in result.all():
            if user_id and session_id:
                grouped[user_id].add(str(session_id))
        return {user_id: len(sessions) for user_id, sessions in grouped.items()}


async def _task_stats_map(window: CohortWindow) -> dict[UUID, dict[str, int]]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                Task.user_id,
                Task.status,
                Task.created_at,
                Task.completed_at,
            ).where(
                or_(
                    Task.created_at >= window.start,
                    Task.completed_at >= window.start,
                )
            )
        )
        stats: dict[UUID, dict[str, int]] = defaultdict(lambda: {"total_tasks": 0, "completed_tasks": 0})
        for user_id, status, created_at, completed_at in result.all():
            if not user_id:
                continue
            if created_at and window.start <= created_at < window.end:
                stats[user_id]["total_tasks"] += 1
            if status == TaskStatus.COMPLETED and completed_at and window.start <= completed_at < window.end:
                stats[user_id]["completed_tasks"] += 1
        return stats


async def _feedback_count_map(window: CohortWindow) -> dict[UUID, int]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TaskFeedback.user_id).where(
                TaskFeedback.created_at >= window.start,
                TaskFeedback.created_at < window.end,
            )
        )
        counts: dict[UUID, int] = defaultdict(int)
        for user_id in result.scalars().all():
            if user_id:
                counts[user_id] += 1
        return counts


async def _engagement_events_map(start: datetime, end: datetime) -> dict[UUID, list[datetime]]:
    async with AsyncSessionLocal() as db:
        events: dict[UUID, list[datetime]] = defaultdict(list)
        task_result = await db.execute(
            select(Task.user_id, Task.completed_at).where(
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= start,
                Task.completed_at < end,
            )
        )
        for user_id, ts in task_result.all():
            if user_id and ts:
                events[user_id].append(ts)
        chat_result = await db.execute(
            select(ChatMessage.user_id, ChatMessage.created_at).where(
                ChatMessage.role == MessageRole.USER,
                ChatMessage.created_at >= start,
                ChatMessage.created_at < end,
            )
        )
        for user_id, ts in chat_result.all():
            if user_id and ts:
                events[user_id].append(ts)
        return events


async def _insight_adoption_map(window: CohortWindow) -> dict[UUID, dict[str, int]]:
    redis = cache_service.redis
    if redis is None:
        return {}
    updates = SystemUpdateService(redis)
    user_ids = await _distinct_users_in_window(window)
    engagement_events = await _engagement_events_map(window.start, window.end + timedelta(days=1))
    adoption: dict[UUID, dict[str, int]] = defaultdict(lambda: {"sent": 0, "adopted": 0})
    for user_id in user_ids:
        payloads = await updates.list_updates(user_id, limit=120)
        for item in payloads:
            created_at = int(item.get("created_at") or 0)
            created_ts = datetime.fromtimestamp(created_at, tz=UTC).replace(tzinfo=None) if created_at else None
            metadata = item.get("metadata") if isinstance(item, dict) else None
            if not created_ts or not isinstance(metadata, dict):
                continue
            if metadata.get("evolution_kind") != "proactive_insight":
                continue
            if not (window.start <= created_ts < window.end):
                continue
            adoption[user_id]["sent"] += 1
            for event_ts in engagement_events.get(user_id, []):
                if created_ts <= event_ts <= created_ts + timedelta(hours=24):
                    adoption[user_id]["adopted"] += 1
                    break
    return adoption


def _aggregate_by_cohort(
    *,
    users: list[UUID],
    task_stats: dict[UUID, dict[str, int]],
    feedback_counts: dict[UUID, int],
    session_counts: dict[UUID, int],
    insight_adoption: dict[UUID, dict[str, int]],
    previous_session_counts: dict[UUID, int] | None = None,
) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {
        "A": {"users": 0, "total_tasks": 0, "completed_tasks": 0, "feedbacks": 0, "sessions": 0, "previous_sessions": 0, "insight_sent": 0, "insight_adopted": 0},
        "B": {"users": 0, "total_tasks": 0, "completed_tasks": 0, "feedbacks": 0, "sessions": 0, "previous_sessions": 0, "insight_sent": 0, "insight_adopted": 0},
        "C": {"users": 0, "total_tasks": 0, "completed_tasks": 0, "feedbacks": 0, "sessions": 0, "previous_sessions": 0, "insight_sent": 0, "insight_adopted": 0},
    }
    for user_id in users:
        cohort = _cohort_for_user(user_id)
        if not cohort:
            continue
        bucket = payload[cohort]
        bucket["users"] += 1
        bucket["total_tasks"] += int((task_stats.get(user_id) or {}).get("total_tasks", 0))
        bucket["completed_tasks"] += int((task_stats.get(user_id) or {}).get("completed_tasks", 0))
        bucket["feedbacks"] += int(feedback_counts.get(user_id, 0))
        bucket["sessions"] += int(session_counts.get(user_id, 0))
        bucket["previous_sessions"] += int((previous_session_counts or {}).get(user_id, 0))
        bucket["insight_sent"] += int((insight_adoption.get(user_id) or {}).get("sent", 0))
        bucket["insight_adopted"] += int((insight_adoption.get(user_id) or {}).get("adopted", 0))

    rendered: dict[str, dict[str, Any]] = {}
    for cohort, bucket in payload.items():
        total_tasks = max(int(bucket["total_tasks"]), 0)
        sessions = max(int(bucket["sessions"]), 0)
        sent = max(int(bucket["insight_sent"]), 0)
        previous_sessions = max(int(bucket["previous_sessions"]), 0)
        completion_rate = bucket["completed_tasks"] / total_tasks if total_tasks else 0.0
        feedback_rate = bucket["feedbacks"] / sessions if sessions else 0.0
        insight_adoption_rate = bucket["insight_adopted"] / sent if sent else None
        session_retention_ratio = (
            bucket["sessions"] / previous_sessions
            if previous_sessions
            else None
        )
        rendered[cohort] = {
            **bucket,
            "completion_rate": round(completion_rate, 4),
            "feedback_rate": round(feedback_rate, 4),
            "insight_adoption_rate": round(insight_adoption_rate, 4) if insight_adoption_rate is not None else None,
            "session_retention_ratio": round(session_retention_ratio, 4) if session_retention_ratio is not None else None,
        }
    return rendered


def _score_cohort(metrics: dict[str, Any]) -> float:
    completion = float(metrics.get("completion_rate") or 0.0)
    feedback = min(float(metrics.get("feedback_rate") or 0.0), 1.0)
    adoption = float(metrics.get("insight_adoption_rate") or 0.0)
    retention = float(metrics.get("session_retention_ratio") or 1.0)
    retention_score = min(retention, 1.5) / 1.5
    return round(completion * 0.4 + feedback * 0.2 + adoption * 0.2 + retention_score * 0.2, 4)


def _recommendation(current: dict[str, dict[str, Any]], previous: dict[str, dict[str, Any]]) -> dict[str, Any]:
    current_scored = {
        cohort: {**metrics, "strategy_score": _score_cohort(metrics)}
        for cohort, metrics in current.items()
    }
    previous_scored = {
        cohort: {**metrics, "strategy_score": _score_cohort(metrics)}
        for cohort, metrics in previous.items()
    }
    current_best = max(current_scored.items(), key=lambda item: item[1]["strategy_score"])[0]
    previous_best = max(previous_scored.items(), key=lambda item: item[1]["strategy_score"])[0]
    ranking = sorted(
        ((cohort, metrics["strategy_score"]) for cohort, metrics in current_scored.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    margin = ranking[0][1] - ranking[1][1] if len(ranking) > 1 else ranking[0][1]
    return {
        "recommended_default": current_best,
        "promotion_ready": current_best == previous_best and margin >= 0.05,
        "previous_best": previous_best,
        "current_scores": {cohort: metrics["strategy_score"] for cohort, metrics in current_scored.items()},
        "margin": round(margin, 4),
    }


async def evaluate(window_days: int) -> dict[str, Any]:
    now = _utcnow()
    current = CohortWindow(name="current", start=now - timedelta(days=window_days), end=now)
    previous = CohortWindow(
        name="previous",
        start=now - timedelta(days=window_days * 2),
        end=now - timedelta(days=window_days),
    )
    users = await _distinct_users_in_window(current)
    task_stats = await _task_stats_map(current)
    feedback_counts = await _feedback_count_map(current)
    session_counts = await _session_count_map(current)
    previous_session_counts = await _session_count_map(previous)
    insight_adoption = await _insight_adoption_map(current)

    previous_users = await _distinct_users_in_window(previous)
    previous_task_stats = await _task_stats_map(previous)
    previous_feedback_counts = await _feedback_count_map(previous)
    previous_sessions_only = await _session_count_map(previous)
    previous_insight_adoption = await _insight_adoption_map(previous)

    current_by_cohort = _aggregate_by_cohort(
        users=users,
        task_stats=task_stats,
        feedback_counts=feedback_counts,
        session_counts=session_counts,
        insight_adoption=insight_adoption,
        previous_session_counts=previous_session_counts,
    )
    previous_by_cohort = _aggregate_by_cohort(
        users=previous_users,
        task_stats=previous_task_stats,
        feedback_counts=previous_feedback_counts,
        session_counts=previous_sessions_only,
        insight_adoption=previous_insight_adoption,
        previous_session_counts=None,
    )
    recommendation = _recommendation(current_by_cohort, previous_by_cohort)
    return {
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "current_window": {
            "start": current.start.isoformat(),
            "end": current.end.isoformat(),
            "cohorts": current_by_cohort,
        },
        "previous_window": {
            "start": previous.start.isoformat(),
            "end": previous.end.isoformat(),
            "cohorts": previous_by_cohort,
        },
        "recommendation": recommendation,
        "notes": {
            "insight_adoption_rule": "在 proactive insight 发出后 24 小时内，如果出现用户消息或任务完成，则记为 adopted。",
            "cohort_rule": "Cohort 由 SHA256(user_id) % 3 稳定分桶。",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate perceptible-intelligence cohorts from recent product data.")
    parser.add_argument("--window-days", type=int, default=7, help="Window size in days for current/previous cohort comparison.")
    parser.add_argument("--output", help="Optional output JSON file.")
    args = parser.parse_args()
    result = asyncio.run(evaluate(args.window_days))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
