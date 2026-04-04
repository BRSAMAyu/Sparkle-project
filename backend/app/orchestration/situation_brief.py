from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone, datetime
from typing import Any

from app.semantic.state_primitives import StudyDomainSemanticAdapter


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    if value is None:
        return []
    return list(value) if isinstance(value, tuple) else []


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _compact_text(value: Any, *, limit: int = 160) -> str:
    text = " ".join(_strip(value).split())
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    raw = _strip(value)
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _freshness_bucket(score: float) -> str:
    if score >= 0.75:
        return "fresh"
    if score >= 0.45:
        return "mixed"
    return "stale"


def _confidence_bucket(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


@dataclass
class SituationBrief:
    focus_question: str
    summary: str
    vision: dict[str, Any]
    current_state: dict[str, Any]
    primary_obstacle: dict[str, Any]
    evidence: dict[str, Any]
    intervention: dict[str, Any]
    outcome: dict[str, Any]
    sparkle_self_state: dict[str, Any]
    recommended_stance: dict[str, Any]
    semantic_primitives: dict[str, Any]
    source_trace: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "focus_question": self.focus_question,
            "summary": self.summary,
            "vision": self.vision,
            "current_state": self.current_state,
            "obstacle": self.primary_obstacle,
            "primary_obstacle": self.primary_obstacle,
            "evidence": self.evidence,
            "intervention": self.intervention,
            "outcome": self.outcome,
            "sparkle_self_state": self.sparkle_self_state,
            "recommended_stance": self.recommended_stance,
            "semantic_primitives": self.semantic_primitives,
            "source_trace": self.source_trace,
        }


class SituationBriefBuilder:
    """Build a compact read-model from already assembled orchestration context."""

    def build(
        self,
        *,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        focused_memory: dict[str, Any] | None,
        context_briefing_note: str | None,
        visible_update_context: dict[str, Any] | None,
        dual_core_snapshot: dict[str, Any] | None,
        session_feedback_signal: dict[str, Any] | None,
        progress_snapshot: dict[str, Any] | None = None,
        adaptation_records: list[dict[str, Any]] | None = None,
    ) -> SituationBrief:
        user_context = _as_dict(user_context_payload)
        plan_context = _as_dict(plan_context)
        focused_memory = _as_dict(focused_memory or user_context.get("focused_memory"))
        visible_update_context = _as_dict(visible_update_context)
        dual_core_snapshot = _as_dict(dual_core_snapshot)
        session_feedback_signal = _as_dict(session_feedback_signal)
        progress_snapshot = _as_dict(progress_snapshot or user_context.get("progress_snapshot"))
        adaptation_records = [
            record for record in _as_list(adaptation_records or user_context.get("adaptation_records")) if isinstance(record, dict)
        ]

        context_focus = _as_dict(user_context.get("context_focus"))
        user_strategy_state = _as_dict(user_context.get("user_strategy_state"))
        dual_core_decision = _as_dict(dual_core_snapshot.get("decision"))
        dual_core_instruction = _strip(dual_core_snapshot.get("prompt_instruction"))
        semantic_context_payload = dict(user_context)
        if dual_core_snapshot:
            semantic_context_payload["dual_core_snapshot"] = dual_core_snapshot
        semantic_primitives = StudyDomainSemanticAdapter().map_from_context(
            user_context_payload=semantic_context_payload,
            plan_context=plan_context,
            focused_memory=focused_memory,
            progress_snapshot=progress_snapshot,
            visible_update_context=visible_update_context,
            adaptation_records=adaptation_records,
        ).to_dict()

        vision = _as_dict(semantic_primitives.get("vision"))
        current_state = _as_dict(semantic_primitives.get("current_state"))
        primary_obstacle = _as_dict(semantic_primitives.get("obstacle"))
        evidence = _as_dict(semantic_primitives.get("evidence"))
        intervention = _as_dict(semantic_primitives.get("intervention"))
        outcome = _as_dict(semantic_primitives.get("outcome"))

        source_trace = self._build_source_trace(
            user_context=user_context,
            plan_context=plan_context,
            progress_snapshot=progress_snapshot,
            dual_core_decision=dual_core_decision,
            visible_update_context=visible_update_context,
            context_briefing_note=context_briefing_note,
            semantic_primitives=semantic_primitives,
        )
        sparkle_self_state = self._build_sparkle_self_state(
            dual_core_decision=dual_core_decision,
            evidence=evidence,
            source_trace=source_trace,
            adaptation_records=adaptation_records,
            visible_update_context=visible_update_context,
        )
        recommended_stance = self._build_recommended_stance(
            context_focus=context_focus,
            dual_core_decision=dual_core_decision,
            dual_core_instruction=dual_core_instruction,
            session_feedback_signal=session_feedback_signal,
            visible_update_context=visible_update_context,
            primary_obstacle=primary_obstacle,
            user_strategy_state=user_strategy_state,
            intervention=intervention,
            outcome=outcome,
        )
        focus_question = self._build_focus_question(
            vision=vision,
            primary_obstacle=primary_obstacle,
            context_focus=context_focus,
        )
        summary = self._build_summary(
            vision=vision,
            current_state=current_state,
            primary_obstacle=primary_obstacle,
            evidence=evidence,
            intervention=intervention,
            outcome=outcome,
            recommended_stance=recommended_stance,
        )

        return SituationBrief(
            focus_question=focus_question,
            summary=summary,
            vision=vision,
            current_state=current_state,
            primary_obstacle=primary_obstacle,
            evidence=evidence,
            intervention=intervention,
            outcome=outcome,
            sparkle_self_state=sparkle_self_state,
            recommended_stance=recommended_stance,
            semantic_primitives=semantic_primitives,
            source_trace=source_trace,
        )

    def _build_source_trace(
        self,
        *,
        user_context: dict[str, Any],
        plan_context: dict[str, Any],
        progress_snapshot: dict[str, Any],
        dual_core_decision: dict[str, Any],
        visible_update_context: dict[str, Any],
        context_briefing_note: str | None,
        semantic_primitives: dict[str, Any],
    ) -> dict[str, Any]:
        used_sources: list[str] = []
        if _as_dict(user_context.get("profile_context")):
            used_sources.append("profile_context")
        if plan_context:
            used_sources.append("plan_context")
        if _as_dict(user_context.get("context_focus")):
            used_sources.append("context_focus")
        if dual_core_decision:
            used_sources.append("dual_core_snapshot")
        if progress_snapshot:
            used_sources.append("progress_snapshot")
        if visible_update_context:
            used_sources.append("visible_update_context")
        if _strip(context_briefing_note):
            used_sources.append("context_briefing_note")
        if semantic_primitives:
            used_sources.append("semantic_state_mapper")

        timestamps = [
            _parse_dt(progress_snapshot.get("generated_at")),
        ]
        timestamps = [item for item in timestamps if item is not None]
        freshness_score = 0.35
        if timestamps:
            freshest = max(timestamps)
            hours_old = max(0.0, (_utcnow() - freshest).total_seconds() / 3600.0)
            freshness_score = max(0.05, min(1.0, 1.0 - (hours_old / 120.0)))
        coherence_hits = sum(
            1
            for value in (
                _strip(user_context.get("learning_gaps_summary")),
                _strip(plan_context.get("goal") or plan_context.get("plan_title")),
                _strip((dual_core_decision or {}).get("mode")),
                _strip((progress_snapshot or {}).get("generated_at")),
            )
            if value
        )
        coherence_score = min(1.0, 0.25 + (coherence_hits * 0.18))

        return {
            "used_sources": used_sources,
            "missing_sources": [
                name
                for name, present in {
                    "progress_snapshot": bool(progress_snapshot),
                    "dual_core_snapshot": bool(dual_core_decision),
                    "profile_context": bool(_as_dict(user_context.get("profile_context"))),
                }.items()
                if not present
            ],
            "freshness": {
                "score": round(freshness_score, 2),
                "label": _freshness_bucket(freshness_score),
            },
            "coherence": {
                "score": round(coherence_score, 2),
                "label": "high" if coherence_score >= 0.75 else "medium" if coherence_score >= 0.5 else "low",
            },
            "semantic_layer": {
                "adapter_name": _strip(semantic_primitives.get("adapter_name")),
                "mapped_primitives": [
                    name
                    for name in ("vision", "current_state", "obstacle", "evidence", "intervention", "outcome")
                    if isinstance(semantic_primitives.get(name), dict) and semantic_primitives.get(name)
                ],
                "source_mapping": _as_dict(semantic_primitives).get("source_mapping", {}),
            },
        }

    def _build_sparkle_self_state(
        self,
        *,
        dual_core_decision: dict[str, Any],
        evidence: dict[str, Any],
        source_trace: dict[str, Any],
        adaptation_records: list[dict[str, Any]],
        visible_update_context: dict[str, Any],
    ) -> dict[str, Any]:
        freshness_score = float(_as_dict(source_trace.get("freshness")).get("score") or 0.0)
        coherence_score = float(_as_dict(source_trace.get("coherence")).get("score") or 0.0)
        source_count = len(_as_list(source_trace.get("used_sources")))
        evidence_count = len(_as_list(evidence.get("freshest_items")))
        confidence = min(
            0.95,
            0.25 + (source_count * 0.08) + (evidence_count * 0.07) + (freshness_score * 0.22) + (coherence_score * 0.18),
        )
        recent_effect = ""
        if adaptation_records:
            first = adaptation_records[0]
            recent_effect = _strip(first.get("effectiveness") or first.get("outcome") or first.get("status"))
        if not recent_effect:
            recent_effect = _strip(visible_update_context.get("post_adaptation_question"))

        return {
            "dual_core_mode": _strip(dual_core_decision.get("mode") or "balanced"),
            "recent_intervention_signal": recent_effect,
            "evidence_freshness": _freshness_bucket(freshness_score),
            "confidence_estimate": round(confidence, 2),
            "confidence_label": _confidence_bucket(confidence),
        }

    def _build_recommended_stance(
        self,
        *,
        context_focus: dict[str, Any],
        dual_core_decision: dict[str, Any],
        dual_core_instruction: str,
        session_feedback_signal: dict[str, Any],
        visible_update_context: dict[str, Any],
        primary_obstacle: dict[str, Any],
        user_strategy_state: dict[str, Any],
        intervention: dict[str, Any],
        outcome: dict[str, Any],
    ) -> dict[str, Any]:
        focus_mode = _strip(context_focus.get("focus_mode") or "general_focus")
        dual_core_mode = _strip(dual_core_decision.get("mode") or "balanced")
        feedback_type = _strip(session_feedback_signal.get("signal_type"))
        strategy_mode = _strip(user_strategy_state.get("session_mode"))
        explanation_style = _strip(user_strategy_state.get("explanation_style"))
        retrieval_emphasis = _strip(user_strategy_state.get("retrieval_emphasis"))
        intervention_status = _strip(intervention.get("status"))
        outcome_status = _strip(outcome.get("status"))

        if strategy_mode == "recovery":
            stance = "先减负、稳住情绪和节奏，再给最小可执行下一步。"
        elif focus_mode == "emotional_focus" or dual_core_mode == "cognitive_first":
            stance = "先承接状态，再把下一步压到足够轻。"
        elif feedback_type == "simplify":
            stance = "先给结论和下一步，避免展开过多背景。"
        elif feedback_type == "mismatch":
            stance = "先纠正方向，再重新对齐当前诉求。"
        elif dual_core_mode == "execution_first":
            stance = "先推进执行，再补最少必要解释。"
        else:
            stance = "先抓住最关键阻力，再给结构化推进。"

        if intervention_status and outcome_status in {"stalled", "mixed"}:
            stance = "先校准前一轮支持动作哪里没贴合，再给更轻更准的下一步。"

        opening_move = _strip(
            visible_update_context.get("proactive_opening_message")
            or visible_update_context.get("pending_observation")
        )

        return {
            "stance": stance,
            "focus_mode": focus_mode,
            "dual_core_mode": dual_core_mode,
            "response_shape": feedback_type or "steady",
            "opening_move": opening_move,
            "instruction": _compact_text(dual_core_instruction, limit=160),
            "obstacle_anchor": _strip(primary_obstacle.get("label")),
            "strategy_mode": strategy_mode,
            "explanation_style": explanation_style,
            "retrieval_emphasis": retrieval_emphasis,
        }

    def _build_focus_question(
        self,
        *,
        vision: dict[str, Any],
        primary_obstacle: dict[str, Any],
        context_focus: dict[str, Any],
    ) -> str:
        goal = _strip(vision.get("primary_goal") or vision.get("active_plan"))
        obstacle = _strip(primary_obstacle.get("summary") or primary_obstacle.get("label"))
        focus_mode = _strip(context_focus.get("focus_mode"))
        if focus_mode == "emotional_focus":
            return "用户现在最需要先被承接的是什么，以及怎样把它转换成最轻的下一步？"
        if goal and obstacle:
            return f"为了继续推进「{goal}」，这轮最该先处理的阻力是什么，为什么是现在？"
        if obstacle:
            return f"这轮为什么要先处理「{obstacle}」？"
        return "这轮对用户最重要的事是什么，为什么是现在？"

    def _build_summary(
        self,
        *,
        vision: dict[str, Any],
        current_state: dict[str, Any],
        primary_obstacle: dict[str, Any],
        evidence: dict[str, Any],
        intervention: dict[str, Any],
        outcome: dict[str, Any],
        recommended_stance: dict[str, Any],
    ) -> str:
        goal = _strip(vision.get("primary_goal") or vision.get("active_plan") or "当前目标")
        current_snapshot = _strip(current_state.get("snapshot"))
        obstacle = _strip(primary_obstacle.get("summary") or primary_obstacle.get("label") or "当前阻力")
        evidence_item = _strip(evidence.get("summary"))
        intervention_summary = _strip(intervention.get("summary") or intervention.get("label"))
        outcome_summary = _strip(outcome.get("summary") or outcome.get("latest_signal"))
        stance = _strip(recommended_stance.get("stance"))

        parts = [f"目标图景是「{goal}」"]
        if current_snapshot:
            parts.append(f"当前状态是 {current_snapshot}")
        parts.append(f"主要阻力是 {obstacle}")
        if evidence_item:
            parts.append(f"最近证据是 {evidence_item}")
        if intervention_summary:
            parts.append(f"当前干预是 {intervention_summary}")
        elif outcome_summary:
            parts.append(f"最近结果是 {outcome_summary}")
        if stance:
            parts.append(f"本轮宜 {stance}")
        return "；".join(parts[:6]) + "。"


def format_situation_brief_section(brief: SituationBrief | dict[str, Any] | None) -> str:
    payload = brief.to_dict() if isinstance(brief, SituationBrief) else _as_dict(brief)
    if not payload:
        return ""

    summary = _compact_text(payload.get("summary"), limit=220)
    focus_question = _compact_text(payload.get("focus_question"), limit=120)
    semantic_primitives = _as_dict(payload.get("semantic_primitives"))
    vision = _as_dict(payload.get("vision") or semantic_primitives.get("vision"))
    current_state = _as_dict(payload.get("current_state") or semantic_primitives.get("current_state"))
    obstacle = _as_dict(payload.get("obstacle") or payload.get("primary_obstacle") or semantic_primitives.get("obstacle"))
    evidence = _as_dict(payload.get("evidence") or semantic_primitives.get("evidence"))
    intervention = _as_dict(payload.get("intervention") or semantic_primitives.get("intervention"))
    outcome = _as_dict(payload.get("outcome") or semantic_primitives.get("outcome"))
    stance = _as_dict(payload.get("recommended_stance"))

    current_line_parts = [
        _strip(current_state.get("snapshot")),
        _strip(vision.get("why_now")),
    ]
    current_line = "；".join(part for part in current_line_parts if part)
    evidence_items = [_compact_text(item, limit=80) for item in _as_list(evidence.get("freshest_items")) if _strip(item)]
    evidence_line = "；".join(evidence_items[:2])

    goal = _strip(vision.get("primary_goal") or vision.get("active_plan"))
    active_plan = _strip(vision.get("active_plan"))
    if goal and active_plan and active_plan != goal:
        header_goal = f"目标图景: {goal} / 当前计划 {active_plan}"
    elif goal:
        header_goal = f"目标图景: {goal}"
    elif active_plan:
        header_goal = f"目标图景: {active_plan}"
    else:
        header_goal = "目标图景: 先对齐本轮最重要的方向"

    lines = [
        "## Situation Brief [L0 简报]",
        "先用这份简报判断这轮最重要的事，再决定是否展开更广的画像背景。",
        f"- 聚焦问题: {focus_question or '这轮最重要的事是什么，为什么是现在？'}",
        f"- {header_goal}",
    ]
    if summary:
        lines.append(f"- 判断摘要: {summary}")
    if current_line:
        lines.append(f"- 当前状态: {current_line}")
    obstacle_line = _strip(obstacle.get("summary") or obstacle.get("label"))
    if obstacle_line:
        lines.append(f"- 主要阻力: {obstacle_line}")
    if evidence_line:
        lines.append(f"- 最新证据: {evidence_line}")
    intervention_line = _strip(intervention.get("summary") or intervention.get("label"))
    if intervention_line:
        lines.append(f"- 当前干预: {intervention_line}")
    outcome_line = _strip(outcome.get("summary") or outcome.get("latest_signal"))
    if outcome_line:
        lines.append(f"- 最近结果: {outcome_line}")
    stance_line = _strip(stance.get("stance"))
    if stance_line:
        lines.append(f"- 本轮站位: {stance_line}")
    return "\n" + "\n".join(lines[:11])
