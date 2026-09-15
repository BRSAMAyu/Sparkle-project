from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.api.v1.counterfactual import router as counterfactual_router
from app.aurora.runtime_v1.models import CounterfactualReport
from app.signals.counterfactual_evaluation import (
    CounterfactualEstimate,
    CounterfactualIronLawEnforcer,
    CounterfactualReportService,
    EvidenceGrade,
    PolicyUpdateCandidate,
)
from app.signals.intervention_episode import (
    ContextSignature,
    EvidenceQuality,
    ExecutionOutcome,
    InterventionEpisode,
    OutcomeVector,
)


class FakeRedis:
    def __init__(self, user_id: str, episodes: list[InterventionEpisode]):
        self.user_id = user_id
        self.episodes = {episode.episode_id: episode.to_dict() for episode in episodes}

    async def lrange(self, key, start, end):
        assert key == f"spine:episodes:{self.user_id}"
        return list(self.episodes.keys())

    async def get(self, key):
        episode_id = key.rsplit(":", 1)[-1]
        payload = self.episodes.get(episode_id)
        return json.dumps(payload) if payload else None

    async def scan_iter(self, match=None, count=None):
        yield f"spine:episodes:{self.user_id}"


def _episode(user_id: str, policy: str, completed: bool = True) -> InterventionEpisode:
    return InterventionEpisode(
        user_id=user_id,
        domain="exam_sprint",
        context_signature=ContextSignature(
            goal_mode="standard_learning",
            failure_type="knowledge_gap",
            cognitive_load="medium",
            user_id=user_id,
        ),
        candidate_policies=["reduce_pace", "worked_example_first"],
        selected_policy=policy,
        selection_probability=0.5,
        outcome_vector=OutcomeVector(execution=ExecutionOutcome(started=True, completed=completed)),
        evidence_quality=EvidenceQuality(
            propensity_logged=True,
            counterfactual_candidates_logged=True,
            outcome_complete=True,
            user_feedback_present=True,
        ),
    )


@pytest.mark.asyncio
async def test_daily_counterfactual_evaluation_persists_report(db_session):
    user_id = str(uuid4())
    episodes = [
        _episode(user_id, "reduce_pace", completed=True),
        _episode(user_id, "worked_example_first", completed=False),
    ]
    service = CounterfactualReportService(db_session, FakeRedis(user_id, episodes))

    result = await service.run_daily_evaluations(user_ids=[user_id])

    assert result["reports_generated"] == 1
    reports = await service.list_reports(user_id=user_id)
    assert len(reports) == 1
    report = reports[0]
    assert report.policy_a == "reduce_pace"
    assert report.policy_b == "worked_example_first"
    assert report.estimate["evidence_grade"]["grade"] >= 1
    assert "promotion_requires_simulation" in report.iron_law_compliance["checks"]


def test_counterfactual_iron_laws_enforce_all_six_checks():
    estimate = CounterfactualEstimate(
        actual_policy="a",
        alternative_policy="b",
        matched_episodes_actual=2,
        matched_episodes_alternative=2,
        evidence_grade=EvidenceGrade(grade=1),
        allowed_mode="hard_constraint",
        recommendation="This has proven to work.",
    )
    candidate = PolicyUpdateCandidate(
        source_estimate_id=estimate.estimate_id,
        current_policy="a",
        proposed_policy="b",
        evidence_grade=estimate.evidence_grade,
        guardrail_checks_passed=False,
        allowed_mode="hard_constraint",
    )

    result = CounterfactualIronLawEnforcer.enforce_all(estimate, is_high_risk=True, candidate=candidate)

    assert result["compliant"] is False
    assert len(result["checks"]) == 6
    assert "direct_live_change_violation" in result["violations"]
    assert any(item.startswith("promotion_missing_") for item in result["violations"])
    assert any(item.startswith("overconfident_language") for item in result["violations"])


@pytest.fixture
def counterfactual_client(db_session):
    app = FastAPI()
    app.include_router(counterfactual_router)

    state = {"current_user": None, "admin_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    def _override_get_current_active_superuser():
        return state["admin_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_current_active_superuser] = _override_get_current_active_superuser

    with TestClient(app) as client:
        yield client, state


@pytest.mark.asyncio
async def test_counterfactual_api_returns_owned_report(db_session, counterfactual_client):
    client, state = counterfactual_client
    user_id = str(uuid4())
    state["current_user"] = SimpleNamespace(id=user_id, is_superuser=False)
    report = CounterfactualReport(
        user_id=user_id,
        context_signature={"goal_mode": "standard_learning"},
        context_hash="ctx",
        policy_a="reduce_pace",
        policy_b="worked_example_first",
        estimate={"estimate_id": "cfe1"},
        confidence=0.6,
        evidence_grade=2,
        generated_at=datetime.utcnow(),
        promotion_candidate={},
        promotion_status="not_ready",
        iron_law_compliance={"compliant": True},
        runtime_metadata={},
    )
    db_session.add(report)
    await db_session.commit()

    response = client.get("/counterfactual/reports")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == str(report.id)


@pytest.mark.asyncio
async def test_admin_promote_marks_report_pending_review(db_session, counterfactual_client):
    client, state = counterfactual_client
    user_id = str(uuid4())
    admin_id = str(uuid4())
    state["admin_user"] = SimpleNamespace(id=admin_id, is_superuser=True)
    report = CounterfactualReport(
        user_id=user_id,
        context_signature={"goal_mode": "standard_learning"},
        context_hash="ctx",
        policy_a="reduce_pace",
        policy_b="worked_example_first",
        estimate={"estimate_id": "cfe1"},
        confidence=0.9,
        evidence_grade=4,
        generated_at=datetime.utcnow(),
        promotion_candidate={"promotion_blocked_reasons": []},
        promotion_status="candidate_ready",
        iron_law_compliance={"compliant": True, "violations": []},
        runtime_metadata={},
    )
    db_session.add(report)
    await db_session.commit()

    response = client.post(f"/counterfactual/promote/{report.id}")

    assert response.status_code == 200
    assert response.json()["promotion_status"] == "pending_review"
