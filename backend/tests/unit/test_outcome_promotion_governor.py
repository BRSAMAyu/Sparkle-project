from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.business_metrics import (
    OUTCOME_LEARNING_CONFLICTS_TOTAL,
    OUTCOME_LEARNING_PLANNING_CONSTRAINTS_TOTAL,
    PROFILE_LEDGER_PENDING_SYNTHESIS,
    VALIDATED_OUTCOME_LEARNING_PROMOTIONS_TOTAL,
    snapshot_metric,
)
from app.services.outcome_promotion_governor import OutcomePromotionGovernor
from app.services.plan_outcome_service import PROFILE_OUTCOME_LEDGER_KEY


class _AsyncRedisStub:
    def __init__(self) -> None:
        self.payload: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.payload.get(key)

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.payload[key] = value
        self.ttl[key] = ttl_seconds


class _PreferenceServiceStub:
    def __init__(self, inferred: dict | None = None) -> None:
        self.prefs = SimpleNamespace(inferred=dict(inferred or {}), version=1)

    async def get_preferences(self, user_id):
        return self.prefs

    async def update_inferred(self, user_id, updates: dict):
        self.prefs.inferred.update(dict(updates or {}))
        return self.prefs


class _PlanStateServiceStub:
    def __init__(self) -> None:
        self.states: dict[tuple[str, str], SimpleNamespace] = {}

    async def get_or_create_plan_state(self, user_id, plan_id, *args, **kwargs):
        key = (str(user_id), str(plan_id))
        state = self.states.get(key)
        if state is None:
            state = SimpleNamespace(facts={})
            self.states[key] = state
        return state

    async def upsert_plan_state(self, user_id, plan_id, patch: dict, bump_version: bool = True):
        state = await self.get_or_create_plan_state(user_id, plan_id)
        state.facts = dict(patch.get("facts") or {})
        return state

    async def get_plan_state(self, user_id, plan_id, refresh: bool = False):
        return self.states.get((str(user_id), str(plan_id)))


class _UserStrategyStateServiceStub:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def apply_adjustment(self, user_id, changes: dict, **kwargs):
        self.calls.append({"changes": dict(changes), **kwargs})
        return {"applied": list(changes.keys())}


def _metric_value(snapshot: dict[str, float], needle: str) -> float:
    for label, value in snapshot.items():
        if needle in label:
            return value
    return 0.0


@pytest.mark.asyncio
async def test_outcome_promotion_governor_promotes_episode_and_profile_layers() -> None:
    user_id = uuid4()
    plan_id = uuid4()
    redis = _AsyncRedisStub()
    governor = OutcomePromotionGovernor(db=object(), redis=redis)
    governor.preference_service = _PreferenceServiceStub()
    governor.plan_state_service = _PlanStateServiceStub()
    governor.user_strategy_state_service = _UserStrategyStateServiceStub()

    report = {
        "validated_plan_learnings": [
            {
                "learning_key": "grounded_plans_work_better",
                "learning_domain": "plan",
                "direction": "success",
                "summary": "Grounded plans worked better repeatedly.",
                "sample_count": 3,
                "unique_sessions": 2,
                "confidence": 0.86,
                "planning_bias_constraints": {"grounding_mode": "mandatory"},
                "known_failure_avoidance_rules": [],
                "known_success_patterns": ["Grounded planning improved outcomes in similar scenarios."],
                "plan_generation_hints_from_outcomes": ["Require user-material grounding before approving a full plan."],
                "suggested_layer": "profile",
            }
        ],
        "validated_insight_learnings": [],
        "promotion_candidates": [
            {"learning_key": "grounded_plans_work_better", "suggested_layer": "profile"}
        ],
        "demotion_candidates": [],
        "conflict_report": [],
        "planning_bias_constraints": {"grounding_mode": "mandatory"},
        "known_failure_avoidance_rules": [],
        "known_success_patterns": ["Grounded planning improved outcomes in similar scenarios."],
        "plan_generation_hints_from_outcomes": ["Require user-material grounding before approving a full plan."],
    }

    result = await governor.apply_learning_report(
        user_id,
        report=report,
        plan_id=plan_id,
        session_id="session-1",
    )

    decisions = result["promotion_decision"]
    assert any(item["layer"] == "episode" and item["decision"] == "promoted" for item in decisions)
    assert any(item["layer"] == "profile" and item["decision"] == "promoted" for item in decisions)
    assert json.loads(redis.payload["session:outcome_learning:session-1"])["planning_bridge"]["planning_bias_constraints"]["grounding_mode"] == "mandatory"
    assert governor.user_strategy_state_service.calls[0]["changes"]["retrieval_emphasis"] == "user_materials"


@pytest.mark.asyncio
async def test_outcome_promotion_governor_blocks_conflicting_profile_promotion() -> None:
    user_id = uuid4()
    governor = OutcomePromotionGovernor(db=object(), redis=None)
    governor.preference_service = _PreferenceServiceStub(
        inferred={
            "validated_outcome_learning": {
                "validated_learnings": [
                    {"learning_key": "dense_first_step_overloads_user", "direction": "success"}
                ]
            }
        }
    )
    governor.plan_state_service = _PlanStateServiceStub()
    governor.user_strategy_state_service = _UserStrategyStateServiceStub()

    result = await governor.apply_learning_report(
        user_id,
        report={
            "validated_plan_learnings": [
                {
                    "learning_key": "dense_first_step_overloads_user",
                    "learning_domain": "plan",
                    "direction": "failure",
                    "summary": "Dense first steps fail repeatedly.",
                    "sample_count": 3,
                    "unique_sessions": 2,
                    "confidence": 0.84,
                    "planning_bias_constraints": {"lighter_first_step": True},
                    "known_failure_avoidance_rules": ["Avoid dense first steps when similar conditions recur."],
                    "known_success_patterns": [],
                    "plan_generation_hints_from_outcomes": ["Default to a lighter first step."],
                    "suggested_layer": "profile",
                }
            ],
            "validated_insight_learnings": [],
            "promotion_candidates": [{"learning_key": "dense_first_step_overloads_user", "suggested_layer": "profile"}],
            "demotion_candidates": [],
            "conflict_report": [],
        },
    )

    assert any(item["layer"] == "profile" and item["decision"] == "blocked_conflict" for item in result["promotion_decision"])


@pytest.mark.asyncio
async def test_outcome_promotion_governor_synthesizes_profile_ledger_into_profile_learning() -> None:
    user_id = uuid4()
    governor = OutcomePromotionGovernor(db=object(), redis=None)
    governor.preference_service = _PreferenceServiceStub(
        inferred={
            PROFILE_OUTCOME_LEDGER_KEY: [
                {
                    "record_id": "profile-1",
                    "recorded_at": "2026-04-05T09:00:00",
                    "source_family": "behavioral_outcome",
                    "source_id": "bo-1",
                    "evidence_level": "Behavioral Signal",
                    "evidence_strength": "strong",
                    "target_type": "intervention",
                    "target_layer": "session",
                    "target_object": "iv-1",
                    "target_hypothesis": "dense_first_step_overloads_user",
                    "learning_domain": "plan",
                    "observed_outcome": "too_difficult",
                    "outcome_signal": {},
                    "outcome_window": "",
                    "time_horizon": "short_horizon_behavior",
                    "confidence": 0.78,
                    "evidence_sources": ["behavioral_outcome_tracker"],
                    "planning_implications": {"lighter_first_step": True, "scaffold_level": "high"},
                    "promotion_recommendation": "episode_candidate",
                    "reversal_candidate": False,
                    "session_id": "",
                    "plan_id": None,
                    "intervention_id": "iv-1",
                    "freshness_deadline": "2026-05-05T09:00:00",
                    "metadata": {"persist_profile_ledger": True},
                },
                {
                    "record_id": "profile-2",
                    "recorded_at": "2026-04-05T10:00:00",
                    "source_family": "behavioral_outcome",
                    "source_id": "bo-2",
                    "evidence_level": "Behavioral Signal",
                    "evidence_strength": "strong",
                    "target_type": "intervention",
                    "target_layer": "session",
                    "target_object": "iv-2",
                    "target_hypothesis": "dense_first_step_overloads_user",
                    "learning_domain": "plan",
                    "observed_outcome": "too_difficult",
                    "outcome_signal": {},
                    "outcome_window": "",
                    "time_horizon": "short_horizon_behavior",
                    "confidence": 0.8,
                    "evidence_sources": ["behavioral_outcome_tracker"],
                    "planning_implications": {"lighter_first_step": True, "scaffold_level": "high"},
                    "promotion_recommendation": "episode_candidate",
                    "reversal_candidate": False,
                    "session_id": "",
                    "plan_id": None,
                    "intervention_id": "iv-2",
                    "freshness_deadline": "2026-05-05T10:00:00",
                    "metadata": {"persist_profile_ledger": True},
                },
                {
                    "record_id": "profile-3",
                    "recorded_at": "2026-04-05T11:00:00",
                    "source_family": "behavioral_outcome",
                    "source_id": "bo-3",
                    "evidence_level": "Behavioral Signal",
                    "evidence_strength": "strong",
                    "target_type": "intervention",
                    "target_layer": "session",
                    "target_object": "iv-3",
                    "target_hypothesis": "dense_first_step_overloads_user",
                    "learning_domain": "plan",
                    "observed_outcome": "too_difficult",
                    "outcome_signal": {},
                    "outcome_window": "",
                    "time_horizon": "short_horizon_behavior",
                    "confidence": 0.82,
                    "evidence_sources": ["behavioral_outcome_tracker"],
                    "planning_implications": {"lighter_first_step": True, "scaffold_level": "high"},
                    "promotion_recommendation": "episode_candidate",
                    "reversal_candidate": False,
                    "session_id": "",
                    "plan_id": None,
                    "intervention_id": "iv-3",
                    "freshness_deadline": "2026-05-05T11:00:00",
                    "metadata": {"persist_profile_ledger": True},
                },
            ]
        }
    )
    governor.plan_state_service = _PlanStateServiceStub()
    governor.user_strategy_state_service = _UserStrategyStateServiceStub()
    governor.outcome_learning_service.plan_outcome_service.preference_service = governor.preference_service

    result = await governor.synthesize_profile_ledger_learning(
        user_id,
        trigger_source="unit_test",
    )

    profile_state = governor.preference_service.prefs.inferred["validated_outcome_learning"]
    assert result["status"] == "applied"
    assert result["pending_records_before"] == 3
    assert result["pending_records_after"] == 0
    assert any(item["layer"] == "profile" and item["decision"] == "promoted" for item in result["promotion_decision"])
    assert profile_state["validated_learnings"][0]["learning_key"] == "dense_first_step_overloads_user"
    assert profile_state["planning_bridge"]["planning_bias_constraints"]["lighter_first_step"] is True
    assert snapshot_metric(PROFILE_LEDGER_PENDING_SYNTHESIS)["default"] == 0.0


@pytest.mark.asyncio
async def test_outcome_promotion_governor_emits_metrics_for_promotions_conflicts_and_constraints() -> None:
    user_id = uuid4()
    governor = OutcomePromotionGovernor(db=object(), redis=None)
    governor.preference_service = _PreferenceServiceStub()
    governor.plan_state_service = _PlanStateServiceStub()
    governor.user_strategy_state_service = _UserStrategyStateServiceStub()

    before_promotions = snapshot_metric(VALIDATED_OUTCOME_LEARNING_PROMOTIONS_TOTAL)
    before_conflicts = snapshot_metric(OUTCOME_LEARNING_CONFLICTS_TOTAL)
    before_constraints = snapshot_metric(OUTCOME_LEARNING_PLANNING_CONSTRAINTS_TOTAL)

    await governor.apply_learning_report(
        user_id,
        report={
            "validated_plan_learnings": [
                {
                    "learning_key": "grounded_plans_work_better",
                    "learning_domain": "plan",
                    "direction": "success",
                    "summary": "Grounded plans worked better repeatedly.",
                    "sample_count": 3,
                    "unique_sessions": 2,
                    "confidence": 0.86,
                    "planning_bias_constraints": {"grounding_mode": "mandatory"},
                    "known_failure_avoidance_rules": [],
                    "known_success_patterns": ["Grounded planning improved outcomes in similar scenarios."],
                    "plan_generation_hints_from_outcomes": ["Require user-material grounding before approving a full plan."],
                    "suggested_layer": "profile",
                }
            ],
            "validated_insight_learnings": [],
            "promotion_candidates": [{"learning_key": "grounded_plans_work_better", "suggested_layer": "profile"}],
            "demotion_candidates": [{"learning_key": "grounded_plans_work_better", "reason": "validated_direction_changed"}],
            "conflict_report": [{"learning_key": "grounded_plans_work_better", "reason": "human_truth_overrides_weaker_evidence"}],
            "planning_bias_constraints": {"grounding_mode": "mandatory"},
            "known_failure_avoidance_rules": [],
            "known_success_patterns": [],
            "plan_generation_hints_from_outcomes": [],
        },
    )

    after_promotions = snapshot_metric(VALIDATED_OUTCOME_LEARNING_PROMOTIONS_TOTAL)
    after_conflicts = snapshot_metric(OUTCOME_LEARNING_CONFLICTS_TOTAL)
    after_constraints = snapshot_metric(OUTCOME_LEARNING_PLANNING_CONSTRAINTS_TOTAL)

    promotions_delta = _metric_value(after_promotions, "layer=profile,direction=success") - _metric_value(
        before_promotions,
        "layer=profile,direction=success",
    )
    conflict_delta = _metric_value(after_conflicts, "layer=synthesis,reason=human_truth_overrides_weaker_evidence") - _metric_value(
        before_conflicts,
        "layer=synthesis,reason=human_truth_overrides_weaker_evidence",
    )
    constraint_delta = _metric_value(after_constraints, "constraint_key=grounding_mode,constraint_value=mandatory") - _metric_value(
        before_constraints,
        "constraint_key=grounding_mode,constraint_value=mandatory",
    )

    assert promotions_delta == 1.0
    assert conflict_delta == 1.0
    assert constraint_delta == 1.0
