from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

PRIMITIVE_SOURCE_MAPPING: dict[str, list[str]] = {
    "vision": ["MemoryGoal", "Plan", "GlobalCompass", "strategy_map"],
    "current_state": ["UserContext", "ProfileContext", "PlanState", "focus_stats", "time_capacity"],
    "obstacle": ["ErrorRecord", "BehaviorPattern", "CognitiveFragment", "plan_risk_flags"],
    "evidence": ["UserNodeStatus", "StudyRecord", "task_completion", "progress_narrative", "retrieved_passages"],
    "intervention": ["InterventionRecord", "adaptive_replanner_records", "visible_intelligence_messages"],
    "outcome": ["InterventionStrategyOutcome", "mastery_changes", "recurring_error_deltas", "feedback_binding"],
}


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _compact_text(value: Any, *, limit: int = 160) -> str:
    text = " ".join(_strip(value).split())
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _format_mastery(value: Any) -> str:
    try:
        numeric = float(value)
    except Exception:
        return _strip(value)
    if 0.0 <= numeric <= 1.0:
        return f"{numeric:.0%}"
    return f"{numeric:.0f}%"


@dataclass(frozen=True)
class VisionPrimitive:
    primary_goal: str
    active_plan: str
    north_star: str
    why_now: str
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_refs"] = list(self.source_refs)
        return payload


@dataclass(frozen=True)
class CurrentStatePrimitive:
    mode: str
    focus_channel: str
    phase: str
    route_intent: str
    focus_mode: str
    plan_stage: str
    learning_state: str
    progress_signal: str
    capacity_signal: str
    active_domains: tuple[str, ...]
    snapshot: str
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["active_domains"] = list(self.active_domains)
        payload["source_refs"] = list(self.source_refs)
        return payload


@dataclass(frozen=True)
class ObstaclePrimitive:
    label: str
    summary: str
    obstacle_type: str
    source: str
    confidence: float
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_refs"] = list(self.source_refs)
        return payload


@dataclass(frozen=True)
class EvidencePrimitive:
    summary: str
    freshest_items: tuple[str, ...]
    progress_highlights: tuple[str, ...]
    supporting_items: tuple[str, ...]
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["freshest_items"] = list(self.freshest_items)
        payload["progress_highlights"] = list(self.progress_highlights)
        payload["supporting_items"] = list(self.supporting_items)
        payload["source_refs"] = list(self.source_refs)
        return payload


@dataclass(frozen=True)
class InterventionPrimitive:
    active: bool
    intervention_id: str
    label: str
    summary: str
    status: str
    source: str
    recent_feedback: str
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_refs"] = list(self.source_refs)
        return payload


@dataclass(frozen=True)
class OutcomePrimitive:
    status: str
    summary: str
    latest_signal: str
    trend: str
    source: str
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_refs"] = list(self.source_refs)
        return payload


@dataclass(frozen=True)
class SemanticPrimitiveBundle:
    adapter_name: str
    vision: VisionPrimitive
    current_state: CurrentStatePrimitive
    obstacle: ObstaclePrimitive
    evidence: EvidencePrimitive
    intervention: InterventionPrimitive
    outcome: OutcomePrimitive

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "vision": self.vision.to_dict(),
            "current_state": self.current_state.to_dict(),
            "obstacle": self.obstacle.to_dict(),
            "evidence": self.evidence.to_dict(),
            "intervention": self.intervention.to_dict(),
            "outcome": self.outcome.to_dict(),
            "source_mapping": {key: list(value) for key, value in PRIMITIVE_SOURCE_MAPPING.items()},
        }


class SemanticDomainAdapter(Protocol):
    adapter_name: str

    def map_from_context(
        self,
        *,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        focused_memory: dict[str, Any] | None,
        progress_snapshot: dict[str, Any] | None,
        visible_update_context: dict[str, Any] | None,
        adaptation_records: list[dict[str, Any]] | None,
    ) -> SemanticPrimitiveBundle: ...


class StudyDomainSemanticAdapter:
    """Read-only adapter from current study-domain context to universal primitives."""

    adapter_name = "study_domain_v1"

    def map_from_context(
        self,
        *,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        focused_memory: dict[str, Any] | None,
        progress_snapshot: dict[str, Any] | None,
        visible_update_context: dict[str, Any] | None,
        adaptation_records: list[dict[str, Any]] | None,
    ) -> SemanticPrimitiveBundle:
        user_context = _as_dict(user_context_payload)
        plan_context = _as_dict(plan_context)
        focused_memory = _as_dict(focused_memory or user_context.get("focused_memory"))
        progress_snapshot = _as_dict(progress_snapshot or user_context.get("progress_snapshot"))
        visible_update_context = _as_dict(visible_update_context)
        adaptation_records = [item for item in _as_list(adaptation_records or user_context.get("adaptation_records")) if isinstance(item, dict)]

        profile_context = _as_dict(user_context.get("profile_context"))
        knowledge_summary = _as_dict(profile_context.get("knowledge_summary") or user_context.get("knowledge_summary"))
        cognitive_summary = _as_dict(profile_context.get("cognitive_summary"))
        cognitive_insights = _as_dict(user_context.get("cognitive_insights"))
        context_focus = _as_dict(user_context.get("context_focus"))
        dual_core_snapshot = _as_dict(user_context.get("dual_core_snapshot"))
        dual_core_decision = _as_dict(dual_core_snapshot.get("decision"))
        dual_core_signals = _as_dict(dual_core_snapshot.get("signal_snapshot"))

        active_goals = [item for item in _as_list(user_context.get("active_goals") or focused_memory.get("active_goals")) if isinstance(item, dict)]
        active_plans = [item for item in _as_list(user_context.get("active_plans")) if isinstance(item, dict)]
        weak_spots = [item for item in _as_list(knowledge_summary.get("weak_spots")) if isinstance(item, dict)]
        mastery_changes = [item for item in _as_list(knowledge_summary.get("recent_mastery_changes")) if isinstance(item, dict)]
        active_patterns = [item for item in _as_list(cognitive_summary.get("active_patterns")) if isinstance(item, dict)]
        top_patterns = [item for item in _as_list(cognitive_insights.get("top_patterns")) if isinstance(item, dict)]
        active_interventions = [
            item
            for item in _as_list(user_context.get("active_interventions") or visible_update_context.get("active_interventions"))
            if isinstance(item, dict)
        ]
        last_feedback_binding = _as_dict(user_context.get("last_feedback_binding") or visible_update_context.get("last_feedback_binding"))

        return SemanticPrimitiveBundle(
            adapter_name=self.adapter_name,
            vision=self._build_vision(user_context=user_context, plan_context=plan_context, active_goals=active_goals, active_plans=active_plans),
            current_state=self._build_current_state(
                user_context=user_context,
                plan_context=plan_context,
                progress_snapshot=progress_snapshot,
                knowledge_summary=knowledge_summary,
                context_focus=context_focus,
                dual_core_signals=dual_core_signals,
            ),
            obstacle=self._build_obstacle(
                user_context=user_context,
                plan_context=plan_context,
                progress_snapshot=progress_snapshot,
                cognitive_insights=cognitive_insights,
                active_patterns=active_patterns,
                top_patterns=top_patterns,
                weak_spots=weak_spots,
                dual_core_signals=dual_core_signals,
            ),
            evidence=self._build_evidence(
                user_context=user_context,
                progress_snapshot=progress_snapshot,
                mastery_changes=mastery_changes,
                weak_spots=weak_spots,
                active_patterns=active_patterns,
                visible_update_context=visible_update_context,
                adaptation_records=adaptation_records,
            ),
            intervention=self._build_intervention(
                active_interventions=active_interventions,
                adaptation_records=adaptation_records,
                visible_update_context=visible_update_context,
                last_feedback_binding=last_feedback_binding,
            ),
            outcome=self._build_outcome(
                mastery_changes=mastery_changes,
                adaptation_records=adaptation_records,
                last_feedback_binding=last_feedback_binding,
            ),
        )

    def _build_vision(
        self,
        *,
        user_context: dict[str, Any],
        plan_context: dict[str, Any],
        active_goals: list[dict[str, Any]],
        active_plans: list[dict[str, Any]],
    ) -> VisionPrimitive:
        primary_goal = ""
        if active_goals:
            primary_goal = _strip(active_goals[0].get("title") or active_goals[0].get("name"))
        if not primary_goal:
            primary_goal = _strip(plan_context.get("goal") or plan_context.get("plan_description"))

        active_plan = _strip(plan_context.get("plan_title") or plan_context.get("title") or plan_context.get("name"))
        if not active_plan and active_plans:
            active_plan = _strip(active_plans[0].get("title") or active_plans[0].get("name"))

        global_compass = _as_dict(user_context.get("global_compass") or user_context.get("card_protocol"))
        north_star = _strip(global_compass.get("north_star") or global_compass.get("summary"))

        urgency = _as_dict(user_context.get("exam_urgency"))
        why_now = ""
        if urgency.get("days_left") is not None:
            why_now = f"倒计时 {urgency.get('days_left')} 天"
        elif active_plan and _strip(plan_context.get("plan_stage")):
            why_now = f"当前处于{_strip(plan_context.get('plan_stage'))}阶段"
        elif _strip(user_context.get("learning_gaps_summary")):
            why_now = _compact_text(user_context.get("learning_gaps_summary"), limit=80)

        return VisionPrimitive(
            primary_goal=primary_goal,
            active_plan=active_plan,
            north_star=north_star,
            why_now=why_now,
            source_refs=("MemoryGoal", "Plan", "GlobalCompass"),
        )

    def _build_current_state(
        self,
        *,
        user_context: dict[str, Any],
        plan_context: dict[str, Any],
        progress_snapshot: dict[str, Any],
        knowledge_summary: dict[str, Any],
        context_focus: dict[str, Any],
        dual_core_signals: dict[str, Any],
    ) -> CurrentStatePrimitive:
        analytics = _as_dict(user_context.get("analytics_summary"))
        focus_stats = _as_dict(user_context.get("focus_stats"))
        active_subjects = [_strip(item) for item in _as_list(knowledge_summary.get("active_learning_subjects")) if _strip(item)]
        progress_highlights = [_strip(item) for item in _as_list(progress_snapshot.get("highlights")) if _strip(item)]
        learning_gaps = _strip(user_context.get("learning_gaps_summary"))
        route_intent = _strip(context_focus.get("route_intent") or dual_core_signals.get("intent") or "chat")
        focus_mode = _strip(context_focus.get("focus_mode") or "general_focus")
        plan_stage = _strip(plan_context.get("plan_stage") or plan_context.get("status"))
        capacity_signal = ""
        if focus_stats.get("total_minutes") or focus_stats.get("pomodoro_count"):
            capacity_signal = (
                f"今日专注 {int(focus_stats.get('total_minutes', 0) or 0)} 分钟，番茄钟 {int(focus_stats.get('pomodoro_count', 0) or 0)} 次"
            )

        state_lines = [item for item in (learning_gaps, progress_highlights[0] if progress_highlights else "", capacity_signal) if item]

        return CurrentStatePrimitive(
            mode=route_intent,
            focus_channel=focus_mode,
            phase=plan_stage,
            route_intent=route_intent,
            focus_mode=focus_mode,
            plan_stage=plan_stage,
            learning_state=learning_gaps,
            progress_signal=progress_highlights[0] if progress_highlights else "",
            capacity_signal=capacity_signal,
            active_domains=tuple(active_subjects[:3]),
            snapshot="；".join(state_lines[:2]),
            source_refs=("UserContext", "ProfileContext", "PlanState", "focus_stats"),
        )

    def _build_obstacle(
        self,
        *,
        user_context: dict[str, Any],
        plan_context: dict[str, Any],
        progress_snapshot: dict[str, Any],
        cognitive_insights: dict[str, Any],
        active_patterns: list[dict[str, Any]],
        top_patterns: list[dict[str, Any]],
        weak_spots: list[dict[str, Any]],
        dual_core_signals: dict[str, Any],
    ) -> ObstaclePrimitive:
        guidance = _strip(dual_core_signals.get("current_guidance"))
        plan_health = _strip(dual_core_signals.get("plan_health_status"))
        learning_gap = _strip(user_context.get("learning_gaps_summary"))
        attention_areas = [_strip(item) for item in _as_list(progress_snapshot.get("attention_areas")) if _strip(item)]
        pattern = top_patterns[0] if top_patterns else (active_patterns[0] if active_patterns else {})
        pattern_name = _strip(pattern.get("pattern_name") or pattern.get("raw_pattern_name"))
        pattern_description = _compact_text(pattern.get("description"), limit=100)
        weak_spot = weak_spots[0] if weak_spots else {}
        weak_spot_name = _strip(weak_spot.get("node_name") or weak_spot.get("node_id"))
        weak_spot_mastery = _format_mastery(weak_spot.get("mastery")) if weak_spot else ""

        if guidance:
            return ObstaclePrimitive(
                label="current_guidance",
                summary=guidance,
                obstacle_type="guidance_gap",
                source="dual_core_signal_snapshot.current_guidance",
                confidence=0.82,
                source_refs=("CognitiveFragment", "PlanState"),
            )
        if learning_gap:
            return ObstaclePrimitive(
                label="learning_gap",
                summary=_compact_text(learning_gap, limit=110),
                obstacle_type="knowledge_gap",
                source="user_context.learning_gaps_summary",
                confidence=0.78,
                source_refs=("ErrorRecord", "UserContext"),
            )
        if pattern_name or pattern_description:
            return ObstaclePrimitive(
                label=pattern_name or "behavior_pattern",
                summary=pattern_description or f"当前主要阻力与「{pattern_name}」有关。",
                obstacle_type="behavior_pattern",
                source="cognitive_insights/top_patterns",
                confidence=float(pattern.get("confidence") or 0.7),
                source_refs=("BehaviorPattern", "CognitiveFragment"),
            )
        if attention_areas:
            return ObstaclePrimitive(
                label="attention_area",
                summary=_compact_text(attention_areas[0], limit=110),
                obstacle_type="progress_risk",
                source="progress_snapshot.attention_areas",
                confidence=0.68,
                source_refs=("PlanState", "StudyRecord"),
            )
        if weak_spot_name:
            return ObstaclePrimitive(
                label=weak_spot_name,
                summary=f"{weak_spot_name} 仍是薄弱点，当前掌握度约 {weak_spot_mastery}。",
                obstacle_type="skill_gap",
                source="profile_context.knowledge_summary.weak_spots",
                confidence=0.63,
                source_refs=("ErrorRecord", "UserNodeStatus"),
            )
        if plan_health:
            return ObstaclePrimitive(
                label="plan_health",
                summary=f"当前计划健康度信号为 {plan_health}，说明推进节奏可能需要调整。",
                obstacle_type="plan_risk",
                source="dual_core_signal_snapshot.plan_health_status",
                confidence=0.58,
                source_refs=("PlanState",),
            )
        fallback = _strip(plan_context.get("goal") or plan_context.get("plan_description") or user_context.get("current_query"))
        return ObstaclePrimitive(
            label="current_turn_alignment",
            summary=_compact_text(fallback or "这轮需要先对齐用户当下最在意的问题。", limit=110),
            obstacle_type="alignment_gap",
            source="fallback",
            confidence=0.4,
            source_refs=("UserContext",),
        )

    def _build_evidence(
        self,
        *,
        user_context: dict[str, Any],
        progress_snapshot: dict[str, Any],
        mastery_changes: list[dict[str, Any]],
        weak_spots: list[dict[str, Any]],
        active_patterns: list[dict[str, Any]],
        visible_update_context: dict[str, Any],
        adaptation_records: list[dict[str, Any]],
    ) -> EvidencePrimitive:
        evidence_lines: list[str] = []
        highlights = [_strip(item) for item in _as_list(progress_snapshot.get("highlights")) if _strip(item)]
        for item in highlights[:2]:
            evidence_lines.append(_compact_text(item, limit=88))

        for change in mastery_changes[:2]:
            node_name = _strip(change.get("node_name") or change.get("node_id"))
            if not node_name:
                continue
            try:
                delta = float(change.get("new_mastery", 0.0) or 0.0) - float(change.get("old_mastery", 0.0) or 0.0)
                evidence_lines.append(f"{node_name} 最近掌握度变化约 +{delta:.1f}")
            except Exception:
                evidence_lines.append(f"{node_name} 最近有新的掌握度变化")

        proactive_opening = _strip(visible_update_context.get("proactive_opening_message"))
        if proactive_opening:
            evidence_lines.append(_compact_text(proactive_opening, limit=88))

        top_pattern = active_patterns[0] if active_patterns else {}
        pattern_name = _strip(top_pattern.get("pattern_name"))
        if pattern_name:
            evidence_lines.append(f"近期反复出现的模式: {pattern_name}")

        if not evidence_lines and weak_spots:
            first_spot = weak_spots[0]
            node_name = _strip(first_spot.get("node_name") or first_spot.get("node_id"))
            if node_name:
                evidence_lines.append(f"{node_name} 仍是当前最明显的薄弱点")

        if adaptation_records:
            recent = adaptation_records[0]
            label = _strip(recent.get("strategy_name") or recent.get("name"))
            status = _strip(recent.get("effectiveness") or recent.get("outcome") or recent.get("status"))
            if label:
                evidence_lines.append(_compact_text(f"最近一次支持动作: {label} ({status or 'pending'})", limit=88))

        summary = evidence_lines[0] if evidence_lines else _strip(user_context.get("progress_narrative"))

        return EvidencePrimitive(
            summary=summary,
            freshest_items=tuple(evidence_lines[:4]),
            progress_highlights=tuple(highlights[:2]),
            supporting_items=tuple(
                [_strip(item) for item in _as_list(user_context.get("evolution_highlights")) if _strip(item)][:2]
            ),
            source_refs=("UserNodeStatus", "StudyRecord", "progress_narrative", "retrieved_passages"),
        )

    def _build_intervention(
        self,
        *,
        active_interventions: list[dict[str, Any]],
        adaptation_records: list[dict[str, Any]],
        visible_update_context: dict[str, Any],
        last_feedback_binding: dict[str, Any],
    ) -> InterventionPrimitive:
        active = active_interventions[0] if active_interventions else {}
        recent = adaptation_records[0] if adaptation_records else {}
        intervention_id = _strip(active.get("intervention_id") or last_feedback_binding.get("intervention_id"))
        label = _strip(
            active.get("label")
            or active.get("trigger_type")
            or recent.get("strategy_name")
            or recent.get("name")
            or visible_update_context.get("proactive_opening_message")
        )
        status = _strip(
            active.get("acceptance_status")
            or active.get("outcome_status")
            or recent.get("effectiveness")
            or recent.get("status")
        )
        feedback = _strip(last_feedback_binding.get("sentiment") or last_feedback_binding.get("reason"))
        source = _strip(active.get("source") or ("adaptation_records" if recent else "visible_update_context"))

        summary = ""
        if intervention_id or label:
            summary = _compact_text(
                f"当前正在跟踪的支持动作是「{label or intervention_id}」"
                + (f"，状态 {status}" if status else "")
                + (f"，最近反馈 {feedback}" if feedback else ""),
                limit=120,
            )
        elif _strip(visible_update_context.get("post_adaptation_question")):
            summary = _compact_text(visible_update_context.get("post_adaptation_question"), limit=120)

        return InterventionPrimitive(
            active=bool(intervention_id or label),
            intervention_id=intervention_id,
            label=label,
            summary=summary,
            status=status,
            source=source,
            recent_feedback=feedback,
            source_refs=("InterventionRecord", "adaptive_replanner_records", "visible_intelligence_messages"),
        )

    def _build_outcome(
        self,
        *,
        mastery_changes: list[dict[str, Any]],
        adaptation_records: list[dict[str, Any]],
        last_feedback_binding: dict[str, Any],
    ) -> OutcomePrimitive:
        recent = adaptation_records[0] if adaptation_records else {}
        sentiment = _strip(last_feedback_binding.get("sentiment"))
        feedback_words = _compact_text(last_feedback_binding.get("user_words"), limit=72)
        recent_effect = _strip(recent.get("effectiveness") or recent.get("outcome") or recent.get("status"))

        mastery_signal = ""
        if mastery_changes:
            change = mastery_changes[0]
            node_name = _strip(change.get("node_name") or change.get("node_id"))
            if node_name:
                try:
                    delta = float(change.get("new_mastery", 0.0) or 0.0) - float(change.get("old_mastery", 0.0) or 0.0)
                    mastery_signal = f"{node_name} 最近掌握度变化约 +{delta:.1f}"
                except Exception:
                    mastery_signal = f"{node_name} 最近有掌握度变化"

        latest_signal = feedback_words or sentiment or recent_effect or mastery_signal
        trend = "unclear"
        status = "pending"
        source = "fallback"
        if sentiment in {"helped", "accepted"} or recent_effect in {"accepted", "effective"}:
            trend = "improving"
            status = "progressing"
            source = "feedback_binding"
        elif sentiment in {"dismissed", "not_helped"} or recent_effect in {"dismissed", "ineffective"}:
            trend = "blocked"
            status = "stalled"
            source = "feedback_binding"
        elif sentiment == "mixed" or recent_effect == "mixed":
            trend = "mixed"
            status = "mixed"
            source = "feedback_binding"
        elif mastery_signal:
            trend = "improving"
            status = "emerging"
            source = "mastery_changes"

        summary = ""
        if latest_signal:
            summary = _compact_text(f"最近结果信号显示 {latest_signal}", limit=120)
        elif recent_effect:
            summary = _compact_text(f"最近一轮支持动作的结果是 {recent_effect}", limit=120)

        return OutcomePrimitive(
            status=status,
            summary=summary,
            latest_signal=latest_signal,
            trend=trend,
            source=source,
            source_refs=("InterventionStrategyOutcome", "mastery_changes", "feedback_binding"),
        )
