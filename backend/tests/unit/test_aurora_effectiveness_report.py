from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.aurora.runtime_v1.models import AuroraDecisionTelemetry
from app.aurora.runtime_v1.telemetry import STRATEGY_FIELDS, AuroraDecisionTelemetryService
from app.models.user import User


def _strategy_payload(**overrides: bool) -> dict[str, bool]:
    payload = {field: False for field in STRATEGY_FIELDS}
    payload.update(overrides)
    return payload


def _empty_strategy_payload() -> dict[str, bool]:
    return {field: False for field in STRATEGY_FIELDS}


def _make_row(
    *,
    user_id,
    decision_id: str,
    decided_at: datetime,
    outcome: str | None,
    wake_score: float = 0.5,
    strategy: dict | None = None,
    conversation_id: str = "conv-eff-1",
) -> AuroraDecisionTelemetry:
    return AuroraDecisionTelemetry(
        decision_id=decision_id,
        user_id=user_id,
        surface="aurora_modeling",
        conversation_id=conversation_id,
        request_id=f"req-{decision_id}",
        decided_at=decided_at,
        wake_score=wake_score,
        energy_level="medium",
        strategy_payload=strategy if strategy is not None else _empty_strategy_payload(),
        expression_payload={},
        context_mask=[],
        action="emit_message",
        chat_directive_core={},
        standard_layer_contract={"response_type": "task_help"},
        strategy_confidence=0.7,
        outcome=outcome,
        outcome_filled_at=decided_at + timedelta(minutes=5) if outcome else None,
        outcome_reason="test" if outcome else None,
    )


@pytest.mark.asyncio
async def test_effectiveness_report_returns_empty_when_fewer_than_10_records(db_session, test_user) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(5):
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-few-{i}",
                decided_at=now - timedelta(hours=i),
                outcome="task_completed",
            )
        )
    await db_session.commit()

    report = await AuroraDecisionTelemetryService(db_session).get_effectiveness_report(days=30)

    assert report.total_turns == 5
    assert report.has_enough_data is False
    assert report.strategy_adjusted_completion_rate == 0.0
    assert report.top_effective_strategy is None


@pytest.mark.asyncio
async def test_effectiveness_report_computes_lift(db_session, test_user) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)

    # 6 strategy-adjusted turns, 5 completed
    for i in range(6):
        outcome = "task_completed" if i < 5 else "timeout"
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-adj-{i}",
                decided_at=now - timedelta(hours=12 - i),
                outcome=outcome,
                strategy=_strategy_payload(concept_first=True),
                conversation_id="conv-eff-adj",
            )
        )

    # 6 baseline turns (no strategy), 3 completed
    for i in range(6):
        outcome = "task_completed" if i < 3 else "timeout"
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-base-{i}",
                decided_at=now - timedelta(hours=6 - i),
                outcome=outcome,
                strategy=_empty_strategy_payload(),
                conversation_id="conv-eff-base",
            )
        )

    await db_session.commit()

    report = await AuroraDecisionTelemetryService(db_session).get_effectiveness_report(days=30)

    assert report.has_enough_data is True
    assert report.strategy_adjusted_turns == 6
    assert report.strategy_adjusted_completed_turns == 5
    assert report.strategy_adjusted.turns == 6
    assert report.strategy_adjusted.completed == 5
    assert report.strategy_adjusted_completion_rate == pytest.approx(5 / 6, abs=0.01)
    assert report.strategy_adjusted.completion_rate == pytest.approx(5 / 6, abs=0.01)

    assert report.non_adjusted_turns == 6
    assert report.baseline_completed_turns == 3
    assert report.baseline.turns == 6
    assert report.baseline.completed == 3
    assert report.baseline_completion_rate == pytest.approx(3 / 6, abs=0.01)
    assert report.baseline.completion_rate == pytest.approx(3 / 6, abs=0.01)
    assert report.lift_percentage == pytest.approx(66.67, abs=0.05)


@pytest.mark.asyncio
async def test_effectiveness_report_identifies_top_strategy(db_session, test_user) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)

    # concept_first: 4 resolved, 3 completed → 75%
    for i in range(4):
        outcome = "task_completed" if i < 3 else "timeout"
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-cf-{i}",
                decided_at=now - timedelta(hours=20 - i),
                outcome=outcome,
                strategy=_strategy_payload(concept_first=True),
            )
        )

    # retrieval_practice: 4 resolved, 1 completed → 25%
    for i in range(4):
        outcome = "task_completed" if i < 1 else "timeout"
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-rp-{i}",
                decided_at=now - timedelta(hours=10 - i),
                outcome=outcome,
                strategy=_strategy_payload(retrieval_practice=True),
            )
        )

    # 4 baseline (no strategy) turns to reach 12 total
    for i in range(4):
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-none-{i}",
                decided_at=now - timedelta(hours=2 - i),
                outcome="skipped",
                strategy=_empty_strategy_payload(),
            )
        )

    await db_session.commit()

    report = await AuroraDecisionTelemetryService(db_session).get_effectiveness_report(days=30)

    assert report.top_effective_strategy == "concept_first"
    assert report.top_effective_strategy_completion_rate == pytest.approx(0.75, abs=0.01)
    assert report.top_effective_strategy_correlation > 0
    assert report.top_effective_strategy_insight is not None
    assert report.top_effective_strategy_insight.strategy == "concept_first"


@pytest.mark.asyncio
async def test_effectiveness_report_wake_score_retention(db_session, test_user) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    today = now.replace(hour=10, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    baseline_user = User(
        username="baseline-user",
        email="baseline@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add(baseline_user)
    await db_session.flush()

    for i in range(3):
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-hw-y-{i}",
                decided_at=yesterday + timedelta(hours=i),
                outcome="task_completed",
                wake_score=0.75,
                conversation_id="conv-eff-high-wake",
            )
        )

    # User returns today → high_wake_return
    for i in range(2):
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-hw-t-{i}",
                decided_at=today + timedelta(hours=i),
                outcome="task_completed",
                wake_score=0.8,
                conversation_id="conv-eff-today",
            )
        )

    for i in range(5):
        db_session.add(
            _make_row(
                user_id=baseline_user.id,
                decision_id=f"eff-lw-y-{i}",
                decided_at=two_days_ago + timedelta(hours=3 + i),
                outcome="task_completed",
                wake_score=0.3,
                conversation_id="conv-eff-low-wake",
            )
        )

    await db_session.commit()

    report = await AuroraDecisionTelemetryService(db_session).get_effectiveness_report(days=30)

    assert report.has_enough_data is True
    assert report.high_wake_score_sessions == 1
    assert report.high_wake_score_next_day_return_rate == pytest.approx(1.0, abs=0.01)
    assert report.baseline_next_day_return_rate == pytest.approx(0.0, abs=0.01)
    assert report.next_day_return_rate_lift_percentage == pytest.approx(100.0, abs=0.01)
    assert report.wake_retention.high_wake_score_return_rate == pytest.approx(1.0, abs=0.01)
    assert report.wake_retention.baseline_return_rate == pytest.approx(0.0, abs=0.01)


@pytest.mark.asyncio
async def test_effectiveness_report_filters_by_user_id(db_session, test_user) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)

    # Create 12 rows for test_user
    for i in range(12):
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-filter-{i}",
                decided_at=now - timedelta(hours=i),
                outcome="task_completed" if i % 2 == 0 else "timeout",
                strategy=_strategy_payload(concept_first=True) if i % 3 == 0 else _empty_strategy_payload(),
            )
        )

    await db_session.commit()

    report = await AuroraDecisionTelemetryService(db_session).get_effectiveness_report(
        user_id=str(test_user.id), days=30
    )

    assert report.has_enough_data is True
    assert report.total_turns == 12


@pytest.mark.asyncio
async def test_effectiveness_report_skips_pending_outcomes(db_session, test_user) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)

    # 10 rows: 5 with outcome, 5 without (pending)
    for i in range(10):
        outcome = "task_completed" if i < 5 else None
        db_session.add(
            _make_row(
                user_id=test_user.id,
                decision_id=f"eff-pending-{i}",
                decided_at=now - timedelta(hours=i),
                outcome=outcome,
                strategy=_strategy_payload(concept_first=True) if i < 5 else _empty_strategy_payload(),
            )
        )

    await db_session.commit()

    report = await AuroraDecisionTelemetryService(db_session).get_effectiveness_report(days=30)

    assert report.total_turns == 10
    assert report.resolved_turns == 5
    assert report.strategy_adjusted.turns + report.baseline.turns == 5
