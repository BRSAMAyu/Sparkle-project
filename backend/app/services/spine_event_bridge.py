"""
Bridge EventBus lifecycle events into the Signal-to-Action Spine.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.signals.external_integration import CalendarEvent, CalendarSignalBridge
from app.signals.spine_orchestrator import SpineOrchestrator
from app.signals.types import ActionableSignal, CausalTrace, _uid

SPINE_EVENT_TYPES = {
    "task.abandoned",
    "task.stuck",
    "focus.session.completed",
    "plan.created",
    "srl.phase.transition",
    "calendar.event.created",
    "calendar.event.updated",
    "calendar.event.deleted",
    "notification.fatigue_detected",
    "shop.purchase_completed",
    "achievement.unlocked",
}


class SpineEventBridge:
    """Translate high-value EventBus events into Spine signals."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.spine = SpineOrchestrator(redis_client)

    async def handle_event(self, event: dict[str, Any]) -> CausalTrace | None:
        user_id = str(event.get("user_id") or "").strip()
        if not user_id:
            return None

        signal = self.build_signal(event)
        if signal is None:
            return None

        try:
            return await self.spine._run_signal_pipeline(
                user_id=user_id,
                signal=signal,
                event_ids=[self._event_id(event)],
            )
        except Exception as exc:
            logger.warning("SpineEventBridge degraded for event {}: {}", event.get("event_type"), exc)
            return None

    def build_signal(self, event: dict[str, Any]) -> ActionableSignal | None:
        event_type = str(event.get("event_type") or "")
        if event_type not in SPINE_EVENT_TYPES:
            return None

        builders = {
            "task.abandoned": self._task_abandoned,
            "task.stuck": self._task_stuck,
            "focus.session.completed": self._focus_completed,
            "plan.created": self._plan_created,
            "srl.phase.transition": self._srl_transition,
            "calendar.event.created": self._calendar_changed,
            "calendar.event.updated": self._calendar_changed,
            "calendar.event.deleted": self._calendar_changed,
            "notification.fatigue_detected": self._notification_fatigue,
            "shop.purchase_completed": self._shop_purchase,
            "achievement.unlocked": self._achievement_unlocked,
        }
        return builders[event_type](event)

    def _task_abandoned(self, event: dict[str, Any]) -> ActionableSignal:
        reason = event.get("reason") or "unspecified"
        return self._signal(
            event,
            source_system="event_bus.task",
            state_key="execution_consistency",
            claim="task_abandoned",
            confidence=0.72,
            scope="current_sprint",
            ttl_hours=72,
            evidence_summary=f"Task {event.get('task_id')} was abandoned; reason={reason}.",
            possible_effects=["adjust_task_size", "ask_for_blocker", "reduce_load"],
            priority="medium",
        )

    def _task_stuck(self, event: dict[str, Any]) -> ActionableSignal:
        elapsed_seconds = int(event.get("elapsed_seconds") or 0)
        priority = "high" if elapsed_seconds >= 900 else "medium"
        confidence = 0.82 if elapsed_seconds >= 900 else 0.7
        return self._signal(
            event,
            source_system="event_bus.task",
            state_key="knowledge_bottleneck",
            claim="task_stuck",
            confidence=confidence,
            scope="task",
            ttl_hours=24,
            evidence_summary=(
                f"Task {event.get('task_id')} reported stuck point "
                f"{event.get('stuck_point') or 'unknown'} after {elapsed_seconds}s."
            ),
            possible_effects=["offer_worked_example", "switch_to_smaller_step", "retrieve_supporting_material"],
            priority=priority,
        )

    def _focus_completed(self, event: dict[str, Any]) -> ActionableSignal:
        duration = float(event.get("duration_minutes") or 0)
        completed = bool(event.get("completed", True))
        high_load = duration >= 90 or not completed
        return self._signal(
            event,
            source_system="event_bus.focus",
            state_key="cognitive_load",
            claim="focus_load_observed" if high_load else "focus_session_completed",
            confidence=0.75 if high_load else 0.58,
            scope="day",
            ttl_hours=24,
            evidence_summary=f"Focus session duration={duration:.0f}min completed={completed}.",
            possible_effects=["reduce_next_task_density", "adjust_response_length", "schedule_recovery"],
            priority="high" if high_load else "low",
        )

    def _plan_created(self, event: dict[str, Any]) -> ActionableSignal:
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        return self._signal(
            event,
            source_system="event_bus.plan",
            state_key="goal_mode",
            claim="plan_created",
            confidence=0.8,
            scope="goal",
            ttl_hours=168,
            evidence_summary=(
                f"Plan {event.get('plan_id')} created via {event.get('source') or 'unknown'}; "
                f"type={metadata.get('plan_type') or 'unknown'}."
            ),
            possible_effects=["activate_plan_context", "prioritize_first_step", "exam_sprint_check"],
            priority="medium",
        )

    def _srl_transition(self, event: dict[str, Any]) -> ActionableSignal:
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        return self._signal(
            event,
            source_system="event_bus.srl",
            state_key="strategy_confidence",
            claim="srl_phase_transition",
            confidence=0.68,
            scope="session",
            ttl_hours=12,
            evidence_summary=(
                f"SRL transition from trigger {event.get('trigger_event_type')}; "
                f"phase={metadata.get('phase') or metadata.get('to_phase') or 'unknown'}."
            ),
            possible_effects=["adjust_metacognitive_prompt", "ask_for_reflection", "update_learning_strategy"],
            priority="medium",
        )

    def _notification_fatigue(self, event: dict[str, Any]) -> ActionableSignal:
        consecutive = int(event.get("consecutive_dismissals") or 0)
        confidence = min(0.9, 0.5 + consecutive * 0.1)
        return self._signal(
            event,
            source_system="event_bus.notification",
            state_key="notification_fatigue",
            claim="consecutive_notification_dismissal",
            confidence=confidence,
            scope="session",
            ttl_hours=48,
            evidence_summary=(
                f"User dismissed {consecutive} consecutive notifications; "
                f"type={event.get('notification_type') or 'mixed'}."
            ),
            possible_effects=["reduce_notification_frequency", "soften_tone", "pause_proactive_push"],
            priority="high" if consecutive >= 4 else "medium",
        )

    def _calendar_changed(self, event: dict[str, Any]) -> ActionableSignal:
        event_type = str(event.get("event_type") or "")
        deleted = event_type == "calendar.event.deleted"

        # Build CalendarEvent from EventBus payload
        cal_event = CalendarEvent(
            event_id=str(event.get("event_id") or event.get("id") or ""),
            title=str(event.get("title") or ""),
            start_time=str(event.get("start_time") or ""),
            end_time=str(event.get("end_time") or ""),
            event_type=str(event.get("calendar_event_type") or "other"),
            subject=event.get("subject"),
            location=event.get("location"),
        )

        bridge = CalendarSignalBridge()

        # Try enriched deadline-pressure analysis
        if not deleted and cal_event.start_time:
            deadline_signal = bridge.detect_deadline_pressure([cal_event])
            if deadline_signal is not None:
                return deadline_signal

        # Fallback: build time-context-aware signal
        if not deleted and cal_event.start_time:
            time_ctx = bridge.build_time_context([cal_event])
            has_pressure = time_ctx.get("has_time_pressure", False)
            nearest_hours = time_ctx.get("nearest_deadline_hours")
            priority = "high" if (nearest_hours is not None and nearest_hours < 24) else "medium"
            confidence = 0.85 if has_pressure else 0.7
            effects = ["adjust_plan_density", "refresh_today_tasks"]
            if has_pressure:
                effects.append("prioritize_review")
            return self._signal(
                event,
                source_system="calendar_bridge",
                state_key="time_context",
                claim="calendar_time_context_updated",
                confidence=confidence,
                scope="current_sprint",
                ttl_hours=int(nearest_hours) + 1 if nearest_hours else 72,
                evidence_summary=(
                    f"{cal_event.title}: {nearest_hours:.0f}h until deadline"
                    if nearest_hours
                    else f"{event_type}: {cal_event.title}"
                ),
                possible_effects=effects,
                priority=priority,
            )

        # Deleted event or event without start_time — recompute pressure or generic signal
        if deleted:
            return self._signal(
                event,
                source_system="calendar_bridge",
                state_key="time_context",
                claim="calendar_deadline_removed",
                confidence=0.62,
                scope="current_sprint",
                ttl_hours=72,
                evidence_summary=f"Removed: {cal_event.title}.",
                possible_effects=["recompute_time_pressure", "adjust_plan_density", "refresh_today_tasks"],
                priority="medium",
            )

        return self._signal(
            event,
            source_system="calendar_bridge",
            state_key="time_context",
            claim="calendar_event_observed",
            confidence=0.6,
            scope="day",
            ttl_hours=48,
            evidence_summary=f"{event_type}: {cal_event.title}.",
            possible_effects=["refresh_today_tasks"],
            priority="low",
        )

    def _shop_purchase(self, event: dict[str, Any]) -> ActionableSignal:
        item_name = event.get("item_name") or event.get("item_id") or "shop item"
        amount = int(event.get("amount") or 0)
        return self._signal(
            event,
            source_system="event_bus.shop",
            state_key="reward_engagement",
            claim="photon_spent",
            confidence=0.6,
            scope="day",
            ttl_hours=24,
            evidence_summary=f"User purchased {item_name} for {amount} photons.",
            possible_effects=["acknowledge_reward_progress", "motivational_reinforcement"],
            priority="low",
        )

    def _achievement_unlocked(self, event: dict[str, Any]) -> ActionableSignal:
        name = event.get("achievement_name") or event.get("achievement_id") or "achievement"
        rarity = event.get("rarity") or "common"
        confidence = {"legendary": 0.9, "epic": 0.85, "rare": 0.78, "common": 0.6}.get(rarity, 0.6)
        return self._signal(
            event,
            source_system="event_bus.achievement",
            state_key="reward_engagement",
            claim="achievement_unlocked",
            confidence=confidence,
            scope="session",
            ttl_hours=12,
            evidence_summary=f"Achievement unlocked: {name} (rarity={rarity}).",
            possible_effects=["celebrate_milestone", "suggest_next_challenge", "reinforce_pattern"],
            priority="medium",
        )

    def _signal(
        self,
        event: dict[str, Any],
        *,
        source_system: str,
        state_key: str,
        claim: str,
        confidence: float,
        scope: str,
        ttl_hours: int,
        evidence_summary: str,
        possible_effects: list[str],
        priority: str,
    ) -> ActionableSignal:
        return ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[self._event_id(event)],
            source_system=source_system,
            state_key=state_key,
            claim=claim,
            confidence=confidence,
            scope=scope,
            ttl_hours=ttl_hours,
            evidence_summary=evidence_summary,
            possible_effects=possible_effects,
            priority=priority,
        )

    @staticmethod
    def _event_id(event: dict[str, Any]) -> str:
        for key in ("event_id", "task_id", "plan_id", "session_id", "evidence_id"):
            value = event.get(key)
            if value:
                return f"{event.get('event_type')}:{value}"
        return f"{event.get('event_type')}:{_uid('evt')}"
