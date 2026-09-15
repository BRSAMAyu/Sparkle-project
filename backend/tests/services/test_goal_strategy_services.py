from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.cognitive import router as cognitive_router
from app.api.v1.goals import router as goals_router
from app.db.session import get_db
from app.models.goal import Goal
from app.models.strategy_belief import StrategyBeliefSnapshot
from app.models.user import User
from app.services.goal_decomposition_service import goal_decomposition_service
from app.services.strategy_belief_service import strategy_belief_service


@pytest.mark.asyncio
async def test_decomposition_preview_builds_editable_milestones() -> None:
    preview = goal_decomposition_service.preview(
        title="Prepare calculus exam",
        goal_type="academic",
        motivation="I need a stronger final score",
        time_horizon="short",
    )

    assert preview.goal_type == "academic"
    assert preview.time_horizon == "short"
    assert len(preview.milestones) == 4
    assert preview.milestones[0].acceptance_criteria


@pytest.mark.asyncio
async def test_create_goal_persists_wizard_milestones(db_session, test_user: User) -> None:
    goal = await goal_decomposition_service.create_goal(
        db_session,
        user_id=test_user.id,
        title="Build a writing habit",
        goal_type="habit",
        motivation="Publish consistently",
        time_horizon="medium",
        description="Daily writing practice",
        target_date=None,
        milestones=[
            {
                "id": "m1",
                "title": "Seven day streak",
                "description": "Write a small note every day.",
                "estimated_days": 7,
                "acceptance_criteria": ["7 notes exist"],
            }
        ],
    )

    assert goal.goal_type == "habit"
    assert goal.minimum_acceptance_criteria[0]["label"] == "Seven day streak"
    assert goal.metadata_payload["creation_wizard"]["milestones"][0]["id"] == "m1"


@pytest.mark.asyncio
async def test_suggest_alternatives_uses_low_confidence_counter_evidence(db_session, test_user: User) -> None:
    goal = Goal(
        user_id=test_user.id,
        title="Project launch",
        goal_type="project",
        metadata_payload={"current_strategy_id": "recover_execution_rhythm"},
    )
    weak_belief = StrategyBeliefSnapshot(
        user_id=str(test_user.id),
        strategy_key="recover_execution_rhythm",
        alpha=1.0,
        beta=8.0,
        evidence_count=9,
        counter_evidence=[{"reason": "Large tasks still miss their review window", "weight": 0.8}],
        metadata_payload={},
    )
    db_session.add_all([goal, weak_belief])
    await db_session.flush()

    bundle = await strategy_belief_service.suggest_alternatives(
        user_id=test_user.id,
        goal_id=goal.id,
        db=db_session,
    )

    assert bundle.current_strategy_id == "recover_execution_rhythm"
    assert bundle.confidence < 0.4
    assert bundle.counter_evidence[0].reason.startswith("Large tasks")
    assert all(item.strategy_id != "recover_execution_rhythm" for item in bundle.alternatives)


@pytest.mark.asyncio
async def test_migrate_strategy_updates_goal_metadata_and_belief(db_session, test_user: User) -> None:
    goal = Goal(
        user_id=test_user.id,
        title="Skill sprint",
        goal_type="skill",
        metadata_payload={"current_strategy_id": "recover_execution_rhythm"},
    )
    db_session.add(goal)
    await db_session.flush()

    result = await strategy_belief_service.migrate_strategy(
        user_id=test_user.id,
        goal_id=goal.id,
        new_strategy_id="repair_knowledge_bottleneck",
        db=db_session,
    )

    assert result.previous_strategy_id == "recover_execution_rhythm"
    assert goal.metadata_payload["current_strategy_id"] == "repair_knowledge_bottleneck"
    assert goal.metadata_payload["strategy_migrations"][0]["to_strategy_id"] == "repair_knowledge_bottleneck"


@pytest.fixture
def goal_strategy_client(db_session, test_user: User):
    app = FastAPI()
    app.include_router(goals_router, prefix="/goals")
    app.include_router(cognitive_router, prefix="/cognitive")

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user

    with TestClient(app) as client:
        yield client


def test_decompose_preview_api_returns_milestone_payload(goal_strategy_client: TestClient) -> None:
    response = goal_strategy_client.post(
        "/goals/decompose-preview",
        json={
            "goal_type": "skill",
            "title": "Learn data visualization",
            "motivation": "I want to explain research better",
            "time_horizon": "medium",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["goal_type"] == "skill"
    assert len(payload["milestones"]) >= 3


@pytest.mark.asyncio
async def test_strategy_migrate_api_returns_result(goal_strategy_client: TestClient, db_session, test_user: User) -> None:
    goal = Goal(
        user_id=test_user.id,
        title="Academic rescue",
        goal_type="academic",
        metadata_payload={"current_strategy_id": "recover_execution_rhythm"},
    )
    db_session.add(goal)
    await db_session.flush()

    response = goal_strategy_client.post(
        "/cognitive/strategies/migrate",
        json={
            "goal_id": str(goal.id),
            "new_strategy_id": "exam_rescue_sprint",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["previous_strategy_id"] == "recover_execution_rhythm"
    assert payload["new_strategy_id"] == "exam_rescue_sprint"
    assert datetime.fromisoformat(payload["migrated_at"]).tzinfo is not None
