from __future__ import annotations

import asyncio
import inspect
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.aurora.runtime_v1.control_surface import AuroraHardBounds, ControlSurfaceReading
from app.aurora.runtime_v1.skills import SkillAffordance
from app.aurora.runtime_v1.state import CORE_MODELING_DOMAINS
from app.aurora.runtime_v1.write_pipeline import AURORA_CLAIM_KEY_TEMPLATE
from app.sprint_packs.sprint_pack_loader import load_pack

REQUIRED_MODELING_DOMAINS: tuple[str, ...] = ("goal", "scope", "baseline", "time")
AURORA_CONFIRMED_WEAK_NODES_CONTEXT_KEY = "_aurora_confirmed_weak_nodes"
AURORA_DEEP_PATTERN_ALERTS_CONTEXT_KEY = "_aurora_deep_pattern_alerts"
AURORA_CONFIRMED_STRATEGY_PREFERENCE_CONTEXT_KEY = "_aurora_confirmed_strategy_preference"
_MISSING = object()

_DOMAIN_IMPORTANCE: dict[str, str] = {
    "goal": "锚定整个规划方向——目标模糊会导致后续所有决策偏移",
    "scope": "决定任务分解粒度——不知道考什么就无法生成有效计划",
    "baseline": "决定起点和难度梯度——高估或低估都会造成计划不可执行",
    "time": "决定密度和取舍策略——时间约束直接决定 seven_day_survival 模式是否激活",
    "motivation": "决定干预语言和策略——为什么做决定了 AI 如何调整节奏和语气",
}

_DOMAIN_ALIASES: dict[str, set[str]] = {
    "goal": {
        "goal",
        "goal_raw",
        "goal_summary",
        "goal_type",
        "objective",
        "target",
        "target_goal",
        "desired_outcome",
        "outcome",
        "motivation_goal",
        "目标",
    },
    "scope": {
        "scope",
        "range",
        "exam_scope",
        "exam_range",
        "subject",
        "subjects",
        "chapter",
        "chapters",
        "topic",
        "topics",
        "coverage",
        "focus_area",
        "focus_areas",
        "material_scope",
        "study_scope",
        "范围",
        "章节",
        "题型",
    },
    "baseline": {
        "baseline",
        "knowledge_baseline",
        "starting_point",
        "current_level",
        "foundation",
        "mastery",
        "familiarity",
        "readiness",
        "skill_level",
        "knowledge_level",
        "weaknesses",
        "strengths",
        "基础",
        "起点",
        "掌握",
    },
    "time": {
        "time",
        "time_available",
        "availability",
        "schedule",
        "deadline",
        "days_remaining",
        "countdown_days",
        "time_constraint_days",
        "daily_available_hours",
        "hours_per_day",
        "available_hours",
        "exam_date",
        "study_window",
        "时间",
        "日程",
    },
    "motivation": {
        "motivation",
        "reason",
        "why",
        "purpose",
        "drive",
        "pressure",
        "motivation_context",
        "goal_motivation",
        "exam_motivation",
        "study_motivation",
        "动机",
        "原因",
        "为什么",
        "目的",
        "压力",
        "重要性",
    },
}

_DOMAIN_TEXT_HINTS: dict[str, tuple[str, ...]] = {
    "goal": (
        "目标",
        "想达到",
        "想要",
        "想考",
        "备考",
        "考试",
        "期末",
        "希望",
        "打算",
        "通过",
        "goal",
        "target",
        "objective",
    ),
    "scope": (
        "范围",
        "章节",
        "题型",
        "考哪些",
        "哪几章",
        "哪些内容",
        "传输层",
        "网络层",
        "应用层",
        "数据链路层",
        "物理层",
        "tcp",
        "udp",
        "路由",
        "子网",
        "拥塞控制",
        "scope",
        "chapter",
        "topic",
    ),
    "baseline": (
        "基础",
        "掌握",
        "学过",
        "没学过",
        "零基础",
        "完全不会",
        "不太会",
        "不太懂",
        "熟悉",
        "会不会",
        "薄弱",
        "baseline",
        "foundation",
        "mastery",
    ),
    "time": ("每天", "几天", "多久", "时间", "日程", "小时", "deadline", "schedule", "available"),
    "motivation": (
        "为什么",
        "为了",
        "动机",
        "原因",
        "不想挂",
        "不挂科",
        "一定要过",
        "想冲",
        "想拿高分",
        "尽量考高分",
        "考高分",
        "探索兴趣",
        "保研",
        "必须过",
        "目的",
        "重要",
        "有意义",
        "motivation",
        "reason",
        "why",
    ),
}

_QUESTION_MARKERS = ("？", "?", "吗", "呢", "多少", "哪些", "哪几", "多久", "几点", "什么", "告诉我")

_PROMPT_CONTEXT_MASK: frozenset[str] = frozenset({"surface", "recently_asked_domains"})

COMPACT_CONTEXT_KEYS: frozenset[str] = frozenset({"user_message", "task_state", "wake_policy"})

_ACTION_CONTEXT_MASK: dict[str, frozenset[str]] = {
    "emit_message": frozenset(
        {
            "user_message",
            "covered_domains",
            "missing_domains",
            "cold_start_context",
            "informational_tensions",
            "social_signals",
            "wake_policy",
            "spine_signals",
        }
    ),
    "wait": frozenset({"user_message", "covered_domains", "missing_domains", "wake_policy"}),
    "schedule_wake": frozenset({"activity_profile", "explicit_user_constraints"}),
    "update_harness": frozenset(
        {
            "user_message",
            "covered_domains",
            "missing_domains",
            "cold_start_context",
            "informational_tensions",
            "activity_profile",
            "explicit_user_constraints",
            "wake_policy",
        }
    ),
    "update_state": frozenset(
        {
            "user_message",
            "covered_domains",
            "missing_domains",
            "cold_start_context",
            "informational_tensions",
            "social_signals",
            "wake_policy",
            "spine_signals",
        }
    ),
    "soft_return_topic": frozenset(
        {
            "user_message",
            "covered_domains",
            "missing_domains",
            "cold_start_context",
            "informational_tensions",
            "social_signals",
            "latent_thread_recovery_candidates",
            "wake_policy",
        }
    ),
    "drop_thread": frozenset(
        {
            "covered_domains",
            "missing_domains",
            "latent_thread_recovery_candidates",
            "wake_policy",
        }
    ),
}

_SURFACE_CONTEXT_ADDITIONS: dict[str, frozenset[str]] = {
    "aurora_checkpoint": frozenset({"checkpoint_state", "sprint_pack_mistakes"}),
    # last_24h_mode is a synthesised flag exposed to the decision loop even when
    # exam_sprint_policy itself is excluded from the planning surface LLM payload.
    "aurora_planning": frozenset({"sprint_policy_summary", "task_state", "last_24h_mode"}),
}

_SURFACE_CONTEXT_EXCLUSIONS: dict[str, frozenset[str]] = {
    "aurora_checkpoint": frozenset(),
    "aurora_modeling": frozenset({"task_state", "checkpoint_state", "exam_sprint_policy", "sprint_policy_summary"}),
    "aurora_planning": frozenset(
        {"cold_start_context", "achievement_signals", "checkpoint_state", "exam_sprint_policy"}
    ),
}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def canonicalize_runtime_domain(value: Any) -> str | None:
    token = _normalize_text(value).lower()
    if not token:
        return None
    normalized = re.sub(r"[\s\-]+", "_", token)
    for canonical, aliases in _DOMAIN_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized


@dataclass(slots=True)
class DashboardReadout:
    """Pre-digested instrument panel for Aurora's LLM decision loop.

    The dashboard is intentionally not a prompt transcript. It is a compact
    control surface: processed state, boundaries, and affordances that let the
    model reason without doing low-level data plumbing.
    """

    surface: str
    user_id: str
    conversation_id: str
    request_id: str
    user_message: str
    activity_profile: dict[str, Any]
    hard_bounds: AuroraHardBounds
    candidate_affordances: list[SkillAffordance] = field(default_factory=list)
    profile_context: dict[str, Any] = field(default_factory=dict)
    cold_start_context: dict[str, Any] = field(default_factory=dict)
    informational_tensions: list[dict[str, Any]] = field(default_factory=list)
    latent_threads: list[dict[str, Any]] = field(default_factory=list)
    covered_domains: list[str] = field(default_factory=list)
    missing_domains: list[str] = field(default_factory=list)
    recently_asked_domains: list[str] = field(default_factory=list)
    sprint_policy_summary: dict[str, Any] = field(default_factory=dict)
    explicit_user_constraints: dict[str, Any] = field(default_factory=dict)
    latent_thread_recovery_candidates: list[dict[str, Any]] = field(default_factory=list)
    conversation_summary: dict[str, Any] = field(default_factory=dict)
    control_surface: dict[str, Any] = field(default_factory=dict)
    exam_sprint_policy: dict[str, Any] = field(default_factory=dict)
    task_state: dict[str, Any] = field(default_factory=dict)
    checkpoint_state: dict[str, Any] = field(default_factory=dict)
    request_extra_context: dict[str, Any] = field(default_factory=dict)
    achievement_signals: dict[str, Any] = field(default_factory=dict)
    self_model: dict[str, Any] = field(default_factory=dict)
    social_signals: dict[str, Any] = field(default_factory=dict)
    wake_policy: dict[str, Any] = field(default_factory=dict)
    # Synthesised convenience flag: True when sprint_mode == "last_24h_cram" or exam_sprint_policy.last_24h_mode.
    # Exposed to the decision loop even for surfaces where exam_sprint_policy is excluded from the LLM payload.
    last_24h_mode: bool = False
    # Spine signals — active directives, risk flags, outcome history from Signal-to-Action Spine
    spine_signals: dict[str, Any] = field(default_factory=dict)

    def to_llm_payload(self, *, action: str | None = None, context_budget: str | None = None) -> dict[str, Any]:
        payload = {
            "surface": self.surface,
            "user_message": self.user_message,
            "activity_profile": self.activity_profile,
            "hard_boundaries": self.hard_bounds.model_dump(mode="json"),
            "candidate_affordances": [affordance.model_dump(mode="json") for affordance in self.candidate_affordances],
            "profile_context": self.profile_context,
            "cold_start_context": self.cold_start_context,
            "informational_tensions": self.informational_tensions,
            "latent_threads": self.latent_threads,
            "covered_domains": self.covered_domains,
            "missing_domains": self.missing_domains,
            "recently_asked_domains": self.recently_asked_domains,
            "sprint_policy_summary": self.sprint_policy_summary,
            "explicit_user_constraints": self.explicit_user_constraints,
            "latent_thread_recovery_candidates": self.latent_thread_recovery_candidates,
            "conversation_summary": self.conversation_summary,
            "control_surface": self.control_surface,
            "exam_sprint_policy": self.exam_sprint_policy,
            "task_state": self.task_state,
            "checkpoint_state": self.checkpoint_state,
            "request_extra_context": self.request_extra_context,
            "achievement_signals": self.achievement_signals,
            "self_model": self.self_model,
            "social_signals": self.social_signals,
            "wake_policy": self.wake_policy,
            "last_24h_mode": self.last_24h_mode,
            "spine_signals": self.spine_signals,
        }
        allowed_keys = self._context_mask_keys(action=action, context_budget=context_budget)
        return {key: value for key, value in payload.items() if key in allowed_keys}

    def _context_mask_keys(self, *, action: str | None, context_budget: str | None = None) -> set[str]:
        normalized_context_budget = str(context_budget or "").strip().lower()
        # G28: compact budget returns the minimal COMPACT_CONTEXT_KEYS set only.
        if normalized_context_budget == "compact":
            return set(COMPACT_CONTEXT_KEYS)
        if action:
            allowed_keys = set(_ACTION_CONTEXT_MASK.get(action, _ACTION_CONTEXT_MASK["emit_message"]))
        else:
            allowed_keys: set[str] = set(_PROMPT_CONTEXT_MASK)
            for keys in _ACTION_CONTEXT_MASK.values():
                allowed_keys.update(keys)
        allowed_keys.update(_SURFACE_CONTEXT_ADDITIONS.get(self.surface, frozenset()))
        allowed_keys.difference_update(_SURFACE_CONTEXT_EXCLUSIONS.get(self.surface, frozenset()))
        return allowed_keys


class DashboardReadoutBuilder:
    def __init__(self, redis_client=None) -> None:
        self.redis = redis_client

    def build(
        self,
        *,
        surface: str,
        user_id: str,
        conversation_id: str,
        request_id: str,
        user_message: str,
        request_extra_context: dict[str, Any],
        conversation_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        control_surface_reading: ControlSurfaceReading,
        activity_profile: dict[str, Any],
        candidate_affordances: list[SkillAffordance],
        self_model: dict[str, Any] | None = None,
        wake_policy: dict[str, Any] | None = None,
    ) -> DashboardReadout:
        profile_context = user_context_payload.get("profile_context")
        if not isinstance(profile_context, dict):
            profile_context = {}

        cold_start_context = self._extract_cold_start_context(
            profile_context,
            user_context_payload,
            user_id=user_id,
        )
        request_cold_start_context = self._as_dict(request_extra_context.get("cold_start_context"))
        if request_cold_start_context:
            cold_start_context = {
                **cold_start_context,
                **request_cold_start_context,
            }
        messages = conversation_context.get("messages")
        if not isinstance(messages, list):
            messages = []
        informational_tensions = self._enrich_tensions_with_importance(
            self._as_list_of_dicts(request_extra_context.get("informational_tensions"))
        )
        latent_threads = self._as_list_of_dicts(request_extra_context.get("latent_threads"))
        exam_sprint_policy = self._as_dict(
            request_extra_context.get("exam_sprint_policy")
            or user_context_payload.get("exam_sprint_policy")
            or user_context_payload.get("sprint_policy")
        )
        task_state = self._as_dict(request_extra_context.get("task_state") or user_context_payload.get("task_state"))
        checkpoint_state = self._as_dict(
            request_extra_context.get("checkpoint_state") or user_context_payload.get("checkpoint_state")
        )
        covered_domains, missing_domains = self._build_domain_coverage(
            surface=surface,
            user_message=user_message,
            messages=messages,
            request_extra_context=request_extra_context,
            user_context_payload=user_context_payload,
            profile_context=profile_context,
            cold_start_context=cold_start_context,
            informational_tensions=informational_tensions,
            exam_sprint_policy=exam_sprint_policy,
            task_state=task_state,
            checkpoint_state=checkpoint_state,
        )
        recently_asked_domains = self._build_recently_asked_domains(
            request_extra_context=request_extra_context,
            messages=messages,
        )
        explicit_user_constraints = self._build_explicit_user_constraints(
            request_extra_context=request_extra_context,
            user_context_payload=user_context_payload,
            profile_context=profile_context,
            control_surface_reading=control_surface_reading,
        )
        latent_thread_recovery_candidates = self._build_latent_thread_recovery_candidates(
            latent_threads=latent_threads,
            covered_domains=covered_domains,
            missing_domains=missing_domains,
            recently_asked_domains=recently_asked_domains,
        )

        achievement_signals = self._extract_achievement_signals(request_extra_context, user_context_payload)
        social_signals = self._extract_social_signals(request_extra_context, user_context_payload)
        last_24h_mode = bool(
            exam_sprint_policy.get("sprint_mode") == "last_24h_cram" or exam_sprint_policy.get("last_24h_mode") is True
        )

        # F18: Auto-load Sprint Pack when goal_type == "exam" and subject is known.
        self._inject_sprint_pack_into_cold_start(cold_start_context)

        # F20: Inject Sprint Pack mistake types into checkpoint_state when sprint_pack_id is present.
        self._inject_sprint_pack_mistakes_into_checkpoint(checkpoint_state)

        return DashboardReadout(
            surface=surface,
            user_id=str(user_id),
            conversation_id=str(conversation_id),
            request_id=str(request_id),
            user_message=str(user_message or ""),
            activity_profile=dict(activity_profile),
            hard_bounds=control_surface_reading.hard_bounds,
            candidate_affordances=list(candidate_affordances),
            profile_context=profile_context,
            cold_start_context=cold_start_context,
            informational_tensions=informational_tensions,
            latent_threads=latent_threads,
            covered_domains=covered_domains,
            missing_domains=missing_domains,
            recently_asked_domains=recently_asked_domains,
            sprint_policy_summary=self._build_sprint_policy_summary(exam_sprint_policy),
            explicit_user_constraints=explicit_user_constraints,
            latent_thread_recovery_candidates=latent_thread_recovery_candidates,
            conversation_summary={
                "message_count": len(messages),
                "recent_messages": messages[-6:],
            },
            control_surface={
                "runtime_enabled": control_surface_reading.runtime_enabled,
                "adjustable": control_surface_reading.adjustable.model_dump(mode="json"),
            },
            exam_sprint_policy=exam_sprint_policy,
            task_state=task_state,
            checkpoint_state=checkpoint_state,
            request_extra_context=dict(request_extra_context),
            achievement_signals=achievement_signals,
            self_model=dict(self_model or {}),
            social_signals=social_signals,
            wake_policy=dict(wake_policy or {}),
            last_24h_mode=last_24h_mode,
            spine_signals=dict(request_extra_context.get("spine_signals") or {}),
        )

    def _extract_cold_start_context(
        self,
        profile_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        *,
        user_id: str | None = None,
        redis_client=None,
    ) -> dict[str, Any]:
        candidates = [
            profile_context.get("cold_start_context"),
            (
                profile_context.get("preferences", {}).get("cold_start_context")
                if isinstance(profile_context.get("preferences"), dict)
                else None
            ),
            user_context_payload.get("cold_start_context"),
        ]
        cold_start_context: dict[str, Any] = {}
        for candidate in candidates:
            if isinstance(candidate, dict):
                cold_start_context = dict(candidate)
                break

        weak_nodes = self._coerce_weak_node_values(user_context_payload.get(AURORA_CONFIRMED_WEAK_NODES_CONTEXT_KEY))
        if user_id:
            weak_nodes = self._merge_unique(
                weak_nodes,
                self._read_confirmed_weak_nodes_from_redis_sync(
                    user_id=user_id,
                    redis_client=redis_client or self.redis,
                ),
            )
        if weak_nodes:
            cold_start_context["confirmed_weak_nodes"] = self._merge_unique(
                self._coerce_weak_node_values(cold_start_context.get("confirmed_weak_nodes")),
                weak_nodes,
            )

        strategy_preference = self._collect_confirmed_strategy_preference_from_payload(user_context_payload)
        if strategy_preference:
            cold_start_context["confirmed_strategy_preference"] = strategy_preference

        deep_pattern_alerts = self._coerce_deep_pattern_alerts(
            user_context_payload.get(AURORA_DEEP_PATTERN_ALERTS_CONTEXT_KEY)
        )
        if deep_pattern_alerts:
            cold_start_context["deep_pattern_alerts"] = self._merge_deep_pattern_alerts(
                self._coerce_deep_pattern_alerts(cold_start_context.get("deep_pattern_alerts")),
                deep_pattern_alerts,
            )

        # G11: Carry cross-sprint mastery hints into planning so the next
        # sprint can keep mastered nodes light and push persistent weak nodes up.
        previous_sprint_summary = user_context_payload.get("previous_sprint_summary")
        if isinstance(previous_sprint_summary, Mapping):
            strongest_nodes = self._coerce_weak_node_values(previous_sprint_summary.get("strongest_nodes"))
            persistent_weak_nodes = self._coerce_weak_node_values(previous_sprint_summary.get("persistent_weak_nodes"))
            mastery_snapshot = self._coerce_mastery_snapshot(previous_sprint_summary.get("mastery_snapshot"))
            sanitized_summary: dict[str, Any] = {}
            if strongest_nodes:
                cold_start_context["strongest_nodes"] = self._merge_unique(
                    self._coerce_weak_node_values(cold_start_context.get("strongest_nodes")),
                    strongest_nodes,
                )
                sanitized_summary["strongest_nodes"] = strongest_nodes
            if persistent_weak_nodes:
                cold_start_context["persistent_weak_nodes"] = self._merge_unique(
                    self._coerce_weak_node_values(cold_start_context.get("persistent_weak_nodes")),
                    persistent_weak_nodes,
                )
                sanitized_summary["persistent_weak_nodes"] = persistent_weak_nodes
            if mastery_snapshot:
                existing_snapshot = self._coerce_mastery_snapshot(cold_start_context.get("mastery_snapshot"))
                cold_start_context["mastery_snapshot"] = {**existing_snapshot, **mastery_snapshot}
                sanitized_summary["mastery_snapshot"] = mastery_snapshot
            if sanitized_summary:
                cold_start_context["previous_sprint_summary"] = sanitized_summary

        # F16: Extract Galaxy weak nodes (mastery < 0.4) for sprint priority injection.
        galaxy_mastery = user_context_payload.get("galaxy_mastery")
        if isinstance(galaxy_mastery, dict):
            galaxy_weak = [
                node_id
                for node_id, mastery in galaxy_mastery.items()
                if isinstance(mastery, (int, float)) and float(mastery) < 0.4
            ]
            if galaxy_weak:
                cold_start_context["galaxy_weak_nodes"] = galaxy_weak

        # F19: Extract seed library nodes for sprint pack bridging.
        seed_library_summary = user_context_payload.get("seed_library_summary")
        if isinstance(seed_library_summary, dict):
            node_ids = seed_library_summary.get("node_ids")
            if isinstance(node_ids, list) and node_ids:
                cold_start_context["seed_library_nodes"] = [str(nid) for nid in node_ids if str(nid).strip()]

        # G13: Inject confirmed strategy preference from Redis claims.
        effective_redis = redis_client or self.redis
        if not strategy_preference and user_id and effective_redis is not None:
            strategy_preference = self._read_confirmed_strategy_preference(
                user_id=user_id,
                redis_client=effective_redis,
            )
            if strategy_preference:
                cold_start_context["confirmed_strategy_preference"] = strategy_preference

        return cold_start_context

    @staticmethod
    def _inject_sprint_pack_into_cold_start(cold_start_context: dict[str, Any]) -> None:
        """Load Sprint Pack data into cold_start_context when exam intent is detected."""
        if cold_start_context.get("goal_type") != "exam":
            return
        subject = cold_start_context.get("subject")
        if not subject or not str(subject).strip():
            return
        pack = load_pack(str(subject).strip())
        if not pack:
            return
        if pack.get("id"):
            cold_start_context["sprint_pack_id"] = str(pack["id"])
        # Expose the canonical Sprint Pack node ids so Aurora can bind
        # completion-check answers back to Galaxy without inventing node ids.
        pack_node_ids = [
            str(node.get("node_id") or "").strip()
            for node in pack.get("knowledge_nodes", [])
            if isinstance(node, Mapping) and str(node.get("node_id") or "").strip()
        ]
        if pack_node_ids:
            cold_start_context["sprint_pack_nodes"] = DashboardReadoutBuilder._merge_unique(
                DashboardReadoutBuilder._coerce_node_ids(cold_start_context.get("sprint_pack_nodes")),
                pack_node_ids,
            )
        # Inject minimum_output from strategy_presets["7d"]["daily_targets"]
        strategy_presets = pack.get("strategy_presets", {})
        preset_7d = strategy_presets.get("7d", {}) if isinstance(strategy_presets, dict) else {}
        daily_targets = preset_7d.get("daily_targets", {}) if isinstance(preset_7d, dict) else {}
        if isinstance(daily_targets, dict) and daily_targets.get("minimum_output"):
            cold_start_context["sprint_pack_minimum_output"] = daily_targets["minimum_output"]
        # Inject aurora_rules hint (trigger_conditions + actions → concise instruction)
        aurora_rules = pack.get("aurora_rules", {})
        if isinstance(aurora_rules, dict):
            medium = aurora_rules.get("medium_aurora", {})
            if isinstance(medium, dict):
                parts: list[str] = []
                triggers = medium.get("trigger_conditions")
                if isinstance(triggers, list) and triggers:
                    parts.append("触发条件：" + "；".join(str(t) for t in triggers))
                actions = medium.get("actions")
                if isinstance(actions, list) and actions:
                    parts.append("介入动作：" + "；".join(str(a) for a in actions))
                if parts:
                    cold_start_context["sprint_pack_aurora_hint"] = " ".join(parts)

    @staticmethod
    def _inject_sprint_pack_mistakes_into_checkpoint(checkpoint_state: dict[str, Any]) -> None:
        """F20: Load Sprint Pack mistakes for today_nodes when sprint_pack_id is set."""
        sprint_pack_id = checkpoint_state.get("sprint_pack_id")
        if not sprint_pack_id or not str(sprint_pack_id).strip():
            return
        pack_id_str = str(sprint_pack_id).strip()
        # sprint_pack_id format: "computer_networks@v1" → subject="computer_networks", version="v1"
        parts = pack_id_str.split("@", 1)
        subject = parts[0]
        version = parts[1] if len(parts) > 1 else "v1"
        pack = load_pack(subject, version)
        if not pack:
            return
        today_nodes = checkpoint_state.get("today_nodes")
        if not isinstance(today_nodes, list) or not today_nodes:
            return
        from app.sprint_packs.sprint_pack_loader import get_mistake_by_nodes

        mistakes = get_mistake_by_nodes(pack, today_nodes)
        if mistakes:
            checkpoint_state["sprint_pack_mistakes"] = mistakes[:5]

    def _read_confirmed_strategy_preference(
        self,
        *,
        user_id: str,
        redis_client: Any,
    ) -> str | None:
        """G13: Read confirmed preferred_strategy claim from Redis and return the flag name."""
        key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=str(user_id), domain="preferred_strategy")
        raw = self._peek_redis_mapping(redis_client, key)
        if raw is _MISSING:
            getter = getattr(redis_client, "get", None)
            if getter is None:
                return None
            if inspect.iscoroutinefunction(getter):
                try:
                    asyncio.get_running_loop()
                    return None
                except RuntimeError:
                    try:
                        raw = asyncio.run(getter(key))
                    except Exception:
                        return None
            else:
                try:
                    raw = getter(key)
                except Exception:
                    return None
                if inspect.isawaitable(raw):
                    try:
                        asyncio.get_running_loop()
                        if inspect.iscoroutine(raw):
                            raw.close()
                        return None
                    except RuntimeError:
                        try:
                            raw = asyncio.run(raw)
                        except Exception:
                            return None
        return self._extract_strategy_preference_value(raw)

    def _extract_strategy_preference_value(self, raw: Any) -> str | None:
        """Extract the strategy flag name from a claim payload."""
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return None
        if not isinstance(raw, Mapping):
            return None
        # Direct value field
        value = raw.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
        # Nested in claims list
        claims = raw.get("claims")
        if isinstance(claims, list) and claims:
            for claim in reversed(claims):
                if not isinstance(claim, Mapping):
                    continue
                claim_value = claim.get("value")
                if isinstance(claim_value, str) and claim_value.strip():
                    return claim_value.strip()
        # Nested in single claim
        claim_payload = raw.get("claim")
        if isinstance(claim_payload, Mapping):
            claim_value = claim_payload.get("value")
            if isinstance(claim_value, str) and claim_value.strip():
                return claim_value.strip()
        return None

    @staticmethod
    def _coerce_node_ids(value: Any) -> list[str]:
        values = value if isinstance(value, list) else [value]
        node_ids: list[str] = []
        for item in values:
            if isinstance(item, Mapping):
                item = item.get("node_id") or item.get("id") or item.get("name")
            node_id = str(item or "").strip()
            if node_id:
                node_ids.append(node_id)
        return node_ids

    async def with_confirmed_weak_nodes_from_redis(
        self,
        *,
        user_id: str,
        user_context_payload: dict[str, Any],
        redis_client=None,
    ) -> dict[str, Any]:
        weak_nodes = await self._load_confirmed_weak_nodes_from_redis(
            user_id=user_id,
            redis_client=redis_client or self.redis,
        )
        if not weak_nodes:
            return user_context_payload
        payload = dict(user_context_payload)
        payload[AURORA_CONFIRMED_WEAK_NODES_CONTEXT_KEY] = self._merge_unique(
            self._coerce_weak_node_values(payload.get(AURORA_CONFIRMED_WEAK_NODES_CONTEXT_KEY)),
            weak_nodes,
        )
        return payload

    async def with_confirmed_strategy_preference_from_redis(
        self,
        *,
        user_id: str,
        user_context_payload: dict[str, Any],
        redis_client=None,
    ) -> dict[str, Any]:
        strategy_preference = await self._load_confirmed_strategy_preference_from_redis(
            user_id=user_id,
            redis_client=redis_client or self.redis,
        )
        if not strategy_preference:
            return user_context_payload
        payload = dict(user_context_payload)
        payload[AURORA_CONFIRMED_STRATEGY_PREFERENCE_CONTEXT_KEY] = strategy_preference
        return payload

    async def with_deep_pattern_alerts_from_error_history(
        self,
        *,
        active_db: Any,
        user_id: str,
        user_context_payload: dict[str, Any],
        redis_client=None,
    ) -> dict[str, Any]:
        weak_nodes = self._collect_confirmed_weak_nodes_from_payload(user_context_payload)
        if not weak_nodes:
            weak_nodes = await self._load_confirmed_weak_nodes_from_redis(
                user_id=user_id,
                redis_client=redis_client or self.redis,
            )
        if active_db is None or not weak_nodes:
            return user_context_payload

        from app.services.error_replan_bridge import ErrorReplanBridge

        bridge = ErrorReplanBridge(active_db, redis=redis_client or self.redis)
        alerts: list[dict[str, Any]] = []
        for weak_node in weak_nodes:
            try:
                analysis = await bridge._analyze_recurring_errors(user_id=user_id, node_id=weak_node)
            except Exception:
                continue
            if isinstance(analysis, Mapping) and analysis.get("recurring") is True:
                alerts.append(dict(analysis))

        if not alerts:
            return user_context_payload
        payload = dict(user_context_payload)
        payload[AURORA_DEEP_PATTERN_ALERTS_CONTEXT_KEY] = self._merge_deep_pattern_alerts(
            self._coerce_deep_pattern_alerts(payload.get(AURORA_DEEP_PATTERN_ALERTS_CONTEXT_KEY)),
            alerts,
        )
        return payload

    async def _load_confirmed_weak_nodes_from_redis(
        self,
        *,
        user_id: str,
        redis_client=None,
    ) -> list[str]:
        redis = redis_client or self.redis
        if redis is None:
            return []
        key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=str(user_id), domain="weak_node")
        getter = getattr(redis, "get", None)
        if getter is None:
            return []
        try:
            raw = getter(key)
            if inspect.isawaitable(raw):
                raw = await raw
        except Exception:
            return []
        return self._confirmed_weak_nodes_from_claim_payload(raw)

    async def _load_confirmed_strategy_preference_from_redis(
        self,
        *,
        user_id: str,
        redis_client=None,
    ) -> str | None:
        redis = redis_client or self.redis
        if redis is None:
            return None
        key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=str(user_id), domain="preferred_strategy")
        getter = getattr(redis, "get", None)
        if getter is None:
            return None
        try:
            raw = getter(key)
            if inspect.isawaitable(raw):
                raw = await raw
        except Exception:
            return None
        return self._extract_strategy_preference_value(raw)

    def _read_confirmed_weak_nodes_from_redis_sync(
        self,
        *,
        user_id: str,
        redis_client=None,
    ) -> list[str]:
        redis = redis_client or self.redis
        if redis is None:
            return []
        key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=str(user_id), domain="weak_node")
        raw = self._peek_redis_mapping(redis, key)
        if raw is _MISSING:
            getter = getattr(redis, "get", None)
            if getter is None:
                return []
            if inspect.iscoroutinefunction(getter):
                try:
                    asyncio.get_running_loop()
                    return []
                except RuntimeError:
                    try:
                        raw = asyncio.run(getter(key))
                    except Exception:
                        return []
            else:
                try:
                    raw = getter(key)
                except Exception:
                    return []
                if inspect.isawaitable(raw):
                    try:
                        asyncio.get_running_loop()
                        if inspect.iscoroutine(raw):
                            raw.close()
                        return []
                    except RuntimeError:
                        try:
                            raw = asyncio.run(raw)
                        except Exception:
                            return []
        return self._confirmed_weak_nodes_from_claim_payload(raw)

    def _confirmed_weak_nodes_from_claim_payload(self, raw: Any) -> list[str]:
        if not raw:
            return []
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return self._coerce_weak_node_values(raw)
        if isinstance(raw, Mapping):
            values = self._coerce_weak_node_values(raw.get("values"))
            direct_value = self._coerce_weak_node_values(raw.get("value"))
            claims = [
                self._weak_node_value_from_claim(item)
                for item in (raw.get("claims") or [])
                if isinstance(item, Mapping)
            ]
            return self._merge_unique(values, direct_value, [item for item in claims if item])
        if isinstance(raw, list):
            values: list[str] = []
            for item in raw:
                if isinstance(item, Mapping):
                    value = self._weak_node_value_from_claim(item)
                    if value:
                        values.append(value)
                else:
                    values.extend(self._coerce_weak_node_values(item))
            return self._merge_unique(values)
        return []

    def _weak_node_value_from_claim(self, claim: Mapping[str, Any]) -> str | None:
        metadata = claim.get("metadata") if isinstance(claim.get("metadata"), Mapping) else {}
        domain = str(claim.get("domain") or claim.get("claim_type") or "").strip()
        metadata_domain = str((metadata or {}).get("domain") or "").strip()
        if domain and domain != "weak_node" and metadata_domain != "weak_node":
            return None
        if str(claim.get("status") or "confirmed").strip().lower() == "revoked":
            return None
        value = (
            claim.get("value")
            or claim.get("knowledge_node_id")
            or claim.get("node_id")
            or (metadata or {}).get("value")
            or (metadata or {}).get("knowledge_node_id")
            or (metadata or {}).get("node_id")
        )
        values = self._coerce_weak_node_values(value)
        return values[0] if values else None

    def _coerce_weak_node_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return self._merge_unique(
                [normalized for item in value for normalized in self._coerce_weak_node_values(item)]
            )
        if isinstance(value, Mapping):
            return self._coerce_weak_node_values(
                value.get("value") or value.get("knowledge_node_id") or value.get("node_id")
            )
        normalized = str(value).strip()
        return [normalized] if normalized else []

    def _collect_confirmed_weak_nodes_from_payload(self, user_context_payload: dict[str, Any]) -> list[str]:
        profile_context = user_context_payload.get("profile_context")
        profile_context = profile_context if isinstance(profile_context, Mapping) else {}
        preferences = profile_context.get("preferences")
        preferences = preferences if isinstance(preferences, Mapping) else {}
        candidates = [
            user_context_payload.get(AURORA_CONFIRMED_WEAK_NODES_CONTEXT_KEY),
            user_context_payload.get("confirmed_weak_nodes"),
            self._as_dict(user_context_payload.get("cold_start_context")).get("confirmed_weak_nodes"),
            self._as_dict(profile_context.get("cold_start_context")).get("confirmed_weak_nodes"),
            self._as_dict(preferences.get("cold_start_context")).get("confirmed_weak_nodes"),
        ]
        return self._merge_unique(*[self._coerce_weak_node_values(candidate) for candidate in candidates])

    def _collect_confirmed_strategy_preference_from_payload(
        self,
        user_context_payload: dict[str, Any],
    ) -> str | None:
        profile_context = user_context_payload.get("profile_context")
        profile_context = profile_context if isinstance(profile_context, Mapping) else {}
        preferences = profile_context.get("preferences")
        preferences = preferences if isinstance(preferences, Mapping) else {}
        candidates = [
            user_context_payload.get(AURORA_CONFIRMED_STRATEGY_PREFERENCE_CONTEXT_KEY),
            user_context_payload.get("confirmed_strategy_preference"),
            self._as_dict(user_context_payload.get("cold_start_context")).get("confirmed_strategy_preference"),
            self._as_dict(profile_context.get("cold_start_context")).get("confirmed_strategy_preference"),
            self._as_dict(preferences.get("cold_start_context")).get("confirmed_strategy_preference"),
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return None

    def _coerce_deep_pattern_alerts(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        alerts: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, Mapping):
                continue
            alert = dict(item)
            node_id = str(alert.get("node_id") or "").strip()
            if not node_id:
                continue
            alert["node_id"] = node_id
            alert["recurring"] = bool(alert.get("recurring"))
            if alert.get("recurring") is not True:
                continue
            alerts.append(alert)
        return alerts

    def _merge_deep_pattern_alerts(
        self,
        *groups: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for group in groups:
            for item in group:
                node_id = str(item.get("node_id") or "").strip()
                cause_category = str(item.get("cause_category") or "").strip()
                key = (node_id, cause_category)
                if not node_id or key in seen:
                    continue
                seen.add(key)
                merged.append(dict(item))
        return merged

    def _coerce_mastery_snapshot(self, value: Any) -> dict[str, float]:
        if not isinstance(value, Mapping):
            return {}
        snapshot: dict[str, float] = {}
        for node_id, mastery in value.items():
            normalized_id = str(node_id or "").strip()
            if not normalized_id:
                continue
            parsed = self._safe_float(mastery, default=None)
            if parsed is None or parsed < 0:
                continue
            if parsed > 1.0:
                parsed = parsed / 100.0
            snapshot[normalized_id] = max(0.0, min(float(parsed), 1.0))
        return snapshot

    @staticmethod
    def _merge_unique(*groups: list[str]) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for item in group:
                normalized = str(item or "").strip()
                if normalized and normalized not in merged:
                    merged.append(normalized)
        return merged

    @staticmethod
    def _peek_redis_mapping(redis: Any, key: str) -> Any:
        for attr in ("store", "kv", "data", "_store"):
            mapping = getattr(redis, attr, None)
            if isinstance(mapping, Mapping) and key in mapping:
                return mapping[key]
        return _MISSING

    def _extract_achievement_signals(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> dict[str, Any]:
        streak_info = self._extract_streak_info(user_context_payload)
        direct = self._as_dict(
            request_extra_context.get("achievement_signals") or user_context_payload.get("achievement_signals")
        )
        if direct:
            return self._normalize_achievement_signals({**streak_info, **direct})
        cognitive = self._as_dict((user_context_payload.get("cognitive_context") or {}).get("achievement_summary"))
        if not cognitive:
            return self._normalize_achievement_signals(streak_info) if streak_info else {}
        active_streaks = list(cognitive.get("active_streaks") or [])
        recent_unlocks = list(cognitive.get("recent_unlocks") or [])
        in_progress = list(cognitive.get("in_progress_achievements") or [])
        total_score = self._safe_float(cognitive.get("total_achievement_score"), default=0.0)
        return self._normalize_achievement_signals(
            {
                "active_streaks": active_streaks,
                "recent_unlocks": recent_unlocks,
                "in_progress_count": len(in_progress),
                "momentum": min(1.0, round(total_score / 50.0, 3)),
                **streak_info,
            }
        )

    def _extract_social_signals(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> dict[str, Any]:
        cognitive_context = self._as_mapping_dict(user_context_payload.get("cognitive_context"))
        for candidate in (
            request_extra_context.get("social_signals"),
            request_extra_context.get("social_signals_summary"),
            user_context_payload.get("social_signals"),
            user_context_payload.get("social_signals_summary"),
            user_context_payload.get("social_context_v1"),
            cognitive_context.get("social_signals_summary"),
            cognitive_context.get("social_context_v1"),
        ):
            payload = self._as_mapping_dict(candidate)
            if not payload:
                continue
            nested_value = self._as_mapping_dict(payload.get("value"))
            return self._normalize_social_signals(nested_value or payload)

        legacy_social = self._as_mapping_dict(user_context_payload.get("social_context"))
        if not legacy_social:
            return {}
        return self._normalize_social_signals(
            {
                "mention_count": len(legacy_social.get("recent_person_mentions") or []),
                "relationship_count": legacy_social.get("relationship_count"),
                "pending_commitments_count": legacy_social.get("pending_commitments_count"),
            }
        )

    def _normalize_social_signals(self, signals: dict[str, Any]) -> dict[str, Any]:
        mention_count = self._first_nonnegative_int(signals.get("mention_count")) or 0
        relationship_count = self._first_nonnegative_int(signals.get("relationship_count")) or 0
        pending_commitments_count = self._first_nonnegative_int(signals.get("pending_commitments_count")) or 0
        summary_lines = [str(item).strip() for item in (signals.get("summary_lines") or []) if str(item).strip()]
        if not summary_lines and str(signals.get("summary_text") or "").strip():
            summary_lines = [
                part.strip() for part in str(signals.get("summary_text") or "").split("；") if part.strip()
            ]
        if not summary_lines:
            if mention_count > 0:
                summary_lines.append(f"最近 7 天提到过 {mention_count} 位学习相关人物。")
            if relationship_count > 0:
                summary_lines.append(f"当前有 {relationship_count} 条关系型背景需要在建议里保持边界感。")
            if pending_commitments_count > 0:
                summary_lines.append(f"目前有 {pending_commitments_count} 条到期承诺待跟进。")

        normalized = {
            "mention_count": mention_count,
            "relationship_count": relationship_count,
            "pending_commitments_count": pending_commitments_count,
            "summary_lines": summary_lines[:3],
            "summary_text": "；".join(summary_lines[:3])[:400],
            "rule_z_boundary": (
                "Rule Z: use only as aggregate collaboration context; do not infer social identity, "
                "name third parties, or push social/accountability actions without explicit user intent."
            ),
        }
        for key in ("community_engagement_level", "social_learning_preference", "content_contribution_rate"):
            if signals.get(key) is not None:
                normalized[key] = signals[key]
        if not any(
            (
                normalized["mention_count"],
                normalized["relationship_count"],
                normalized["pending_commitments_count"],
                normalized["summary_lines"],
                normalized.get("community_engagement_level"),
                normalized.get("social_learning_preference") is not None,
                normalized.get("content_contribution_rate") is not None,
            )
        ):
            return {}
        return normalized

    def _normalize_achievement_signals(self, signals: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(signals)
        active_streaks = normalized.get("active_streaks")
        if isinstance(active_streaks, tuple):
            active_streaks = list(active_streaks)
            normalized["active_streaks"] = active_streaks
        elif not isinstance(active_streaks, list):
            active_streaks = []

        current_streak_days = self._first_nonnegative_int(
            normalized.get("current_streak_days"),
            normalized.get("current_streak"),
            normalized.get("streak_days"),
            normalized.get("streak"),
        )
        if current_streak_days is not None:
            normalized["current_streak_days"] = current_streak_days

        gap_since_last_study_days = self._first_nonnegative_int(
            normalized.get("gap_since_last_study_days"),
            normalized.get("days_since_last_study"),
            normalized.get("study_gap_days"),
            normalized.get("inactive_days"),
        )
        if gap_since_last_study_days is not None:
            normalized["gap_since_last_study_days"] = gap_since_last_study_days

        streak_active = self._coerce_bool(normalized.get("streak_active"))
        if streak_active is None:
            streak_active = bool(active_streaks) or bool(current_streak_days and current_streak_days > 0)
        normalized["streak_active"] = streak_active

        recently_unlocked = self._coerce_bool(normalized.get("recently_unlocked"))
        if recently_unlocked is None:
            recently_unlocked = self._has_recent_unlock(
                normalized.get("recent_unlocks")
                or normalized.get("recent_unlocked")
                or normalized.get("unlocked_achievements")
            )
        normalized["recently_unlocked"] = recently_unlocked

        momentum = self._safe_float(normalized.get("momentum"), default=None)
        if momentum is not None:
            normalized["momentum"] = min(1.0, max(0.0, momentum))
        return normalized

    def _extract_streak_info(self, user_context_payload: dict[str, Any]) -> dict[str, int]:
        payloads = self._achievement_streak_payloads(user_context_payload)
        current_streak_days = self._first_nonnegative_int(
            *(
                candidate.get(key)
                for candidate in payloads
                for key in (
                    "current_streak_days",
                    "current_streak",
                    "streak_days",
                    "streak",
                    "study_streak_days",
                    "daily_streak_days",
                    "currentStudyStreak",
                )
            )
        )
        if current_streak_days is None:
            current_streak_days = self._current_streak_from_active_streaks(payloads)

        gap_since_last_study_days = self._first_nonnegative_int(
            *(
                candidate.get(key)
                for candidate in payloads
                for key in (
                    "gap_since_last_study_days",
                    "days_since_last_study",
                    "study_gap_days",
                    "last_study_gap_days",
                    "inactive_days",
                    "break_days",
                    "gap_days",
                    "days_since_last_activity",
                )
            )
        )
        if gap_since_last_study_days is None:
            gap_since_last_study_days = self._gap_days_from_last_study_at(payloads)

        streak_info: dict[str, int] = {}
        if current_streak_days is not None:
            streak_info["current_streak_days"] = current_streak_days
        if gap_since_last_study_days is not None:
            streak_info["gap_since_last_study_days"] = gap_since_last_study_days
        return streak_info

    def _achievement_streak_payloads(self, user_context_payload: dict[str, Any]) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []

        def add(value: Any) -> None:
            payload = self._as_mapping_dict(value)
            if not payload:
                return
            payloads.append(payload)
            nested_value = self._as_mapping_dict(payload.get("value"))
            if nested_value:
                payloads.append(nested_value)
            nested_streak = self._as_mapping_dict(payload.get("streak") or payload.get("streak_info"))
            if nested_streak:
                payloads.append(nested_streak)

        add(user_context_payload)
        for key in (
            "achievement_signals",
            "achievement",
            "achievements",
            "achievement_summary",
            "achievement_engine",
            "growth_signal_contract",
            "growth_signal_summary",
            "streak_info",
            "streak",
            "streak_stats",
            "study_streak",
            "engagement_state",
        ):
            add(user_context_payload.get(key))

        for parent_key in ("cognitive_context", "profile_context", "state", "user_state"):
            parent = self._as_mapping_dict(user_context_payload.get(parent_key))
            if not parent:
                continue
            for key in (
                "achievement_signals",
                "achievement",
                "achievement_summary",
                "achievement_engine",
                "growth_signal_contract",
                "growth_signal_summary",
                "streak_info",
                "streak",
                "streak_stats",
                "study_streak",
                "engagement_state",
            ):
                add(parent.get(key))

        optional_signals = self._as_mapping_dict(user_context_payload.get("optional_signals"))
        achievement_engine = self._as_mapping_dict(optional_signals.get("achievement_engine"))
        add(achievement_engine)
        add(achievement_engine.get("growth_signal_contract"))
        add(achievement_engine.get("growth_signal_summary"))
        return payloads

    def _current_streak_from_active_streaks(self, payloads: list[dict[str, Any]]) -> int | None:
        values: list[Any] = []
        for payload in payloads:
            active_streaks = payload.get("active_streaks")
            if not isinstance(active_streaks, list):
                continue
            for item in active_streaks:
                if isinstance(item, Mapping):
                    values.extend(
                        item.get(key)
                        for key in ("current_streak_days", "current_streak", "streak_days", "days", "count")
                    )
                else:
                    values.append(item)
        return self._first_nonnegative_int(*values)

    def _gap_days_from_last_study_at(self, payloads: list[dict[str, Any]]) -> int | None:
        for payload in payloads:
            raw_timestamp = next(
                (
                    payload.get(key)
                    for key in (
                        "last_study_at",
                        "last_learning_at",
                        "last_activity_at",
                        "last_active_at",
                        "last_checkin_at",
                        "last_session_at",
                    )
                    if payload.get(key)
                ),
                None,
            )
            timestamp = self._coerce_datetime(raw_timestamp)
            if timestamp is None:
                continue
            return max(0, (datetime.now(UTC).date() - timestamp.date()).days)
        return None

    def _has_recent_unlock(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list) or not value:
            return False

        now = datetime.now(UTC)
        for item in value:
            if not isinstance(item, dict):
                return True
            raw_timestamp = next(
                (
                    item.get(key)
                    for key in ("unlocked_at", "created_at", "timestamp", "occurred_at", "time")
                    if item.get(key)
                ),
                None,
            )
            if raw_timestamp is None:
                return True
            timestamp = self._coerce_datetime(raw_timestamp)
            if timestamp is None:
                return True
            if now - timedelta(hours=24) <= timestamp <= now + timedelta(minutes=5):
                return True
        return False

    def _coerce_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            if raw.endswith("Z"):
                raw = f"{raw[:-1]}+00:00"
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                return None
        else:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _safe_float(self, value: Any, *, default: float | None) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _first_nonnegative_int(self, *values: Any) -> int | None:
        for value in values:
            if isinstance(value, bool) or value is None:
                continue
            try:
                parsed = int(float(value))
            except (TypeError, ValueError):
                continue
            if parsed >= 0:
                return parsed
        return None

    def _coerce_bool(self, value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y", "on"}:
                return True
            if normalized in {"false", "0", "no", "n", "off"}:
                return False
            return None
        return bool(value)

    def _as_dict(self, value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _as_mapping_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        if hasattr(value, "model_dump"):
            dumped = value.model_dump(mode="python")
            return dict(dumped) if isinstance(dumped, Mapping) else {}
        if hasattr(value, "__dict__"):
            return {str(key): item for key, item in vars(value).items() if not str(key).startswith("_")}
        return {}

    def _as_list_of_dicts(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    def _build_domain_coverage(
        self,
        *,
        surface: str,
        user_message: str,
        messages: list[Any],
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        profile_context: dict[str, Any],
        cold_start_context: dict[str, Any],
        informational_tensions: list[dict[str, Any]],
        exam_sprint_policy: dict[str, Any],
        task_state: dict[str, Any],
        checkpoint_state: dict[str, Any],
    ) -> tuple[list[str], list[str]]:
        status_by_domain = self._collect_domain_statuses(informational_tensions)
        covered = {domain for domain, status in status_by_domain.items() if status == "resolved"}
        missing = {domain for domain, status in status_by_domain.items() if status in {"open", "partially_resolved"}}
        evidence_sources: list[Any] = [
            request_extra_context,
            user_context_payload,
            profile_context,
            cold_start_context,
            exam_sprint_policy,
            task_state,
            checkpoint_state,
            request_extra_context.get("user_model_snapshot"),
            request_extra_context.get("modeling_state"),
        ]
        user_texts = [
            str(user_message or ""),
            *[
                str(item.get("content") or "")
                for item in messages[-6:]
                if isinstance(item, dict) and str(item.get("role") or "").lower() == "user"
            ],
        ]
        user_supplied_domains = {domain for text in user_texts for domain in self._infer_domains_from_text(text)}
        for domain in CORE_MODELING_DOMAINS:
            if domain in missing and domain in user_supplied_domains:
                covered.add(domain)
                missing.discard(domain)
                continue
            if domain in missing:
                continue
            if self._sources_have_domain_evidence(domain, evidence_sources, user_texts):
                covered.add(domain)
        if surface == "aurora_modeling":
            for domain in CORE_MODELING_DOMAINS:
                if domain not in covered and domain not in missing:
                    missing.add(domain)
        covered_list = [domain for domain in CORE_MODELING_DOMAINS if domain in covered]
        missing_list = [domain for domain in CORE_MODELING_DOMAINS if domain in missing and domain not in covered]
        covered_tail = sorted(domain for domain in covered if domain not in set(CORE_MODELING_DOMAINS))
        missing_tail = sorted(domain for domain in missing if domain not in set(CORE_MODELING_DOMAINS))
        return covered_list + covered_tail, missing_list + missing_tail

    def _collect_domain_statuses(self, tensions: list[dict[str, Any]]) -> dict[str, str]:
        priorities = {"resolved": 0, "dropped": 1, "partially_resolved": 2, "open": 3}
        statuses: dict[str, str] = {}
        for tension in tensions:
            domain = canonicalize_runtime_domain(tension.get("domain"))
            status = _normalize_text(tension.get("status") or "open").lower() or "open"
            if not domain:
                continue
            current = statuses.get(domain)
            if current is None or priorities.get(status, 2) >= priorities.get(current, 2):
                statuses[domain] = status
        return statuses

    def _sources_have_domain_evidence(self, domain: str, sources: list[Any], user_texts: list[str]) -> bool:
        if any(self._source_has_domain_evidence(domain, item) for item in sources):
            return True
        return any(domain in self._infer_domains_from_text(text) for text in user_texts)

    def _source_has_domain_evidence(self, domain: str, value: Any) -> bool:
        if value in (None, "", [], {}):
            return False
        if isinstance(value, dict):
            for key, nested in value.items():
                if canonicalize_runtime_domain(key) == domain and nested not in (None, "", [], {}):
                    return True
                if self._source_has_domain_evidence(domain, nested):
                    return True
            return False
        if isinstance(value, (list, tuple, set)):
            return any(self._source_has_domain_evidence(domain, item) for item in value)
        if isinstance(value, str):
            return domain in self._infer_domains_from_text(value)
        return False

    def _build_recently_asked_domains(
        self,
        *,
        request_extra_context: dict[str, Any],
        messages: list[Any],
    ) -> list[str]:
        domains: list[str] = []
        for item in list(request_extra_context.get("recently_asked_domains") or []):
            canonical = canonicalize_runtime_domain(item)
            if canonical and canonical not in domains:
                domains.append(canonical)
        assistant_messages = [
            item
            for item in messages[-6:]
            if isinstance(item, dict) and str(item.get("role") or "").lower() == "assistant"
        ]
        for message in reversed(assistant_messages):
            inferred = self._infer_domains_from_text(str(message.get("content") or ""), question_only=True)
            for domain in inferred:
                if domain not in domains:
                    domains.append(domain)
        return domains[:3]

    def _build_sprint_policy_summary(self, exam_sprint_policy: dict[str, Any]) -> dict[str, Any]:
        if not exam_sprint_policy:
            return {}
        summary: dict[str, Any] = {}
        mode = (
            exam_sprint_policy.get("mode")
            or exam_sprint_policy.get("policy_mode")
            or exam_sprint_policy.get("sprint_mode")
        )
        days_remaining = (
            exam_sprint_policy.get("days_remaining")
            or exam_sprint_policy.get("days_left")
            or exam_sprint_policy.get("time_constraint_days")
        )
        headline = (
            exam_sprint_policy.get("summary")
            or exam_sprint_policy.get("policy_summary")
            or exam_sprint_policy.get("headline")
            or exam_sprint_policy.get("focus")
        )
        non_negotiables = exam_sprint_policy.get("non_negotiables") or exam_sprint_policy.get("rules") or []
        defer_or_skip = exam_sprint_policy.get("defer_or_skip") or exam_sprint_policy.get("low_roi_topics") or []
        if mode:
            summary["mode"] = str(mode)
        if days_remaining not in (None, ""):
            summary["days_remaining"] = days_remaining
        if headline:
            summary["headline"] = str(headline)
        if isinstance(non_negotiables, list) and non_negotiables:
            summary["non_negotiables"] = [str(item) for item in non_negotiables[:3] if _normalize_text(item)]
        if isinstance(defer_or_skip, list) and defer_or_skip:
            summary["defer_or_skip"] = [str(item) for item in defer_or_skip[:3] if _normalize_text(item)]
        for key in ("last_24h_mode", "drop_low_roi_topics", "new_topic_allowed", "error_analysis_required"):
            if key in exam_sprint_policy:
                summary[key] = exam_sprint_policy.get(key)
        return summary

    def _build_explicit_user_constraints(
        self,
        *,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        profile_context: dict[str, Any],
        control_surface_reading: ControlSurfaceReading,
    ) -> dict[str, Any]:
        constraints: dict[str, Any] = {}
        hard_bounds = control_surface_reading.hard_bounds.model_dump(mode="json")
        hard_bounds = {key: value for key, value in hard_bounds.items() if value not in (None, "", [], {})}
        if hard_bounds:
            constraints["hard_bounds"] = hard_bounds
        merged_constraints: dict[str, Any] = {}
        for candidate in (
            profile_context.get("explicit_constraints"),
            user_context_payload.get("explicit_constraints"),
            request_extra_context.get("explicit_constraints"),
        ):
            if isinstance(candidate, dict):
                merged_constraints.update(candidate)
        if merged_constraints:
            constraints["stated_constraints"] = merged_constraints
        preferences = profile_context.get("preferences")
        if isinstance(preferences, dict):
            stated_preferences = {
                key: value
                for key, value in preferences.items()
                if key in {"conversation_style", "pace_preference", "focus_preference"} and value not in (None, "")
            }
            if stated_preferences:
                constraints["stated_preferences"] = stated_preferences
        return constraints

    def _build_latent_thread_recovery_candidates(
        self,
        *,
        latent_threads: list[dict[str, Any]],
        covered_domains: list[str],
        missing_domains: list[str],
        recently_asked_domains: list[str],
    ) -> list[dict[str, Any]]:
        covered = set(covered_domains)
        missing = set(missing_domains)
        recent = set(recently_asked_domains)
        candidates: list[dict[str, Any]] = []
        for thread in latent_threads:
            status = _normalize_text(thread.get("status") or "active").lower() or "active"
            if status in {"resolved", "dropped"}:
                continue
            source_intent = thread.get("source_intent")
            target_domain = None
            if isinstance(source_intent, dict):
                target_domain = canonicalize_runtime_domain(source_intent.get("target_domain"))
            target_domain = target_domain or canonicalize_runtime_domain(thread.get("domain"))
            if target_domain in covered:
                continue
            salience = float(thread.get("salience") or 0.0)
            priority = (
                salience + (0.25 if target_domain in missing else 0.0) - (0.15 if target_domain in recent else 0.0)
            )
            candidates.append(
                {
                    "thread_id": str(thread.get("thread_id") or ""),
                    "target_domain": target_domain,
                    "salience": round(salience, 3),
                    "context_snapshot": _normalize_text(thread.get("context_snapshot")),
                    "still_missing": target_domain in missing,
                    "recently_asked": target_domain in recent,
                    "recovery_priority": round(priority, 3),
                }
            )
        candidates.sort(
            key=lambda item: (
                not bool(item.get("still_missing")),
                bool(item.get("recently_asked")),
                -float(item.get("recovery_priority") or 0.0),
                -float(item.get("salience") or 0.0),
            )
        )
        return candidates[:3]

    def _enrich_tensions_with_importance(self, tensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for tension in tensions:
            if not tension.get("importance_reasoning"):
                domain = _normalize_text(tension.get("domain") or "")
                reasoning = _DOMAIN_IMPORTANCE.get(domain)
                if reasoning:
                    tension = {**tension, "importance_reasoning": reasoning}
            enriched.append(tension)
        return enriched

    def _infer_domains_from_text(self, text: str, *, question_only: bool = False) -> list[str]:
        normalized = _normalize_text(text).lower()
        if not normalized:
            return []
        if question_only and not any(marker in normalized for marker in _QUESTION_MARKERS):
            return []
        domains: list[str] = []
        for domain, hints in _DOMAIN_TEXT_HINTS.items():
            if any(hint.lower() in normalized for hint in hints):
                domains.append(domain)
        return domains
