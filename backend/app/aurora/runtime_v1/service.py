from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
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
from app.aurora.runtime_v1.decision_loop import AuroraDecision, AuroraDecisionLoop
from app.aurora.runtime_v1.self_model import SparkleSelfModelService
from app.aurora.runtime_v1.skills import AuroraSkillRegistry
from app.aurora.runtime_v1.state import ActivityProfile, merge_activity_profile_payload
from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
from app.aurora.runtime_v1.wake_policy import AuroraWakePolicyService
from app.aurora.runtime_v1.write_pipeline import InferenceClaim
from app.models.user_preferences import UserPreferencesCenter
from app.sprint_packs.last_24h_mode import (
    apply_last_24h_policy_overrides,
    calculate_days_left,
    extract_exam_date,
    is_last_24h_window,
)

GALAXY_BASELINE_TTL_SECONDS = 300  # 5-min stale-acceptable cache
CHINA_TIMEZONE = timezone(timedelta(hours=8))
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


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed


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


class AuroraRuntimeV1Service:
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
    ):
        self.redis = redis_client
        self.decision_loop = decision_loop or AuroraDecisionLoop()
        self.chat_adapter = chat_adapter or ChatLayerAdapter()
        self.dashboard_builder = dashboard_builder or DashboardReadoutBuilder(redis_client)
        self.self_model_service = self_model_service or SparkleSelfModelService(redis_client)
        self.skill_registry = skill_registry or AuroraSkillRegistry()
        self.wake_policy_service = wake_policy_service or AuroraWakePolicyService(redis_client)

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

        control_surface_reading = await self._read_control_surface(active_db=active_db, user_id=user_id)
        activity_profile = self._build_activity_profile(surface=surface, request_extra_context=request_extra_context)
        activity_profile.update(self._activity_payload(control_surface_reading.adjustable))
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
            await AuroraDecisionTelemetryService(active_db).record_turn(
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
        await self._persist_runtime_state(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
            request_id=request_id,
            user_message=user_message,
            conversation_context=conversation_context,
            user_context_payload=user_context_payload,
            plan=plan,
            decision=decision,
            wake_policy=wake_decision.to_payload(),
        )
        return plan

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
            return await ControlSurfaceService(active_db, self.redis, enabled=True).read_control_surface(user_id)
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
            request_extra_context.get("task_state")
            or user_context_payload.get("task_state")
            or {},
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

    async def _persist_runtime_state(
        self,
        *,
        user_id: str,
        surface: str,
        conversation_id: str,
        request_id: str,
        user_message: str,
        conversation_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        plan: AuroraRuntimeTurnPlan,
        decision: AuroraDecision,
        wake_policy: dict[str, Any],
    ) -> None:
        if self.redis is None:
            return
        runtime_key = AURORA_RUNTIME_STATE_KEY_TEMPLATE.format(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
        )
        profile_context = user_context_payload.get("profile_context")
        if not isinstance(profile_context, dict):
            profile_context = {}

        runtime_state = {
            "user_id": user_id,
            "surface": surface,
            "conversation_id": conversation_id,
            "runtime_session_id": request_id,
            "user_model_snapshot": profile_context,
            "informational_tensions": plan.informational_tensions,
            "current_intent": {
                "intent_type": self._intent_type_from_decision(decision, plan),
                "target_tension_id": plan.activity_profile.get("agenda_priority"),
                "payload": decision.chat_directive,
            },
            "latent_threads": decision.state_updates.get("latent_threads", []),
            "activity_profile": plan.activity_profile,
            "self_scheduled_wakes": [decision.wake_schedule] if decision.wake_schedule else [],
            "streaming_status": "waiting_user",
            "ingress_events": [{"type": "user_message", "content": str(user_message or "")}],
            "last_decision_at": _utcnow().isoformat(),
            "updated_at": _utcnow().isoformat(),
            "messages": plan.messages,
            "hard_boundaries": plan.hard_boundaries,
            "decision": decision.to_payload(),
            "wake_policy": wake_policy,
            "history_size": len(conversation_context.get("messages") or []),
        }
        try:
            await self.redis.setex(
                runtime_key,
                AURORA_RUNTIME_STATE_TTL_SECONDS,
                json.dumps(runtime_state, ensure_ascii=False, default=str),
            )
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to persist Redis runtime state: {}", exc)

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
