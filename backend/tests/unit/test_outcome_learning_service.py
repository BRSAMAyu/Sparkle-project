from __future__ import annotations

from datetime import datetime

from app.services.outcome_learning_service import OutcomeLearningService


def _record(**overrides):
    base = {
        "record_id": overrides.get("record_id", "r1"),
        "recorded_at": overrides.get("recorded_at", datetime(2026, 4, 5, 10, 0, 0).isoformat()),
        "source_family": overrides.get("source_family", "plan_feedback"),
        "source_id": overrides.get("source_id", "s1"),
        "evidence_level": overrides.get("evidence_level", "Plan Outcome"),
        "evidence_strength": overrides.get("evidence_strength", "strong"),
        "target_type": overrides.get("target_type", "plan"),
        "target_layer": overrides.get("target_layer", "episode"),
        "target_object": overrides.get("target_object", "plan-1"),
        "target_hypothesis": overrides.get("target_hypothesis", "dense_first_step_overloads_user"),
        "learning_domain": overrides.get("learning_domain", "plan"),
        "observed_outcome": overrides.get("observed_outcome", "too_difficult"),
        "outcome_signal": overrides.get("outcome_signal", {}),
        "outcome_window": overrides.get("outcome_window", "7_days"),
        "time_horizon": overrides.get("time_horizon", "episode"),
        "confidence": overrides.get("confidence", 0.82),
        "evidence_sources": overrides.get("evidence_sources", ["test"]),
        "planning_implications": overrides.get(
            "planning_implications",
            {"lighter_first_step": True, "scaffold_level": "high", "checkpoint_cadence": "short"},
        ),
        "promotion_recommendation": overrides.get("promotion_recommendation", "episode_candidate"),
        "reversal_candidate": overrides.get("reversal_candidate", False),
        "session_id": overrides.get("session_id", "session-1"),
        "plan_id": overrides.get("plan_id", "plan-1"),
        "intervention_id": overrides.get("intervention_id"),
        "freshness_deadline": overrides.get("freshness_deadline", datetime(2026, 5, 5, 10, 0, 0).isoformat()),
        "metadata": overrides.get("metadata", {}),
    }
    return base


def test_outcome_learning_service_validates_repeated_failures_and_ignores_turn_noise() -> None:
    service = OutcomeLearningService(db=object(), redis=None)

    report = service.build_report(
        [
            _record(record_id="plan-fail-1"),
            _record(record_id="plan-fail-2", session_id="session-2"),
            _record(
                record_id="turn-1",
                evidence_level="Turn Reaction",
                observed_outcome="thumbs_down",
                evidence_strength="medium",
                confidence=0.9,
            ),
        ],
        now=datetime(2026, 4, 5, 12, 0, 0),
    )

    assert len(report.validated_plan_learnings) == 1
    learning = report.validated_plan_learnings[0].to_dict()
    assert learning["direction"] == "failure"
    assert learning["suggested_layer"] == "episode"
    assert "Default to a lighter first step." in learning["plan_generation_hints_from_outcomes"]
    assert report.ignored_noise[0]["reason"] == "turn_reaction_only"


def test_outcome_learning_service_flags_conflicts_against_existing_learning() -> None:
    service = OutcomeLearningService(db=object(), redis=None)

    report = service.build_report(
        [
            _record(record_id="success-1", observed_outcome="effective", planning_implications={"preserve_success_pattern": True}),
            _record(
                record_id="failure-1",
                observed_outcome="too_difficult",
                planning_implications={"lighter_first_step": True},
            ),
        ],
        current_learning_state={
            "validated_learnings": [
                {"learning_key": "dense_first_step_overloads_user", "direction": "success"}
            ]
        },
        now=datetime(2026, 4, 5, 12, 0, 0),
    )

    assert report.conflict_report[0]["learning_key"] == "dense_first_step_overloads_user"
    assert report.demotion_candidates[0]["reason"] == "new_conflict_against_existing_learning"


def test_outcome_learning_service_allows_profile_ledger_behavioral_evidence_to_suggest_profile_layer() -> None:
    service = OutcomeLearningService(db=object(), redis=None)

    report = service.build_report(
        [
            _record(record_id="profile-1", metadata={"persist_profile_ledger": True}, session_id=""),
            _record(record_id="profile-2", metadata={"persist_profile_ledger": True}, session_id=""),
            _record(record_id="profile-3", metadata={"persist_profile_ledger": True}, session_id=""),
        ],
        now=datetime(2026, 4, 5, 12, 0, 0),
    )

    assert len(report.validated_plan_learnings) == 1
    assert report.validated_plan_learnings[0].suggested_layer == "profile"


def test_outcome_learning_service_lets_human_truth_override_weaker_behavioral_noise() -> None:
    service = OutcomeLearningService(db=object(), redis=None)

    report = service.build_report(
        [
            _record(
                record_id="human-1",
                evidence_level="Human Truth",
                observed_outcome="wrong",
                target_hypothesis="grounding_missing_hurts_plan_quality",
                planning_implications={"grounding_mode": "mandatory"},
                source_family="human_eval",
                confidence=0.9,
            ),
            _record(
                record_id="behavioral-1",
                evidence_level="Behavioral Signal",
                observed_outcome="success",
                target_hypothesis="grounding_missing_hurts_plan_quality",
                planning_implications={"preserve_success_pattern": True},
                source_family="behavioral_outcome",
                confidence=0.72,
            ),
            _record(
                record_id="turn-1",
                evidence_level="Turn Reaction",
                observed_outcome="thumbs_down",
                target_hypothesis="grounding_missing_hurts_plan_quality",
                source_family="response_feedback",
                confidence=0.9,
            ),
        ],
        now=datetime(2026, 4, 5, 12, 0, 0),
    )

    assert len(report.validated_plan_learnings) == 1
    learning = report.validated_plan_learnings[0].to_dict()
    assert learning["direction"] == "failure"
    assert learning["planning_bias_constraints"]["grounding_mode"] == "mandatory"
    assert report.conflict_report[0]["reason"] == "human_truth_overrides_weaker_evidence"
