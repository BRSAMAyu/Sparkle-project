from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.models.user_preferences import UserPreferencesCenter

GALAXY_BASELINE_TTL_SECONDS = 300  # 5-min stale-acceptable cache

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


@dataclass(slots=True)
class AuroraRuntimeTurnPlan:
    surface: str
    messages: list[str]
    surface_complete: bool
    modeling_complete: bool
    activity_profile: dict[str, Any] = field(default_factory=dict)
    hard_boundaries: dict[str, Any] = field(default_factory=dict)
    informational_tensions: list[dict[str, Any]] = field(default_factory=list)


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
    ):
        self.redis = redis_client
        self.decision_loop = decision_loop or AuroraDecisionLoop()
        self.chat_adapter = chat_adapter or ChatLayerAdapter()
        self.dashboard_builder = dashboard_builder or DashboardReadoutBuilder()
        self.self_model_service = self_model_service or SparkleSelfModelService(redis_client)
        self.skill_registry = skill_registry or AuroraSkillRegistry()

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

        if not request_extra_context.get("galaxy_baseline") and active_db is not None:
            galaxy_baseline = await self._fetch_galaxy_baseline(active_db=active_db, user_id=user_id)
            if galaxy_baseline:
                request_extra_context = {**request_extra_context, "galaxy_baseline": galaxy_baseline}

        control_surface_reading = await self._read_control_surface(active_db=active_db, user_id=user_id)
        activity_profile = self._build_activity_profile(surface=surface, request_extra_context=request_extra_context)
        activity_profile.update(self._activity_payload(control_surface_reading.adjustable))

        candidate_affordances = self.skill_registry.load_candidate_affordances(surface)
        self_model = await self.self_model_service.get_readout_summary(
            user_id=user_id,
            request_extra_context=request_extra_context,
            user_context_payload=user_context_payload,
        )
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
        surface_state = dict(enriched.get("surface_state") or {}) if isinstance(enriched.get("surface_state"), dict) else {}
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

    def _activity_payload(self, profile: ActivityProfile) -> dict[str, Any]:
        default_payload = ActivityProfile().model_dump(mode="python")
        payload = profile.model_dump(mode="python")
        return {
            key: value
            for key, value in payload.items()
            if value not in (None, "") and value != default_payload.get(key)
        }

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

        domain = canonicalize_runtime_domain(updates.get("agenda_priority") or decision.harness_updates.get("agenda_priority"))
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
