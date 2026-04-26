from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.runtime_v1.persistence import AuroraPersistenceStore
from app.aurora.runtime_v1.state import (
    ActivityProfile as PersistedActivityProfile,
)
from app.aurora.runtime_v1.state import (
    AuroraTeachingStrategy as PersistedTeachingStrategy,
)
from app.aurora.runtime_v1.state import (
    AuroraIntent as PersistedAuroraIntent,
)
from app.aurora.runtime_v1.state import (
    AuroraState as PersistedAuroraState,
)
from app.aurora.runtime_v1.state import (
    InformationalTension as PersistedInformationalTension,
)
from app.aurora.runtime_v1.state import (
    LatentThread as PersistedLatentThread,
)
from app.aurora.runtime_v1.state import default_activity_expression, merge_expression_settings

AURORA_PLANNING_SURFACE = "aurora_planning"
AURORA_RUNTIME_TTL_SECONDS = 24 * 60 * 60
AURORA_SURFACE_INDEX_TTL_SECONDS = 24 * 60 * 60
AURORA_RUNTIME_KEY_TEMPLATE = "aurora:runtime:{user_id}:{surface}:{conversation_id}"
AURORA_SURFACE_INDEX_KEY_TEMPLATE = "aurora:surface-index:{user_id}"
AURORA_MODELING_METADATA_KEYS = (
    "aurora_surface",
    "aurora_runtime_enabled",
    "surface_complete",
    "modeling_complete",
)
REQUIRED_PLANNING_FIELDS = ("exam_scope", "knowledge_baseline", "time_available")
TENSION_FIELD_MAP = {
    "exam_scope": "exam_scope",
    "knowledge_baseline": "knowledge_baseline",
    "time_available": "time_available",
    "motivation": "motivation_context",
}
_TENSION_PROMPT_REGISTRY: dict[str, str] = {
    "exam_scope": "这次更具体考哪些范围？如果你手上有教材目录、老师画的重点或真题来源，也可以一起告诉我。",
    "knowledge_baseline": "你现在对这门课的基础大概在哪个位置？比如完全没学过、上过课但没复习，或者已经能讲清一部分核心内容。",
    "time_available": "接下来这几天你每天大概能投入多少时间？有没有哪几天会明显更忙、需要我主动避开？",
    "motivation": "最后一个问题：这次考试对你来说意味着什么？是一定要过还是想尽量考高分？",
}
_DEFAULT_TENSION_PROMPT = "我还差一块关键信息，方便你再补一句吗？"
_TENSION_DOMAIN_ALIASES = {
    "scope": "exam_scope",
    "baseline": "knowledge_baseline",
    "time": "time_available",
    "motivation_context": "motivation",
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if value in (None, "", (), []):
        return []
    return [value]


def _coerce_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = _strip(value)
    return text or None


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _default_strategy_payload() -> dict[str, bool]:
    return PersistedTeachingStrategy().model_dump(mode="python")


def _normalize_strategy_payload(value: Any, *, include_defaults: bool) -> dict[str, bool]:
    if not isinstance(value, dict):
        return _default_strategy_payload() if include_defaults else {}
    strategy = PersistedTeachingStrategy.model_validate(value)
    return strategy.model_dump(mode="python", exclude_unset=not include_defaults)


def _merge_strategy_payload(current: dict[str, bool] | None, updates: Any) -> dict[str, bool]:
    merged = _default_strategy_payload()
    if isinstance(current, dict):
        merged.update(_normalize_strategy_payload(current, include_defaults=False))
    merged.update(_normalize_strategy_payload(updates, include_defaults=False))
    return merged


def _serialize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def get_tension_prompt(domain: str) -> str:
    normalized = _strip(domain)
    registry_key = normalized if normalized in _TENSION_PROMPT_REGISTRY else _TENSION_DOMAIN_ALIASES.get(normalized)
    if registry_key:
        return _TENSION_PROMPT_REGISTRY.get(registry_key, _DEFAULT_TENSION_PROMPT)
    return _DEFAULT_TENSION_PROMPT


_TENSION_IMPORTANCE: dict[str, str] = {
    "exam_scope": "决定任务分解粒度——不知道考什么就无法生成有效计划",
    "knowledge_baseline": "决定起点和难度梯度——高估或低估都会造成计划不可执行",
    "time_available": "决定密度和取舍策略——时间约束直接决定 seven_day_survival 模式是否激活",
    "motivation": "决定干预语言和策略——为什么做决定了 AI 如何调整节奏和语气",
}
_ZERO_BASELINE_MARKERS = ("完全没学过", "没学过", "零基础", "完全不会", "zero")
_UNCERTAIN_BASELINE_MARKERS = ("不太会", "不太懂", "薄弱", "有点虚", "学了一点", "会一点")
_SCOPE_TOPIC_MARKERS = ("传输层", "网络层", "应用层", "数据链路层", "物理层", "TCP", "UDP", "路由", "子网")


def _importance_tail(domain: str) -> str:
    reasoning = _strip(_TENSION_IMPORTANCE.get(domain))
    if not reasoning:
        return ""
    return _strip(reasoning.split("——", 1)[-1])


def _has_any_marker(value: Any, markers: tuple[str, ...]) -> bool:
    text = _strip(value).lower()
    return any(marker.lower() in text for marker in markers)


@dataclass
class AuroraTension:
    tension_id: str
    domain: str
    description: str
    priority: float
    status: str = "open"
    evidence: list[str] = field(default_factory=list)
    importance_reasoning: str | None = None
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    last_attempted_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AuroraTension:
        return cls(
            tension_id=_strip(payload.get("tension_id")) or f"tension-{uuid.uuid4()}",
            domain=_strip(payload.get("domain")),
            description=_strip(payload.get("description")),
            priority=float(payload.get("priority") or 0.0),
            status=_strip(payload.get("status")) or "open",
            evidence=[_strip(item) for item in list(payload.get("evidence") or []) if _strip(item)],
            importance_reasoning=_strip(payload.get("importance_reasoning")) or None,
            created_at=_strip(payload.get("created_at")) or _utcnow().isoformat(),
            last_attempted_at=_coerce_iso(payload.get("last_attempted_at")),
        )


@dataclass
class AuroraLatentThread:
    thread_id: str
    source_intent: dict[str, Any]
    tension_links: list[str]
    salience: float
    context_snapshot: str
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AuroraLatentThread:
        return cls(
            thread_id=_strip(payload.get("thread_id")) or f"thread-{uuid.uuid4()}",
            source_intent=_as_dict(payload.get("source_intent")),
            tension_links=[_strip(item) for item in list(payload.get("tension_links") or []) if _strip(item)],
            salience=float(payload.get("salience") or 0.0),
            context_snapshot=_strip(payload.get("context_snapshot")),
            created_at=_strip(payload.get("created_at")) or _utcnow().isoformat(),
            status=_strip(payload.get("status")) or "active",
        )


@dataclass
class AuroraActivityProfile:
    proactive_intensity: float = 0.6
    next_wake_at: str | None = None
    conversation_style: str = "structured"
    expression: dict[str, float] = field(default_factory=default_activity_expression)
    agenda_priority: str | None = None
    task_density_hint: float = 0.7
    strategy: dict[str, bool] = field(default_factory=_default_strategy_payload)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AuroraActivityProfile:
        return cls(
            proactive_intensity=max(0.0, min(1.0, _safe_float(payload.get("proactive_intensity"), 0.6))),
            next_wake_at=_coerce_iso(payload.get("next_wake_at")),
            conversation_style=_strip(payload.get("conversation_style")) or "structured",
            expression=merge_expression_settings(updates=payload.get("expression")),
            agenda_priority=_strip(payload.get("agenda_priority")) or None,
            task_density_hint=max(0.0, min(1.0, _safe_float(payload.get("task_density_hint"), 0.7))),
            strategy=_normalize_strategy_payload(payload.get("strategy"), include_defaults=True),
        )


@dataclass
class AuroraRuntimePlanningState:
    user_id: str
    surface: str
    conversation_id: str
    runtime_session_id: str
    user_model_snapshot: dict[str, Any] = field(default_factory=dict)
    informational_tensions: list[AuroraTension] = field(default_factory=list)
    current_intent: dict[str, Any] | None = None
    latent_threads: list[AuroraLatentThread] = field(default_factory=list)
    activity_profile: AuroraActivityProfile = field(default_factory=AuroraActivityProfile)
    self_scheduled_wakes: list[dict[str, Any]] = field(default_factory=list)
    streaming_status: str = "waiting_user"
    ingress_events: list[dict[str, Any]] = field(default_factory=list)
    last_decision_at: str | None = None
    updated_at: str = field(default_factory=lambda: _utcnow().isoformat())
    planning_session_id: str | None = None
    covered_domains: list[str] = field(default_factory=list)
    missing_domains: list[str] = field(default_factory=list)

    @property
    def cold_start_context(self) -> dict[str, Any]:
        context = self.user_model_snapshot.get("cold_start_context")
        if not isinstance(context, dict):
            context = {}
            self.user_model_snapshot["cold_start_context"] = context
        return context

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["informational_tensions"] = [item.to_dict() for item in self.informational_tensions]
        payload["latent_threads"] = [item.to_dict() for item in self.latent_threads]
        payload["activity_profile"] = self.activity_profile.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AuroraRuntimePlanningState:
        return cls(
            user_id=_strip(payload.get("user_id")),
            surface=_strip(payload.get("surface")) or AURORA_PLANNING_SURFACE,
            conversation_id=_strip(payload.get("conversation_id")),
            runtime_session_id=_strip(payload.get("runtime_session_id")) or str(uuid.uuid4()),
            user_model_snapshot=_as_dict(payload.get("user_model_snapshot")),
            informational_tensions=[
                AuroraTension.from_dict(_as_dict(item)) for item in list(payload.get("informational_tensions") or [])
            ],
            current_intent=_as_dict(payload.get("current_intent")) or None,
            latent_threads=[
                AuroraLatentThread.from_dict(_as_dict(item)) for item in list(payload.get("latent_threads") or [])
            ],
            activity_profile=AuroraActivityProfile.from_dict(_as_dict(payload.get("activity_profile"))),
            self_scheduled_wakes=[_as_dict(item) for item in list(payload.get("self_scheduled_wakes") or [])],
            streaming_status=_strip(payload.get("streaming_status")) or "waiting_user",
            ingress_events=[_as_dict(item) for item in list(payload.get("ingress_events") or [])][-12:],
            last_decision_at=_coerce_iso(payload.get("last_decision_at")),
            updated_at=_strip(payload.get("updated_at")) or _utcnow().isoformat(),
            planning_session_id=_strip(payload.get("planning_session_id")) or None,
            covered_domains=[_strip(item) for item in list(payload.get("covered_domains") or []) if _strip(item)],
            missing_domains=[_strip(item) for item in list(payload.get("missing_domains") or []) if _strip(item)],
        )


class AuroraRuntimePlanningAdapter:
    """Planning-surface Aurora runtime adapter backed by Redis runtime state."""

    surface = AURORA_PLANNING_SURFACE

    def __init__(self, redis_client=None) -> None:
        self.redis = redis_client

    @classmethod
    def runtime_key(cls, *, user_id: str, conversation_id: str, surface: str = AURORA_PLANNING_SURFACE) -> str:
        return AURORA_RUNTIME_KEY_TEMPLATE.format(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
        )

    @classmethod
    def surface_index_key(cls, *, user_id: str) -> str:
        return AURORA_SURFACE_INDEX_KEY_TEMPLATE.format(user_id=user_id)

    async def get_or_create_state(
        self,
        *,
        user_id: str,
        conversation_id: str,
        db: AsyncSession | None = None,
        planning_session_id: str | None = None,
        goal_raw: str | None = None,
        profile_context: dict[str, Any] | None = None,
        collected: dict[str, Any] | None = None,
    ) -> AuroraRuntimePlanningState:
        state = await self.load_state(user_id=user_id, conversation_id=conversation_id, db=db)
        if state is None:
            state = AuroraRuntimePlanningState(
                user_id=user_id,
                surface=self.surface,
                conversation_id=conversation_id,
                runtime_session_id=str(uuid.uuid4()),
            )
        state.planning_session_id = planning_session_id or state.planning_session_id
        self._merge_profile_seed(state, profile_context)
        self._merge_snapshot(state, collected or {}, goal_raw=goal_raw)
        self._recompute_tensions(state)
        await self.save_state(state, db=db)
        return state

    async def load_state(
        self,
        *,
        user_id: str,
        conversation_id: str,
        db: AsyncSession | None = None,
    ) -> AuroraRuntimePlanningState | None:
        if self.redis and user_id and conversation_id:
            raw = await self.redis.get(self.runtime_key(user_id=user_id, conversation_id=conversation_id))
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                try:
                    return AuroraRuntimePlanningState.from_dict(_as_dict(json.loads(raw)))
                except Exception:
                    logger.warning(
                        "Failed to decode Aurora planning runtime state for user=%s conversation=%s",
                        user_id,
                        conversation_id,
                    )

        if db is None:
            return None
        try:
            snapshot = await AuroraPersistenceStore(db, enabled=True).load_cognitive_snapshot(user_id)
        except Exception as exc:
            await db.rollback()
            logger.warning("Failed to load Aurora planning snapshot for user=%s error=%s", user_id, exc)
            return None
        if snapshot is None:
            return None
        return self._state_from_snapshot(snapshot, conversation_id=conversation_id)

    async def save_state(
        self,
        state: AuroraRuntimePlanningState,
        *,
        db: AsyncSession | None = None,
    ) -> None:
        state.updated_at = _utcnow().isoformat()
        if not self.redis:
            if db is not None:
                await self._persist_snapshot(db, state)
            return
        payload = _serialize_payload(state.to_dict())
        await self.redis.setex(
            self.runtime_key(user_id=state.user_id, conversation_id=state.conversation_id, surface=state.surface),
            AURORA_RUNTIME_TTL_SECONDS,
            payload,
        )
        await self.redis.setex(
            self.surface_index_key(user_id=state.user_id),
            AURORA_SURFACE_INDEX_TTL_SECONDS,
            _serialize_payload(
                {
                    "surface": state.surface,
                    "conversation_id": state.conversation_id,
                    "planning_session_id": state.planning_session_id,
                    "updated_at": state.updated_at,
                }
            ),
        )
        if db is not None:
            await self._persist_snapshot(db, state)

    async def sync_session(
        self,
        *,
        state: AuroraRuntimePlanningState,
        db: AsyncSession | None = None,
        planning_session_id: str | None,
        goal_raw: str | None,
        collected: dict[str, Any],
        profile_context: dict[str, Any] | None = None,
    ) -> AuroraRuntimePlanningState:
        state.planning_session_id = planning_session_id or state.planning_session_id
        self._merge_profile_seed(state, profile_context)
        self._merge_snapshot(state, collected, goal_raw=goal_raw)
        self._recompute_tensions(state)
        await self.save_state(state, db=db)
        return state

    async def absorb_user_turn(
        self,
        *,
        state: AuroraRuntimePlanningState,
        db: AsyncSession | None = None,
        message: str,
        extracted_fields: dict[str, Any],
        is_detour: bool,
    ) -> AuroraRuntimePlanningState:
        cleaned_message = _strip(message)
        if cleaned_message:
            state.ingress_events.append(
                {
                    "type": "user_message",
                    "message": cleaned_message,
                    "is_detour": bool(is_detour),
                    "detected_fields": sorted(extracted_fields.keys()),
                    "captured_at": _utcnow().isoformat(),
                }
            )
            state.ingress_events = state.ingress_events[-12:]
        if extracted_fields:
            self._merge_snapshot(state, extracted_fields, goal_raw=None)
        self._recompute_tensions(state)
        self._set_surface_state(
            state,
            {
                "in_detour": bool(is_detour),
                "last_detour_message": cleaned_message if is_detour else None,
            },
        )
        if is_detour:
            self._upsert_latent_thread(state)
            state.current_intent = {
                "intent_type": "answer_detour",
                "target_tension_id": self._top_open_tension(state).tension_id if self._top_open_tension(state) else None,
                "payload": {"message": cleaned_message, "surface_state": self._surface_state(state)},
            }
        else:
            self._resolve_latent_threads(state)
            top_tension = self._top_open_tension(state)
            state.current_intent = {
                "intent_type": "pursue_tension" if top_tension else "wait",
                "target_tension_id": top_tension.tension_id if top_tension else None,
                "payload": {"message": cleaned_message},
            }
        state.last_decision_at = _utcnow().isoformat()
        await self.save_state(state, db=db)
        return state

    async def note_question_asked(
        self,
        *,
        state: AuroraRuntimePlanningState,
        db: AsyncSession | None = None,
        domain: str | None,
    ) -> None:
        if not self._mark_tension_attempted(state, domain):
            return
        state.last_decision_at = _utcnow().isoformat()
        await self.save_state(state, db=db)

    async def apply_detour_decision(
        self,
        *,
        state: AuroraRuntimePlanningState,
        action: str,
        chat_directive: dict[str, Any] | None = None,
        harness_updates: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
    ) -> AuroraRuntimePlanningState:
        directive = _as_dict(chat_directive)
        normalized_action = _strip(action) or "wait"
        target_tension = self._resolve_target_tension(state, directive)
        now = _utcnow().isoformat()

        self._apply_activity_updates(state.activity_profile, _as_dict(harness_updates))

        if normalized_action == "soft_return_topic":
            self._mark_tension_attempted(state, target_tension.domain if target_tension else directive.get("target_domain"))
            self._set_surface_state(state, {"in_detour": False})
            state.current_intent = {
                "intent_type": "soft_return",
                "target_tension_id": target_tension.tension_id if target_tension else None,
                "payload": directive,
            }
        elif normalized_action == "drop_thread":
            self._drop_latent_threads(state, target_tension_id=target_tension.tension_id if target_tension else None)
            self._set_surface_state(state, {"in_detour": False})
            state.current_intent = {
                "intent_type": "drop_thread",
                "target_tension_id": target_tension.tension_id if target_tension else None,
                "payload": directive,
            }
        else:
            state.current_intent = {
                "intent_type": "wait",
                "target_tension_id": target_tension.tension_id if target_tension else None,
                "payload": directive,
            }
        state.last_decision_at = now
        await self.save_state(state, db=db)
        return state

    async def update_activity_profile(
        self,
        *,
        state: AuroraRuntimePlanningState,
        db: AsyncSession | None = None,
        updates: dict[str, Any],
    ) -> AuroraRuntimePlanningState:
        profile = state.activity_profile
        if "proactive_intensity" in updates:
            profile.proactive_intensity = max(0.0, min(1.0, _safe_float(updates.get("proactive_intensity"), profile.proactive_intensity)))
        if "next_wake_at" in updates:
            profile.next_wake_at = _coerce_iso(updates.get("next_wake_at"))
        if _strip(updates.get("conversation_style")):
            profile.conversation_style = _strip(updates.get("conversation_style"))
        if isinstance(updates.get("expression"), dict):
            profile.expression = merge_expression_settings(profile.expression, updates.get("expression"))
        if "agenda_priority" in updates:
            profile.agenda_priority = _strip(updates.get("agenda_priority")) or None
        if "task_density_hint" in updates:
            profile.task_density_hint = max(0.0, min(1.0, _safe_float(updates.get("task_density_hint"), profile.task_density_hint)))
        if "strategy" in updates:
            profile.strategy = _merge_strategy_payload(profile.strategy, updates.get("strategy"))
        await self.save_state(state, db=db)
        return state

    def select_next_tension(self, state: AuroraRuntimePlanningState) -> AuroraTension | None:
        candidates = [item for item in state.informational_tensions if item.status in {"open", "partially_resolved"}]
        if not candidates:
            return None

        def sort_key(item: AuroraTension) -> tuple[float, float]:
            attempted_at = item.last_attempted_at or ""
            freshness_penalty = 0.06 if attempted_at else 0.0
            latent_boost = 0.05 if any(item.tension_id in thread.tension_links for thread in state.latent_threads if thread.status == "active") else 0.0
            return (item.priority - freshness_penalty + latent_boost, item.created_at != "")

        return max(candidates, key=sort_key)

    def build_next_prompt(self, state: AuroraRuntimePlanningState) -> tuple[str, str | None]:
        first_question = self._build_first_question(state)
        if first_question is not None:
            return first_question

        tension = self.select_next_tension(state)
        if tension is None:
            return "我已经拿到够用的信息了，你如果愿意，我现在就把最关键的瓶颈和推进策略整理出来。", None
        return self._contextual_tension_prompt(tension.domain, state), tension.domain

    def _build_first_question(self, state: AuroraRuntimePlanningState) -> tuple[str, str | None] | None:
        snapshot = _as_dict(state.user_model_snapshot)
        sprint_pack_id = _strip(snapshot.get("sprint_pack_id"))
        if not sprint_pack_id:
            return None
        if any(item.last_attempted_at for item in state.informational_tensions):
            return None

        subject = _strip(snapshot.get("sprint_pack_subject") or snapshot.get("subject") or snapshot.get("exam_scope"))
        subject_clause = (
            f"我先按【{subject}】冲刺来处理，范围用内置 Sprint Pack 兜底。"
            if subject
            else "我先按这次考试冲刺来处理，范围用内置 Sprint Pack 兜底。"
        )
        if not _strip(snapshot.get("knowledge_baseline")):
            return (
                f"{subject_clause}你目前大概在哪个水平：完全没学过、上过课但没复习，还是已经学过一部分？",
                "knowledge_baseline",
            )
        if not _strip(snapshot.get("time_available")):
            return (
                f"{subject_clause}接下来这几天你每天大概能投入多少时间？",
                "time_available",
            )
        return None

    def _contextual_tension_prompt(self, domain: str, state: AuroraRuntimePlanningState) -> str:
        snapshot = _as_dict(state.user_model_snapshot)
        subject = _strip(snapshot.get("subject") or "这门课")
        scope = self._scope_phrase(snapshot)
        baseline = _strip(snapshot.get("knowledge_baseline"))
        goal = _strip(snapshot.get("goal_raw"))

        if domain == "exam_scope":
            if _has_any_marker(baseline, _ZERO_BASELINE_MARKERS):
                return f"好，零基础先别急着铺满全书。{subject}这次主要考哪几块？章节、题型或老师画过的重点都可以。"
            return f"{subject}这门课，最让你头疼的是哪部分？如果你已经知道考试范围，也可以直接说章节或题型。"
        if domain == "knowledge_baseline":
            if _has_any_marker(goal, _UNCERTAIN_BASELINE_MARKERS):
                return "大概是完全没接触过，还是学了一点点但串不起来？"
            if scope:
                return f"{scope}这几块里，你更像完全没接触过，还是上过课但现在不稳？"
            return get_tension_prompt(domain)
        if domain == "time_available":
            if _has_any_marker(baseline, _ZERO_BASELINE_MARKERS):
                scope_part = f"先围绕{scope}" if scope else "先按最核心范围"
                return f"好，零基础的话，咱们{scope_part}排一个保底节奏。接下来这几天你每天大概能投入多少时间？有没有哪天会特别忙？"
            if scope:
                return f"好，范围先按{scope}来抓。接下来这几天你每天大概能投入多少时间？有没有哪天会特别忙？"
            return get_tension_prompt(domain)
        if domain == "motivation":
            return get_tension_prompt(domain)
        return get_tension_prompt(domain)

    def _scope_phrase(self, snapshot: dict[str, Any]) -> str:
        raw_scope = _strip(snapshot.get("exam_scope") or snapshot.get("subject"))
        if not raw_scope:
            return ""
        topics = [marker for marker in _SCOPE_TOPIC_MARKERS if marker.lower() in raw_scope.lower()]
        if topics:
            return "、".join(dict.fromkeys(topics))
        return raw_scope[:40]

    def build_detour_prompt(self, state: AuroraRuntimePlanningState) -> str:
        """Returns empty string — detour context is conveyed via build_detour_scaffold(), not sidecar prompts."""
        return ""

    def build_detour_scaffold(self, state: AuroraRuntimePlanningState) -> dict[str, Any]:
        top_thread = self._top_active_thread(state)
        top_tension = self.select_next_tension(state)
        open_tensions = [
            {
                "tension_id": item.tension_id,
                "domain": item.domain,
                "description": item.description,
                "priority": round(item.priority, 3),
                "status": item.status,
                "last_attempted_at": item.last_attempted_at,
            }
            for item in state.informational_tensions
            if item.status in {"open", "partially_resolved"}
        ]
        latent_threads = [
            {
                "thread_id": item.thread_id,
                "source_intent": dict(item.source_intent or {}),
                "tension_links": list(item.tension_links),
                "salience": round(item.salience, 3),
                "context_snapshot": item.context_snapshot,
                "status": item.status,
            }
            for item in state.latent_threads
            if item.status == "active"
        ]
        return {
            "surface": state.surface,
            "surface_state": self._surface_state(state),
            "planning_session_id": state.planning_session_id,
            "goal_raw": _strip(state.user_model_snapshot.get("goal_raw")) or "帮助用户完成当前规划",
            "activity_profile": state.activity_profile.to_dict(),
            "current_intent": dict(state.current_intent or {}),
            "resolved_facts": self._resolved_fact_lines(state),
            "recent_detours": [
                _strip(item.get("message"))
                for item in list(state.ingress_events)[-4:]
                if item.get("is_detour") and _strip(item.get("message"))
            ],
            "open_tensions": open_tensions,
            "top_tension": (
                {
                    "tension_id": top_tension.tension_id,
                    "domain": top_tension.domain,
                    "description": top_tension.description,
                    "priority": round(top_tension.priority, 3),
                    "status": top_tension.status,
                    "last_attempted_at": top_tension.last_attempted_at,
                }
                if top_tension is not None
                else None
            ),
            "latent_threads": latent_threads,
            "top_latent_thread": (
                {
                    "thread_id": top_thread.thread_id,
                    "source_intent": dict(top_thread.source_intent or {}),
                    "tension_links": list(top_thread.tension_links),
                    "salience": round(top_thread.salience, 3),
                    "context_snapshot": top_thread.context_snapshot,
                    "status": top_thread.status,
                }
                if top_thread is not None
                else None
            ),
            "hard_bounds": _as_dict(state.user_model_snapshot.get("aurora_hard_bounds")),
            "detour_instruction": (
                "Treat this as state context, not final user wording. "
                "The DecisionLoop should decide whether to follow the detour or gently return to the agenda."
                if self._surface_state(state).get("in_detour")
                else None
            ),
        }

    def build_strategy_brief(self, state: AuroraRuntimePlanningState) -> dict[str, Any]:
        open_tensions = [
            {
                "domain": item.domain,
                "description": item.description,
                "priority": round(item.priority, 2),
            }
            for item in state.informational_tensions
            if item.status in {"open", "partially_resolved"}
        ]
        latent_threads = [
            {
                "thread_id": item.thread_id,
                "salience": round(item.salience, 2),
                "context_snapshot": item.context_snapshot,
            }
            for item in state.latent_threads
            if item.status == "active"
        ]
        snapshot = _as_dict(state.user_model_snapshot)
        return {
            "goal_raw": _strip(snapshot.get("goal_raw")),
            "blocked_days": _as_list(snapshot.get("blocked_days")),
            "available_materials": _as_list(snapshot.get("available_materials")),
            "recent_detours": [
                _strip(item.get("message"))
                for item in list(state.ingress_events)[-4:]
                if item.get("is_detour")
            ],
            "open_tensions": open_tensions,
            "latent_threads": latent_threads,
            "activity_profile": state.activity_profile.to_dict(),
        }

    def build_response_metadata(
        self,
        state: AuroraRuntimePlanningState,
        *,
        surface_complete: bool,
    ) -> dict[str, Any]:
        metadata = {
            "aurora_surface": state.surface,
            "aurora_runtime_enabled": True,
            "surface_complete": bool(surface_complete),
            "modeling_complete": bool(state.user_model_snapshot.get("modeling_complete")),
        }
        return {key: metadata[key] for key in AURORA_MODELING_METADATA_KEYS}

    def _merge_profile_seed(self, state: AuroraRuntimePlanningState, profile_context: dict[str, Any] | None) -> None:
        profile = _as_dict(profile_context)
        prefs = _as_dict(profile.get("preferences"))
        cold_start = _as_dict(prefs.get("cold_start_context"))
        modeling_state = _as_dict(prefs.get("onboarding_modeling_state"))
        aurora_prefs = _as_dict(prefs.get("aurora_preferences"))
        seed = {
            "goal_raw": _strip(cold_start.get("primary_goal_description")),
            "exam_scope": _strip(cold_start.get("exam_scope") or cold_start.get("subject")),
            "knowledge_baseline": _strip(cold_start.get("knowledge_baseline")),
            "time_available": self._format_time_available(cold_start),
            "daily_available_hours": _safe_int(cold_start.get("daily_available_hours")),
            "blocked_days": _as_list(cold_start.get("blocked_days")),
            "available_materials": _as_list(cold_start.get("available_materials")),
            "subject": _strip(cold_start.get("subject")),
            "time_constraint_days": _safe_int(cold_start.get("time_constraint_days")),
            "previous_exam_weak_nodes": _as_list(cold_start.get("previous_exam_weak_nodes")),
            "motivation_context": _strip(
                cold_start.get("motivation_context")
                or cold_start.get("motivation")
                or cold_start.get("goal_motivation")
            ),
            "sprint_pack_id": _strip(cold_start.get("sprint_pack_id")),
            "sprint_pack_subject": _strip(cold_start.get("sprint_pack_subject")),
            "pre_filled_domain_hints": _as_list(cold_start.get("pre_filled_domain_hints")),
            "fast_track_exam_sprint": bool(cold_start.get("fast_track_exam_sprint")),
            "modeling_complete": bool(modeling_state.get("completed")),
            "aurora_hard_bounds": {
                "dnd_windows": _as_list(aurora_prefs.get("dnd_windows")),
                "privacy_boundaries": _as_list(aurora_prefs.get("privacy_boundaries")),
                "disabled_actions": _as_list(aurora_prefs.get("disabled_actions")),
            },
        }
        self._merge_snapshot(state, seed, goal_raw=None)

    def _merge_snapshot(
        self,
        state: AuroraRuntimePlanningState,
        values: dict[str, Any],
        *,
        goal_raw: str | None,
    ) -> None:
        snapshot = dict(state.user_model_snapshot or {})
        if goal_raw:
            snapshot["goal_raw"] = _strip(goal_raw)
        for key, value in values.items():
            if key == "aurora_hard_bounds":
                if isinstance(value, dict):
                    snapshot["aurora_hard_bounds"] = {
                        **_as_dict(snapshot.get("aurora_hard_bounds")),
                        **_as_dict(value),
                    }
                continue
            if key == "surface_state":
                if isinstance(value, dict):
                    snapshot["surface_state"] = {
                        **_as_dict(snapshot.get("surface_state")),
                        **_as_dict(value),
                    }
                continue
            if value in (None, "", [], {}):
                continue
            snapshot[key] = value
            if key == "previous_exam_weak_nodes":
                cold_start = _as_dict(snapshot.get("cold_start_context"))
                cold_start["previous_exam_weak_nodes"] = _as_list(value)
                snapshot["cold_start_context"] = cold_start
        state.user_model_snapshot = snapshot

    def _surface_state(self, state: AuroraRuntimePlanningState) -> dict[str, Any]:
        return _as_dict(_as_dict(state.user_model_snapshot).get("surface_state"))

    def _set_surface_state(self, state: AuroraRuntimePlanningState, updates: dict[str, Any]) -> None:
        snapshot = dict(state.user_model_snapshot or {})
        surface_state = _as_dict(snapshot.get("surface_state"))
        for key, value in updates.items():
            if value is None:
                surface_state.pop(key, None)
            else:
                surface_state[key] = value
        snapshot["surface_state"] = surface_state
        state.user_model_snapshot = snapshot

    def _recompute_tensions(self, state: AuroraRuntimePlanningState) -> None:
        snapshot = _as_dict(state.user_model_snapshot)
        hard_bounds = _as_dict(snapshot.get("aurora_hard_bounds"))
        privacy_boundaries = {item.strip() for item in _as_list(hard_bounds.get("privacy_boundaries")) if _strip(item)}
        existing = {item.domain: item for item in state.informational_tensions}
        rebuilt: list[AuroraTension] = []
        for domain, field_name in TENSION_FIELD_MAP.items():
            current = existing.get(domain)
            field_value = snapshot.get(field_name)
            if current is None:
                current = AuroraTension(
                    tension_id=f"{domain}:{uuid.uuid4()}",
                    domain=domain,
                    description=self._describe_tension(domain, snapshot),
                    priority=0.0,
                )
            current.description = self._describe_tension(domain, snapshot)
            current.importance_reasoning = _TENSION_IMPORTANCE.get(domain)
            current.priority = self._priority_for_domain(domain, snapshot, state)
            if domain in privacy_boundaries:
                current.status = "dropped"
            elif field_value not in (None, "", [], {}):
                current.status = "resolved"
                current.evidence = [self._summarize_field(field_name, field_value)]
            else:
                current.status = "open"
            rebuilt.append(current)
        state.informational_tensions = rebuilt
        state.covered_domains = [item.domain for item in rebuilt if item.status == "resolved"]
        state.missing_domains = [item.domain for item in rebuilt if item.status in {"open", "partially_resolved"}]
        state.activity_profile.agenda_priority = self.select_next_tension(state).domain if self.select_next_tension(state) else None
        state.activity_profile.conversation_style = state.activity_profile.conversation_style or "structured"

    def _priority_for_domain(
        self,
        domain: str,
        snapshot: dict[str, Any],
        state: AuroraRuntimePlanningState,
    ) -> float:
        base = {
            "exam_scope": 0.78,
            "knowledge_baseline": 0.74,
            "time_available": 0.70,
            "motivation": 0.52,
        }.get(domain, 0.65)
        days = _safe_int(snapshot.get("time_constraint_days")) or 7
        hours = _safe_int(snapshot.get("daily_available_hours")) or 0
        if domain == "knowledge_baseline" and days <= 3:
            base += 0.15
        if domain == "time_available" and hours <= 1:
            base += 0.12
        if domain == "exam_scope" and (_strip(snapshot.get("subject")) or _as_list(snapshot.get("available_materials"))):
            base += 0.05
        if domain == "motivation" and set(REQUIRED_PLANNING_FIELDS).issubset(
            {field_name for field_name in REQUIRED_PLANNING_FIELDS if snapshot.get(field_name) not in (None, "", [], {})}
        ):
            base += 0.12
        if any(domain == thread.source_intent.get("target_domain") for thread in state.latent_threads if thread.status == "active"):
            base += 0.04
        return max(0.0, min(1.0, round(base, 3)))

    def _describe_tension(self, domain: str, snapshot: dict[str, Any]) -> str:
        subject = _strip(snapshot.get("subject") or "这次规划")
        reason = _importance_tail(domain)
        if domain == "exam_scope":
            return f"{subject}具体抓哪些章节或题型？我先问这个，是因为{reason}。"
        if domain == "knowledge_baseline":
            return f"{subject}你现在是完全没接触，还是学过一点但不稳？我先校准起点，是因为{reason}。"
        if domain == "time_available":
            return f"接下来几天每天大概能拿出多久？我先对齐时间，是因为{reason}。"
        if domain == "motivation":
            return f"{subject}这次更像必须过线，还是想尽量冲高分？我先问动机，是因为{reason}。"
        return "还有一块信息缺口没闭合：你愿意先补哪句最影响计划的话？"

    def _upsert_latent_thread(self, state: AuroraRuntimePlanningState) -> None:
        top_tension = self.select_next_tension(state)
        if top_tension is None:
            return
        context_snapshot = self._thread_context_snapshot(state, top_tension)
        for thread in state.latent_threads:
            if top_tension.tension_id in thread.tension_links and thread.status == "active":
                thread.salience = max(thread.salience, top_tension.priority)
                thread.context_snapshot = context_snapshot
                thread.source_intent = {
                    "intent_type": "soft_return",
                    "target_tension_id": top_tension.tension_id,
                    "target_domain": top_tension.domain,
                }
                return
        state.latent_threads.append(
            AuroraLatentThread(
                thread_id=f"thread-{uuid.uuid4()}",
                source_intent={
                    "intent_type": "soft_return",
                    "target_tension_id": top_tension.tension_id,
                    "target_domain": top_tension.domain,
                },
                tension_links=[top_tension.tension_id],
                salience=top_tension.priority,
                context_snapshot=context_snapshot,
            )
        )
        state.latent_threads = state.latent_threads[-6:]

    def _resolve_latent_threads(self, state: AuroraRuntimePlanningState) -> None:
        resolved_tension_ids = {
            item.tension_id for item in state.informational_tensions if item.status == "resolved"
        }
        for thread in state.latent_threads:
            if resolved_tension_ids.intersection(thread.tension_links):
                thread.status = "resolved"

    @staticmethod
    def _apply_activity_updates(profile: AuroraActivityProfile, updates: dict[str, Any]) -> None:
        if "proactive_intensity" in updates:
            profile.proactive_intensity = max(0.0, min(1.0, _safe_float(updates.get("proactive_intensity"), profile.proactive_intensity)))
        if "next_wake_at" in updates:
            profile.next_wake_at = _coerce_iso(updates.get("next_wake_at"))
        if _strip(updates.get("conversation_style")):
            profile.conversation_style = _strip(updates.get("conversation_style"))
        if isinstance(updates.get("expression"), dict):
            profile.expression = merge_expression_settings(profile.expression, updates.get("expression"))
        if "agenda_priority" in updates:
            profile.agenda_priority = _strip(updates.get("agenda_priority")) or None
        if "task_density_hint" in updates:
            profile.task_density_hint = max(0.0, min(1.0, _safe_float(updates.get("task_density_hint"), profile.task_density_hint)))
        if "strategy" in updates:
            profile.strategy = _merge_strategy_payload(profile.strategy, updates.get("strategy"))

    def _mark_tension_attempted(self, state: AuroraRuntimePlanningState, domain: str | None) -> bool:
        normalized_domain = _strip(domain)
        if not normalized_domain:
            return False
        now = _utcnow().isoformat()
        updated = False
        for tension in state.informational_tensions:
            if tension.domain == normalized_domain and tension.status in {"open", "partially_resolved"}:
                tension.last_attempted_at = now
                updated = True
        return updated

    def _resolve_target_tension(
        self,
        state: AuroraRuntimePlanningState,
        directive: dict[str, Any],
    ) -> AuroraTension | None:
        target_tension_id = _strip(directive.get("target_tension_id"))
        if target_tension_id:
            for tension in state.informational_tensions:
                if tension.tension_id == target_tension_id:
                    return tension

        target_domain = _strip(directive.get("target_domain"))
        if target_domain:
            for tension in state.informational_tensions:
                if tension.domain == target_domain and tension.status in {"open", "partially_resolved"}:
                    return tension
        return self._top_open_tension(state)

    def _drop_latent_threads(self, state: AuroraRuntimePlanningState, *, target_tension_id: str | None) -> None:
        for thread in state.latent_threads:
            if thread.status != "active":
                continue
            if target_tension_id and target_tension_id not in thread.tension_links:
                continue
            thread.status = "dropped"

    def _top_open_tension(self, state: AuroraRuntimePlanningState) -> AuroraTension | None:
        return self.select_next_tension(state)

    def _top_active_thread(self, state: AuroraRuntimePlanningState) -> AuroraLatentThread | None:
        active = [item for item in state.latent_threads if item.status == "active"]
        if not active:
            return None
        return max(active, key=lambda item: item.salience)

    def _thread_context_snapshot(self, state: AuroraRuntimePlanningState, tension: AuroraTension) -> str:
        snapshot = _as_dict(state.user_model_snapshot)
        goal = _strip(snapshot.get("goal_raw"))
        known = ", ".join(self._resolved_fact_lines(state)[:2])
        prefix = f"目标是 {goal}。" if goal else ""
        suffix = f"已知信息：{known}。" if known else ""
        return f"{prefix} 当前还缺 {tension.domain}，{tension.description} {suffix}".strip()

    def _resolved_fact_lines(self, state: AuroraRuntimePlanningState) -> list[str]:
        snapshot = _as_dict(state.user_model_snapshot)
        lines: list[str] = []
        for key, label in (
            ("exam_scope", "考试范围"),
            ("knowledge_baseline", "当前基础"),
            ("time_available", "可投入时间"),
            ("motivation_context", "动机"),
            ("blocked_days", "忙碌时段"),
            ("available_materials", "现有资料"),
        ):
            value = snapshot.get(key)
            if value in (None, "", [], {}):
                continue
            if isinstance(value, list):
                rendered = "、".join(_strip(item) for item in value if _strip(item))
            else:
                rendered = _strip(value)
            if rendered:
                lines.append(f"{label}: {rendered}")
        return lines

    @staticmethod
    def _summarize_field(field_name: str, value: Any) -> str:
        if isinstance(value, list):
            rendered = "、".join(_strip(item) for item in value if _strip(item))
        else:
            rendered = _strip(value)
        return f"{field_name}={rendered}"

    @staticmethod
    def _format_time_available(payload: dict[str, Any]) -> str:
        hours = _safe_int(payload.get("daily_available_hours"))
        if hours:
            return f"每天约 {hours} 小时"
        minutes = _safe_int(payload.get("study_time_minutes"))
        if minutes:
            return f"每天约 {minutes} 分钟"
        return ""

    @staticmethod
    def _state_from_snapshot(snapshot: Any, *, conversation_id: str) -> AuroraRuntimePlanningState:
        runtime_session_id = _strip(getattr(snapshot, "last_runtime_session_id", None)) or str(uuid.uuid4())
        return AuroraRuntimePlanningState(
            user_id=_strip(getattr(snapshot, "user_id", "")),
            surface=_strip(getattr(snapshot, "last_surface", None)) or AURORA_PLANNING_SURFACE,
            conversation_id=conversation_id,
            runtime_session_id=runtime_session_id,
            user_model_snapshot=_as_dict(getattr(snapshot, "user_model_snapshot", {})),
            informational_tensions=[
                AuroraTension.from_dict(item.model_dump(mode="json") if hasattr(item, "model_dump") else _as_dict(item))
                for item in list(getattr(snapshot, "informational_tensions", []) or [])
            ],
            current_intent=(
                getattr(snapshot, "current_intent", None).model_dump(mode="json")
                if hasattr(getattr(snapshot, "current_intent", None), "model_dump")
                else _as_dict(getattr(snapshot, "current_intent", None))
                or None
            ),
            latent_threads=[
                AuroraLatentThread.from_dict(item.model_dump(mode="json") if hasattr(item, "model_dump") else _as_dict(item))
                for item in list(getattr(snapshot, "latent_threads", []) or [])
            ],
            activity_profile=AuroraActivityProfile.from_dict(
                getattr(snapshot, "activity_profile", None).model_dump(mode="json")
                if hasattr(getattr(snapshot, "activity_profile", None), "model_dump")
                else _as_dict(getattr(snapshot, "activity_profile", None))
            ),
            last_decision_at=_coerce_iso(getattr(snapshot, "last_decision_at", None)),
            updated_at=_coerce_iso(getattr(snapshot, "updated_at", None)) or _utcnow().isoformat(),
        )

    async def _persist_snapshot(self, db: AsyncSession, state: AuroraRuntimePlanningState) -> None:
        try:
            await AuroraPersistenceStore(db, enabled=True).save_cognitive_snapshot(
                self._to_persisted_state(state),
                metadata=self.build_response_metadata(state, surface_complete=False),
            )
        except Exception as exc:
            await db.rollback()
            logger.warning("Failed to persist Aurora planning snapshot for user=%s error=%s", state.user_id, exc)

    @staticmethod
    def _to_persisted_state(state: AuroraRuntimePlanningState) -> PersistedAuroraState:
        return PersistedAuroraState(
            user_id=state.user_id,
            surface=state.surface,
            conversation_id=state.conversation_id,
            runtime_session_id=state.runtime_session_id,
            user_model_snapshot=dict(state.user_model_snapshot or {}),
            informational_tensions=[
                PersistedInformationalTension.model_validate(item.to_dict()) for item in state.informational_tensions
            ],
            current_intent=PersistedAuroraIntent.model_validate(state.current_intent) if state.current_intent else None,
            latent_threads=[PersistedLatentThread.model_validate(item.to_dict()) for item in state.latent_threads],
            activity_profile=PersistedActivityProfile.model_validate(state.activity_profile.to_dict()),
            streaming_status=state.streaming_status,
            ingress_events=list(state.ingress_events),
            last_decision_at=(
                datetime.fromisoformat(state.last_decision_at) if state.last_decision_at else None
            ),
            updated_at=datetime.fromisoformat(state.updated_at),
        )
