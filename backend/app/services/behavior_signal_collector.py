"""
BehaviorSignalCollector - aggregate implicit behavior into cognitive fragments.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, UTC
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curiosity_capsule import CuriosityCapsule
from app.models.plan_state import PlanStateStatus
from app.models.task import Task, TaskStatus
from app.models.task_feedback import TaskFeedback, TaskFeedbackCategory
from app.models.tool_history import UserToolHistory
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.core.event_bus import EventBus
from app.services.capsule_favorite_service import CapsuleFavoriteService
from app.services.cognitive_service import CognitiveService
from app.services.plan_state_service import PlanStateService
from app.services.profile_write_service import ProfileWriteService
from app.services.signal_adaptation import (
    classify_band_with_hysteresis,
    recency_weight,
    weighted_median,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
    INFERRED_TASK_LIMIT = 200
    INFERRED_FEEDBACK_LIMIT = 200

    def __init__(self, db: AsyncSession, redis=None, event_bus: EventBus | None = None):
        self.db = db
        self.redis = redis
        self.event_bus = event_bus
        self._local_cooldowns: dict[str, datetime] = {}
        self.cognitive_service = CognitiveService(db)
        self.plan_state_service = PlanStateService(db, redis)
        self.profile_write_service = ProfileWriteService(db, redis)

    async def handle_task_feedback_event(self, event: dict) -> None:
        user_id = UUID(str(event["user_id"]))
        UUID(str(event["task_id"]))
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

    async def handle_tool_history_event(self, event: dict) -> None:
        user_id_raw = event.get("user_id")
        tool_name = str(event.get("tool_name") or "").strip()
        if not user_id_raw or tool_name not in {"breathing", "calculator"}:
            return

        user_id = UUID(str(user_id_raw))
        record = await self._latest_tool_history_record(user_id, tool_name)
        if record is None or not record.success:
            return

        context = record.context_snapshot or {}
        if tool_name == "breathing":
            await self._maybe_emit_breathing_recovery_signal(user_id, record, context)
        elif tool_name == "calculator":
            await self._maybe_emit_calculator_load_signal(user_id, record, context)

    async def handle_behavior_pattern_event(self, event: dict) -> None:
        user_id = UUID(str(event["user_id"]))
        confidence = float(event.get("confidence_score") or 0.0)
        if confidence < 0.7:
            return

        intervention_created = False
        processed_active_state = False
        pending_push_deliveries: list[tuple[str, dict]] = []
        states = await self.plan_state_service.get_active_plan_states(user_id, limit=3)
        for state in states:
            if state.status != PlanStateStatus.ACTIVE.value:
                continue
            processed_active_state = True
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
                record = None
                if hasattr(self.db, "begin_nested"):
                    async with self.db.begin_nested():
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
                else:
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
                    try:
                        from app.models.card_protocol import DeliveryChannel

                        if record.delivery_channel == DeliveryChannel.PUSH:
                            pending_push_deliveries.append(
                                (
                                    str(record.id),
                                    dict(getattr(record, "diagnosis_payload", {}) or {}),
                                )
                            )
                    except Exception:
                        pass
            except Exception as bridge_exc:
                logger.warning("Behavior→InterventionRecord bridge failed (non-fatal): {}", bridge_exc)

        if processed_active_state:
            await self.db.commit()
        if intervention_created:
            for intervention_id, payload in pending_push_deliveries:
                try:
                    from app.core.celery_tasks import schedule_push_notification

                    schedule_push_notification.delay(
                        user_id=str(user_id),
                        intervention_id=intervention_id,
                        payload=payload,
                    )
                except Exception as delivery_exc:
                    logger.warning(
                        "Behavior→push scheduling failed (non-fatal) for {}: {}",
                        intervention_id,
                        delivery_exc,
                    )

    async def handle_capsule_favorite_event(self, event: dict) -> None:
        user_id_raw = event.get("user_id")
        capsule_id_raw = event.get("capsule_id")
        if not user_id_raw or not capsule_id_raw:
            return

        user_id = UUID(str(user_id_raw))
        capsule_id = UUID(str(capsule_id_raw))
        action = str(event.get("action") or "updated").strip().lower()
        signal_key = f"capsule_favorite:{action}:{capsule_id}"
        if await self._signal_on_cooldown(user_id, signal_key):
            return

        capsule = await self.db.get(CuriosityCapsule, capsule_id)
        if capsule is None or capsule.user_id != user_id:
            return

        verb = {
            "favorited": "收藏了",
            "updated": "更新了收藏备注",
            "unfavorited": "取消收藏了",
        }.get(action, "更新了")
        title = str(capsule.title or "未命名胶囊").strip()
        depth = str(getattr(capsule.depth_level, "value", capsule.depth_level) or "").strip()
        subject = str(capsule.related_subject or "").strip()
        content_parts = [f"用户{verb}认知胶囊《{title}》。"]
        if depth:
            content_parts.append(f"胶囊深度：{depth}。")
        if subject:
            content_parts.append(f"相关主题：{subject}。")
        method_preferences = CapsuleFavoriteService._extract_method_preferences(
            capsule,
            note=str(event.get("note") or "").strip(),
        )
        method_summaries = [f"用户偏好{item['label']}" for item in method_preferences if item.get("label")]
        if method_summaries:
            content_parts.append(f"方法偏好信号：{'；'.join(method_summaries[:3])}。")

        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content=" ".join(content_parts),
            source_type="capsule_favorite",
            resource_type="curiosity_capsule",
            context_tags={
                "signal_key": signal_key,
                "capsule_id": str(capsule_id),
                "capsule_title": title,
                "action": action,
                "depth_level": depth,
                "related_subject": subject,
                "method_preferences": method_preferences,
                "method_preference_summary": method_summaries,
            },
            error_tags=["content.preference_signal"],
            severity=1,
            task_id=capsule.related_task_id,
            source_event_id=f"capsule_fav:{action[:8]}:{capsule_id}",
        )
        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        await self._mark_signal_emitted(user_id, signal_key)

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
            select(func.count(Task.id)).where(
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
        signal_key = "pattern_adjustment"
        if await self._signal_on_cooldown(user_id, signal_key):
            return
        states = await self.plan_state_service.get_active_plan_states(user_id, limit=3)
        for state in states:
            replanner = AdaptiveReplanner(self.db, self.redis)
            await replanner.on_behavior_pattern_detected(
                user_id=user_id,
                plan_id=state.plan_id,
                pattern_name=None,
            )
        if states:
            await self._mark_signal_emitted(user_id, signal_key)

    async def _latest_tool_history_record(self, user_id: UUID, tool_name: str) -> UserToolHistory | None:
        result = await self.db.execute(
            select(UserToolHistory)
            .where(
                UserToolHistory.user_id == user_id,
                UserToolHistory.tool_name == tool_name,
            )
            .order_by(desc(UserToolHistory.created_at))
            .limit(1)
        )
        return result.scalars().first()

    async def _maybe_emit_breathing_recovery_signal(
        self,
        user_id: UUID,
        record: UserToolHistory,
        context: dict,
    ) -> None:
        signal_key = "tool_breathing_recovery"
        if await self._signal_on_cooldown(user_id, signal_key):
            return

        duration = context.get("duration_minutes") or 0
        pattern = str(context.get("pattern") or "呼吸练习")
        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content=f"用户完成了一次 {duration} 分钟的{pattern}，这是主动压力调节和恢复信号。",
            source_type="tool_history",
            context_tags={
                "signal_key": signal_key,
                "tool_name": record.tool_name,
                "tool_history_id": record.id,
                "duration_minutes": duration,
                "rounds_completed": context.get("rounds_completed"),
                "pattern": pattern,
                "used_at": context.get("used_at"),
            },
            error_tags=["wellbeing.stress_regulation", "wellbeing.recovery"],
            severity=1,
            source_event_id=f"tool_history:breathing:{record.id}",
        )
        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        await self._mark_signal_emitted(user_id, signal_key)

    async def _maybe_emit_calculator_load_signal(
        self,
        user_id: UUID,
        record: UserToolHistory,
        context: dict,
    ) -> None:
        complexity = str(context.get("complexity") or "simple")
        if complexity not in {"medium", "complex"}:
            return

        signal_key = f"tool_calculator_{complexity}"
        if await self._signal_on_cooldown(user_id, signal_key):
            return

        severity = 2 if complexity == "complex" else 1
        fragment = await self.cognitive_service.create_fragment(
            user_id=user_id,
            content=f"用户完成了一次{complexity}复杂度的计算器演算，表达式内容未被保存。",
            source_type="tool_history",
            context_tags={
                "signal_key": signal_key,
                "tool_name": record.tool_name,
                "tool_history_id": record.id,
                "complexity": complexity,
                "used_at": context.get("used_at"),
            },
            error_tags=["workflow.calculation_load"],
            severity=severity,
            source_event_id=f"tool_history:calculator:{record.id}",
        )
        await self.cognitive_service.analyze_behavior(user_id, fragment.id)
        await self._mark_signal_emitted(user_id, signal_key)

    async def _signal_on_cooldown(self, user_id: UUID, signal_key: str) -> bool:
        key = self._cooldown_key(user_id, signal_key)
        if self.redis:
            try:
                raw = await self.redis.get(key)
                if raw:
                    return True
            except Exception:
                logger.warning(f"Redis cooldown check failed for {key}, falling back to local")
        expires_at = self._local_cooldowns.get(key)
        if not expires_at:
            return False
        if expires_at <= _utcnow():
            self._local_cooldowns.pop(key, None)
            return False
        return True

    async def _mark_signal_emitted(self, user_id: UUID, signal_key: str) -> None:
        key = self._cooldown_key(user_id, signal_key)
        self._local_cooldowns[key] = _utcnow() + self.SIGNAL_COOLDOWN
        if self.redis:
            try:
                await self.redis.setex(
                    key,
                    int(self.SIGNAL_COOLDOWN.total_seconds()),
                    json.dumps({"emitted_at": _utcnow().isoformat()}),
                )
            except Exception:
                logger.warning(f"Redis cooldown mark failed for {key}")

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
                return

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
            .limit(self.INFERRED_TASK_LIMIT)
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
            .limit(self.INFERRED_FEEDBACK_LIMIT)
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

        return {key: round(count / total, 3) if total else 0.0 for key, count in buckets.items()}

    @staticmethod
    def _task_signal_counter_key(user_id: UUID) -> str:
        return f"behavior:task_inferred_counter:{user_id}"
