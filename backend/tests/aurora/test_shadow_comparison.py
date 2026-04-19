from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import UUID
from unittest.mock import patch

from app.aurora.engine import AuroraDecisionContext, AuroraEngine
from app.aurora.migration import (
    prepare_shadow_pre_response_formatting_hook,
    prepare_shadow_pre_tool_selection_hook,
    project_aurora_to_dual_core_mode,
)
from app.aurora.policy_loader import load_policy_version
from app.aurora.schemas import SignalSnapshot, TransitionDecisionRecord
from app.orchestration.dual_core_router import DualCoreRoutingInput, dual_core_router


_POLICY = load_policy_version("v1.0")
_ENGINE = AuroraEngine()
_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
_NOW = datetime(2026, 4, 19, 10, 0, 0)
_SHADOW_CORPUS_PATH = Path(__file__).with_name("fixtures") / "shadow_corpus" / "shadow_corpus.json"


@dataclass(frozen=True)
class ShadowComparisonCase:
    """One curated shadow-mode comparison between legacy and Aurora routing."""

    name: str
    snapshot: SignalSnapshot
    legacy_input: DualCoreRoutingInput
    expected_legacy_mode: str
    current_node: str = "day3_execution"
    candidate_node: str | None = None
    counts_for_routine_gate: bool = True
    rationale: str = ""


@dataclass(frozen=True)
class ShadowComparisonResult:
    case: ShadowComparisonCase
    aurora_mode: str
    legacy_mode: str
    agreed: bool
    aurora_decision: TransitionDecisionRecord
    divergence_reason: str | None = None


def _snapshot(
    snapshot_hash: str,
    core: dict[str, object],
    enhanced: dict[str, object] | None = None,
    optional: dict[str, object] | None = None,
) -> SignalSnapshot:
    return SignalSnapshot(
        snapshot_hash=snapshot_hash,
        user_id=_USER_ID,
        collected_at=_NOW,
        scenario_pack_id="exam_prep_14d@v1.0",
        policy_version=_POLICY.id,
        core_signals=core,
        enhanced_signals=enhanced or {},
        optional_signals=optional or {},
        total_tokens=900,
        budget_limit=4000,
    )


def _load_shadow_corpus() -> tuple[dict[str, str], ...]:
    payload = json.loads(_SHADOW_CORPUS_PATH.read_text(encoding="utf-8"))
    return tuple(dict(case) for case in payload["cases"])


def _corpus_routing_input(case_kind: str) -> DualCoreRoutingInput:
    if case_kind == "execution_clear":
        return DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.95,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="healthy",
            recent_task_feedback_distribution={"just_right": 2},
            session_length_preference=25,
            difficulty_preference=0.5,
        )
    if case_kind == "support_first":
        return DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.83,
            information_sufficient=False,
            primary_challenge_area="emotional",
            recent_sentiment_distribution={"stressed": 2, "anxious": 1},
            has_active_plan=True,
            plan_health_status="critical",
            recent_task_feedback_distribution={"too_difficult": 3, "too_long": 1},
            emotional_block_detected=True,
        )
    if case_kind == "balanced":
        return DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.61,
            information_sufficient=True,
            primary_challenge_area="cognitive",
            recent_sentiment_distribution={"neutral": 2, "frustrated": 1},
            has_active_plan=False,
            plan_health_status=None,
            recent_task_feedback_distribution={"too_long": 1},
            current_guidance="need help regroup",
        )
    if case_kind == "concept_confusion":
        return DualCoreRoutingInput(
            intent="knowledge",
            intent_confidence=0.88,
            information_sufficient=False,
            primary_challenge_area="cognitive",
            recent_sentiment_distribution={"neutral": 2},
            has_active_plan=True,
            plan_health_status="warning",
            recent_task_feedback_distribution={"unclear": 2},
            cognitive_mode_suggested=True,
        )
    if case_kind == "procrastination":
        return DualCoreRoutingInput(
            intent="plan",
            intent_confidence=0.9,
            information_sufficient=True,
            primary_challenge_area="execution",
            recent_sentiment_distribution={"neutral": 3},
            has_active_plan=True,
            plan_health_status="warning",
            recent_task_feedback_distribution={"too_long": 2, "too_difficult": 1},
            procrastination_pattern=True,
            behavior_pattern_names=["拖延回避", "完美主义"],
        )
    raise ValueError(f"unsupported corpus kind: {case_kind}")


def _cases() -> tuple[ShadowComparisonCase, ...]:
    return (
        ShadowComparisonCase(
            name="clear_plan_execution",
            snapshot=_snapshot("ss_shadow_01", {"user_message": "请帮我把这周复习计划拆成每天三步"}),
            legacy_input=DualCoreRoutingInput(
                intent="plan",
                intent_confidence=0.95,
                information_sufficient=True,
                primary_challenge_area="execution",
                recent_sentiment_distribution={"neutral": 4},
                has_active_plan=True,
                plan_health_status="healthy",
                recent_task_feedback_distribution={"just_right": 2},
                session_length_preference=25,
                difficulty_preference=0.5,
            ),
            expected_legacy_mode="execution_first",
            rationale="clear planning intent with no emotional or procrastination drag should stay execution-led",
        ),
        ShadowComparisonCase(
            name="difficulty_feedback",
            snapshot=_snapshot(
                "ss_shadow_02",
                {"user_message": "这个计划太难了，我现在没法继续"},
                {"energy_state": "sharp_drop"},
            ),
            legacy_input=DualCoreRoutingInput(
                intent="plan",
                intent_confidence=0.91,
                information_sufficient=True,
                primary_challenge_area="emotional",
                recent_sentiment_distribution={"anxious": 3, "neutral": 1},
                has_active_plan=True,
                plan_health_status="warning",
                recent_task_feedback_distribution={"too_difficult": 3, "too_long": 1},
                session_length_preference=25,
                difficulty_preference=0.4,
            ),
            expected_legacy_mode="cognitive_first",
            candidate_node="crisis_recovery",
            rationale="repeated difficulty plus inability to continue should push both systems into support-first mode",
        ),
        ShadowComparisonCase(
            name="mixed_signals",
            snapshot=_snapshot("ss_shadow_03", {"user_message": "最近有点烦，但也还能推进，先随便聊聊"}),
            legacy_input=DualCoreRoutingInput(
                intent="chat",
                intent_confidence=0.68,
                information_sufficient=True,
                primary_challenge_area="cognitive",
                recent_sentiment_distribution={"neutral": 2, "frustrated": 1},
                has_active_plan=False,
                plan_health_status=None,
                recent_task_feedback_distribution={"too_long": 1},
            ),
            expected_legacy_mode="balanced",
            rationale="mixed ambient signals without strong blockage should remain balanced",
        ),
        ShadowComparisonCase(
            name="procrastination",
            snapshot=_snapshot("ss_shadow_04", {"user_message": "我总是在真正开始前往后拖，不想开头"}),
            legacy_input=DualCoreRoutingInput(
                intent="plan",
                intent_confidence=0.9,
                information_sufficient=True,
                primary_challenge_area="execution",
                recent_sentiment_distribution={"neutral": 3},
                has_active_plan=True,
                plan_health_status="healthy",
                recent_task_feedback_distribution={"just_right": 1},
                procrastination_pattern=True,
                behavior_pattern_details=[
                    {
                        "pattern_name": "拖延回避",
                        "canonical_key": "procrastination_avoidance",
                        "description": "总在真正开始前往后拖。",
                        "confidence": 0.82,
                    }
                ],
            ),
            expected_legacy_mode="cognitive_first",
            rationale="execution resistance should still count as cognitive-first even if Aurora stays on the backbone",
        ),
        ShadowComparisonCase(
            name="concept_confusion",
            snapshot=_snapshot("ss_shadow_05", {"user_message": "这两个热力学概念我总搞混，先别给计划，想先讲清楚"}),
            legacy_input=DualCoreRoutingInput(
                intent="knowledge",
                intent_confidence=0.66,
                information_sufficient=True,
                primary_challenge_area="cognitive",
                recent_sentiment_distribution={"neutral": 2},
                has_active_plan=True,
                plan_health_status="warning",
                recent_task_feedback_distribution={"unclear": 1},
                cognitive_mode_suggested=True,
                behavior_pattern_details=[
                    {
                        "pattern_name": "认知盲点",
                        "canonical_key": "cognitive_blindspot",
                        "description": "在相似概念上反复误解。",
                        "confidence": 0.71,
                    }
                ],
            ),
            expected_legacy_mode="cognitive_first",
            rationale="knowledge-gap style requests should project to cognitive-first even when materiality stays low",
        ),
        ShadowComparisonCase(
            name="partner_concern",
            snapshot=_snapshot(
                "ss_shadow_06",
                {"partner_report": {"severity": "medium", "summary": "连续四天未完成且在回避"}},
                {"task_completion_4d": 0.0, "behavioral_signal": "gaming_detected"},
            ),
            legacy_input=DualCoreRoutingInput(
                intent="plan",
                intent_confidence=0.82,
                information_sufficient=True,
                primary_challenge_area="execution",
                recent_sentiment_distribution={"neutral": 2},
                has_active_plan=True,
                plan_health_status="warning",
                recent_task_feedback_distribution={"too_long": 1},
                behavior_pattern_details=[{"pattern_name": "回避", "canonical_key": "avoidance"}],
            ),
            expected_legacy_mode="cognitive_first",
            candidate_node="recovery_probe",
            counts_for_routine_gate=False,
            rationale="legacy has no explicit partner signal, but the comparable user-facing posture is still support-first",
        ),
        ShadowComparisonCase(
            name="family_crisis",
            snapshot=_snapshot(
                "ss_shadow_07",
                {"user_message": "我家里出事了，最近可能没法继续"},
                {"energy_state": "sharp_drop"},
            ),
            legacy_input=DualCoreRoutingInput(
                intent="plan",
                intent_confidence=0.72,
                information_sufficient=False,
                primary_challenge_area="emotional",
                recent_sentiment_distribution={"overwhelmed": 3},
                has_active_plan=True,
                plan_health_status="critical",
                recent_task_feedback_distribution={"too_difficult": 1},
                emotional_block_detected=True,
            ),
            expected_legacy_mode="cognitive_first",
            candidate_node="crisis_recovery",
            counts_for_routine_gate=False,
            rationale="explicit crisis signal should align on cognitive-first and crisis routing",
        ),
        ShadowComparisonCase(
            name="routine_chat",
            snapshot=_snapshot("ss_shadow_08", {"user_message": "今天有点累，先随便聊聊最近状态"}),
            legacy_input=DualCoreRoutingInput(
                intent="chat",
                intent_confidence=0.55,
                information_sufficient=True,
                primary_challenge_area=None,
                recent_sentiment_distribution={"neutral": 2},
                has_active_plan=False,
                plan_health_status=None,
                recent_task_feedback_distribution={},
            ),
            expected_legacy_mode="cognitive_first",
            rationale="legacy router is conservative on low-confidence chat; Aurora keeps this balanced",
        ),
        ShadowComparisonCase(
            name="deadline_conflict",
            snapshot=_snapshot("ss_shadow_09", {"commitment_conflict": "考试提前了，原计划需要压缩"}),
            legacy_input=DualCoreRoutingInput(
                intent="plan",
                intent_confidence=0.93,
                information_sufficient=True,
                primary_challenge_area="execution",
                recent_sentiment_distribution={"neutral": 3},
                has_active_plan=True,
                plan_health_status="warning",
                recent_task_feedback_distribution={"just_right": 1},
            ),
            expected_legacy_mode="execution_first",
            candidate_node="replan_deadline",
            rationale="deadline compression should still be an execution-first replanning move",
        ),
        ShadowComparisonCase(
            name="need_help_pause",
            snapshot=_snapshot("ss_shadow_10", {"user_message": "need help, can we pause and regroup?"}),
            legacy_input=DualCoreRoutingInput(
                intent="plan",
                intent_confidence=0.74,
                information_sufficient=False,
                primary_challenge_area="emotional",
                recent_sentiment_distribution={"stressed": 2},
                has_active_plan=True,
                plan_health_status="warning",
                recent_task_feedback_distribution={"too_long": 1},
                emotional_block_detected=True,
            ),
            expected_legacy_mode="cognitive_first",
            candidate_node="holding_replan",
            rationale="pause-and-regroup language is support-first even when Aurora remains on the current node",
        ),
        ShadowComparisonCase(
            name="short_sprint_plan",
            snapshot=_snapshot("ss_shadow_11", {"user_message": "帮我排一个25分钟的冲刺任务清单"}),
            legacy_input=DualCoreRoutingInput(
                intent="task",
                intent_confidence=0.91,
                information_sufficient=True,
                primary_challenge_area="execution",
                recent_sentiment_distribution={"neutral": 3},
                has_active_plan=True,
                plan_health_status="healthy",
                recent_task_feedback_distribution={"just_right": 1},
                session_length_preference=25,
                difficulty_preference=0.5,
            ),
            expected_legacy_mode="execution_first",
            rationale="explicit short-sprint planning should remain execution-first",
        ),
        ShadowComparisonCase(
            name="perfectionism_friction",
            snapshot=_snapshot("ss_shadow_12", {"user_message": "我总想一次做完美，结果迟迟不开工"}),
            legacy_input=DualCoreRoutingInput(
                intent="plan",
                intent_confidence=0.83,
                information_sufficient=True,
                primary_challenge_area="execution",
                recent_sentiment_distribution={"neutral": 2},
                has_active_plan=True,
                plan_health_status="warning",
                recent_task_feedback_distribution={"too_long": 1},
                behavior_pattern_details=[
                    {
                        "pattern_name": "完美主义",
                        "canonical_key": "perfectionism_avoidance",
                        "description": "总想一次到位所以拖延",
                    }
                ],
            ),
            expected_legacy_mode="cognitive_first",
            rationale="perfectionism-induced start friction should still surface as cognitive-first support",
        ),
    )
def _run_case(case: ShadowComparisonCase) -> ShadowComparisonResult:
    aurora_decision = _ENGINE.safe_route(
        AuroraDecisionContext(
            snapshot=case.snapshot,
            trigger_point="pre-node-routing",
            current_node=case.current_node,
            candidate_node=case.candidate_node,
            policy_version=_POLICY,
            mode="shadow",
        )
    )
    legacy_decision = dual_core_router.route(case.legacy_input)
    aurora_mode = project_aurora_to_dual_core_mode(case.snapshot, aurora_decision)
    agreed = aurora_mode == legacy_decision.mode == case.expected_legacy_mode
    divergence_reason = None
    if not agreed:
        divergence_reason = (
            f"legacy={legacy_decision.mode}, aurora={aurora_mode}, "
            f"basis={aurora_decision.decision_basis.value}, decision={aurora_decision.decision_type}"
        )
    return ShadowComparisonResult(
        case=case,
        aurora_mode=aurora_mode,
        legacy_mode=legacy_decision.mode,
        agreed=agreed,
        aurora_decision=aurora_decision,
        divergence_reason=divergence_reason,
    )


def _render_report(results: Iterable[ShadowComparisonResult]) -> str:
    lines = []
    for result in results:
        status = "agree" if result.agreed else "diverge"
        lines.append(
            f"{result.case.name}: {status} "
            f"(legacy={result.legacy_mode}, aurora={result.aurora_mode}, "
            f"basis={result.aurora_decision.decision_basis.value}, decision={result.aurora_decision.decision_type})"
        )
    return "\n".join(lines)


def test_shadow_comparison_meets_wave2_gate() -> None:
    results = tuple(_run_case(case) for case in _cases())
    routine_results = tuple(result for result in results if result.case.counts_for_routine_gate)
    overall_agreement = sum(1 for result in results if result.agreed) / len(results)
    routine_agreement = sum(1 for result in routine_results if result.agreed) / len(routine_results)

    assert len(results) >= 10
    assert routine_agreement >= 0.8, _render_report(results)
    assert overall_agreement >= 0.75, _render_report(results)


def test_shadow_comparison_current_divergence_profile_is_explicit() -> None:
    results = tuple(_run_case(case) for case in _cases())
    divergences = {result.case.name: result.divergence_reason for result in results if not result.agreed}

    assert divergences == {
        "routine_chat": "legacy=cognitive_first, aurora=balanced, basis=mixed, decision=stay"
    }


def test_shadow_corpus_expands_to_fifty_entries_across_both_hooks() -> None:
    corpus = _load_shadow_corpus()
    hook_counts = Counter(case["hook_point"] for case in corpus)
    kind_counts = Counter(case["case_kind"] for case in corpus)
    observations = []

    assert len(corpus) == 50
    assert hook_counts == Counter({"pre-tool-selection": 25, "pre-response-formatting": 25})
    assert kind_counts == Counter(
        {
            "balanced": 10,
            "concept_confusion": 10,
            "execution_clear": 10,
            "procrastination": 10,
            "support_first": 10,
        }
    )

    with (
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_MODE", True),
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE", False),
    ):
        for index, case in enumerate(corpus, start=1):
            routing_input = _corpus_routing_input(case["case_kind"])
            user_id = f"00000000-0000-0000-0000-{index:012d}"
            if case["hook_point"] == "pre-tool-selection":
                observation = prepare_shadow_pre_tool_selection_hook(
                    routing_input,
                    user_id=user_id,
                    enabled=True,
                )
            else:
                observation = prepare_shadow_pre_response_formatting_hook(
                    routing_input,
                    user_id=user_id,
                    enabled=True,
                )
            assert observation is not None
            assert observation.hook_point == case["hook_point"]
            observations.append(observation)

    aligned = sum(1 for observation in observations if observation.agreed)
    diverged = len(observations) - aligned

    assert aligned > 0
    assert diverged > 0
