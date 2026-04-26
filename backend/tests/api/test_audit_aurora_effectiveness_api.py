from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_superuser, get_db
from app.api.v1.router import api_router
from app.aurora.runtime_v1.models import AuroraDecisionTelemetry


app = FastAPI()
app.include_router(api_router)


def _strategy_payload(**overrides: bool) -> dict[str, bool]:
    payload = {
        "concept_first": False,
        "problem_first": False,
        "worked_example_first": False,
        "retrieval_practice": False,
        "interleaving": False,
        "spaced_review": False,
        "error_analysis_required": False,
        "drop_low_roi_topics": False,
        "new_topic_allowed": False,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_audit_aurora_effectiveness_requires_superuser(db_session) -> None:
    async def override_get_db():
        yield db_session

    async def override_superuser_forbidden():
        raise HTTPException(status_code=403, detail="forbidden")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser_forbidden

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/audit/aurora-effectiveness?days=30")

    assert response.status_code == 403
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_audit_aurora_effectiveness_returns_report(db_session, test_user) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)

    for i in range(6):
        db_session.add(
            AuroraDecisionTelemetry(
                decision_id=f"audit-eff-adjusted-{i}",
                user_id=test_user.id,
                surface="aurora_modeling",
                conversation_id="audit-conv-adjusted",
                request_id=f"req-adjusted-{i}",
                decided_at=now - timedelta(days=2, hours=6 - i),
                wake_score=0.75,
                energy_level="medium",
                strategy_payload=_strategy_payload(concept_first=True),
                expression_payload={},
                context_mask=[],
                action="emit_message",
                chat_directive_core={"intent": "teach"},
                standard_layer_contract={"response_type": "task_help"},
                strategy_confidence=0.7,
                outcome="task_completed" if i < 4 else "timeout",
                outcome_filled_at=now - timedelta(days=2, hours=6 - i) + timedelta(minutes=5),
                outcome_reason="test",
            )
        )

    for i in range(6):
        db_session.add(
            AuroraDecisionTelemetry(
                decision_id=f"audit-eff-baseline-{i}",
                user_id=test_user.id,
                surface="aurora_modeling",
                conversation_id="audit-conv-baseline",
                request_id=f"req-baseline-{i}",
                decided_at=now - timedelta(days=1, hours=6 - i),
                wake_score=0.35,
                energy_level="light",
                strategy_payload=_strategy_payload(),
                expression_payload={},
                context_mask=[],
                action="emit_message",
                chat_directive_core={"intent": "teach"},
                standard_layer_contract={"response_type": "task_help"},
                strategy_confidence=0.7,
                outcome="task_completed" if i < 2 else "timeout",
                outcome_filled_at=now - timedelta(days=1, hours=6 - i) + timedelta(minutes=5),
                outcome_reason="test",
            )
        )

    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_superuser():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = override_superuser

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/audit/aurora-effectiveness?days=30")

    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 30
    assert body["total_turns"] == 12
    assert body["strategy_adjusted_completion_rate"] == pytest.approx(4 / 6, abs=0.01)
    assert body["baseline_completion_rate"] == pytest.approx(2 / 6, abs=0.01)
    assert body["lift_percentage"] == pytest.approx(100.0, abs=0.05)
    assert body["top_effective_strategy"] == "concept_first"
    assert body["strategy_adjusted"]["turns"] == 6
    assert body["baseline"]["turns"] == 6

    app.dependency_overrides = {}
