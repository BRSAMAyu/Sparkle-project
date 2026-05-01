from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from datetime import date as date_type
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.aurora.runtime_v1.write_pipeline as write_pipeline
from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.control_surface import (
    AuroraHardBounds,
    ControlSurfaceReading,
    ControlSurfaceService,
)
from app.aurora.runtime_v1.dashboard import DashboardReadoutBuilder, canonicalize_runtime_domain
from app.aurora.runtime_v1.decision_loop import STRATEGY_FIELDS, AuroraDecision, AuroraDecisionLoop
from app.aurora.runtime_v1.self_model import SparkleSelfModelService
from app.aurora.runtime_v1.skills import AuroraSkillRegistry
from app.aurora.runtime_v1.state import (
    ActivityProfile,
    AuroraIntent,
    AuroraRuntimeStore,
    AuroraState,
    AuroraTeachingStrategy,
    InformationalTension,
    LatentThread,
    ScheduledWake,
    merge_activity_profile_payload,
)
from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
from app.aurora.runtime_v1.wake_policy import AuroraWakePolicyService
from app.aurora.runtime_v1.write_pipeline import InferenceClaim
from app.models.calendar_event import CalendarEvent
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.services.memory_service import MemoryService
from app.sprint_packs.last_24h_mode import (
    apply_last_24h_policy_overrides,
    calculate_days_left,
    extract_exam_date,
    is_last_24h_window,
)

GALAXY_BASELINE_TTL_SECONDS = 300  # 5-min stale-acceptable cache
CORRECT_ANSWER_MASTERY_DELTA = 0.15
CORRECT_ANSWER_MASTERY_REASON = "aurora_completion_check_correct"
CHINA_TIMEZONE = timezone(timedelta(hours=8))
LAST_SESSION_MOOD_WINDOW_SECONDS = 24 * 60 * 60
LAST_SESSION_MOOD_TRIGGER_LABELS = {"stressed", "frustrated", "overwhelmed"}
SLEEP_GUARD_START_HOUR = 23
SLEEP_GUARD_END_HOUR = 6
REQUEST_TIMESTAMP_KEYS = (
    "timestamp",
    "request_timestamp",
    "client_timestamp",
    "message_timestamp",
    "user_message_timestamp",
    "created_at",
    "event_time",
)

AURORA_SURFACE_MODELING = "aurora_modeling"
AURORA_RUNTIME_MODE_SURFACES = {
    "onboarding_modeling": AURORA_SURFACE_MODELING,
    "aurora_modeling": AURORA_SURFACE_MODELING,
    "modeling": AURORA_SURFACE_MODELING,
    "aurora_planning": "aurora_planning",
    "aurora_checkpoint": "aurora_checkpoint",
}
AURORA_RUNTIME_STATE_KEY_TEMPLATE = "aurora:runtime:{user_id}:{surface}:{conversation_id}"
AURORA_RUNTIME_STATE_TTL_SECONDS = 24 * 60 * 60

_SURFACE_ACTIVITY_DEFAULTS = {
    AURORA_SURFACE_MODELING: {
        "proactive_intensity": 0.6,
        "next_wake_at": None,
        "conversation_style": "warm",
        "expression": {
            "tone_warmth": 0.84,
            "directness": 0.34,
            "brevity": 0.62,
            "friendliness": 0.86,
            "challenge_intensity": 0.24,
        },
        "agenda_priority": None,
        "task_density_hint": 0.35,
    },
    "aurora_planning": {
        "proactive_intensity": 0.45,
        "next_wake_at": None,
        "conversation_style": "structured",
        "expression": {
            "tone_warmth": 0.34,
            "directness": 0.84,
            "brevity": 0.82,
            "friendliness": 0.42,
            "challenge_intensity": 0.78,
        },
        "agenda_priority": None,
        "task_density_hint": 0.65,
    },
    "aurora_checkpoint": {
        "proactive_intensity": 0.5,
        "next_wake_at": None,
        "conversation_style": "warm",
        "expression": {
            "tone_warmth": 0.68,
            "directness": 0.58,
            "brevity": 0.54,
            "friendliness": 0.74,
            "challenge_intensity": 0.52,
        },
        "agenda_priority": None,
        "task_density_hint": 0.45,
    },
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_utc_naive(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if getattr(value, "tzinfo", None) is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


@dataclass(slots=True)
class AuroraRuntimeTurnPlan:
    surface: str
    messages: list[str]
    surface_complete: bool
    modeling_complete: bool
    activity_profile: dict[str, Any] = field(default_factory=dict)
    hard_boundaries: dict[str, Any] = field(default_factory=dict)
    informational_tensions: list[dict[str, Any]] = field(default_factory=list)
    wake_policy: dict[str, Any] = field(default_factory=dict)
    action: str = "emit_message"
    chat_directive: dict[str, Any] = field(default_factory=dict)


class AuroraRuntimeV1Service:
    _REVIEW_NODE_LABEL_ALIASES: dict[str, str] = {
        "cn.tcp_flow": "TCP 流量控制",
        "cn.tcp_flow_control": "TCP 流量控制",
    }

    def __init__(
        self,
        redis_client=None,
        *,
        decision_loop: AuroraDecisionLoop | None = None,
        chat_adapter: ChatLayerAdapter | None = None,
        dashboard_builder: DashboardReadoutBuilder | None = None,
        self_model_service: SparkleSelfModelService | None = None,
        skill_registry: AuroraSkillRegistry | None = None,
        wake_policy_service: AuroraWakePolicyService | None = None,
        galaxy_service: Any | None = None,
        galaxy_service_factory: Any | None = None,
    ):
        self.redis = redis_client
        self.decision_loop = decision_loop or AuroraDecisionLoop()
        self.chat_adapter = chat_adapter or ChatLayerAdapter()
        self.dashboard_builder = dashboard_builder or DashboardReadoutBuilder(redis_client)
        self.self_model_service = self_model_service or SparkleSelfModelService(redis_client)
        self.skill_registry = skill_registry or AuroraSkillRegistry()
        self.wake_policy_service = wake_policy_service or AuroraWakePolicyService(redis_client)
        self.galaxy_service = galaxy_service
        self.galaxy_service_factory = galaxy_service_factory

    async def get_daily_startup_message(
        self,
        *,
        active_db: AsyncSession,
        user_id: str | UUID,
        plan_id: str | UUID,
        session_date: date_type | datetime | str | None = None,
    ) -> dict[str, Any]:
        """Build Aurora's proactive daily opener for an active sprint plan."""
        user_uuid = UUID(str(user_id))
        plan_uuid = UUID(str(plan_id))
        session_day = self._coerce_session_date(session_date)

        plan = await self._fetch_active_sprint_plan(
            active_db=active_db,
            user_id=user_uuid,
            plan_id=plan_uuid,
        )
        if plan is None:
            raise LookupError("active sprint plan not found")

        tasks = await self._list_plan_tasks(active_db=active_db, plan_id=plan_uuid)
        initial_days_left = self._derive_initial_days_left(plan=plan, tasks=tasks)
        days_left = self._days_left(plan.target_date, session_day=session_day, fallback=initial_days_left)
        current_day_index = self._current_day_index(
            initial_days_left=initial_days_left,
            days_left=days_left,
            tasks=tasks,
        )
        display_name = await self._resolve_user_display_name(active_db=active_db, user_id=user_uuid)
        today_tasks = [task for task in tasks if self._task_day_index(task) == current_day_index]
        yesterday_rate = self._completion_rate_for_day(tasks=tasks, day_index=current_day_index - 1)
        plan_context = self._daily_startup_plan_context(
            plan=plan,
            day_index=current_day_index,
            tasks=today_tasks,
            display_name=display_name,
        )

        today_focus = (
            _strip(plan_context.get("today_focus"))
            or self._today_focus_from_tasks(today_tasks)
            or self._stored_day_recommendation(plan=plan, day_index=current_day_index)
            or _strip(plan.subject)
            or _strip(plan.name)
            or "今天的核心任务"
        )
        estimated_minutes = self._estimated_minutes(today_tasks, fallback=plan.daily_available_minutes)
        day_recommendation = _strip(plan_context.get("day_recommendation")) or self._stored_day_recommendation(
            plan=plan, day_index=current_day_index
        )

        wake_decision_payload: dict[str, Any] = {}
        try:
            wake_decision = await self.wake_policy_service.evaluate(
                active_db=active_db,
                user_id=str(user_uuid),
                user_message="",
                request_extra_context={
                    "plan_id": str(plan_uuid),
                    "days_left": days_left,
                    "plan_completion_rate": yesterday_rate,
                    "expected_completion_rate": 0.75,
                    "struggle_score": 0.0,
                },
                user_context_payload={},
                self_model={},
            )
            wake_decision_payload = wake_decision.to_payload()
        except Exception as exc:
            logger.warning("Aurora daily startup wake policy evaluation failed: {}", exc)

        adjustment_reason = self._daily_adjustment_reason(
            completion_rate=yesterday_rate,
            wake_energy=_strip(wake_decision_payload.get("energy")),
        )
        calendar_note = await self._daily_startup_calendar_note(
            active_db=active_db,
            user_id=user_uuid,
            session_day=session_day,
            today_focus=today_focus,
            estimated_minutes=estimated_minutes,
        )
        message = self._daily_startup_message(
            plan=plan,
            day_index=current_day_index,
            today_focus=today_focus,
            estimated_minutes=estimated_minutes,
            completion_rate=yesterday_rate,
            adjustment_reason=adjustment_reason,
            day_recommendation=day_recommendation,
            display_name=display_name,
            calendar_note=calendar_note,
        )
        return {
            "message": message,
            "today_focus": today_focus,
            "estimated_minutes": estimated_minutes,
            "adjustment_reason": adjustment_reason,
            "calendar_note": calendar_note,
        }

    async def get_comeback_context(
        self,
        *,
        active_db: AsyncSession,
        user_id: str | UUID,
        inactive_threshold_days: int = 3,
    ) -> dict[str, Any] | None:
        """Build a comeback message for users who have been away with an active plan.

        Returns ``None`` when the user does not qualify (recently active or no
        active sprint plan).
        """
        from sqlalchemy import and_, select

        from app.models.plan import Plan
        from app.models.task import Task
        from app.models.user import User
        from app.services.user_activity_service import UserActivityService

        user_uuid = UUID(str(user_id))
        user = await active_db.get(User, user_uuid)
        if user is None or not user.is_active:
            return None

        now = datetime.now(UTC).replace(tzinfo=None)
        last_activity_at = await UserActivityService(active_db).get_last_real_activity_at(user_uuid)
        if last_activity_at is None:
            return None
        days_away = max(0, (now - last_activity_at).days)
        if days_away < inactive_threshold_days:
            return None

        # Most recent active plan with a target date
        stmt = (
            select(Plan)
            .where(
                and_(
                    Plan.user_id == user_uuid,
                    Plan.is_active.is_(True),
                    Plan.target_date.isnot(None),
                    Plan.not_deleted_filter(),
                )
            )
            .order_by(Plan.is_primary.desc(), Plan.created_at.desc())
            .limit(1)
        )
        result = await active_db.execute(stmt)
        plan = result.scalar_one_or_none()
        if plan is None:
            return None

        days_remaining = max(0, (plan.target_date - now.date()).days) if plan.target_date else 0
        subject = _strip(plan.subject) or _strip(plan.name) or "你的计划"

        # Next incomplete task
        task_stmt = (
            select(Task)
            .where(
                and_(
                    Task.plan_id == plan.id,
                    Task.deleted_at.is_(None),
                    Task.status != TaskStatus.COMPLETED,
                )
            )
            .order_by(Task.due_date.asc().nullslast())
            .limit(1)
        )
        task_result = await active_db.execute(task_stmt)
        next_task = task_result.scalar_one_or_none()
        next_task_title = next_task.title if next_task else None
        recent_task_summary = self._comeback_recent_task_summary(next_task)
        light_restart_suggestion = self._comeback_light_restart_suggestion(
            subject=subject,
            recent_task_summary=recent_task_summary,
            next_task_title=next_task_title,
        )
        message = self._comeback_message(
            subject=subject,
            days_away=days_away,
            days_remaining=days_remaining,
            recent_task_summary=recent_task_summary,
            next_task_title=next_task_title,
            light_restart_suggestion=light_restart_suggestion,
        )

        return {
            "title": "好久不见，我一直在等你",
            "message": message,
            "days_away": days_away,
            "days_remaining": days_remaining,
            "subject": subject,
            "next_task_title": next_task_title or "",
            "recent_task_summary": recent_task_summary,
            "light_restart_suggestion": light_restart_suggestion,
            "plan_id": str(plan.id),
        }

    async def plan_turn(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        surface: str,
        conversation_id: str,
        request_id: str,
        user_message: str,
        request_extra_context: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
    ) -> AuroraRuntimeTurnPlan:
        request_extra_context = dict(request_extra_context or {})
        conversation_context = dict(conversation_context or {})
        user_context_payload = dict(user_context_payload or {})
        surface = AURORA_RUNTIME_MODE_SURFACES.get(surface, surface)
        prior_runtime_state = await self._load_prior_runtime_state(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
        )
        request_extra_context = self._with_prior_runtime_context(
            request_extra_context=request_extra_context,
            prior_state=prior_runtime_state,
        )
        request_extra_context = await self._with_strategy_recalibration_context(
            active_db=active_db,
            user_id=user_id,
            conversation_id=conversation_id,
            request_extra_context=request_extra_context,
        )
        request_extra_context = await self._with_last_session_mood_context(
            active_db=active_db,
            user_id=user_id,
            request_extra_context=request_extra_context,
            conversation_context=conversation_context,
        )
        request_extra_context = self._with_surface_state(surface=surface, request_extra_context=request_extra_context)
        request_extra_context = self._with_last_24h_exam_policy(
            request_extra_context=request_extra_context,
            user_context_payload=user_context_payload,
        )
        request_extra_context = self._with_sleep_guard_context(
            request_extra_context=request_extra_context,
            conversation_context=conversation_context,
            user_context_payload=user_context_payload,
        )

        if not request_extra_context.get("galaxy_baseline") and active_db is not None:
            galaxy_baseline = await self._fetch_galaxy_baseline(active_db=active_db, user_id=user_id)
            if galaxy_baseline:
                request_extra_context = {**request_extra_context, "galaxy_baseline": galaxy_baseline}
        user_context_payload = await self.dashboard_builder.with_confirmed_weak_nodes_from_redis(
            user_id=user_id,
            user_context_payload=user_context_payload,
            redis_client=self.redis,
        )
        user_context_payload = await self.dashboard_builder.with_confirmed_strategy_preference_from_redis(
            user_id=user_id,
            user_context_payload=user_context_payload,
            redis_client=self.redis,
        )
        if active_db is not None:
            user_context_payload = await self.dashboard_builder.with_deep_pattern_alerts_from_error_history(
                active_db=active_db,
                user_id=user_id,
                user_context_payload=user_context_payload,
                redis_client=self.redis,
            )

        control_surface_reading = await self._read_control_surface(active_db=active_db, user_id=user_id)
        activity_profile = self._build_activity_profile(surface=surface, request_extra_context=request_extra_context)
        if prior_runtime_state is not None:
            prior_profile = prior_runtime_state.activity_profile.model_dump(mode="python")
            prior_profile.pop("next_wake_at", None)
            activity_profile = merge_activity_profile_payload(activity_profile, prior_profile)
        activity_profile.update(self._activity_payload(control_surface_reading.adjustable))
        review_focus = self._review_focus_from_context(request_extra_context)
        if review_focus is not None:
            return AuroraRuntimeTurnPlan(
                surface=surface,
                messages=[self._build_review_node_first_turn_message(review_focus)],
                surface_complete=False,
                modeling_complete=False,
                activity_profile=activity_profile,
                hard_boundaries=control_surface_reading.hard_bounds.model_dump(mode="json"),
                informational_tensions=[],
                wake_policy={},
            )
        if self._is_last_24h_policy(request_extra_context.get("exam_sprint_policy")):
            activity_profile = merge_activity_profile_payload(
                activity_profile,
                {
                    "strategy": {
                        "worked_example_first": True,
                        "retrieval_practice": True,
                        "spaced_review": True,
                        "error_analysis_required": True,
                        "drop_low_roi_topics": True,
                        "new_topic_allowed": False,
                    }
                },
            )
            if self._looks_like_new_topic_request(user_message):
                return AuroraRuntimeTurnPlan(
                    surface=surface,
                    messages=["明天就考试了，现在看新章节的收益很低。建议先把你最容易丢分的 TCP 状态变化再过一遍。"],
                    surface_complete=False,
                    modeling_complete=False,
                    activity_profile=activity_profile,
                    hard_boundaries=control_surface_reading.hard_bounds.model_dump(mode="json"),
                    informational_tensions=[],
                    wake_policy={},
                )

        candidate_affordances = self.skill_registry.load_candidate_affordances(surface)
        self_model = await self.self_model_service.get_readout_summary(
            user_id=user_id,
            request_extra_context=request_extra_context,
            user_context_payload=user_context_payload,
        )
        self_model = await self._maybe_apply_daily_recap(
            user_id=user_id,
            request_extra_context=request_extra_context,
            user_context_payload=user_context_payload,
            self_model=self_model,
        )
        wake_decision = await self.wake_policy_service.evaluate(
            active_db=active_db,
            user_id=user_id,
            user_message=user_message,
            request_extra_context=request_extra_context,
            user_context_payload=user_context_payload,
            self_model=self_model,
        )
        activity_profile = wake_decision.apply_activity_profile(activity_profile)
        readout = self.dashboard_builder.build(
            surface=surface,
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            user_message=user_message,
            request_extra_context=request_extra_context,
            conversation_context=conversation_context,
            user_context_payload=user_context_payload,
            control_surface_reading=control_surface_reading,
            activity_profile=activity_profile,
            candidate_affordances=candidate_affordances,
            self_model=self_model,
            wake_policy=wake_decision.to_payload(),
        )

        decision = await self.decision_loop.decide(readout)
        activity_profile = self._merge_harness_updates(activity_profile, decision)
        messages = await self.chat_adapter.render(decision, readout)
        if not messages and decision.action not in {"wait", "drop_thread"}:
            messages = await self.chat_adapter._fallback_messages(
                decision=decision,
                readout=readout,
                reason="empty_render",
            )
        if not messages and decision.action not in {"wait", "drop_thread"}:
            logger.warning("Aurora runtime v1 produced no chat output for non-wait action {}", decision.action)

        surface_complete = bool(decision.surface_complete)
        modeling_complete = bool(decision.modeling_complete)
        if surface == AURORA_SURFACE_MODELING and modeling_complete:
            surface_complete = True

        informational_tensions = self._extract_informational_tensions(decision)

        plan = AuroraRuntimeTurnPlan(
            surface=surface,
            messages=messages,
            surface_complete=surface_complete,
            modeling_complete=modeling_complete,
            activity_profile=activity_profile,
            hard_boundaries=control_surface_reading.hard_bounds.model_dump(mode="json"),
            informational_tensions=informational_tensions,
            wake_policy=wake_decision.to_payload(),
            action=decision.action,
            chat_directive=decision.chat_directive,
        )
        if self.redis is not None:
            claims = self._extract_inference_claims_from_decision(decision, readout)
            for claim in claims:
                try:
                    await write_pipeline.submit_claim(claim, redis=self.redis)
                except Exception as exc:
                    logger.warning(
                        "Aurora runtime v1 failed to submit inference claim {} for user {}: {}",
                        claim.domain,
                        user_id,
                        exc,
                    )
        if wake_decision.full_allowed and messages:
            await self.wake_policy_service.record_full_wake(
                user_id=user_id,
                policy=wake_decision.cooldown_policy,
            )
        if active_db is not None:
            await AuroraDecisionTelemetryService(active_db, redis_client=self.redis).record_turn(
                user_id=user_id,
                surface=surface,
                conversation_id=conversation_id,
                request_id=request_id,
                user_message=user_message,
                request_extra_context=request_extra_context,
                readout=readout,
                decision=decision,
                plan=plan,
            )
        await self._check_strategy_pattern(
            user_id=user_id,
            conversation_id=conversation_id,
            decision=decision,
        )
        await self._apply_correct_answer_mastery_update(
            active_db=active_db,
            user_id=user_id,
            request_id=request_id,
            decision=decision,
            readout=readout,
        )
        await self._persist_runtime_state(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
            request_id=request_id,
            user_message=user_message,
            request_extra_context=request_extra_context,
            conversation_context=conversation_context,
            user_context_payload=user_context_payload,
            plan=plan,
            decision=decision,
            wake_policy=wake_decision.to_payload(),
        )
        return plan

    async def _load_prior_runtime_state(
        self,
        *,
        user_id: str,
        surface: str,
        conversation_id: str,
    ) -> AuroraState | None:
        if self.redis is None:
            return None
        store = AuroraRuntimeStore(self.redis, enabled=True)
        try:
            state = await store.load_runtime_state(
                user_id=user_id,
                surface=surface,
                conversation_id=conversation_id,
            )
            if state is not None:
                return state
            if surface == "aurora_checkpoint":
                return await store.load_latest_surface_state(user_id=user_id, surface=surface)
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to load prior runtime state: {}", exc)
        return None

    def _with_prior_runtime_context(
        self,
        *,
        request_extra_context: dict[str, Any],
        prior_state: AuroraState | None,
    ) -> dict[str, Any]:
        if prior_state is None:
            return request_extra_context

        enriched = dict(request_extra_context)
        prior_tensions = [item.model_dump(mode="json") for item in prior_state.informational_tensions]
        prior_threads = [item.model_dump(mode="json") for item in prior_state.latent_threads]
        enriched["previous_runtime_state"] = {
            "surface": prior_state.surface,
            "conversation_id": prior_state.conversation_id,
            "runtime_session_id": prior_state.runtime_session_id,
            "updated_at": prior_state.updated_at.isoformat(),
            "last_decision_at": prior_state.last_decision_at.isoformat() if prior_state.last_decision_at else None,
            "informational_tensions": prior_tensions,
            "latent_threads": prior_threads,
            "activity_profile": prior_state.activity_profile.model_dump(mode="json"),
        }
        enriched["informational_tensions"] = self._merge_context_items(
            prior_tensions,
            enriched.get("informational_tensions"),
            key_field="tension_id",
        )
        enriched["latent_threads"] = self._merge_context_items(
            prior_threads,
            enriched.get("latent_threads"),
            key_field="thread_id",
        )
        return enriched

    def _merge_context_items(
        self, prior_items: list[dict[str, Any]], current_value: Any, *, key_field: str
    ) -> list[dict[str, Any]]:
        if not isinstance(prior_items, list):
            prior_items = []
        current_items = (
            [dict(item) for item in current_value if isinstance(item, Mapping)]
            if isinstance(current_value, list)
            else []
        )
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in [*prior_items, *current_items]:
            key = _strip(item.get(key_field)) or json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return merged

    async def _with_strategy_recalibration_context(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        conversation_id: str,
        request_extra_context: dict[str, Any],
    ) -> dict[str, Any]:
        if self.redis is None:
            return request_extra_context

        try:
            stale_signal = await AuroraDecisionTelemetryService(
                active_db,
                redis_client=self.redis,
            ).detect_stale_strategy(
                user_id=user_id,
                conversation_id=conversation_id,
            )
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to detect stale strategy: {}", exc)
            return request_extra_context

        if not stale_signal or stale_signal.get("stale") is not True:
            return request_extra_context

        enriched = dict(request_extra_context)
        enriched["strategy_recalibration_needed"] = True
        if stale_signal.get("stuck_on"):
            enriched["stuck_domain"] = stale_signal["stuck_on"]
        return enriched

    async def _with_last_session_mood_context(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        request_extra_context: dict[str, Any],
        conversation_context: dict[str, Any],
    ) -> dict[str, Any]:
        if request_extra_context.get("last_session_mood"):
            return request_extra_context
        if not self._is_new_conversation(conversation_context):
            return request_extra_context

        try:
            mood = await MemoryService(active_db, redis_client=self.redis).get_last_session_mood(user_id)
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to read last session mood: {}", exc)
            return request_extra_context

        if not isinstance(mood, dict):
            return request_extra_context
        mood_label = str(mood.get("mood_label") or "").strip().lower()
        if mood_label not in LAST_SESSION_MOOD_TRIGGER_LABELS:
            return request_extra_context

        recorded_at = self._coerce_session_mood_datetime(
            mood.get("recorded_at") or mood.get("updated_at") or mood.get("created_at")
        )
        if recorded_at is None:
            return request_extra_context
        age_seconds = (datetime.now(UTC) - recorded_at).total_seconds()
        if age_seconds < 0 or age_seconds > LAST_SESSION_MOOD_WINDOW_SECONDS:
            return request_extra_context

        enriched = dict(request_extra_context)
        enriched["last_session_mood"] = mood_label
        enriched["last_session_mood_at"] = recorded_at.isoformat().replace("+00:00", "Z")
        if mood.get("mood_score") is not None:
            enriched["last_session_mood_score"] = mood.get("mood_score")
        return enriched

    @staticmethod
    def _is_new_conversation(conversation_context: dict[str, Any]) -> bool:
        messages = conversation_context.get("messages")
        if not isinstance(messages, list):
            return True
        return len(messages) <= 1

    @staticmethod
    def _coerce_session_mood_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            parsed = value
        else:
            text = _strip(value)
            if not text:
                return None
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    async def _read_control_surface(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
    ) -> ControlSurfaceReading:
        if active_db is None:
            return ControlSurfaceReading(
                adjustable=ActivityProfile(),
                hard_bounds=AuroraHardBounds(),
                runtime_enabled=True,
            )
        try:
            return await ControlSurfaceService(active_db, self.redis, preference_service=None, enabled=True).read_control_surface(user_id)
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to read control surface: {}", exc)
            hard_boundaries = await self._read_hard_boundaries(active_db=active_db, user_id=user_id)
            return ControlSurfaceReading(
                adjustable=ActivityProfile(),
                hard_bounds=AuroraHardBounds.model_validate(hard_boundaries or {}),
                runtime_enabled=True,
            )

    async def _read_hard_boundaries(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
    ) -> dict[str, Any]:
        if active_db is None:
            return {}
        try:
            user_uuid = UUID(str(user_id))
        except (TypeError, ValueError):
            return {}

        try:
            explicit_payload = (
                await active_db.execute(
                    select(UserPreferencesCenter.explicit).where(UserPreferencesCenter.user_id == user_uuid)
                )
            ).scalar_one_or_none()
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to read hard boundaries: {}", exc)
            return {}

        if not isinstance(explicit_payload, dict):
            return {}
        aurora_preferences = explicit_payload.get("aurora_preferences")
        return dict(aurora_preferences) if isinstance(aurora_preferences, dict) else {}

    def _build_activity_profile(
        self,
        *,
        surface: str,
        request_extra_context: dict[str, Any],
    ) -> dict[str, Any]:
        profile = merge_activity_profile_payload(
            _SURFACE_ACTIVITY_DEFAULTS.get(surface, _SURFACE_ACTIVITY_DEFAULTS[AURORA_SURFACE_MODELING]),
            {},
        )
        if request_extra_context.get("conversation_style") in {"warm", "structured", "exploratory"}:
            profile["conversation_style"] = request_extra_context["conversation_style"]
        if isinstance(request_extra_context.get("expression"), dict):
            profile = merge_activity_profile_payload(profile, {"expression": request_extra_context["expression"]})
        return profile

    def _review_focus_from_context(self, request_extra_context: Mapping[str, Any]) -> dict[str, Any] | None:
        review_node = _strip(request_extra_context.get("review_node"))
        if not review_node:
            return None

        node_label = _strip(request_extra_context.get("node_label"))
        if not node_label:
            node_label = self._REVIEW_NODE_LABEL_ALIASES.get(review_node, self._humanize_review_node_id(review_node))

        result: dict[str, Any] = {
            "review_node": review_node,
            "node_label": node_label or "这个知识点",
        }

        mastery_raw = request_extra_context.get("mastery")
        if isinstance(mastery_raw, (int, float)):
            result["mastery"] = float(mastery_raw)

        study_count_raw = request_extra_context.get("study_count")
        if isinstance(study_count_raw, int):
            result["study_count"] = study_count_raw

        error_count_raw = request_extra_context.get("related_error_count")
        if isinstance(error_count_raw, int):
            result["related_error_count"] = error_count_raw

        related_errors_raw = request_extra_context.get("related_errors")
        if isinstance(related_errors_raw, list):
            related_errors: list[dict[str, Any]] = []
            for item in related_errors_raw[:3]:
                if not isinstance(item, Mapping):
                    continue
                question_text = _strip(item.get("question_text"))
                analysis_summary = _strip(item.get("analysis_summary"))
                if not question_text and not analysis_summary:
                    continue
                related_errors.append(
                    {
                        **({"question_text": question_text} if question_text else {}),
                        **({"analysis_summary": analysis_summary} if analysis_summary else {}),
                    }
                )
            if related_errors:
                result["related_errors"] = related_errors

        return result

    @staticmethod
    def _humanize_review_node_id(review_node: str) -> str:
        compact = _strip(review_node).replace(".", " ").replace("_", " ")
        if not compact:
            return ""
        return compact.upper() if compact.isascii() else compact

    @staticmethod
    def _build_review_node_first_turn_message(review_focus: Mapping[str, Any]) -> str:
        node_label = _strip(review_focus.get("node_label")) or "这个知识点"
        mastery = review_focus.get("mastery")
        study_count = review_focus.get("study_count", 0)
        error_count = review_focus.get("related_error_count", 0)
        related_errors = review_focus.get("related_errors")

        mastery_pct: int | None = None
        if isinstance(mastery, (int, float)):
            mastery_pct = int(mastery * 100) if mastery <= 1 else int(mastery)
            mastery_pct = max(0, min(100, mastery_pct))

        if mastery_pct is not None and mastery_pct <= 0 and study_count == 0:
            return (
                f"好的，我们开始学习「{node_label}」。用户当前对该节点掌握 {mastery_pct}%。"
                "先从最基础的概念入手，弄清它要解决什么问题，"
                "再用基础题逐步深入到核心原理和常见考法。"
            )

        parts = [f"收到，我们先围绕「{node_label}」做一轮定点复习。"]

        if mastery_pct is not None:
            parts.append(f"用户当前对该节点掌握 {mastery_pct}%。")
            if mastery_pct >= 70:
                parts.append("你的掌握度已经不错了，这次会直接上挑战题来查漏补缺。")
            elif mastery_pct >= 40:
                parts.append("你有一些基础但还有薄弱环节，我们用进阶题趁热打铁。")
            else:
                parts.append("这个知识点你还比较生疏，我们先从基础题和关键概念梳理开始。")

        if error_count and error_count > 0:
            parts.append(f"注意到你有 {error_count} 道相关错题，复习时会特别针对易错点。")

        if isinstance(related_errors, list) and related_errors:
            summaries = [
                _strip(item.get("analysis_summary")) or _strip(item.get("question_text"))
                for item in related_errors
                if isinstance(item, Mapping)
            ]
            summaries = [summary for summary in summaries if summary]
            if summaries:
                parts.append(f"先点名处理这些线索：{'；'.join(summaries[:3])}。")

        parts.append("先用你自己的话说清它要解决什么问题，再对比一个最容易混淆的相邻概念。")
        return "".join(parts)

    def _with_surface_state(self, *, surface: str, request_extra_context: dict[str, Any]) -> dict[str, Any]:
        if surface != "aurora_planning":
            return request_extra_context

        enriched = dict(request_extra_context)
        surface_state = (
            dict(enriched.get("surface_state") or {}) if isinstance(enriched.get("surface_state"), dict) else {}
        )
        scaffold = enriched.get("planning_detour_scaffold")
        if isinstance(scaffold, dict):
            scaffold_state = scaffold.get("surface_state")
            if isinstance(scaffold_state, dict):
                surface_state.update(scaffold_state)
            if scaffold.get("recent_detours") or scaffold.get("top_latent_thread"):
                surface_state.setdefault("in_detour", True)
        if surface_state:
            enriched["surface_state"] = surface_state
        return enriched

    def _with_last_24h_exam_policy(
        self,
        *,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> dict[str, Any]:
        profile_context = user_context_payload.get("profile_context")
        if not isinstance(profile_context, dict):
            profile_context = {}

        policy = (
            request_extra_context.get("exam_sprint_policy")
            or user_context_payload.get("exam_sprint_policy")
            or profile_context.get("exam_sprint_policy")
        )
        policy = dict(policy) if isinstance(policy, dict) else {}

        cold_start = (
            request_extra_context.get("cold_start_context")
            or user_context_payload.get("cold_start_context")
            or profile_context.get("cold_start_context")
        )
        cold_start = dict(cold_start) if isinstance(cold_start, dict) else {}

        exam_date = extract_exam_date(request_extra_context, user_context_payload, policy, cold_start)
        days_left = (
            calculate_days_left(exam_date)
            if exam_date is not None
            else (
                _safe_int(policy.get("days_left"))
                or _safe_int(policy.get("time_constraint_days"))
                or _safe_int(request_extra_context.get("days_left"))
                or _safe_int(cold_start.get("time_constraint_days"))
            )
        )
        if not is_last_24h_window(exam_date=exam_date, days_left=days_left):
            return request_extra_context

        subject = (
            _strip(policy.get("subject"))
            or _strip(request_extra_context.get("subject"))
            or _strip(cold_start.get("subject"))
            or _strip(cold_start.get("exam_scope"))
            or "当前科目"
        )
        enriched = dict(request_extra_context)
        enriched["exam_sprint_policy"] = apply_last_24h_policy_overrides(
            policy,
            subject=subject,
            exam_date=exam_date,
            days_left=days_left,
        )
        return enriched

    def _with_sleep_guard_context(
        self,
        *,
        request_extra_context: dict[str, Any],
        conversation_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> dict[str, Any]:
        enriched = dict(request_extra_context)
        enriched.pop("sleep_guard_active", None)
        enriched.pop("sleep_guard_hint", None)

        observed_at = self._request_timestamp_in_china_time(
            request_extra_context=request_extra_context,
            conversation_context=conversation_context,
        )
        if not self._is_sleep_guard_window(observed_at):
            return enriched

        enriched["sleep_guard_active"] = True
        hint = self._extract_sleep_guard_hint(enriched, user_context_payload)
        if hint:
            enriched["sleep_guard_hint"] = hint
        return enriched

    def _request_timestamp_in_china_time(
        self,
        *,
        request_extra_context: dict[str, Any],
        conversation_context: dict[str, Any],
    ) -> datetime:
        for value in self._request_timestamp_candidates(request_extra_context, conversation_context):
            parsed = self._coerce_china_datetime(value)
            if parsed is not None:
                return parsed
        return datetime.now(timezone(timedelta(hours=8)))

    def _request_timestamp_candidates(
        self,
        request_extra_context: dict[str, Any],
        conversation_context: dict[str, Any],
    ) -> list[Any]:
        candidates: list[Any] = []
        for key in REQUEST_TIMESTAMP_KEYS:
            if key in request_extra_context:
                candidates.append(request_extra_context.get(key))

        for key in ("user_message", "message", "request"):
            nested = request_extra_context.get(key)
            if isinstance(nested, dict):
                for timestamp_key in REQUEST_TIMESTAMP_KEYS:
                    if timestamp_key in nested:
                        candidates.append(nested.get(timestamp_key))

        messages = conversation_context.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                if not isinstance(message, dict):
                    continue
                if str(message.get("role") or "").lower() not in {"user", "human"}:
                    continue
                for timestamp_key in REQUEST_TIMESTAMP_KEYS:
                    if timestamp_key in message:
                        candidates.append(message.get(timestamp_key))
                break
        return candidates

    def _coerce_china_datetime(self, value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, (int, float)):
            parsed = self._datetime_from_epoch(value)
            if parsed is None:
                return None
        elif isinstance(value, dict):
            seconds = value.get("seconds")
            if seconds is None:
                return None
            nanos = value.get("nanos") or value.get("nanos_adjustment") or 0
            try:
                parsed = self._datetime_from_epoch(float(seconds) + float(nanos) / 1_000_000_000)
            except (TypeError, ValueError):
                return None
            if parsed is None:
                return None
        else:
            text = _strip(value)
            if not text:
                return None
            parsed = self._parse_timestamp_text(text)
            if parsed is None:
                return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=CHINA_TIMEZONE)
        return parsed.astimezone(CHINA_TIMEZONE)

    def _datetime_from_epoch(self, value: Any) -> datetime | None:
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            return None
        if abs(seconds) > 10_000_000_000:
            seconds /= 1000
        try:
            return datetime.fromtimestamp(seconds, tz=CHINA_TIMEZONE)
        except (OverflowError, OSError, ValueError):
            return None

    def _parse_timestamp_text(self, text: str) -> datetime | None:
        numeric = text.strip()
        if numeric.replace(".", "", 1).isdigit():
            return self._datetime_from_epoch(numeric)

        normalized = text.replace("Z", "+00:00")
        if normalized.endswith(" CST"):
            normalized = f"{normalized[:-4]}+08:00"
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            pass

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def _is_sleep_guard_window(self, observed_at: datetime) -> bool:
        local_time = (
            observed_at.astimezone(CHINA_TIMEZONE) if observed_at.tzinfo else observed_at.replace(tzinfo=CHINA_TIMEZONE)
        )
        return local_time.hour >= SLEEP_GUARD_START_HOUR or local_time.hour < SLEEP_GUARD_END_HOUR

    def _extract_sleep_guard_hint(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> str:
        profile_context = user_context_payload.get("profile_context")
        if not isinstance(profile_context, dict):
            profile_context = {}

        for candidate in (
            request_extra_context.get("sprint_policy"),
            request_extra_context.get("exam_sprint_policy"),
            user_context_payload.get("sprint_policy"),
            user_context_payload.get("exam_sprint_policy"),
            profile_context.get("sprint_policy"),
            profile_context.get("exam_sprint_policy"),
        ):
            if isinstance(candidate, dict):
                hint = _strip(candidate.get("sleep_guard_hint"))
                if hint:
                    return hint
        return ""

    def _is_last_24h_policy(self, policy: Any) -> bool:
        return isinstance(policy, dict) and (
            bool(policy.get("last_24h_mode"))
            or _strip(policy.get("sprint_mode") or policy.get("mode")).lower() == "last_24h_cram"
        )

    def _looks_like_new_topic_request(self, user_message: str) -> bool:
        text = _strip(user_message).lower()
        if not text:
            return False
        return any(
            token in text
            for token in (
                "新章节",
                "新内容",
                "全新",
                "没学过",
                "从头讲",
                "低频",
                "拓展",
                "扩展",
                "new chapter",
                "new topic",
                "fresh topic",
            )
        )

    def _activity_payload(self, profile: ActivityProfile) -> dict[str, Any]:
        default_payload = ActivityProfile().model_dump(mode="python")
        payload = profile.model_dump(mode="python")
        return {
            key: value
            for key, value in payload.items()
            if value not in (None, "") and value != default_payload.get(key)
        }

    async def _maybe_apply_daily_recap(
        self,
        *,
        user_id: str,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        self_model: dict[str, Any],
    ) -> dict[str, Any]:
        task_state = dict(
            request_extra_context.get("task_state") or user_context_payload.get("task_state") or {},
        )
        if not task_state.get("day_completed"):
            return self_model

        raw_rate = task_state.get("completion_rate")
        try:
            completion_rate = float(raw_rate)
        except (TypeError, ValueError):
            logger.warning("Aurora daily recap: invalid completion_rate={} for user {}", raw_rate, user_id)
            return self_model

        try:
            await self.self_model_service.update_daily_recap(
                user_id=user_id,
                completion_rate=completion_rate,
            )
            return await self.self_model_service.get_readout_summary(
                user_id=user_id,
                request_extra_context=request_extra_context,
                user_context_payload=user_context_payload,
            )
        except Exception as exc:
            logger.warning("Aurora daily recap failed for user {}: {}", user_id, exc)
            return self_model

    def _merge_harness_updates(self, activity_profile: dict[str, Any], decision: AuroraDecision) -> dict[str, Any]:
        return merge_activity_profile_payload(activity_profile, decision.harness_updates or {})

    def _extract_informational_tensions(self, decision: AuroraDecision) -> list[dict[str, Any]]:
        if decision.modeling_complete:
            return []
        updates = decision.state_updates or {}
        tensions = updates.get("informational_tensions")
        if isinstance(tensions, list):
            normalized: list[dict[str, Any]] = []
            seen: set[str] = set()
            for item in tensions:
                if not isinstance(item, dict):
                    continue
                domain = canonicalize_runtime_domain(item.get("domain"))
                status = str(item.get("status") or "open")
                if not domain or status in {"resolved", "dropped"} or domain in seen:
                    continue
                seen.add(domain)
                normalized.append(
                    {
                        **dict(item),
                        "domain": domain,
                        "status": status,
                    }
                )
            return normalized

        if decision.action in {"wait", "drop_thread"}:
            return []

        domain = canonicalize_runtime_domain(
            updates.get("agenda_priority") or decision.harness_updates.get("agenda_priority")
        )
        if not domain:
            return []
        return [
            {
                "domain": domain,
                "status": "open",
                "description": f"需要继续补齐 {domain} 相关线索",
                "priority": 0.7,
            }
        ]

    async def _apply_correct_answer_mastery_update(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        request_id: str,
        decision: AuroraDecision,
        readout: Any,
    ) -> None:
        node_ids = self._extract_correct_answer_node_ids(decision.state_updates or {})
        if not node_ids:
            return

        allowed_node_ids = self._allowed_sprint_pack_node_ids(readout)
        if not allowed_node_ids:
            logger.warning(
                "Aurora correct-answer mastery update skipped: no Sprint Pack node whitelist for user {}",
                user_id,
            )
            return

        galaxy_service = self._galaxy_service(active_db)
        if galaxy_service is None:
            return

        try:
            user_uuid = UUID(str(user_id))
        except (TypeError, ValueError):
            user_uuid = None

        if active_db is not None and self.galaxy_service is None and self.galaxy_service_factory is None:
            if user_uuid is None:
                return

        user_ref = user_uuid or str(user_id)
        updated_nodes: set[str] = set()
        for raw_node_id in node_ids:
            node_id = self._canonical_correct_answer_node_id(raw_node_id, allowed_node_ids)
            if not node_id or node_id in updated_nodes:
                continue
            updated_nodes.add(node_id)

            current_mastery = self._mastery_from_context(readout, node_id)
            current_mastery = await self._current_sprint_node_mastery(
                galaxy_service=galaxy_service,
                user_id=user_uuid,
                node_id=node_id,
                fallback=current_mastery,
            )

            new_mastery = self._increment_mastery(current_mastery)
            try:
                await galaxy_service.update_node_mastery(
                    user_id=user_ref,
                    node_id=node_id,
                    new_mastery=new_mastery,
                    reason=CORRECT_ANSWER_MASTERY_REASON,
                    request_id=request_id,
                )
            except Exception as exc:
                logger.warning(
                    "Aurora correct-answer mastery update failed for user {} node {}: {}",
                    user_id,
                    node_id,
                    exc,
                )

    def _extract_correct_answer_node_ids(self, updates: Mapping[str, Any]) -> list[str]:
        raw_values: list[Any] = []
        for key in ("correct_answer_node", "correct_answer_nodes"):
            value = updates.get(key)
            if value in (None, "", [], {}):
                continue
            if isinstance(value, (list, tuple, set)):
                raw_values.extend(value)
            else:
                raw_values.append(value)

        node_ids: list[str] = []
        seen: set[str] = set()
        for value in raw_values:
            if isinstance(value, Mapping):
                value = value.get("node_id") or value.get("id") or value.get("name")
            node_id = str(value or "").strip()
            if node_id and node_id not in seen:
                seen.add(node_id)
                node_ids.append(node_id)
        return node_ids

    def _allowed_sprint_pack_node_ids(self, readout: Any) -> set[str]:
        allowed: set[str] = set()

        def add_nodes(value: Any) -> None:
            values = value if isinstance(value, (list, tuple, set)) else [value]
            for item in values:
                if isinstance(item, Mapping):
                    item = item.get("node_id") or item.get("id") or item.get("name")
                node_id = str(item or "").strip()
                if node_id:
                    allowed.add(node_id)

        cold_start = getattr(readout, "cold_start_context", {}) or {}
        checkpoint = getattr(readout, "checkpoint_state", {}) or {}
        if isinstance(cold_start, Mapping):
            add_nodes(cold_start.get("sprint_pack_nodes"))
            subject = _strip(cold_start.get("subject"))
        else:
            subject = ""

        if isinstance(checkpoint, Mapping):
            sprint_pack_id = _strip(checkpoint.get("sprint_pack_id"))
            if sprint_pack_id and "@" in sprint_pack_id:
                subject = subject or sprint_pack_id.split("@", 1)[0]

        if subject:
            try:
                from app.sprint_packs.sprint_pack_loader import load_pack

                pack = load_pack(subject)
            except Exception as exc:
                logger.warning("Aurora failed to load Sprint Pack for correct-answer whitelist {}: {}", subject, exc)
                pack = None
            if isinstance(pack, Mapping):
                add_nodes(
                    [node.get("node_id") for node in pack.get("knowledge_nodes", []) if isinstance(node, Mapping)]
                )
        return allowed

    def _canonical_correct_answer_node_id(self, node_id: str, allowed_node_ids: set[str]) -> str | None:
        if node_id in allowed_node_ids:
            return node_id
        aliases = {
            "cn.tcp_handshake": "cn.tcp_three_way",
            "cn.tcp_three_way_handshake": "cn.tcp_three_way",
        }
        alias_target = aliases.get(node_id)
        if alias_target in allowed_node_ids:
            return alias_target
        return None

    def _galaxy_service(self, active_db: AsyncSession | None) -> Any | None:
        if self.galaxy_service is not None:
            return self.galaxy_service
        if active_db is None:
            return None
        if self.galaxy_service_factory is not None:
            return self.galaxy_service_factory(active_db)
        from app.services.galaxy_service import GalaxyService

        return GalaxyService(active_db)

    async def _current_sprint_node_mastery(
        self,
        *,
        galaxy_service: Any,
        user_id: UUID | None,
        node_id: str,
        fallback: float,
    ) -> float:
        if user_id is None:
            return fallback
        getter = getattr(galaxy_service, "get_sprint_mastery_summary", None)
        if getter is None:
            return fallback
        try:
            summary = await getter(user_id, [node_id])
            if isinstance(summary, Mapping) and node_id in summary:
                return float(summary[node_id])
        except Exception as exc:
            logger.warning("Aurora failed to read Sprint Pack mastery summary for node {}: {}", node_id, exc)
        return fallback

    def _mastery_from_context(self, readout: Any, node_id: str) -> float:
        for source in (
            getattr(readout, "request_extra_context", {}),
            getattr(readout, "cold_start_context", {}),
            getattr(readout, "profile_context", {}),
            getattr(readout, "task_state", {}),
        ):
            value = self._find_node_mastery(source, node_id)
            if value is not None:
                return value
        return 0.0

    def _find_node_mastery(self, payload: Any, node_id: str) -> float | None:
        if payload in (None, "", [], {}):
            return None
        if isinstance(payload, Mapping):
            for key in ("galaxy_mastery", "current_mastery", "node_mastery", "mastery_by_node"):
                value = payload.get(key)
                if isinstance(value, Mapping) and node_id in value:
                    try:
                        return float(value[node_id])
                    except (TypeError, ValueError):
                        return None
            for value in payload.values():
                found = self._find_node_mastery(value, node_id)
                if found is not None:
                    return found
        elif isinstance(payload, list):
            for item in payload:
                found = self._find_node_mastery(item, node_id)
                if found is not None:
                    return found
        return None

    def _increment_mastery(self, current_mastery: float) -> float:
        scale_cap = 1.0 if current_mastery <= 1.0 else 100.0
        delta = CORRECT_ANSWER_MASTERY_DELTA if scale_cap == 1.0 else CORRECT_ANSWER_MASTERY_DELTA * 100.0
        return round(min(scale_cap, max(0.0, current_mastery) + delta), 4)

    def _extract_inference_claims_from_decision(
        self,
        decision: AuroraDecision,
        readout: Any,
    ) -> list[InferenceClaim]:
        user_id = _strip(getattr(readout, "user_id", ""))
        if not user_id:
            return []

        claims: list[InferenceClaim] = []
        if decision.modeling_complete:
            claims.append(
                InferenceClaim(
                    user_id=user_id,
                    domain="modeling_complete",
                    evidence_type="modeling_turn",
                    value=True,
                    confidence=0.9,
                    status="confirmed",
                    needs_confirmation=False,
                    evidence=["Aurora decision marked modeling_complete=true."],
                    source="aurora_runtime_v1",
                )
            )

        tensions = (decision.state_updates or {}).get("informational_tensions")
        if isinstance(tensions, list):
            for item in tensions:
                if not isinstance(item, Mapping):
                    continue
                if _strip(item.get("status")).lower() != "resolved":
                    continue
                domain = canonicalize_runtime_domain(item.get("domain"))
                if not domain:
                    continue
                claims.append(
                    InferenceClaim(
                        user_id=user_id,
                        domain=domain,
                        evidence_type="resolved_tension",
                        value=self._value_for_resolved_tension(domain=domain, tension=item, readout=readout),
                        confidence=self._claim_confidence(item, default=0.85),
                        status="confirmed",
                        needs_confirmation=False,
                        evidence=self._evidence_for_resolved_tension(item),
                        source="aurora_runtime_v1",
                    )
                )

        strategy = (decision.harness_updates or {}).get("strategy")
        if isinstance(strategy, Mapping) and strategy.get("concept_first") is True:
            claims.append(
                InferenceClaim(
                    user_id=user_id,
                    domain="learning_style",
                    evidence_type="harness_strategy",
                    value="concept_first",
                    confidence=0.7,
                    evidence=["Aurora selected concept_first=true in the teaching strategy."],
                    source="aurora_runtime_v1",
                )
            )
        return claims

    def _value_for_resolved_tension(
        self,
        *,
        domain: str,
        tension: Mapping[str, Any],
        readout: Any,
    ) -> Any:
        for key in ("value", "resolved_value", "confirmed_value", "answer", "content"):
            value = tension.get(key)
            if value not in (None, "", [], {}):
                return value

        evidence = tension.get("evidence")
        if isinstance(evidence, list):
            for item in reversed(evidence):
                if item not in (None, "", [], {}):
                    return item

        for source in (
            getattr(readout, "request_extra_context", {}),
            getattr(readout, "task_state", {}),
            getattr(readout, "profile_context", {}),
            getattr(readout, "cold_start_context", {}),
            getattr(readout, "self_model", {}),
            getattr(readout, "exam_sprint_policy", {}),
        ):
            value = self._find_domain_value(domain=domain, payload=source)
            if value not in (None, "", [], {}):
                return value
        return True

    def _find_domain_value(self, *, domain: str, payload: Any) -> Any:
        if payload in (None, "", [], {}):
            return None
        if isinstance(payload, Mapping):
            for key, value in payload.items():
                if canonicalize_runtime_domain(key) == domain and value not in (None, "", [], {}):
                    return value
                nested = self._find_domain_value(domain=domain, payload=value)
                if nested not in (None, "", [], {}):
                    return nested
        if isinstance(payload, list):
            for item in payload:
                nested = self._find_domain_value(domain=domain, payload=item)
                if nested not in (None, "", [], {}):
                    return nested
        return None

    def _evidence_for_resolved_tension(self, tension: Mapping[str, Any]) -> list[str]:
        evidence: list[str] = []
        raw_evidence = tension.get("evidence")
        if isinstance(raw_evidence, list):
            evidence.extend(_strip(item) for item in raw_evidence if _strip(item))
        description = _strip(tension.get("description"))
        if description:
            evidence.append(description)
        return evidence[-5:]

    def _claim_confidence(self, payload: Mapping[str, Any], *, default: float) -> float:
        for key in ("confidence", "priority"):
            try:
                return round(max(0.0, min(1.0, float(payload.get(key)))), 4)
            except (TypeError, ValueError):
                continue
        return default

    def _coerce_session_date(self, value: date_type | datetime | str | None) -> date_type:
        if value is None:
            return datetime.now(CHINA_TIMEZONE).date()
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date_type):
            return value
        text = _strip(value)
        if not text:
            return datetime.now(CHINA_TIMEZONE).date()
        try:
            return date_type.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError("session_date must be an ISO date") from exc

    async def _fetch_active_sprint_plan(
        self,
        *,
        active_db: AsyncSession,
        user_id: UUID,
        plan_id: UUID,
    ) -> Plan | None:
        stmt = (
            select(Plan)
            .where(
                Plan.id == plan_id,
                Plan.user_id == user_id,
                Plan.type == PlanType.SPRINT,
                Plan.is_active.is_(True),
                Plan.not_deleted_filter(),
            )
            .limit(1)
        )
        result = await active_db.execute(stmt)
        return result.scalar_one_or_none()

    async def _list_plan_tasks(self, *, active_db: AsyncSession, plan_id: UUID) -> list[Task]:
        stmt = (
            select(Task)
            .where(Task.plan_id == plan_id, Task.not_deleted_filter())
            .order_by(Task.order_index.asc(), Task.created_at.asc())
        )
        result = await active_db.execute(stmt)
        return list(result.scalars().all())

    def _derive_initial_days_left(self, *, plan: Plan, tasks: list[Task]) -> int:
        metadata = _as_dict(plan.source_metadata)
        exam_sprint = _as_dict(metadata.get("exam_sprint_intake"))
        goal_model = _as_dict(exam_sprint.get("goal_model"))
        from_goal_model = _safe_int(goal_model.get("days_left"))
        if from_goal_model is not None and from_goal_model > 0:
            return from_goal_model

        max_task_day = max((self._task_day_index(task) for task in tasks), default=0)
        if max_task_day > 0:
            return max_task_day

        if plan.target_date and plan.created_at:
            return max((plan.target_date - plan.created_at.date()).days, 1)
        return 1

    def _days_left(self, target_date: date_type | None, *, session_day: date_type, fallback: int) -> int:
        if target_date is None:
            return max(fallback, 0)
        return max((target_date - session_day).days, 0)

    def _current_day_index(self, *, initial_days_left: int, days_left: int, tasks: list[Task]) -> int:
        max_task_day = max((self._task_day_index(task) for task in tasks), default=initial_days_left)
        derived = max(initial_days_left - days_left + 1, 1)
        return min(derived, max(max_task_day, 1))

    def _task_day_index(self, task: Task) -> int:
        order_index = int(task.order_index or 0)
        if order_index >= 1000:
            return max(order_index // 1000, 1)

        for tag in list(task.tags or []):
            tag_text = _strip(tag).lower()
            if not tag_text.startswith("day:"):
                continue
            parsed = _safe_int(tag_text.split(":", maxsplit=1)[1])
            if parsed is not None and parsed > 0:
                return parsed
        return 1

    def _task_status(self, task: Task) -> str:
        raw = getattr(task.status, "value", task.status)
        return _strip(raw or TaskStatus.PENDING.value)

    def _completion_rate_for_day(self, *, tasks: list[Task], day_index: int) -> float | None:
        if day_index <= 0:
            return None
        day_tasks = [task for task in tasks if self._task_day_index(task) == day_index]
        if not day_tasks:
            return None
        completed = sum(1 for task in day_tasks if self._task_status(task) == TaskStatus.COMPLETED.value)
        return round(completed / len(day_tasks), 4)

    def _estimated_minutes(self, tasks: list[Task], *, fallback: int | None) -> int:
        total = sum(max(int(task.estimated_minutes or 0), 0) for task in tasks)
        if total > 0:
            return total
        return max(int(fallback or 0), 0)

    def _today_focus_from_tasks(self, tasks: list[Task]) -> str:
        if not tasks:
            return ""

        for task in tasks:
            guide = _as_dict(task.guide_json)
            knowledge_nodes = [_strip(item) for item in list(guide.get("knowledge_nodes") or []) if _strip(item)]
            if knowledge_nodes:
                return "、".join(knowledge_nodes[:2])

        for task in tasks:
            guide = _as_dict(task.guide_json)
            for key in ("focus", "focus_cue", "objective", "output_action"):
                focus = self._compact_focus_text(guide.get(key))
                if focus:
                    return focus
            for key in ("guide_content", "title"):
                focus = self._compact_focus_text(getattr(task, key, ""))
                if focus:
                    return focus
        return ""

    def _compact_focus_text(self, value: Any) -> str:
        text = " ".join(_strip(value).split())
        if not text:
            return ""
        text = re.sub(r"^Day\s*\d+\s*[：:·-]*\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^第\s*\d+\s*天[：:，,]*\s*", "", text)
        text = re.sub(r"^优先拿下\s*", "", text)
        text = text.replace("这些考试收益最高的节点", "")
        text = text.strip(" 。；;，,")
        return text[:42].rstrip("，,。")

    def _stored_day_recommendation(self, *, plan: Plan, day_index: int) -> str:
        metadata = _as_dict(plan.source_metadata)
        highlights = _as_dict(metadata.get("day_highlights"))
        stored_day = _safe_int(highlights.get("day"))
        if stored_day == day_index:
            return self._compact_focus_text(highlights.get("recommendation") or highlights.get("ai_recommendation"))
        keyed = _as_dict(highlights.get(str(day_index)))
        return self._compact_focus_text(keyed.get("recommendation") or keyed.get("ai_recommendation"))

    async def _resolve_user_display_name(self, *, active_db: AsyncSession, user_id: UUID) -> str:
        result = await active_db.execute(select(User).where(User.id == user_id).limit(1))
        user = result.scalar_one_or_none()
        if user is None:
            return ""
        return _strip(user.nickname or user.full_name or user.username or "")

    def _daily_startup_plan_context(
        self,
        *,
        plan: Plan,
        day_index: int,
        tasks: list[Task],
        display_name: str,
    ) -> dict[str, Any]:
        metadata = _as_dict(plan.source_metadata)
        raw_plan_context = _as_dict(metadata.get("plan_context"))
        day_context = _as_dict(raw_plan_context.get("daily_startup"))
        keyed = _as_dict(day_context.get(str(day_index)))
        current = keyed or _as_dict(day_context.get("current_day"))
        return {
            "display_name": display_name,
            "today_focus": (
                self._compact_focus_text(current.get("today_focus"))
                or self._compact_focus_text(current.get("task"))
                or self._compact_focus_text(raw_plan_context.get("today_focus"))
                or self._today_focus_from_tasks(tasks)
            ),
            "day_recommendation": (
                self._compact_focus_text(current.get("recommendation"))
                or self._compact_focus_text(current.get("message"))
                or self._compact_focus_text(raw_plan_context.get("day_recommendation"))
                or self._stored_day_recommendation(plan=plan, day_index=day_index)
            ),
        }

    def _daily_adjustment_reason(self, *, completion_rate: float | None, wake_energy: str) -> str:
        if completion_rate is None:
            return "今天是这个冲刺日程的新启动点，先按当前计划进入状态。"
        percent = int(round(completion_rate * 100))
        if completion_rate >= 0.8:
            return f"昨天完成率 {percent}%，今天保持当前节奏。"
        if completion_rate < 0.5:
            return f"昨天完成率 {percent}%，今天先缩小任务切口，优先完成核心任务。"
        if wake_energy in {"light", "moderate", "full"}:
            return f"昨天完成率 {percent}%，Aurora 会把今天的推进提示放轻一点。"
        return f"昨天完成率 {percent}%，今天稳住节奏，先完成一个闭环。"

    def _daily_startup_message(
        self,
        *,
        plan: Plan,
        day_index: int,
        today_focus: str,
        estimated_minutes: int,
        completion_rate: float | None,
        adjustment_reason: str,
        day_recommendation: str = "",
        display_name: str = "",
        calendar_note: str = "",
    ) -> str:
        subject = _strip(plan.subject) or _strip(plan.name) or "这场考试"
        greeting = self._daily_greeting()
        recommendation_tail = self._daily_recommendation_tail(day_recommendation, today_focus=today_focus)
        calendar_tail = self._daily_calendar_tail(calendar_note)
        name_prefix = f"{display_name}，" if display_name and len(display_name) <= 12 else ""
        greeting_prefix = f"{greeting}，{name_prefix}" if name_prefix else f"{greeting}，"
        opening = (
            f"{greeting_prefix}今天是你备考{subject}的第 {day_index} 天。"
            f"今天的核心任务是 {today_focus}，预计 {estimated_minutes} 分钟。"
        )
        if completion_rate is None:
            return f"{opening}{adjustment_reason}{recommendation_tail}{calendar_tail}准备好了吗？"
        percent = int(round(completion_rate * 100))
        if completion_rate >= 0.8:
            return (
                f"{opening}昨天完成率 {percent}%，做得很好，推进很顺利，"
                f"今天我们保持这个手感。{recommendation_tail}{calendar_tail}准备好了吗？"
            )
        if completion_rate < 0.5:
            return (
                f"{opening}昨天完成率 {percent}%，完成得偏少，"
                f"今天我们轻一点，先缩小到最核心的一步。{recommendation_tail}{calendar_tail}准备好了吗？"
            )
        return f"{opening}{adjustment_reason}{recommendation_tail}{calendar_tail}准备好了吗？"

    async def _daily_startup_calendar_note(
        self,
        *,
        active_db: AsyncSession,
        user_id: UUID,
        session_day: date_type,
        today_focus: str,
        estimated_minutes: int,
    ) -> str:
        day_start = datetime.combine(session_day, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        result = await active_db.execute(
            select(CalendarEvent)
            .where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.deleted_at.is_(None),
                CalendarEvent.start_time < day_end,
                CalendarEvent.end_time > day_start,
            )
            .order_by(CalendarEvent.start_time)
            .limit(6)
        )
        events = list(result.scalars().all())
        if not events:
            return ""

        event = events[0]
        start_label = self._format_event_time(event.start_time)
        end_label = self._format_event_time(event.end_time)
        slot = self._first_free_calendar_slot(
            events=events,
            session_day=session_day,
            estimated_minutes=estimated_minutes,
        )
        title = _strip(event.title) or "日程"
        if slot:
            return (
                f"今天 {start_label}-{end_label} 你有「{title}」，"
                f"建议把「{today_focus}」放在 {slot[0]}-{slot[1]} 的空档里。"
            )
        return f"今天 {start_label}-{end_label} 你有「{title}」，这段时间先不要安排冲刺任务。"

    @staticmethod
    def _format_event_time(value: datetime) -> str:
        value = value.astimezone(CHINA_TIMEZONE) if value.tzinfo else value
        return value.strftime("%H:%M")

    @staticmethod
    def _first_free_calendar_slot(
        *,
        events: list[CalendarEvent],
        session_day: date_type,
        estimated_minutes: int,
    ) -> tuple[str, str] | None:
        required_minutes = max(30, min(60, int(estimated_minutes or 60)))
        day_start = datetime.combine(session_day, datetime.min.time()).replace(hour=9)
        day_end = datetime.combine(session_day, datetime.min.time()).replace(hour=22)
        cursor = day_start
        for event in sorted(events, key=lambda item: item.start_time):
            event_start = event.start_time.replace(tzinfo=None) if event.start_time.tzinfo else event.start_time
            event_end = event.end_time.replace(tzinfo=None) if event.end_time.tzinfo else event.end_time
            event_start = max(day_start, event_start)
            event_end = min(day_end, event_end)
            if event_start > cursor and (event_start - cursor).total_seconds() >= required_minutes * 60:
                slot_end = min(event_start, cursor + timedelta(minutes=max(60, required_minutes)))
                return cursor.strftime("%H:%M"), slot_end.strftime("%H:%M")
            if event_end > cursor:
                cursor = event_end
        if day_end > cursor and (day_end - cursor).total_seconds() >= required_minutes * 60:
            slot_end = min(day_end, cursor + timedelta(minutes=max(60, required_minutes)))
            return cursor.strftime("%H:%M"), slot_end.strftime("%H:%M")
        return None

    def _daily_recommendation_tail(self, recommendation: str, *, today_focus: str) -> str:
        text = self._compact_focus_text(recommendation)
        if not text:
            return ""
        if text == today_focus:
            return ""
        if not text.endswith(("。", "！", "？")):
            text = f"{text}。"
        return text

    @staticmethod
    def _daily_calendar_tail(calendar_note: str) -> str:
        text = " ".join(_strip(calendar_note).split())
        if not text:
            return ""
        if not text.endswith(("。", "！", "？")):
            text = f"{text}。"
        return text

    def _comeback_recent_task_summary(self, task: Task | None) -> str:
        if task is None:
            return ""

        guide = _as_dict(task.guide_json)
        knowledge_nodes = [_strip(item) for item in list(guide.get("knowledge_nodes") or []) if _strip(item)]
        if knowledge_nodes:
            return "、".join(knowledge_nodes[:2])

        for key in ("objective", "focus", "focus_cue", "output_action"):
            focus = self._compact_focus_text(guide.get(key))
            if focus:
                return focus

        return self._compact_focus_text(task.title)

    def _comeback_light_restart_suggestion(
        self,
        *,
        subject: str,
        recent_task_summary: str,
        next_task_title: str | None,
    ) -> str:
        focus = recent_task_summary or _strip(next_task_title) or subject or "今天最简单的一步"
        return f"先开一个「30分钟保底版」，把「{focus}」推进到一个最小闭环。"

    def _comeback_message(
        self,
        *,
        subject: str,
        days_away: int,
        days_remaining: int,
        recent_task_summary: str,
        next_task_title: str | None,
        light_restart_suggestion: str,
    ) -> str:
        plan_label = subject if subject.endswith("冲刺") else f"{subject}冲刺"
        focus = recent_task_summary or _strip(next_task_title) or subject or "最简单的一步"
        days_str = f"{days_remaining} 天" if days_remaining > 0 else "最后一点收尾窗口"
        still_time = "现在回来还来得及" if days_remaining > 0 else "现在回来也还能先追回一点节奏"
        return (
            f"你已经 {days_away} 天没来了，我一直在等你。"
            f"你的{plan_label}还剩 {days_str}，最近最适合重新捡起来的是「{focus}」。"
            f"{still_time}——如果累了，{light_restart_suggestion}"
        )

    def _daily_greeting(self) -> str:
        hour = datetime.now(CHINA_TIMEZONE).hour
        if 5 <= hour < 12:
            return "早上好"
        if 12 <= hour < 18:
            return "下午好"
        if 18 <= hour < 23:
            return "晚上好"
        return "夜深了"

    async def _persist_runtime_state(
        self,
        *,
        user_id: str,
        surface: str,
        conversation_id: str,
        request_id: str,
        user_message: str,
        request_extra_context: dict[str, Any],
        conversation_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        plan: AuroraRuntimeTurnPlan,
        decision: AuroraDecision,
        wake_policy: dict[str, Any],
    ) -> None:
        if self.redis is None:
            return
        profile_context = user_context_payload.get("profile_context")
        if not isinstance(profile_context, dict):
            profile_context = {}
        now = _utcnow()
        current_intent = AuroraIntent(
            intent_type=self._intent_type_from_decision(decision, plan),
            target_tension_id=_strip(plan.activity_profile.get("agenda_priority")) or None,
            payload=decision.chat_directive,
        )
        tensions = self._runtime_tensions(
            raw_items=self._merge_context_items(
                request_extra_context.get("informational_tensions") if isinstance(request_extra_context, dict) else [],
                plan.informational_tensions,
                key_field="tension_id",
            ),
            conversation_id=conversation_id,
            now=now,
        )
        threads = self._runtime_threads(
            raw_items=self._merge_context_items(
                request_extra_context.get("latent_threads") if isinstance(request_extra_context, dict) else [],
                decision.state_updates.get("latent_threads"),
                key_field="thread_id",
            ),
            conversation_id=conversation_id,
            current_intent=current_intent,
            fallback_tensions=tensions,
            now=now,
        )
        runtime_state = AuroraState(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
            runtime_session_id=request_id,
            user_model_snapshot=profile_context,
            informational_tensions=tensions,
            current_intent=current_intent,
            latent_threads=threads,
            activity_profile=ActivityProfile.model_validate(plan.activity_profile),
            self_scheduled_wakes=self._runtime_wakes(decision.wake_schedule),
            streaming_status="waiting_user",
            ingress_events=[
                {
                    "type": "user_message",
                    "content": str(user_message or ""),
                    "messages": plan.messages,
                    "hard_boundaries": plan.hard_boundaries,
                    "decision": decision.to_payload(),
                    "wake_policy": wake_policy,
                    "history_size": len(conversation_context.get("messages") or []),
                }
            ],
            last_decision_at=now,
            updated_at=now,
        )
        try:
            await AuroraRuntimeStore(
                self.redis, ttl_seconds=AURORA_RUNTIME_STATE_TTL_SECONDS, enabled=True
            ).save_runtime_state(runtime_state)
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to persist Redis runtime state: {}", exc)

    def _runtime_tensions(
        self,
        *,
        raw_items: Any,
        conversation_id: str,
        now: datetime,
    ) -> list[InformationalTension]:
        normalized: list[InformationalTension] = []
        seen: set[str] = set()
        items = raw_items if isinstance(raw_items, list) else []
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                continue
            domain = canonicalize_runtime_domain(item.get("domain")) or _strip(item.get("domain")) or "checkpoint_gap"
            status = str(item.get("status") or "open")
            if status in {"resolved", "dropped"}:
                continue
            key = _strip(item.get("tension_id")) or f"{conversation_id}:tension:{domain}:{index}"
            if key in seen:
                continue
            seen.add(key)
            description = _strip(item.get("description")) or f"需要继续补齐 {domain} 相关线索"
            try:
                priority = float(item.get("priority") or 0.7)
            except (TypeError, ValueError):
                priority = 0.7
            normalized.append(
                InformationalTension(
                    tension_id=key,
                    domain=domain,
                    description=description,
                    priority=max(0.0, min(1.0, priority)),
                    status=status,
                    evidence=[str(value) for value in item.get("evidence") or [] if str(value).strip()],
                    importance_reasoning=_strip(item.get("importance_reasoning")) or None,
                    created_at=_as_utc_naive(item.get("created_at")) or now,
                    last_attempted_at=_as_utc_naive(item.get("last_attempted_at")),
                )
            )
        return normalized

    def _runtime_threads(
        self,
        *,
        raw_items: Any,
        conversation_id: str,
        current_intent: AuroraIntent,
        fallback_tensions: list[InformationalTension],
        now: datetime,
    ) -> list[LatentThread]:
        normalized: list[LatentThread] = []
        items = raw_items if isinstance(raw_items, list) else []
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                continue
            snapshot = (
                _strip(item.get("context_snapshot")) or _strip(item.get("summary")) or _strip(item.get("description"))
            )
            if not snapshot:
                continue
            source_intent = (
                AuroraIntent.model_validate(item.get("source_intent"))
                if isinstance(item.get("source_intent"), Mapping)
                else current_intent
            )
            try:
                salience = float(item.get("salience") or 0.6)
            except (TypeError, ValueError):
                salience = 0.6
            normalized.append(
                LatentThread(
                    thread_id=_strip(item.get("thread_id")) or f"{conversation_id}:thread:{index}",
                    source_intent=source_intent,
                    tension_links=[
                        str(value)
                        for value in item.get("tension_links")
                        or [tension.tension_id for tension in fallback_tensions[:1]]
                        if str(value).strip()
                    ],
                    salience=max(0.0, min(1.0, salience)),
                    context_snapshot=snapshot,
                    created_at=_as_utc_naive(item.get("created_at")) or now,
                )
            )
        return normalized

    def _runtime_wakes(self, wake_schedule: dict[str, Any] | None) -> list[ScheduledWake]:
        if not isinstance(wake_schedule, Mapping) or not wake_schedule.get("scheduled_at"):
            return []
        reason = _strip(wake_schedule.get("reason")) or _strip(wake_schedule.get("planned_action")) or "scheduled wake"
        try:
            return [
                ScheduledWake(
                    wake_id=_strip(wake_schedule.get("wake_id"))
                    or _strip(wake_schedule.get("id"))
                    or str(uuid.uuid4()),
                    scheduled_at=_as_utc_naive(wake_schedule.get("scheduled_at")) or _utcnow(),
                    reason=reason,
                    planned_action=_strip(wake_schedule.get("planned_action")) or "emit_message",
                    status=str(wake_schedule.get("status") or "pending"),
                )
            ]
        except Exception:
            return []

    async def _fetch_galaxy_baseline(
        self,
        *,
        active_db: AsyncSession,
        user_id: str,
    ) -> dict | None:
        try:
            from sqlalchemy import select

            from app.models.galaxy import KnowledgeNode, UserNodeStatus

            user_uuid = UUID(str(user_id))
            result = await active_db.execute(
                select(KnowledgeNode.name, UserNodeStatus.mastery_score)
                .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
                .where(UserNodeStatus.user_id == user_uuid)
                .where(UserNodeStatus.mastery_score > 0)
                .order_by(UserNodeStatus.mastery_score.asc())
                .limit(40)
            )
            rows = result.fetchall()
            if not rows:
                return None
            scores = [float(row.mastery_score) for row in rows]
            avg_mastery = sum(scores) / len(scores)
            weak_nodes = [row.name for row in rows if float(row.mastery_score) < 30]
            strong_nodes = [row.name for row in rows if float(row.mastery_score) >= 60]
            return {
                "avg_mastery": round(avg_mastery, 1),
                "weak_nodes": weak_nodes[:10],
                "strong_nodes": strong_nodes[:10],
                "total_nodes_tracked": len(rows),
            }
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to fetch Galaxy baseline: {}", exc)
            return None

    # --- G13: Learning Style Persistence ---
    STRATEGY_PATTERN_WINDOW = 10
    STRATEGY_PATTERN_THRESHOLD = 0.80
    STRATEGY_PATTERN_MIN_ROUNDS = 5

    async def _check_strategy_pattern(
        self,
        *,
        user_id: str,
        conversation_id: str,
        decision: AuroraDecision,
    ) -> None:
        """Detect repeated strategy flags in recent telemetry and submit a confirmed claim."""
        if self.redis is None:
            return
        strategy = (decision.harness_updates or {}).get("strategy")
        if not isinstance(strategy, Mapping):
            return
        try:
            telemetry_service = AuroraDecisionTelemetryService(None, redis_client=self.redis)
            key = telemetry_service.recent_telemetry_key(user_id=user_id, conversation_id=conversation_id)
            raw_items = await telemetry_service._redis_call("lrange", key, 0, self.STRATEGY_PATTERN_WINDOW - 1)
        except Exception as exc:
            logger.warning("Aurora G13 strategy pattern read failed for user {}: {}", user_id, exc)
            return

        records: list[dict[str, Any]] = []
        for item in raw_items or []:
            if isinstance(item, bytes):
                item = item.decode("utf-8")
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except (json.JSONDecodeError, ValueError):
                    continue
            if isinstance(item, Mapping):
                records.append(dict(item))

        if len(records) < self.STRATEGY_PATTERN_MIN_ROUNDS:
            return

        tracked_strategy_flags = tuple(
            flag_name
            for flag_name, default_value in AuroraTeachingStrategy().model_dump(mode="python").items()
            if default_value is False and flag_name in STRATEGY_FIELDS
        )

        flag_counts: dict[str, int] = {}
        for record in records:
            payload = record.get("strategy_payload")
            if not isinstance(payload, Mapping):
                continue
            for flag_name in tracked_strategy_flags:
                if bool(payload.get(flag_name)):
                    flag_counts[flag_name] = flag_counts.get(flag_name, 0) + 1

        total = len(records)
        for flag_name, count in flag_counts.items():
            if count / total >= self.STRATEGY_PATTERN_THRESHOLD:
                claim = InferenceClaim(
                    user_id=user_id,
                    domain="preferred_strategy",
                    evidence_type="repeated_strategy_flag",
                    value=flag_name,
                    confidence=0.85,
                    status="confirmed",
                    needs_confirmation=False,
                    evidence=[
                        f"Strategy flag {flag_name}=True appeared in {count}/{total} recent telemetry turns (>=80%)."
                    ],
                    source="aurora_runtime_v1_g13",
                )
                try:
                    await write_pipeline.submit_claim(claim, redis=self.redis)
                except Exception as exc:
                    logger.warning(
                        "Aurora G13 failed to submit preferred_strategy claim for user {}: {}",
                        user_id,
                        exc,
                    )

    def _intent_type_from_decision(self, decision: AuroraDecision, plan: AuroraRuntimeTurnPlan) -> str:
        if decision.action == "drop_thread":
            return "drop_thread"
        if decision.action == "soft_return_topic":
            return "soft_return"
        if decision.action == "schedule_wake":
            return "schedule_follow_up"
        if decision.action == "wait":
            return "wait"
        if plan.surface_complete:
            return "confirm_understanding"
        return "pursue_tension"
