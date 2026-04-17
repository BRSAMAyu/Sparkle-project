from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.outcome_promotion_governor import OutcomePromotionGovernor


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
    async def apply_adjustment(self, *args, **kwargs):
        return {"applied": []}


@pytest.mark.asyncio
async def test_outcome_promotion_governor_phase_e_adds_governance_and_shared_conflicts() -> None:
    user_id = uuid4()
    plan_id = uuid4()
    governor = OutcomePromotionGovernor(db=object(), redis=None)
    governor.preference_service = _PreferenceServiceStub()
    governor.plan_state_service = _PlanStateServiceStub()
    governor.user_strategy_state_service = _UserStrategyStateServiceStub()

    await governor.apply_learning_report(
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
                    "confidence": 0.82,
                    "suggested_layer": "profile",
                    "freshness_status": "fresh",
                }
            ],
            "validated_insight_learnings": [],
            "promotion_candidates": [{"learning_key": "dense_first_step_overloads_user", "suggested_layer": "profile"}],
            "demotion_candidates": [],
            "conflict_report": [],
        },
        plan_id=plan_id,
    )

    effective = await governor.get_effective_learning_state(user_id, plan_id=plan_id)
    promoted = governor.preference_service.prefs.inferred["validated_outcome_learning"]

    assert promoted["learning_governance"]["dense_first_step_overloads_user"]["status"] == "active"
    assert effective["shared_conflict_reports"] == []
    assert effective["active_validated_learnings"][0]["learning_key"] == "dense_first_step_overloads_user"


@pytest.mark.asyncio
async def test_effective_learning_state_excludes_demoted_and_blocked_learnings_from_planning_bridge() -> None:
    user_id = uuid4()
    governor = OutcomePromotionGovernor(db=object(), redis=None)
    governor.preference_service = _PreferenceServiceStub(
        inferred={
            "validated_outcome_learning": {
                "validated_learnings": [
                    {
                        "learning_key": "grounded_plans_work_better",
                        "direction": "success",
                        "planning_bias_constraints": {"grounding_mode": "mandatory"},
                        "plan_generation_hints_from_outcomes": ["Keep grounding mandatory."],
                    },
                    {
                        "learning_key": "dense_first_step_overloads_user",
                        "direction": "failure",
                        "planning_bias_constraints": {"lighter_first_step": True},
                        "known_failure_avoidance_rules": ["Avoid dense first steps."],
                    },
                    {
                        "learning_key": "overfit_to_mood_signal",
                        "direction": "failure",
                        "planning_bias_constraints": {"mood_mirroring": True},
                        "plan_generation_hints_from_outcomes": ["Overweight the current mood."],
                    },
                ],
                "learning_governance": {
                    "grounded_plans_work_better": {"status": "active"},
                    "dense_first_step_overloads_user": {"status": "demoted"},
                    "overfit_to_mood_signal": {"status": "blocked"},
                },
            }
        }
    )
    governor.plan_state_service = _PlanStateServiceStub()
    governor.user_strategy_state_service = _UserStrategyStateServiceStub()

    effective = await governor.get_effective_learning_state(user_id)

    assert [item["learning_key"] for item in effective["active_validated_learnings"]] == ["grounded_plans_work_better"]
    assert {item["learning_key"] for item in effective["inactive_validated_learnings"]} == {
        "dense_first_step_overloads_user",
        "overfit_to_mood_signal",
    }
    assert effective["planning_bridge"]["planning_bias_constraints"] == {"grounding_mode": "mandatory"}
    assert effective["planning_bridge"]["known_failure_avoidance_rules"] == []
    assert effective["planning_bridge"]["plan_generation_hints_from_outcomes"] == ["Keep grounding mandatory."]


@pytest.mark.asyncio
async def test_effective_learning_state_surfaces_review_due_and_stale_items_without_activating_them() -> None:
    user_id = uuid4()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    governor = OutcomePromotionGovernor(db=object(), redis=None)
    governor.preference_service = _PreferenceServiceStub(
        inferred={
            "validated_outcome_learning": {
                "validated_learnings": [
                    {
                        "learning_key": "needs_revalidation",
                        "direction": "success",
                        "planning_bias_constraints": {"pace": "gentle"},
                    },
                    {
                        "learning_key": "expired_pattern",
                        "direction": "failure",
                        "planning_bias_constraints": {"long_step_blocks": True},
                    },
                ],
                "learning_governance": {
                    "needs_revalidation": {"review_after": (now - timedelta(days=1)).isoformat()},
                    "expired_pattern": {"expires_at": (now - timedelta(days=1)).isoformat()},
                },
            }
        }
    )
    governor.plan_state_service = _PlanStateServiceStub()
    governor.user_strategy_state_service = _UserStrategyStateServiceStub()

    effective = await governor.get_effective_learning_state(user_id)

    assert effective["active_validated_learnings"] == []
    assert {item["learning_key"] for item in effective["inactive_validated_learnings"]} == {
        "needs_revalidation",
        "expired_pattern",
    }
    assert effective["planning_bridge"]["planning_bias_constraints"] == {}
    assert effective["pending_reviews"][0]["learning_key"] == "needs_revalidation"
    stale_statuses = {item["learning_key"]: item["status"] for item in effective["stale_items"]}
    assert stale_statuses["needs_revalidation"] == "review_due"
    assert stale_statuses["expired_pattern"] == "stale"
