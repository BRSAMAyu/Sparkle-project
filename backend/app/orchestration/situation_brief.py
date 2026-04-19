from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timezone, datetime
from typing import Any
import re

from app.orchestration.learning_state_fragment import build_learning_state_fragment
from app.orchestration.planning_intent import detect_planning_like_turn
from app.orchestration.plan_quality_contract import build_plan_quality_contract
from app.orchestration.ai_strategy_renderer import build_semantic_control, format_semantic_control_lines
from app.orchestration.capability_requirement_compiler import CapabilityRequirementCompiler
from app.orchestration.capability_selection_policy import CapabilitySelectionPolicy
from app.orchestration.decision_policy import DecisionPolicyCompiler
from app.orchestration.planning_strategy_compiler import PlanningStrategyCompiler
from app.orchestration.residual_diagnosis import ResidualDiagnosisRuntime
from app.semantic.state_primitives import StudyDomainSemanticAdapter
from app.services.capability_registry_service import CapabilityRegistryService


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


def _extract_cognitive_context(value: dict[str, Any]) -> dict[str, Any]:
    payload = value.get("cognitive_context") if isinstance(value, dict) else None
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}


def _recent_pain_points(user_context: dict[str, Any]) -> list[str]:
    cognitive_context = _extract_cognitive_context(user_context)
    summary = user_context.get("error_summary")
    if not isinstance(summary, dict):
        summary = cognitive_context.get("error_summary")
    recent_errors = user_context.get("recent_errors")
    if not isinstance(recent_errors, list):
        recent_errors = cognitive_context.get("recent_errors")

    points: list[str] = []
    if isinstance(summary, dict) and summary:
        parts: list[str] = []
        total_errors = summary.get("total_errors")
        if total_errors is not None:
            parts.append(f"累计错题 {int(total_errors)}")
        need_review = summary.get("need_review_count") or summary.get("due_for_review")
        if need_review is not None:
            parts.append(f"待复习 {int(need_review)}")
        subject_distribution = summary.get("subject_distribution")
        if isinstance(subject_distribution, dict) and subject_distribution:
            ranked = sorted(
                (
                    (str(subject).strip(), int(count))
                    for subject, count in subject_distribution.items()
                    if str(subject).strip()
                ),
                key=lambda item: (-item[1], item[0]),
            )
            if ranked:
                parts.append(f"高频科目 {ranked[0][0]}")
        if parts:
            points.append("；".join(parts))

    for item in recent_errors or []:
        if not isinstance(item, dict):
            continue
        preview = _strip(item.get("question_preview") or item.get("title"))
        subject = _strip(item.get("subject"))
        error_type = _strip(item.get("error_type"))
        detail = " / ".join(part for part in (subject, error_type) if part)
        points.append(f"{preview or '最近有一道题反复卡住'}{f'（{detail}）' if detail else ''}")
        if len(points) >= 3:
            break
    return points[:3]


def _recent_wins(user_context: dict[str, Any]) -> list[str]:
    cognitive_context = _extract_cognitive_context(user_context)
    mastery_changes = user_context.get("recent_mastery_changes")
    if not isinstance(mastery_changes, list):
        mastery_changes = cognitive_context.get("recent_mastery_changes")
    if not isinstance(mastery_changes, list):
        profile_context = _as_dict(user_context.get("profile_context"))
        mastery_changes = _as_dict(profile_context.get("knowledge_summary")).get("recent_mastery_changes")

    wins: list[str] = []
    for item in mastery_changes or []:
        if not isinstance(item, dict):
            continue
        node_name = _strip(item.get("node_name") or item.get("node_id"))
        if not node_name:
            continue
        old_mastery = item.get("old_mastery")
        new_mastery = item.get("new_mastery")
        if old_mastery is None or new_mastery is None:
            wins.append(f"{node_name} 最近有明显进步")
        else:
            try:
                wins.append(
                    f"{node_name} 掌握度从 {float(old_mastery):.0f}% 提升到 {float(new_mastery):.0f}%"
                )
            except Exception:
                wins.append(f"{node_name} 掌握度从 {old_mastery} 提升到 {new_mastery}")
        if len(wins) >= 3:
            break
    return wins[:3]


def _merge_signal_evidence(
    evidence: dict[str, Any],
    user_context: dict[str, Any],
    *,
    learning_state_fragment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(evidence or {})
    freshest_items = [_strip(item) for item in _as_list(merged.get("freshest_items")) if _strip(item)]
    fragment = _as_dict(learning_state_fragment)
    pain_points = [
        _strip(item)
        for item in _as_list(fragment.get("recent_pain_points"))[:3]
        if _strip(item)
    ] or _recent_pain_points(user_context)
    recent_wins = [
        _strip(item)
        for item in _as_list(fragment.get("recent_wins"))[:3]
        if _strip(item)
    ] or _recent_wins(user_context)

    for item in pain_points:
        marker = f"近期痛点：{item}"
        if marker not in freshest_items:
            freshest_items.append(marker)
    for item in recent_wins:
        marker = f"近期进展：{item}"
        if marker not in freshest_items:
            freshest_items.append(marker)

    merged["freshest_items"] = freshest_items[:5]
    if pain_points:
        merged["recent_pain_points"] = pain_points
    if recent_wins:
        merged["recent_wins"] = recent_wins

    summary_parts = [_strip(merged.get("summary"))]
    if pain_points:
        summary_parts.append(f"近期痛点：{pain_points[0]}")
    if recent_wins:
        summary_parts.append(f"近期进展：{recent_wins[0]}")
    merged["summary"] = "；".join(part for part in summary_parts if part)
    return merged


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
    learning_state_fragment: dict[str, Any]
    intervention: dict[str, Any]
    outcome: dict[str, Any]
    sparkle_self_state: dict[str, Any]
    recommended_stance: dict[str, Any]
    decision_context: dict[str, Any]
    semantic_control: dict[str, Any]
    semantic_primitives: dict[str, Any]
    source_trace: dict[str, Any]
    insight_state: dict[str, Any] = field(default_factory=dict)
    planning_strategy: dict[str, Any] = field(default_factory=dict)
    outcome_learning: dict[str, Any] = field(default_factory=dict)
    five_layer_growth: dict[str, Any] = field(default_factory=dict)
    body_map: dict[str, Any] = field(default_factory=dict)
    capability_requirements: dict[str, Any] = field(default_factory=dict)
    capability_selection: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "focus_question": self.focus_question,
            "summary": self.summary,
            "vision": self.vision,
            "current_state": self.current_state,
            "obstacle": self.primary_obstacle,
            "primary_obstacle": self.primary_obstacle,
            "evidence": self.evidence,
            "learning_state_fragment": self.learning_state_fragment,
            "intervention": self.intervention,
            "outcome": self.outcome,
            "sparkle_self_state": self.sparkle_self_state,
            "recommended_stance": self.recommended_stance,
            "decision_context": self.decision_context,
            "semantic_control": self.semantic_control,
            "semantic_primitives": self.semantic_primitives,
            "source_trace": self.source_trace,
            "insight_state": self.insight_state,
            "planning_strategy": self.planning_strategy,
            "outcome_learning": self.outcome_learning,
            "five_layer_growth": self.five_layer_growth,
            "body_map": self.body_map,
            "capability_requirements": self.capability_requirements,
            "capability_selection": self.capability_selection,
        }


class SituationBriefBuilder:
    """Build a compact read-model from already assembled orchestration context."""

    async def build(
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
        learning_state_fragment = build_learning_state_fragment(user_context=user_context).to_dict()
        evidence = _merge_signal_evidence(
            _as_dict(semantic_primitives.get("evidence")),
            user_context,
            learning_state_fragment=learning_state_fragment,
        )
        intervention = _as_dict(semantic_primitives.get("intervention"))
        outcome = _as_dict(semantic_primitives.get("outcome"))
        outcome_learning = _as_dict(
            user_context.get("outcome_learning")
            or user_context.get("validated_outcome_learning")
            or _as_dict(user_context.get("plan_state_facts")).get("validated_outcome_learning")
            or plan_context.get("outcome_learning")
            or _as_dict(plan_context.get("facts")).get("validated_outcome_learning")
        )

        # Phase A: User Insight Engine
        profile_context_raw = user_context.get("profile_context")
        from app.core.profile_context import ProfileContext
        profile_context = None
        if isinstance(profile_context_raw, dict):
            profile_context = ProfileContext(**profile_context_raw)
        elif hasattr(profile_context_raw, "model_dump"):
             profile_context = profile_context_raw

        route_intent = _strip(context_focus.get("route_intent") or current_state.get("route_intent") or "plan")
        phase_a_planning_context = self._build_phase_a_planning_context(
            user_context=user_context,
            plan_context=plan_context,
            semantic_primitives=semantic_primitives,
            context_briefing_note=context_briefing_note,
            dual_core_instruction=dual_core_instruction,
        )
        phase_a_turn_signals = self._build_phase_a_turn_signals(
            planning_context=phase_a_planning_context,
            user_strategy_state=user_strategy_state,
        )

        insight_state: dict[str, Any] = {}
        if profile_context:
            from app.services.insight_gap_detector import InsightGapDetector
            from app.services.planning_readiness_gate import PlanningReadinessGate
            from app.services.profile_truth_compiler import ProfileTruthCompiler

            compiler = ProfileTruthCompiler()
            detector = InsightGapDetector()
            gate = PlanningReadinessGate()

            # 1. Compile Truth
            compiled_state = await compiler.compile(
                profile_context=profile_context,
                user_strategy_state=user_strategy_state,
                turn_signals=phase_a_turn_signals,
            )

            # 2. Detect Gaps
            gaps = await detector.detect_gaps(
                insight_state=compiled_state,
                user_message=_strip(phase_a_planning_context.get("user_message")),
                intent=route_intent or "plan",
                planning_context=phase_a_planning_context,
            )

            # 3. Evaluate Readiness
            readiness = gate.evaluate(insight_state=compiled_state, gaps=gaps)
            
            # 4. Generate Strategic Questions
            questions = detector.generate_questions(gaps)

            compiled_state.missing_information = list(gaps)
            compiled_state.key_uncertainties = [
                {"id": gap, "description": detector.PLANNING_GAPS.get(gap, gap)}
                for gap in gaps
            ]
            compiled_state.planning_readiness = dict(readiness)
            compiled_state.recommended_clarification = list(questions)

            insight_state = compiled_state.to_dict()
            insight_state.update(readiness)
            insight_state["recommended_clarification"] = list(questions)
        else:
            # Fallback for missing profile
            fallback_questions = ["你能先介绍一下你的背景或当前目标吗？"]
            readiness = {
                "readiness_level": "low",
                "readiness_score": 0.0,
                "recommended_action": "ask",
                "blocking_unknowns": ["profile_missing"],
                "blocking_contradictions": [],
                "ask_before_plan": True,
            }
            insight_state = {
                **readiness,
                "planning_readiness": readiness,
                "recommended_clarification": fallback_questions,
                "missing_information": ["profile_missing"],
                "key_uncertainties": [{"id": "profile_missing", "description": "Missing user profile context."}],
            }

        source_trace = self._build_source_trace(
            user_context=user_context,
            plan_context=plan_context,
            progress_snapshot=progress_snapshot,
            dual_core_decision=dual_core_decision,
            visible_update_context=visible_update_context,
            context_briefing_note=context_briefing_note,
            semantic_primitives=semantic_primitives,
            outcome_learning=outcome_learning,
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
        diagnosis = ResidualDiagnosisRuntime().diagnose(
            user_context_payload=user_context,
            plan_context=plan_context,
            context_briefing_note=context_briefing_note,
            visible_update_context=visible_update_context,
            session_feedback_signal=session_feedback_signal,
            user_strategy_state=user_strategy_state,
            vision=vision,
            current_state=current_state,
            primary_obstacle=primary_obstacle,
            evidence=evidence,
            intervention=intervention,
            outcome=outcome,
            sparkle_self_state=sparkle_self_state,
        ).to_dict()
        decision_policy = DecisionPolicyCompiler().compile(
            diagnosis=diagnosis,
            user_context_payload=user_context,
            user_strategy_state=user_strategy_state,
            recommended_stance=recommended_stance,
            vision=vision,
            current_state=current_state,
            primary_obstacle=primary_obstacle,
            intervention=intervention,
            outcome=outcome,
            sparkle_self_state=sparkle_self_state,
        ).to_dict()
        decision_context = {
            **diagnosis,
            **decision_policy,
        }
        if evidence.get("recent_pain_points"):
            decision_context["recent_pain_points"] = list(_as_list(evidence.get("recent_pain_points")))
        if evidence.get("recent_wins"):
            decision_context["recent_wins"] = list(_as_list(evidence.get("recent_wins")))
        decision_context = self._apply_phase_a_decision_context(
            decision_context=decision_context,
            insight_state=insight_state,
            route_intent=route_intent,
        )
        planning_strategy = PlanningStrategyCompiler().compile(
            situation_brief={
                "vision": vision,
                "current_state": current_state,
                "evidence": evidence,
                "decision_context": decision_context,
                "insight_state": insight_state,
            },
            user_context_payload=user_context,
            plan_context=plan_context,
            planning_constraints=_as_dict(plan_context.get("constraints")),
        ).to_dict()
        current_context = self._build_capability_selection_context(
            user_context=user_context,
            plan_context=plan_context,
            decision_context=decision_context,
            insight_state=insight_state,
            route_intent=route_intent,
        )
        registry = CapabilityRegistryService().build_registry()
        capability_requirements = CapabilityRequirementCompiler().compile(
            user_context_payload=user_context,
            plan_context=plan_context,
            decision_context=decision_context,
            insight_state=insight_state,
            planning_strategy=planning_strategy,
            route_intent=route_intent,
        )
        body_map = CapabilitySelectionPolicy().build_body_map(
            registry=registry,
            route_intent=route_intent,
            capability_requirements=capability_requirements,
        )
        capability_selection = CapabilitySelectionPolicy().select(
            body_map=body_map,
            capability_requirements=capability_requirements,
            route_intent=route_intent,
            mode_strategy=recommended_stance,
            current_context=current_context,
        )
        decision_context["body_awareness_guidance"] = _as_dict(capability_selection.get("body_awareness_guidance"))
        decision_context["capability_selection_summary"] = _as_dict(capability_selection.get("summary"))
        decision_context["capability_bounded_adjustments"] = self._merge_capability_bounded_adjustments(
            dual_core_decision=dual_core_decision,
            capability_selection=capability_selection,
        )
        five_layer_growth = self._build_five_layer_growth_summary(
            user_context=user_context,
            outcome_learning=outcome_learning,
            registry=registry,
            capability_selection=capability_selection,
        )
        decision_context["five_layer_growth_summary"] = five_layer_growth
        semantic_control = build_semantic_control(
            decision_context=decision_context,
            planning_strategy=planning_strategy,
            body_awareness_guidance=_as_dict(capability_selection.get("body_awareness_guidance")),
            user_strategy_state=user_strategy_state,
            outcome_learning=outcome_learning,
            language="zh",
        ).to_dict()

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
            decision_context=decision_context,
        )

        return SituationBrief(
            focus_question=focus_question,
            summary=summary,
            vision=vision,
            current_state=current_state,
            primary_obstacle=primary_obstacle,
            evidence=evidence,
            learning_state_fragment=learning_state_fragment,
            intervention=intervention,
            outcome=outcome,
            sparkle_self_state=sparkle_self_state,
            recommended_stance=recommended_stance,
            decision_context=decision_context,
            semantic_control=semantic_control,
            semantic_primitives=semantic_primitives,
            source_trace=source_trace,
            insight_state=insight_state,
            planning_strategy=planning_strategy,
            outcome_learning=outcome_learning,
            five_layer_growth=five_layer_growth,
            body_map=body_map,
            capability_requirements=capability_requirements,
            capability_selection=capability_selection,
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
        outcome_learning: dict[str, Any],
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
        if outcome_learning:
            used_sources.append("outcome_learning")

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
            "outcome_learning": {
                "active": bool(outcome_learning),
                "validated_learning_count": len(
                    _as_list(outcome_learning.get("active_validated_learnings"))
                    or _as_list(outcome_learning.get("validated_learnings"))
                ),
                "known_failure_rule_count": len(_as_list(outcome_learning.get("known_failure_avoidance_rules"))),
            },
        }

    def _merge_capability_bounded_adjustments(
        self,
        *,
        dual_core_decision: dict[str, Any],
        capability_selection: dict[str, Any],
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        def collect(items: list[Any], *, default_source: str) -> None:
            for item in items:
                if not isinstance(item, dict):
                    continue
                field = _strip(item.get("field"))
                if not field:
                    continue
                target_layer = _strip(item.get("target_layer") or "session")
                key = (field, target_layer)
                if key in seen:
                    continue
                payload = dict(item)
                if not _strip(payload.get("source")):
                    payload["source"] = default_source
                merged.append(payload)
                seen.add(key)

        collect(_as_list(dual_core_decision.get("strategy_adjustments")), default_source="dual_core_router")
        collect(_as_list(capability_selection.get("bounded_adjustments")), default_source="capability_selection")
        return merged

    def _build_five_layer_growth_summary(
        self,
        *,
        user_context: dict[str, Any],
        outcome_learning: dict[str, Any],
        registry: dict[str, Any],
        capability_selection: dict[str, Any],
    ) -> dict[str, Any]:
        strategy_meta = _as_dict(_as_dict(user_context.get("user_strategy_state")).get("meta"))
        outcome_payload = _as_dict(outcome_learning)
        layer_alignment = _as_dict(user_context.get("layer_alignment"))
        active_outcome_learnings = list(
            _as_list(outcome_payload.get("active_validated_learnings"))
            or _as_list(outcome_payload.get("validated_learnings"))
        )
        inactive_outcome_learnings = list(_as_list(outcome_payload.get("inactive_validated_learnings")))
        outcome_pending_reviews = list(_as_list(outcome_payload.get("pending_reviews")))
        outcome_stale_items = list(_as_list(outcome_payload.get("stale_items")))
        outcome_active_conflicts = list(_as_list(outcome_payload.get("shared_conflict_reports")))
        active_conflicts = list(_as_list(layer_alignment.get("active_conflicts"))) + list(
            _as_list(strategy_meta.get("active_conflicts"))
        ) + outcome_active_conflicts
        stale_items = list(_as_list(layer_alignment.get("stale_items"))) + list(_as_list(strategy_meta.get("stale_items"))) + list(
            outcome_stale_items
        )

        return {
            "contract_version": _strip(layer_alignment.get("contract_version")) or _strip(strategy_meta.get("five_layer_contract_version")),
            "layers": [
                {"id": "constitutional", "active": True, "summary": "Constitution artifacts remain the bounded source of identity and drift discipline."},
                {"id": "session", "active": bool(strategy_meta.get("session_layer_active") or user_context.get("effective_companion_state")), "summary": "Fast reversible adaptation is live for the current turn."},
                {"id": "episode", "active": bool(strategy_meta.get("episode_layer_active") or outcome_payload.get("episode_layer_active")), "summary": _strip(strategy_meta.get("adaptive_summary")) or "Journey-bounded learnings are available when the active plan supports them."},
                {"id": "profile", "active": bool(strategy_meta.get("profile_layer_active") or outcome_payload.get("profile_layer_active") or _as_dict(user_context.get("profile_context"))), "summary": "Cross-session truths stay compact, evidence-gated, and auditable."},
                {"id": "system", "active": bool(_as_dict(capability_selection.get("body_awareness_guidance"))), "summary": "System-layer choice is advisory, bounded, and registry-governed."},
            ],
            "active_conflict_count": len(active_conflicts),
            "stale_item_count": len(stale_items),
            "review_due_count": len(outcome_pending_reviews),
            "active_conflicts": active_conflicts[:5],
            "stale_items": stale_items[:5],
            "outcome_learning_state": {
                "active_learning_count": len(active_outcome_learnings),
                "inactive_learning_count": len(inactive_outcome_learnings),
                "review_due_count": len(outcome_pending_reviews),
                "stale_learning_count": len(
                    [item for item in outcome_stale_items if _strip(_as_dict(item).get("status")) == "stale"]
                ),
                "active_conflict_count": len(outcome_active_conflicts),
                "governance_policy": _as_dict(outcome_payload.get("governance_summary")).get("policy", {}),
            },
            "system_rights_state": {
                "bounded_knob_count": len(_as_list(registry.get("system_layer_knobs"))),
                "active_bounded_adjustments": len(_as_list(capability_selection.get("bounded_adjustments"))),
            },
        }

    def _build_phase_a_planning_context(
        self,
        *,
        user_context: dict[str, Any],
        plan_context: dict[str, Any],
        semantic_primitives: dict[str, Any],
        context_briefing_note: str | None,
        dual_core_instruction: str,
    ) -> dict[str, Any]:
        vision = _as_dict(semantic_primitives.get("vision"))
        current_state = _as_dict(semantic_primitives.get("current_state"))
        active_goals = [
            item
            for item in _as_list(user_context.get("active_goals"))
            if isinstance(item, dict)
        ]
        goal_titles = [
            _strip(item.get("title") or item.get("name"))
            for item in active_goals[:2]
            if _strip(item.get("title") or item.get("name"))
        ]
        goal_text = " / ".join(
            part
            for part in (
                goal_titles[0] if goal_titles else "",
                _strip(plan_context.get("goal")),
                _strip(vision.get("primary_goal")),
            )
            if part
        )
        user_message = _strip(user_context.get("current_query")) or dual_core_instruction or _strip(context_briefing_note)
        return {
            "user_message": user_message,
            "current_query": _strip(user_context.get("current_query")),
            "context_briefing_note": _strip(context_briefing_note),
            "route_intent": _strip(_as_dict(user_context.get("context_focus")).get("route_intent")),
            "goal_text": goal_text,
            "vision": vision,
            "current_state": current_state,
            "file_ids": _as_list(user_context.get("file_ids")),
            "user_material_grounding": _as_dict(user_context.get("user_material_grounding")),
            "material_sources": _as_list(user_context.get("material_sources")),
            "uploaded_materials": _as_list(user_context.get("uploaded_materials")),
            "attached_materials": _as_list(user_context.get("attached_materials")),
        }

    def _build_phase_a_turn_signals(
        self,
        *,
        planning_context: dict[str, Any],
        user_strategy_state: dict[str, Any],
    ) -> dict[str, Any]:
        text_corpus = " | ".join(
            _strip(item)
            for item in (
                planning_context.get("user_message"),
                planning_context.get("current_query"),
                planning_context.get("context_briefing_note"),
                planning_context.get("goal_text"),
                _as_dict(planning_context.get("vision")).get("why_now"),
                _as_dict(planning_context.get("current_state")).get("snapshot"),
            )
            if _strip(item)
        )
        requested_difficulty = ""
        if re.search(r"\b(hard|harder|challenging|challenge|push me)\b|更难|高强度|狠一点|严格一点", text_corpus, re.IGNORECASE):
            requested_difficulty = "hard"
        elif re.search(r"\b(easy|easier|gentle)\b|简单一点|轻一点", text_corpus, re.IGNORECASE):
            requested_difficulty = "easy"

        wants_push = bool(
            re.search(r"\b(push|push me|go harder|strict)\b|逼一逼|推一推|狠一点|严格一点", text_corpus, re.IGNORECASE)
        )
        aggressive_pace = bool(
            re.search(
                r"\b(urgent|as fast as possible|intensive|sprint|cram|in \d+ days?)\b|冲刺|突击|速成|尽快|马上|两周|14天|期中|期末|考试前",
                text_corpus,
                re.IGNORECASE,
            )
        )
        self_report_high_mastery = bool(
            re.search(
                r"\b(i already know|i know this|basics are fine|foundation is fine)\b|我已经会了|我都懂|基础没问题|这个我会|不用从基础讲",
                text_corpus,
                re.IGNORECASE,
            )
        )
        low_capacity_language = bool(
            re.search(
                r"\b(too much|overwhelmed|cannot start|can't start|burned out|exhausted)\b|太多了|开始不了|撑不住|扛不住|没精力|负荷太高",
                text_corpus,
                re.IGNORECASE,
            )
        )
        return {
            "raw_text": text_corpus,
            "requested_difficulty": requested_difficulty,
            "wants_push": wants_push,
            "aggressive_pace": aggressive_pace,
            "self_report_high_mastery": self_report_high_mastery,
            "low_capacity_language": low_capacity_language,
            "strategy_mode": _strip(user_strategy_state.get("session_mode")),
        }

    def _build_capability_selection_context(
        self,
        *,
        user_context: dict[str, Any],
        plan_context: dict[str, Any],
        decision_context: dict[str, Any],
        insight_state: dict[str, Any],
        route_intent: str,
    ) -> dict[str, Any]:
        query = " | ".join(
            part
            for part in (
                _strip(user_context.get("current_query")),
                _strip(decision_context.get("what_matters_now")),
                _strip(plan_context.get("goal")),
            )
            if part
        ).lower()
        preferred_specialists: list[str] = []
        if any(marker in query for marker in ("error", "debug", "报错", "根因")):
            preferred_specialists.extend(["error_analyst"])
        if any(marker in query for marker in ("math", "积分", "方程", "热力学")):
            preferred_specialists.extend(["math_agent"])
        if any(marker in query for marker in ("predict", "forecast", "预测")):
            preferred_specialists.extend(["deep_analyst"])

        return {
            "query": query,
            "experience_mode": _strip(decision_context.get("experience_mode")),
            "planning_readiness": _strip(insight_state.get("readiness_level")),
            "preferred_specialists": list(dict.fromkeys(preferred_specialists)),
            "route_intent": _strip(route_intent),
        }

    def _apply_phase_a_decision_context(
        self,
        *,
        decision_context: dict[str, Any],
        insight_state: dict[str, Any],
        route_intent: str,
    ) -> dict[str, Any]:
        if not insight_state:
            return decision_context

        planning_like, _planning_source = detect_planning_like_turn(
            normalized_intent=None,
            route_intent=route_intent,
            user_message=_strip(decision_context.get("what_matters_now")),
            decision_context=decision_context,
        )

        readiness_level = _strip(insight_state.get("readiness_level"))
        readiness_score = insight_state.get("readiness_score")
        recommended_action = _strip(insight_state.get("recommended_action"))
        contradictions = [
            _strip(item.get("description"))
            for item in _as_list(insight_state.get("contradiction_map"))
            if isinstance(item, dict) and _strip(item.get("description"))
        ]
        questions = [
            _strip(item)
            for item in _as_list(insight_state.get("recommended_clarification"))
            if _strip(item)
        ]
        blocking_unknowns = [
            _strip(item)
            for item in _as_list(insight_state.get("blocking_unknowns") or insight_state.get("missing_information"))
            if _strip(item)
        ]
        prediction_summary = _as_dict(insight_state.get("prediction_summary"))
        calibration_summary = _as_dict(insight_state.get("calibration_summary"))
        overload_prediction = _as_dict(prediction_summary.get("overload_risk"))
        schedule_prediction = _as_dict(prediction_summary.get("schedule_fit"))
        slippage_prediction = _as_dict(prediction_summary.get("plan_slippage_risk"))
        receptivity_prediction = _as_dict(prediction_summary.get("intervention_receptivity"))

        decision_context["planning_readiness"] = readiness_level
        if readiness_score is not None:
            decision_context["planning_readiness_score"] = readiness_score
        decision_context["planning_readiness_action"] = recommended_action
        decision_context["planning_blocking_unknowns"] = blocking_unknowns
        decision_context["insight_contradictions"] = contradictions
        decision_context["strategic_clarification_questions"] = questions
        if overload_prediction:
            decision_context["predicted_overload_risk"] = _strip(overload_prediction.get("level"))
        if schedule_prediction:
            decision_context["predicted_schedule_fit"] = _strip(schedule_prediction.get("level"))
        if slippage_prediction:
            decision_context["predicted_plan_slippage_risk"] = _strip(slippage_prediction.get("level"))
        if receptivity_prediction:
            decision_context["predicted_intervention_receptivity"] = _strip(receptivity_prediction.get("level"))
        if calibration_summary:
            decision_context["insight_calibration_posture"] = _strip(calibration_summary.get("calibration_posture"))

        if not planning_like:
            return decision_context

        if recommended_action == "ask":
            question_focus = "、".join(blocking_unknowns[:2]) if blocking_unknowns else "关键缺口"
            decision_context["what_matters_now"] = f"先补齐{question_focus}，再进入计划制定。"
            decision_context["experience_mode"] = "clarify"
            decision_context["intervention_family"] = "clarifying_probe"
            decision_context["reversibility_level"] = "high"
            decision_context["phase_a_guardrail"] = "ask_before_plan"
            visible_expression = _as_dict(decision_context.get("user_visible_expression"))
            visible_expression["opening_intent"] = "Ask the highest-value clarification before generating a plan."
            visible_expression["response_shape"] = "ask_one_targeted_question_then_hold_back"
            decision_context["user_visible_expression"] = visible_expression
            feedback_hook = _as_dict(decision_context.get("feedback_hook"))
            if questions:
                feedback_hook["ask"] = questions[0]
            decision_context["feedback_hook"] = feedback_hook
        elif recommended_action == "provisional":
            decision_context["phase_a_guardrail"] = "provisional_plan_with_assumptions"
            visible_expression = _as_dict(decision_context.get("user_visible_expression"))
            visible_expression["response_shape"] = "state_assumptions_then_offer_provisional_plan"
            decision_context["user_visible_expression"] = visible_expression
            if questions and not _strip(decision_context.get("what_matters_now")):
                decision_context["what_matters_now"] = "计划可以先给出，但要把关键假设和待确认点说清楚。"

        return decision_context

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
        decision_context: dict[str, Any],
    ) -> str:
        goal = _strip(vision.get("primary_goal") or vision.get("active_plan") or "当前目标")
        current_snapshot = _strip(current_state.get("snapshot"))
        obstacle = _strip(primary_obstacle.get("summary") or primary_obstacle.get("label") or "当前阻力")
        evidence_item = _strip(evidence.get("summary"))
        intervention_summary = _strip(intervention.get("summary") or intervention.get("label"))
        outcome_summary = _strip(outcome.get("summary") or outcome.get("latest_signal"))
        stance = _strip(recommended_stance.get("stance"))
        what_matters_now = _strip(decision_context.get("what_matters_now"))

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
        if what_matters_now:
            parts.append(f"当前判断是 {what_matters_now}")
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
    decision_context = _as_dict(payload.get("decision_context"))
    semantic_control = _as_dict(
        payload.get("semantic_control")
        or build_semantic_control(
            decision_context=decision_context,
            planning_strategy=_as_dict(payload.get("planning_strategy")),
            body_awareness_guidance=_as_dict(decision_context.get("body_awareness_guidance")),
            user_strategy_state=_as_dict(payload.get("user_strategy_state")),
            outcome_learning=_as_dict(payload.get("outcome_learning")),
            language="zh",
        ).to_dict()
    )
    insight_state = _as_dict(payload.get("insight_state"))
    planning_strategy = _as_dict(payload.get("planning_strategy"))
    outcome_learning = _as_dict(payload.get("outcome_learning"))

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
    decision_line = _strip(decision_context.get("what_matters_now"))
    if decision_line:
        lines.append(f"- 当前判断: {decision_line}")
    readiness_guidance = format_semantic_control_lines(semantic_control, language="zh", section="decision")
    if readiness_guidance:
        lines.append(f"- 当前语义控制: {readiness_guidance[0]}")
    planning_guidance = format_semantic_control_lines(semantic_control, language="zh", section="planning")
    if planning_guidance:
        lines.append(f"- 规划语义约束: {planning_guidance[0]}")
    strategy_guidance = format_semantic_control_lines(semantic_control, language="zh", section="strategy")
    if strategy_guidance:
        lines.append(f"- 当前交互策略: {strategy_guidance[0]}")
    learning_hints = [
        _compact_text(item, limit=88)
        for item in _as_list(outcome_learning.get("plan_generation_hints_from_outcomes"))
        if _strip(item)
    ]
    if learning_hints:
        lines.append(f"- 已验证学习提示: {'；'.join(learning_hints[:2])}")
    required_sections = [
        _strip(item)
        for item in _as_list(planning_strategy.get("required_plan_sections"))
        if _strip(item)
    ]
    if required_sections:
        labels = build_plan_quality_contract().build_prompt_requirements(mode=_strip(planning_strategy.get("plan_mode")) or "full")
        if labels:
            lines.append(f"- 计划必须显式覆盖: {'，'.join(labels[:5])}")
    blocking_unknowns = [
        _strip(item)
        for item in _as_list(
            decision_context.get("planning_blocking_unknowns")
            or insight_state.get("blocking_unknowns")
            or insight_state.get("missing_information")
        )
        if _strip(item)
    ]
    if blocking_unknowns:
        lines.append(f"- 计划前仍需补齐: {', '.join(blocking_unknowns[:3])}")
    contradictions = [
        _compact_text(item, limit=88)
        for item in _as_list(decision_context.get("insight_contradictions") or [])
        if _strip(item)
    ]
    if contradictions:
        lines.append(f"- 洞察冲突: {'；'.join(contradictions[:2])}")
    clarification_questions = [
        _compact_text(item, limit=88)
        for item in _as_list(decision_context.get("strategic_clarification_questions") or [])
        if _strip(item)
    ]
    if clarification_questions:
        lines.append(f"- 优先澄清问题: {clarification_questions[0]}")
    body_guidance = format_semantic_control_lines(semantic_control, language="zh", section="body")
    if body_guidance:
        lines.append(f"- 系统器官协同: {body_guidance[0]}")
    stance_line = _strip(stance.get("stance"))
    if stance_line:
        lines.append(f"- 本轮站位: {stance_line}")
    return "\n" + "\n".join(lines[:20])
