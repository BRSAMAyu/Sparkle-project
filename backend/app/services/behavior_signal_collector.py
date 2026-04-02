"""
BehaviorSignalCollector - aggregate implicit behavior into cognitive fragments.
"""
from __future__ import annotations

import json
from datetime import timezone, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cognitive import CognitiveFragment
from app.models.plan_state import PlanStateStatus
from app.models.task import Task, TaskStatus
from app.models.task_feedback import TaskFeedback, TaskFeedbackCategory
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.core.event_bus import EventBus
from app.services.cognitive_service import CognitiveService
from app.services.plan_state_service import PlanStateService
from app.services.profile_write_service import ProfileWriteService
from app.services.signal_adaptation import (
    classify_band_with_hysteresis,
    recency_weight,
    weighted_median,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BehaviorSignalCollector:
    """Aggregate noisy low-level events into throttled cognitive fragments."""

    SIGNAL_COOLDOWN = timedelta(hours=24)
    FEEDBACK_STREAK = 3
    PLAN_MOD_WINDOW = timedelta(hours=24)
    PLAN_MOD_THRESHOLD = 4
    INACTIVITY_DAYS = 3
    OVERRUN_RATIO = 1.5
    OVERRUN_STREAK = 3
    INFERRED_WINDOW_DAYS = 14
    INFERRED_AGGREGATION_STEP = 5

    def __init__(self, db: AsyncSession, redis=None, event_bus: EventBus | None = None):
        self.db = db
        self.redis = redis
        self.event_bus = event_bus
        self.cognitive_service = CognitiveService(db)
        self.plan_state_service = PlanStateService(db, redis)
        self.profile_write_service = ProfileWriteService(db, redis)

    async def handle_task_feedback_event(self, event: dict) -> None:
        user_id = UUID(str(event["user_id"]))
        task_id = UUID(str(event["task_id"]))
        category = str(event.get("category") or "").strip().lower()

        if category == TaskFeedbackCategory.TOO_DIFFICULT.value:
            await self._maybe_emit_too_difficult_streak(user_id)

        await self._maybe_emit_inactivity_signal(user_id)
        await self._maybe_emit_pattern_adjustment(user_id)
        await self._maybe_update_task_inferred_preferences(user_id)

    async def handle_task_abandoned_event(self, event: dict) -> None:
        user_id = UUID(str(event["user_id"]))
        task_id = UUID(str(event["task_id"]))
        task = await self.db.get(Task, task_id)
        title = getattr(task, "title", None) or "未命名任务"
        time_spent = event.get("time_spent")
        signal_key = f"abandoned:{task_id}"
        if await self._signal_on_cooldown(user_id, signal_key):
            return

        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content=f"用户放弃了任务《{title}》，已执行 {time_spent or 0} 分钟。",
            source_type="behavior_auto",
            context_tags={
                "task_id": str(task_id),
                "task_title": title,
                "time_spent": time_spent,
                "signal_key": signal_key,
            },
            error_tags=["execution.abandonment"],
            severity=2,
            task_id=task_id,
            source_event_id=f"behavior_auto:{signal_key}",
        )
        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        await self._mark_signal_emitted(user_id, signal_key)
        await self._maybe_emit_inactivity_signal(user_id)

    async def handle_task_completed_event(self, event: dict) -> None:
        user_id = UUID(str(event["user_id"]))
        await self._maybe_emit_overrun_pattern(user_id)
        await self._maybe_emit_inactivity_signal(user_id)
        await self._maybe_update_task_inferred_preferences(user_id)

    async def handle_plan_replanned_event(self, event: dict) -> None:
        user_id = UUID(str(event["user_id"]))
        plan_id = str(event.get("plan_id") or event.get("original_plan_id") or "")
        if not plan_id:
            return
        await self._track_plan_modification(user_id, plan_id)
        await self._maybe_emit_inactivity_signal(user_id)

    async def handle_behavior_pattern_event(self, event: dict) -> None:
        user_id = UUID(str(event["user_id"]))
        confidence = float(event.get("confidence_score") or 0.0)
        if confidence < 0.7:
            return

        intervention_created = False
        states = await self.plan_state_service.get_active_plan_states(user_id, limit=3)
        for state in states:
            if state.status != PlanStateStatus.ACTIVE.value:
                continue
            replanner = AdaptiveReplanner(self.db, self.redis)
            await replanner.on_behavior_pattern_detected(
                user_id=user_id,
                plan_id=state.plan_id,
                pattern_name=str(event.get("pattern_name") or ""),
            )

            # --- Card protocol: behavior → intervention record (breakpoint 4 fix) ---
            try:
                from app.services.card_protocol.behavior_intervention_bridge import BehaviorInterventionBridge
                bridge = BehaviorInterventionBridge(self.db, self.event_bus)
                record = await bridge.on_behavior_pattern(
                    user_id=user_id,
                    pattern_name=str(event.get("pattern_name") or ""),
                    pattern_type=str(event.get("pattern_type") or "execution"),
                    confidence=confidence,
                    plan_id=state.plan_id,
                    description=event.get("description"),
                    solution_text=event.get("solution_text"),
                    frequency=int(event.get("frequency") or 1),
                    evidence_ids=event.get("evidence_ids"),
                )
                if record:
                    intervention_created = True
            except Exception as bridge_exc:
                await self.db.rollback()
                logger.warning("Behavior→InterventionRecord bridge failed (non-fatal): {}", bridge_exc)

        if intervention_created:
            await self.db.commit()

    async def _maybe_emit_too_difficult_streak(self, user_id: UUID) -> None:
        signal_key = "too_difficult_streak"
        if await self._signal_on_cooldown(user_id, signal_key):
            return

        result = await self.db.execute(
            select(TaskFeedback, Task.title)
            .join(Task, Task.id == TaskFeedback.task_id)
            .where(TaskFeedback.user_id == user_id)
            .order_by(TaskFeedback.created_at.desc())
            .limit(self.FEEDBACK_STREAK)
        )
        rows = result.all()
        if len(rows) < self.FEEDBACK_STREAK:
            return
        if any(str(feedback.category or "") != TaskFeedbackCategory.TOO_DIFFICULT.value for feedback, _ in rows):
            return

        titles = [title or "未命名任务" for _, title in rows]
        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content=f"用户连续3次反馈任务太难：{', '.join(titles)}",
            source_type="behavior_auto",
            context_tags={
                "signal_key": signal_key,
                "task_titles": titles,
                "feedback_count": len(rows),
            },
            error_tags=["execution.task_resistance"],
            severity=3,
            source_event_id=f"behavior_auto:{signal_key}",
        )
        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        await self._mark_signal_emitted(user_id, signal_key)

    async def _maybe_emit_overrun_pattern(self, user_id: UUID) -> None:
        signal_key = "overrun_streak"
        if await self._signal_on_cooldown(user_id, signal_key):
            return

        result = await self.db.execute(
            select(Task.title, Task.estimated_minutes, Task.actual_minutes)
            .where(Task.user_id == user_id, Task.status == TaskStatus.COMPLETED)
            .order_by(Task.completed_at.desc())
            .limit(self.OVERRUN_STREAK)
        )
        rows = result.all()
        if len(rows) < self.OVERRUN_STREAK:
            return

        titles: list[str] = []
        for title, estimated, actual in rows:
            if not estimated or not actual:
                return
            if float(actual) / float(estimated) < self.OVERRUN_RATIO:
                return
            titles.append(title or "未命名任务")

        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content=f"最近{len(rows)}次任务实际用时都超过预估50%以上：{', '.join(titles)}",
            source_type="behavior_auto",
            context_tags={
                "signal_key": signal_key,
                "task_titles": titles,
            },
            error_tags=["planning.underestimate"],
            severity=2,
            source_event_id=f"behavior_auto:{signal_key}",
        )
        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        await self._mark_signal_emitted(user_id, signal_key)

    async def _track_plan_modification(self, user_id: UUID, plan_id: str) -> None:
        key = f"behavior:plan_mods:{user_id}:{plan_id}"
        if not self.redis:
            return
        now = _utcnow().timestamp()
        cutoff = now - self.PLAN_MOD_WINDOW.total_seconds()
        await self.redis.zadd(key, {f"{now}": now})
        await self.redis.zremrangebyscore(key, "-inf", cutoff)
        await self.redis.expire(key, int(self.PLAN_MOD_WINDOW.total_seconds()))
        count = await self.redis.zcard(key)

        signal_key = f"plan_modifications:{plan_id}"
        if count < self.PLAN_MOD_THRESHOLD or await self._signal_on_cooldown(user_id, signal_key):
            return

        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content=f"用户在24小时内修改了计划 {plan_id} 共 {count} 次。",
            source_type="behavior_auto",
            context_tags={
                "signal_key": signal_key,
                "plan_id": plan_id,
                "modification_count": int(count),
            },
            error_tags=["emotional.overplanning"],
            severity=2,
            source_event_id=f"behavior_auto:{signal_key}",
        )
        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        await self._mark_signal_emitted(user_id, signal_key)

    async def _maybe_emit_inactivity_signal(self, user_id: UUID) -> None:
        signal_key = "inactive_with_active_plan"
        if await self._signal_on_cooldown(user_id, signal_key):
            return

        states = await self.plan_state_service.get_active_plan_states(user_id, limit=1)
        if not states:
            return

        cutoff = _utcnow() - timedelta(days=self.INACTIVITY_DAYS)
        result = await self.db.execute(
            select(func.count(Task.id))
            .where(
                Task.user_id == user_id,
                Task.plan_id == states[0].plan_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
                Task.completed_at >= cutoff,
            )
        )
        completed_count = int(result.scalar() or 0)
        if completed_count > 0:
            return

        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content="用户有活跃计划但连续3天未完成任何任务。",
            source_type="behavior_auto",
            context_tags={
                "signal_key": signal_key,
                "plan_id": str(states[0].plan_id),
            },
            error_tags=["execution.inactive_stall"],
            severity=2,
            source_event_id=f"behavior_auto:{signal_key}",
        )
        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        await self._mark_signal_emitted(user_id, signal_key)

    async def _maybe_emit_pattern_adjustment(self, user_id: UUID) -> None:
        states = await self.plan_state_service.get_active_plan_states(user_id, limit=3)
        for state in states:
            replanner = AdaptiveReplanner(self.db, self.redis)
            await replanner.on_behavior_pattern_detected(
                user_id=user_id,
                plan_id=state.plan_id,
                pattern_name=None,
            )

    async def _signal_on_cooldown(self, user_id: UUID, signal_key: str) -> bool:
        if not self.redis:
            return False
        raw = await self.redis.get(self._cooldown_key(user_id, signal_key))
        return bool(raw)

    async def _mark_signal_emitted(self, user_id: UUID, signal_key: str) -> None:
        if not self.redis:
            return
        await self.redis.setex(
            self._cooldown_key(user_id, signal_key),
            int(self.SIGNAL_COOLDOWN.total_seconds()),
            json.dumps({"emitted_at": _utcnow().isoformat()}),
        )

    @staticmethod
    def _cooldown_key(user_id: UUID, signal_key: str) -> str:
        return f"behavior:auto:cooldown:{user_id}:{signal_key}"

    async def _maybe_update_task_inferred_preferences(self, user_id: UUID) -> None:
        if self.redis:
            counter_key = self._task_signal_counter_key(user_id)
            try:
                count = int(await self.redis.incr(counter_key))
                await self.redis.expire(counter_key, int(timedelta(days=self.INFERRED_WINDOW_DAYS).total_seconds()))
                if count % self.INFERRED_AGGREGATION_STEP != 0:
                    return
            except Exception as exc:
                logger.warning("Task inferred counter failed for %s: %s", user_id, exc)

        updates = await self._build_task_inferred_updates(user_id)
        if not updates:
            return
        try:
            await self.profile_write_service.update_inferred_preference(
                user_id=user_id,
                updates=updates,
                source="ai_inferred",
            )
        except Exception as exc:
            logger.warning("Failed to update task inferred preferences for %s: %s", user_id, exc)

    async def _build_task_inferred_updates(self, user_id: UUID) -> dict[str, object]:
        cutoff = _utcnow() - timedelta(days=self.INFERRED_WINDOW_DAYS)
        task_result = await self.db.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
                Task.completed_at >= cutoff,
            )
            .order_by(desc(Task.completed_at))
        )
        tasks = list(task_result.scalars().all())
        if not tasks:
            return {}

        now = _utcnow()
        ratios: list[tuple[float, float]] = []
        note_lengths: list[tuple[float, float]] = []
        for task in tasks:
            estimated = int(task.estimated_minutes or 0)
            actual = int(task.actual_minutes or 0)
            weight = recency_weight(task.completed_at, now=now, half_life_days=5.0, min_weight=0.25)
            if estimated > 0 and actual > 0:
                ratios.append((abs(actual - estimated) / estimated, weight))
            note = (task.user_note or "").strip()
            if note:
                note_lengths.append((len(note), weight))

        feedback_result = await self.db.execute(
            select(TaskFeedback)
            .where(
                TaskFeedback.user_id == user_id,
                TaskFeedback.created_at >= cutoff,
            )
            .order_by(desc(TaskFeedback.created_at))
        )
        feedbacks = list(feedback_result.scalars().all())
        difficulty_feedback_ratio = self._difficulty_feedback_ratio(feedbacks)

        if not note_lengths:
            note_lengths = [
                (
                    len((feedback.feedback_text or "").strip()),
                    recency_weight(feedback.created_at, now=now, half_life_days=5.0, min_weight=0.25),
                )
                for feedback in feedbacks
                if (feedback.feedback_text or "").strip()
            ]

        weighted_note_total = sum(length * weight for length, weight in note_lengths)
        weighted_note_count = sum(weight for _, weight in note_lengths)
        avg_note_length = (weighted_note_total / weighted_note_count) if weighted_note_count else 0.0

        try:
            prefs = await self.profile_write_service.pref_service.get_preferences(user_id)
            inferred = prefs.inferred or {}
        except Exception:
            inferred = {}

        reflection_depth = classify_band_with_hysteresis(
            avg_note_length,
            str(inferred.get("task_reflection_depth") or "") or None,
            low_enter=10.0,
            high_enter=55.0,
            low_exit=18.0,
            high_exit=45.0,
            low_label="none",
            mid_label="light",
            high_label="deep",
        )

        updates: dict[str, object] = {
            "task_reflection_depth": reflection_depth,
            "difficulty_feedback_ratio": difficulty_feedback_ratio,
        }
        if ratios:
            weighted_ratio_median = weighted_median(ratios)
            if weighted_ratio_median is not None:
                updates["task_difficulty_accuracy"] = round(float(weighted_ratio_median), 3)

        filtered: dict[str, object] = {}
        for key, value in updates.items():
            if inferred.get(key) != value:
                filtered[key] = value
        return filtered

    @staticmethod
    def _difficulty_feedback_ratio(feedbacks: list[TaskFeedback]) -> dict[str, float]:
        if not feedbacks:
            return {"too_hard": 0.0, "too_easy": 0.0, "just_right": 0.0}

        now = _utcnow()
        buckets = {
            "too_hard": 0.0,
            "too_easy": 0.0,
            "just_right": 0.0,
        }
        total = 0.0
        for feedback in feedbacks:
            weight = recency_weight(feedback.created_at, now=now, half_life_days=5.0, min_weight=0.25)
            total += weight
            category = str(feedback.category or "").strip().lower()
            if category == TaskFeedbackCategory.TOO_DIFFICULT.value:
                buckets["too_hard"] += weight
            elif category == TaskFeedbackCategory.TOO_EASY.value:
                buckets["too_easy"] += weight
            elif category == TaskFeedbackCategory.JUST_RIGHT.value:
                buckets["just_right"] += weight

        return {
            key: round(count / total, 3) if total else 0.0
            for key, count in buckets.items()
        }

    @staticmethod
    def _task_signal_counter_key(user_id: UUID) -> str:
        return f"behavior:task_inferred_counter:{user_id}"
