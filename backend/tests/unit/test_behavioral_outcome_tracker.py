from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.orchestration.planning_strategy_compiler import PlanningStrategyCompiler
from app.services.behavioral_outcome_tracker import BehavioralOutcomeTracker


class _DBStub:
    def add(self, _obj) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def refresh(self, obj) -> None:
        obj.id = uuid4()


class _PreferenceServiceStub:
    def __init__(self) -> None:
        self.prefs = SimpleNamespace(inferred={}, version=1)

    async def get_preferences(self, user_id):
        return self.prefs

    async def update_inferred(self, user_id, updates: dict):
        self.prefs.inferred.update(dict(updates or {}))
        return self.prefs


class _PlanStateServiceStub:
    async def get_plan_state(self, user_id, plan_id, refresh: bool = False):
        return None

    async def get_or_create_plan_state(self, user_id, plan_id, *args, **kwargs):
        return SimpleNamespace(facts={})

    async def upsert_plan_state(self, user_id, plan_id, patch: dict, bump_version: bool = True):
        return SimpleNamespace(facts=dict(patch.get("facts") or {}))


class _UserStrategyStateServiceStub:
    async def apply_adjustment(self, user_id, changes: dict, **kwargs):
        return {"applied": list(changes.keys())}


@pytest.mark.asyncio
async def test_behavioral_outcome_tracker_promotes_profile_learning_into_planning() -> None:
    user_id = uuid4()
    db = _DBStub()
    tracker = BehavioralOutcomeTracker(db)
    prefs = _PreferenceServiceStub()

    tracker.plan_outcome_service.preference_service = prefs
    tracker.outcome_promotion_governor.preference_service = prefs
    tracker.outcome_promotion_governor.plan_state_service = _PlanStateServiceStub()
    tracker.outcome_promotion_governor.user_strategy_state_service = _UserStrategyStateServiceStub()
    tracker.outcome_promotion_governor.outcome_learning_service.plan_outcome_service.preference_service = prefs

    for index in range(3):
        await tracker.record(
            user_id=user_id,
            intervention_id=uuid4(),
            outcome_type="dense_first_step_overloads_user",
            time_to_outcome=10 + index,
            success=False,
            context={},
        )

    validated = prefs.prefs.inferred["validated_outcome_learning"]
    assert validated["validated_learnings"][0]["learning_key"] == "dense_first_step_overloads_user"

    strategy = PlanningStrategyCompiler().compile(
        situation_brief={
            "vision": {"primary_goal": "Pass exam"},
            "current_state": {"snapshot": "Need a safer recovery plan"},
            "decision_context": {"planning_readiness_action": "proceed", "planning_readiness": "high"},
            "outcome_learning": validated["planning_bridge"],
        },
        user_context_payload={},
    )

    assert strategy.pacing_profile == "light"
    assert strategy.scaffold_level == "high"
    assert "Default to a lighter first step." in strategy.outcome_learning_hints
