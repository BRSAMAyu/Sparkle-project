"""Auto collector for cognitive fragments based on implicit behavior signals."""
from __future__ import annotations

from datetime import datetime, timedelta, UTC
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_book import ErrorRecord
from app.models.focus import FocusSession, FocusStatus
from app.services.cognitive_service import CognitiveService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


COLLECTION_RULES = {
    "task_completion": {
        "time_deviation_threshold": 0.3,  # 时间偏差超过30%
        "completion_rate_threshold": 0.8,  # 完成度低于80%
    },
    "focus_session": {
        "min_duration": 10,  # 最短10分钟
        "interruption_threshold": 3,  # 中断达到或超过3次
        "window_hours": 24,  # 统计窗口
    },
    "error_pattern": {
        "same_node_count": 2,  # 同一知识点错误2次
    },
}


class AutoFragmentCollector:
    """Collect cognitive fragments based on significant behavior deviations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cognitive_service = CognitiveService(db)

    async def collect_from_task_completion(
        self,
        *,
        user_id: UUID,
        task_id: UUID | None,
        estimated_minutes: int | None,
        actual_minutes: int | None,
        completion_rate: float | None,
        difficulty: int | None = None,
        source_event_id: str | None = None,
    ):
        rules = COLLECTION_RULES["task_completion"]
        error_tags: list[str] = []
        signals: list[str] = []

        deviation_ratio = None
        if estimated_minutes and actual_minutes is not None and estimated_minutes > 0:
            deviation_ratio = abs(actual_minutes - estimated_minutes) / float(estimated_minutes)
            if deviation_ratio > rules["time_deviation_threshold"]:
                if actual_minutes > estimated_minutes:
                    error_tags.append("planning.underestimate")
                    signals.append("时间预估偏低")
                else:
                    error_tags.append("planning.overestimate")
                    signals.append("时间预估偏高")

        if completion_rate is not None and completion_rate < rules["completion_rate_threshold"]:
            error_tags.append("execution.low_completion")
            signals.append("完成度偏低")

        if not error_tags:
            return None

        deviation_text = ""
        if deviation_ratio is not None and estimated_minutes is not None and actual_minutes is not None:
            deviation_percent = round(deviation_ratio * 100)
            deviation_text = f"预估 {estimated_minutes} 分钟，实际 {actual_minutes} 分钟（偏差 {deviation_percent}%）"

        completion_text = ""
        if completion_rate is not None:
            completion_text = f"完成度 {completion_rate:.0%}"

        content_parts = [part for part in [deviation_text, completion_text] if part]
        content = "任务完成出现显著偏差：" + "，".join(content_parts) if content_parts else "任务完成出现显著偏差。"

        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content=content,
            source_type="behavior_auto",
            context_tags={
                "task_id": str(task_id) if task_id else None,
                "estimated_minutes": estimated_minutes,
                "actual_minutes": actual_minutes,
                "time_deviation_ratio": deviation_ratio,
                "completion_rate": completion_rate,
                "difficulty": difficulty,
                "signals": signals,
                "signal_source": "task_completion",
            },
            error_tags=error_tags,
            severity=2 if len(error_tags) == 1 else 3,
            task_id=task_id,
            source_event_id=source_event_id or f"auto.task_completion:{task_id}",
        )

        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        return fragment

    async def collect_from_focus_session(
        self,
        *,
        user_id: UUID,
        session_id: UUID | None,
        duration_minutes: int,
        status: FocusStatus | str | None = None,
        interruptions: int | None = None,
        source_event_id: str | None = None,
    ):
        rules = COLLECTION_RULES["focus_session"]
        if duration_minutes < rules["min_duration"]:
            return None

        interruption_count = interruptions
        window_hours = rules.get("window_hours", 24)

        if interruption_count is None:
            since = _utcnow() - timedelta(hours=window_hours)
            stmt = (
                select(func.count(FocusSession.id))
                .where(FocusSession.user_id == user_id)
                .where(FocusSession.status == FocusStatus.INTERRUPTED)
                .where(FocusSession.end_time >= since)
            )
            result = await self.db.execute(stmt)
            interruption_count = int(result.scalar() or 0)

        if interruption_count < rules["interruption_threshold"]:
            return None

        status_value = None
        if status is not None:
            status_value = status.value if isinstance(status, FocusStatus) else str(status)

        content = (
            f"近期专注中断较多：过去 {window_hours} 小时中断 {interruption_count} 次。"
            if interruptions is None
            else f"本次专注中断次数较多：{interruption_count} 次。"
        )

        daily_key = _utcnow().date().isoformat()
        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content=content,
            source_type="behavior_auto",
            context_tags={
                "session_id": str(session_id) if session_id else None,
                "duration_minutes": duration_minutes,
                "interruption_count": interruption_count,
                "status": status_value,
                "window_hours": window_hours if interruptions is None else None,
                "signal_source": "focus_session",
            },
            error_tags=["execution.focus_breakdown"],
            severity=2,
            source_event_id=source_event_id or f"auto.focus_interruptions:{user_id}:{daily_key}",
        )

        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        return fragment

    async def collect_from_error_pattern(
        self,
        *,
        user_id: UUID,
        error_id: UUID | None,
        linked_node_ids: list[str] | None,
        source_event_id: str | None = None,
    ):
        if not linked_node_ids:
            return None

        threshold = COLLECTION_RULES["error_pattern"]["same_node_count"]
        for node_id in linked_node_ids:
            node_id_str = str(node_id)
            count = await self._count_errors_for_node(user_id, node_id_str)
            if count < threshold:
                continue

            fragment = await self.cognitive_service.create_fragment(
                user_id=user_id,
                content=f"同一知识点错误达到 {count} 次，可能存在知识盲区。",
                source_type="behavior_auto",
                context_tags={
                    "error_id": str(error_id) if error_id else None,
                    "node_id": node_id_str,
                    "error_count": count,
                    "signal_source": "error_pattern",
                },
                error_tags=["knowledge.blind_spot"],
                severity=2,
                source_event_id=source_event_id or f"auto.error_pattern:{user_id}:{node_id_str}",
            )
            await self.cognitive_service.analyze_behavior(user_id, fragment.id)
            return fragment

        return None

    async def _count_errors_for_node(self, user_id: UUID, node_id: str) -> int:
        try:
            stmt = (
                select(func.count(ErrorRecord.id))
                .where(ErrorRecord.user_id == user_id)
                .where(ErrorRecord.is_deleted.is_(False))
                .where(ErrorRecord.linked_knowledge_node_ids.contains([node_id]))
            )
            result = await self.db.execute(stmt)
            return int(result.scalar() or 0)
        except Exception:
            # Fallback for sqlite/json array variants
            result = await self.db.execute(
                select(ErrorRecord.linked_knowledge_node_ids)
                .where(ErrorRecord.user_id == user_id)
                .where(ErrorRecord.is_deleted.is_(False))
            )
            count = 0
            for row in result.scalars().all():
                linked_ids = row or []
                if node_id in [str(value) for value in linked_ids if value is not None]:
                    count += 1
            return count
