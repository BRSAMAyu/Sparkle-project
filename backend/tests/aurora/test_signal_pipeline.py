from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.aurora.ledger import AppendOnlyLedgerStore, ClaimLifecycleManager
from app.aurora.schemas import (
    ClaimLifecycle,
    ClaimSource,
    CommitmentStatus,
    DecisionBasis,
    DecisionMechanism,
    ImpactClass,
    InitiationType,
    InsightClaim,
    ProbeOutcome,
    ProjectionPolicy,
    SignalSnapshot,
    TransitionDecisionRecord,
    UXIntent,
)
from app.aurora.signal_aggregator import SignalAggregator
from app.aurora.signal_processor import SignalProcessor


class _FakeMemoryService:
    async def list_active_goals(self, user_id):
        return [SimpleNamespace(title="goal", status="active", updated_at="2026-04-17T00:00:00")]

    async def list_preferences(self, user_id):
        return {"depth_preference": 0.8, "curiosity_preference": 0.6}

    async def list_recent_episodic(self, user_id, limit=5):
        return [SimpleNamespace(summary="episodic-1")]


class _FakeFocusService:
    async def get_today_stats(self, user_id):
        return {"total_minutes": 120, "pomodoro_count": 4}


class _FakeCompanionStateService:
    async def get_effective_state(self, user_id, *, plan_id=None, session_id=None):
        return {"warmth_calibration": 0.6, "candor_calibration": 0.5}

    async def get_recent_revisions(self, user_id, *, plan_id=None, session_id=None):
        return [{"field": "warmth_calibration", "value": 0.6}]


class _FakeUserStrategyService:
    async def get_effective_state(self, user_id, *, plan_id=None, session_id=None):
        return {"session_mode": "guided", "push_vs_support": 0.4}

    async def get_recent_changes(self, user_id, *, plan_id=None, session_id=None, limit=12):
        return [{"field": "session_mode", "value": "guided"}]


class _FakePersonaService:
    async def get_snapshot(self, user_id, purpose):
        return {"persona_version": "v1", "purpose": purpose, "tags": ["focused"]}


class _FakeErrorBookService:
    async def get_review_stats(self, user_id):
        return {"total_errors": 7, "need_review_count": 2}


class _FakePlanStateService:
    async def get_plan_state(self, user_id, plan_id):
        return {"plan_id": str(plan_id), "facts": {"goal": "exam"}}

    async def get_active_plan_states(self, user_id, limit=5):
        return [{"plan_id": "plan-1", "status": "active"}]


class _FakeAchievementEngine:
    async def get_streak_stats(self, user_id):
        return {"current_streak": 11}

    async def get_user_achievements(self, user_id):
        return [{"achievement_id": "a1"}]


class _FakePredictiveService:
    async def predict_engagement(self, user_id):
        return SimpleNamespace(next_active_time=datetime(2026, 4, 18, 12, 0, 0), confidence=0.7, risk_level="medium")


class _FakeAnalyticsService:
    async def get_user_profile_summary(self, user_id):
        return "active learner"


@pytest.mark.asyncio
async def test_signal_snapshot_assembler_preserves_core_signals_and_trims_budget() -> None:
    aggregator = SignalAggregator(
        service_map={
            "memory_service": _FakeMemoryService(),
            "focus_service": _FakeFocusService(),
            "companion_state_service": _FakeCompanionStateService(),
            "user_strategy_state_service": _FakeUserStrategyService(),
            "persona_service": _FakePersonaService(),
            "error_book_service": _FakeErrorBookService(),
            "plan_state_service": _FakePlanStateService(),
            "achievement_engine": _FakeAchievementEngine(),
            "predictive_service": _FakePredictiveService(),
            "analytics_service": _FakeAnalyticsService(),
        }
    )

    snapshot = await aggregator.assemble_snapshot(
        uuid4(),
        scenario_pack_id="exam_prep_14d@v1.0",
        policy_version="aurora_policy@v1.0",
        budget_limit=240,
        context={"purpose": "test", "plan_id": uuid4()},
    )

    assert isinstance(snapshot, SignalSnapshot)
    assert snapshot.snapshot_hash
    assert snapshot.core_signals
    assert "memory_service" in snapshot.core_signals
    assert "focus_service" in snapshot.core_signals
    assert snapshot.total_tokens <= snapshot.budget_limit
    assert snapshot.retention_tier.value in {"hot", "cold_archive", "reconstructable"}


@pytest.mark.asyncio
async def test_signal_processor_appends_ledger_records_and_applies_writes() -> None:
    ledger = AppendOnlyLedgerStore()
    applied: list[dict[str, object]] = []

    def _commitment_writer(*, user_id, payload):
        applied.append({"user_id": str(user_id), "payload": payload})
        return {"record_id": "commitment-record-1"}

    processor = SignalProcessor(
        ledger=ledger,
        downstream_writers={"commitment": _commitment_writer},
    )
    tdr = TransitionDecisionRecord(
        id=uuid4(),
        user_id=uuid4(),
        created_at=datetime(2026, 4, 18, 9, 0, 0),
        decision_type="transition",
        proposed_transition="day4_focus",
        initiation_type=InitiationType.REACTIVE,
        decision_mechanism=DecisionMechanism.DETERMINISTIC,
        decision_basis=DecisionBasis.COMMITMENT_CONFLICT,
        input_snapshot_ref="snapshot-hash",
        impact_class=ImpactClass.MEDIUM,
        inference_knobs={"stay_bias": 0.7},
        capability_gate={"allow_transition": False},
        rollback_anchor={"prev_focus_contract_version": 2, "prev_active_commitment_ids": ["c1"], "prev_claim_statuses": {}, "policy_version_at_decision": "aurora_policy@v1.0"},
        policy_version="aurora_policy@v1.0",
        ux_intent=UXIntent.ROUTINE,
        projection_policy=ProjectionPolicy.OPEN_DISCUSSABLE,
    )
    claim = InsightClaim(
        id=uuid4(),
        user_id=tdr.user_id,
        created_at=tdr.created_at,
        updated_at=tdr.created_at,
        claim_type="avoidance",
        content="用户今天拖延明显",
        source=ClaimSource.BEHAVIORAL_SIGNAL,
        confidence=0.72,
        projection_policy=ProjectionPolicy.INTERNAL,
    )

    result = processor.process(
        {
            "transition_decision_record": tdr,
            "claims": [claim],
            "write_operations": [
                {
                    "kind": "commitment",
                    "payload": {"commitment_id": "c1", "status": CommitmentStatus.FULFILLED.value, "note": "completed"},
                }
            ],
        }
    )

    assert result["user_id"] == str(tdr.user_id)
    assert ledger.list_decisions(user_id=tdr.user_id)
    assert ledger.latest_by_type("insight_claim", user_id=tdr.user_id) is not None
    assert applied and applied[0]["payload"]["commitment_id"] == "c1"
    assert ledger.latest_by_type("downstream_commitment", user_id=tdr.user_id) is None


@pytest.mark.asyncio
async def test_claim_lifecycle_manager_records_append_only_status_versions() -> None:
    ledger = AppendOnlyLedgerStore()
    manager = ClaimLifecycleManager(ledger)
    claim = InsightClaim(
        id=uuid4(),
        user_id=uuid4(),
        created_at=datetime(2026, 4, 18, 9, 0, 0),
        updated_at=datetime(2026, 4, 18, 9, 0, 0),
        claim_type="pattern",
        content="初始观察",
        source=ClaimSource.USER_REPORT,
        confidence=0.4,
        projection_policy=ProjectionPolicy.OPEN_DISCUSSABLE,
    )

    opened = manager.open_claim(claim)
    probed = manager.register_probe_outcome(
        ProbeOutcome(
            id=uuid4(),
            claim_id=claim.id,
            created_at=datetime(2026, 4, 18, 10, 0, 0),
            probe_type="clarify",
            probe_content="能否举例？",
            result="user_confirmed",
            evidence="user clarified",
            confidence_adjustment=0.15,
        )
    )
    contextualized = manager.contextualize(claim.id, context_note="已和上下文对齐")

    assert opened.status == ClaimLifecycle.OPEN
    assert probed.status == ClaimLifecycle.PROBED
    assert contextualized.status == ClaimLifecycle.CONTEXTUALIZED
    assert manager.get_current_claim(claim.id).status == ClaimLifecycle.CONTEXTUALIZED
    assert len(manager.get_claim_history(claim.id)) >= 2


def test_ledger_cli_appends_rollback_event(tmp_path) -> None:
    store_path = tmp_path / "ledger.json"
    store = AppendOnlyLedgerStore(storage_path=store_path)
    decision = store.record_transition_decision(
        user_id=uuid4(),
        payload={
            "id": str(uuid4()),
            "rollback_anchor": {
                "prev_focus_contract_version": 3,
                "prev_active_commitment_ids": ["c1"],
                "prev_claim_statuses": {},
                "policy_version_at_decision": "aurora_policy@v1.0",
            },
            "policy_version": "aurora_policy@v1.0",
        },
    )

    from app.aurora.ledger import main

    exit_code = main(["--store", str(store_path), "rollback", "--decision-id", decision["payload"]["id"], "--user-id", decision["user_id"]])

    assert exit_code == 0
    reloaded = AppendOnlyLedgerStore.load(store_path)
    assert reloaded.latest_by_type("rollback_event", user_id=decision["user_id"]) is not None
