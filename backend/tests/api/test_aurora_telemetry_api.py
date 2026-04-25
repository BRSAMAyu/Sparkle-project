from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_superuser, get_db
from app.api.v1.aurora import router as aurora_router
from app.aurora.runtime_v1.models import AuroraDecisionTelemetry


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(aurora_router)
    return app


def _strategy_payload(**overrides: bool) -> dict[str, bool]:
    payload = {
        "concept_first": False,
        "problem_first": False,
        "worked_example_first": False,
        "retrieval_practice": False,
        "interleaving": False,
        "spaced_review": False,
        "error_analysis_required": False,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_aurora_telemetry_summary_returns_admin_aggregates(db_session, test_user) -> None:
    now = datetime.utcnow()
    db_session.add_all(
        [
            AuroraDecisionTelemetry(
                decision_id="telemetry-1",
                user_id=test_user.id,
                surface="aurora_modeling",
                conversation_id="conv-api-1",
                request_id="req-api-1",
                decided_at=now - timedelta(hours=2),
                wake_score=0.66,
                energy_level="medium",
                strategy_payload=_strategy_payload(concept_first=True, worked_example_first=True),
                expression_payload={"directness": 0.62},
                context_mask=["user_message", "wake_policy"],
                action="emit_message",
                chat_directive_core={"intent": "ask_scope", "target_domain": "scope"},
                standard_layer_contract={"response_type": "task_help"},
                strategy_confidence=0.71,
                outcome="task_completed",
                outcome_filled_at=now - timedelta(hours=1, minutes=55),
                outcome_reason="user_supplied_scope_signal",
            ),
            AuroraDecisionTelemetry(
                decision_id="telemetry-2",
                user_id=test_user.id,
                surface="aurora_planning",
                conversation_id="conv-api-2",
                request_id="req-api-2",
                decided_at=now - timedelta(hours=1),
                wake_score=0.81,
                energy_level="full",
                strategy_payload=_strategy_payload(problem_first=True, retrieval_practice=True),
                expression_payload={"directness": 0.91},
                context_mask=["user_message", "task_state", "wake_policy"],
                action="emit_message",
                chat_directive_core={"intent": "tighten_plan"},
                standard_layer_contract={"response_type": "plan_guidance"},
                strategy_confidence=0.44,
                outcome="timeout",
                outcome_filled_at=now - timedelta(minutes=50),
                outcome_reason="user_message_signaled_timeout",
            ),
        ]
    )
    await db_session.commit()

    app = _build_app()

    async def _override_get_db():
        yield db_session

    async def _override_superuser():
        return SimpleNamespace(id=test_user.id, is_superuser=True)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_superuser] = _override_superuser

    with TestClient(app) as client:
        response = client.get("/aurora/telemetry/summary?days=30")

    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 30
    assert body["total_decisions"] == 2
    assert body["strategy_distribution"]["concept_first"]["true"] == 1
    assert body["strategy_distribution"]["problem_first"]["true"] == 1
    assert body["wake_frequency"]["by_energy_level"]["medium"] == 1
    assert body["wake_frequency"]["by_energy_level"]["full"] == 1
    assert body["accuracy"]["resolved_count"] == 2
    assert body["accuracy"]["outcome_breakdown"]["task_completed"] == 1
    assert body["accuracy"]["outcome_breakdown"]["timeout"] == 1
    assert body["accuracy"]["success_rate"] == pytest.approx(0.5)
    assert body["accuracy"]["upgrade_accuracy"] == pytest.approx(0.5)
    assert body["accuracy"]["error_upgrade_rate"] == pytest.approx(0.5)
