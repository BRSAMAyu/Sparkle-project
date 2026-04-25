from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.aurora.runtime_v1.control_surface import AuroraHardBounds, ControlSurfaceReading
from app.aurora.runtime_v1.skills import SkillAffordance

CORE_MODELING_DOMAINS: tuple[str, ...] = ("goal", "scope", "baseline", "time", "motivation")
REQUIRED_MODELING_DOMAINS: tuple[str, ...] = ("goal", "scope", "baseline", "time")

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
    "goal": ("目标", "想达到", "想要", "希望", "打算", "通过", "goal", "target", "objective"),
    "scope": ("范围", "章节", "题型", "考哪些", "哪几章", "哪些内容", "scope", "chapter", "topic"),
    "baseline": ("基础", "掌握", "学过", "熟悉", "会不会", "薄弱", "baseline", "foundation", "mastery"),
    "time": ("每天", "几天", "多久", "时间", "日程", "小时", "deadline", "schedule", "available"),
    "motivation": ("为什么", "为了", "动机", "原因", "不想挂", "想冲", "保研", "必须过", "目的", "重要", "有意义", "motivation", "reason", "why"),
}

_QUESTION_MARKERS = ("？", "?", "吗", "呢", "多少", "哪些", "哪几", "多久", "几点", "什么", "告诉我")

_PROMPT_CONTEXT_MASK: frozenset[str] = frozenset({"surface", "recently_asked_domains"})

_ACTION_CONTEXT_MASK: dict[str, frozenset[str]] = {
    "emit_message": frozenset(
        {
            "user_message",
            "covered_domains",
            "missing_domains",
            "cold_start_context",
            "informational_tensions",
        }
    ),
    "wait": frozenset({"user_message", "covered_domains", "missing_domains"}),
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
        }
    ),
    "update_state": frozenset(
        {
            "user_message",
            "covered_domains",
            "missing_domains",
            "cold_start_context",
            "informational_tensions",
        }
    ),
    "soft_return_topic": frozenset(
        {
            "user_message",
            "covered_domains",
            "missing_domains",
            "cold_start_context",
            "informational_tensions",
            "latent_thread_recovery_candidates",
        }
    ),
    "drop_thread": frozenset(
        {
            "covered_domains",
            "missing_domains",
            "latent_thread_recovery_candidates",
        }
    ),
}

_SURFACE_CONTEXT_ADDITIONS: dict[str, frozenset[str]] = {
    "aurora_checkpoint": frozenset({"checkpoint_state"}),
    "aurora_planning": frozenset({"sprint_policy_summary", "task_state"}),
}

_SURFACE_CONTEXT_EXCLUSIONS: dict[str, frozenset[str]] = {
    "aurora_checkpoint": frozenset({"cold_start_context"}),
    "aurora_modeling": frozenset({"task_state", "checkpoint_state", "exam_sprint_policy", "sprint_policy_summary"}),
    "aurora_planning": frozenset({"cold_start_context", "achievement_signals", "checkpoint_state", "exam_sprint_policy"}),
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

    def to_llm_payload(self, *, action: str | None = None) -> dict[str, Any]:
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
        }
        allowed_keys = self._context_mask_keys(action=action)
        return {key: value for key, value in payload.items() if key in allowed_keys}

    def _context_mask_keys(self, *, action: str | None) -> set[str]:
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
    ) -> DashboardReadout:
        profile_context = user_context_payload.get("profile_context")
        if not isinstance(profile_context, dict):
            profile_context = {}

        cold_start_context = self._extract_cold_start_context(profile_context, user_context_payload)
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
        )

    def _extract_cold_start_context(
        self,
        profile_context: dict[str, Any],
        user_context_payload: dict[str, Any],
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
        for candidate in candidates:
            if isinstance(candidate, dict):
                return dict(candidate)
        return {}

    def _extract_achievement_signals(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> dict[str, Any]:
        direct = self._as_dict(
            request_extra_context.get("achievement_signals") or user_context_payload.get("achievement_signals")
        )
        if direct:
            return direct
        cognitive = self._as_dict(
            (user_context_payload.get("cognitive_context") or {}).get("achievement_summary")
        )
        if not cognitive:
            return {}
        in_progress = list(cognitive.get("in_progress_achievements") or [])
        total_score = float(cognitive.get("total_achievement_score") or 0.0)
        return {
            "active_streaks": [],
            "recent_unlocks": list(cognitive.get("recent_unlocks") or []),
            "in_progress_count": len(in_progress),
            "momentum": min(1.0, round(total_score / 50.0, 3)),
        }

    def _as_dict(self, value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

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
        covered = {
            domain
            for domain, status in status_by_domain.items()
            if status == "resolved"
        }
        missing = {
            domain
            for domain, status in status_by_domain.items()
            if status in {"open", "partially_resolved"}
        }
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
        for domain in CORE_MODELING_DOMAINS:
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
            priority = salience + (0.25 if target_domain in missing else 0.0) - (0.15 if target_domain in recent else 0.0)
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
