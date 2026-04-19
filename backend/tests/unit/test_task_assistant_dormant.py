"""WS-D end-to-end acceptance: dormant injection path.

Covers:
1. 5-item initial injection set
2. Cold-start fallback (UXIntent.ROUTINE, AuroraPresenceLevel.AMBIENT)
3. Strong-signal refresh rules
4. Outcome capture for nearline
5. Sidecar/candidate semantics (not frozen enum mutation)
6. Caching and reuse behavior
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from app.task_assistant.dormant_injector import DormantInjector
from app.task_assistant.outcome_capture import OutcomeCapture
from app.task_assistant.refresh_rules import STRONG_SIGNAL_TRIGGERS, is_strong_signal
from app.task_assistant.schemas import (
    AssistantOutcome,
    DormantInjection,
    DormantInjectionItem,
    DormantInjectionKind,
)
from app.task_assistant.store import CacheBackedDormantStore
from app.aurora.schemas.enums import AuroraPresenceLevel, UXIntent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_id() -> UUID:
    return uuid4()


def _task_id() -> UUID:
    return uuid4()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# 1. 5-item injection set
# ---------------------------------------------------------------------------

class TestFiveItemInjectionSet:
    """The injection must contain exactly the 5 approved items."""

    @pytest.mark.asyncio
    async def test_cold_start_produces_five_items(self):
        injector = DormantInjector(store=AsyncMock(spec=CacheBackedDormantStore))
        injector._store.get_injection = AsyncMock(return_value=None)
        injector._store.save_injection = AsyncMock()

        result = await injector.inject(_task_id(), _user_id())

        assert len(result.items) == 5
        kinds = {item.kind for item in result.items}
        assert kinds == {
            DormantInjectionKind.FOCUS_CONTRACT_SUMMARY,
            DormantInjectionKind.TASK_GUIDANCE_AI_OR_FALLBACK,
            DormantInjectionKind.LATEST_TDR_INTENT_PRESENCE,
            DormantInjectionKind.PROJECTION_ALLOWED_INSIGHT_CLAIM,
            DormantInjectionKind.RECENT_PROBE_OUTCOME,
        }

    @pytest.mark.asyncio
    async def test_all_items_unavailable_on_cold_start(self):
        """With no prior_outputs, every item should be available=False."""
        injector = DormantInjector(store=AsyncMock(spec=CacheBackedDormantStore))
        injector._store.get_injection = AsyncMock(return_value=None)
        injector._store.save_injection = AsyncMock()

        result = await injector.inject(_task_id(), _user_id())

        for item in result.items:
            assert item.available is False

    @pytest.mark.asyncio
    async def test_injection_with_prior_outputs(self):
        """With valid prior_outputs, items should be available=True."""
        uid = _user_id()
        tid = _task_id()
        po = {
            "focus_contract": {
                "id": str(uuid4()),
                "focus_description": "Study math",
                "active_node": "calculus",
                "desire_hypothesis": "wants to pass exam",
            },
            "transition_decision_record": {
                "id": str(uuid4()),
                "ux_intent": "routine",
                "aurora_presence": "ambient",
            },
            "insight_claim": {
                "id": str(uuid4()),
                "claim_type": "learning_pattern",
                "content": "User learns best in mornings",
                "confidence": 0.8,
            },
            "probe_outcome": {
                "id": str(uuid4()),
                "probe_type": "preference",
                "result": "confirmed",
                "confidence_adjustment": 0.15,
            },
        }

        injector = DormantInjector(store=AsyncMock(spec=CacheBackedDormantStore))
        injector._store.get_injection = AsyncMock(return_value=None)
        injector._store.save_injection = AsyncMock()

        result = await injector.inject(tid, uid, prior_outputs=po)

        # 4 items have data from po; task_guidance needs TaskGuidance sidecar
        available_count = sum(1 for it in result.items if it.available)
        assert available_count == 4  # focus_contract, tdr, insight_claim, probe_outcome

        # Verify payloads
        fc_item = next(i for i in result.items if i.kind == DormantInjectionKind.FOCUS_CONTRACT_SUMMARY)
        assert fc_item.payload["focus_description"] == "Study math"
        assert fc_item.source_ref is not None


# ---------------------------------------------------------------------------
# 2. Cold-start fallback
# ---------------------------------------------------------------------------

class TestColdStartFallback:
    """Cold-start sessions must fall back to UXIntent.ROUTINE + AMBIENT."""

    @pytest.mark.asyncio
    async def test_cold_start_ux_intent_routine(self):
        injector = DormantInjector(store=AsyncMock(spec=CacheBackedDormantStore))
        injector._store.get_injection = AsyncMock(return_value=None)
        injector._store.save_injection = AsyncMock()

        result = await injector.inject(_task_id(), _user_id())

        assert result.ux_intent == UXIntent.ROUTINE.value

    @pytest.mark.asyncio
    async def test_cold_start_presence_ambient(self):
        injector = DormantInjector(store=AsyncMock(spec=CacheBackedDormantStore))
        injector._store.get_injection = AsyncMock(return_value=None)
        injector._store.save_injection = AsyncMock()

        result = await injector.inject(_task_id(), _user_id())

        assert result.aurora_presence == AuroraPresenceLevel.AMBIENT.value

    @pytest.mark.asyncio
    async def test_even_with_data_still_routine_ambient(self):
        """Even when prior_outputs are provided, dormant stays ROUTINE/AMBIENT."""
        injector = DormantInjector(store=AsyncMock(spec=CacheBackedDormantStore))
        injector._store.get_injection = AsyncMock(return_value=None)
        injector._store.save_injection = AsyncMock()

        result = await injector.inject(
            _task_id(), _user_id(),
            prior_outputs={"focus_contract": {"id": str(uuid4())}},
        )

        assert result.ux_intent == UXIntent.ROUTINE.value
        assert result.aurora_presence == AuroraPresenceLevel.AMBIENT.value


# ---------------------------------------------------------------------------
# 3. Strong-signal refresh rules
# ---------------------------------------------------------------------------

class TestStrongSignalRefresh:
    """Only approved strong signals trigger injection refresh."""

    def test_approved_triggers(self):
        for trigger in STRONG_SIGNAL_TRIGGERS:
            assert is_strong_signal(trigger) is True

    def test_unapproved_triggers_rejected(self):
        assert is_strong_signal("random_event") is False
        assert is_strong_signal("user_sent_message") is False
        assert is_strong_signal("timer_tick") is False
        assert is_strong_signal("") is False

    def test_exactly_five_triggers(self):
        assert len(STRONG_SIGNAL_TRIGGERS) == 5

    @pytest.mark.asyncio
    async def test_cached_injection_reused_without_strong_signal(self):
        """Without force_refresh, the cached injection is reused."""
        cached = DormantInjection(
            task_id=uuid4(),
            user_id=uuid4(),
            items=[],
            ux_intent="routine",
            aurora_presence="ambient",
            generated_by="cached",
            created_at=_utcnow(),
        )
        store = AsyncMock(spec=CacheBackedDormantStore)
        store.get_injection = AsyncMock(return_value=cached)

        injector = DormantInjector(store=store)
        result = await injector.inject(cached.task_id, cached.user_id)

        assert result.generated_by == "cached"
        store.save_injection.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_refresh_rebuilds_injection(self):
        """With force_refresh=True, the injection is rebuilt."""
        cached = DormantInjection(
            task_id=uuid4(),
            user_id=uuid4(),
            items=[],
            ux_intent="routine",
            aurora_presence="ambient",
            generated_by="cached",
            created_at=_utcnow(),
        )
        store = AsyncMock(spec=CacheBackedDormantStore)
        store.get_injection = AsyncMock(return_value=cached)
        store.save_injection = AsyncMock()

        injector = DormantInjector(store=store)
        result = await injector.inject(
            cached.task_id, cached.user_id, force_refresh=True,
        )

        assert result.generated_by == "dormant_injector_v1"
        store.save_injection.assert_called_once()


# ---------------------------------------------------------------------------
# 4. Outcome capture
# ---------------------------------------------------------------------------

class TestOutcomeCapture:
    """Assistant outcome records must be stored for nearline optimization."""

    @pytest.mark.asyncio
    async def test_outcome_stored(self):
        tid = _task_id()
        uid = _user_id()
        store = AsyncMock(spec=CacheBackedDormantStore)
        store.save_outcome = AsyncMock()

        capture = OutcomeCapture(store=store)
        outcome = await capture.record(
            task_id=tid,
            user_id=uid,
            turn_number=1,
            injection_was_used=True,
        )

        assert outcome.task_id == tid
        assert outcome.user_id == uid
        assert outcome.turn_number == 1
        assert outcome.injection_was_used is True
        store.save_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_outcome_has_id_and_timestamp(self):
        store = AsyncMock(spec=CacheBackedDormantStore)
        store.save_outcome = AsyncMock()

        capture = OutcomeCapture(store=store)
        outcome = await capture.record(
            task_id=_task_id(),
            user_id=_user_id(),
            turn_number=2,
        )

        assert outcome.id is not None
        assert outcome.created_at is not None

    @pytest.mark.asyncio
    async def test_outcome_optional_fields(self):
        store = AsyncMock(spec=CacheBackedDormantStore)
        store.save_outcome = AsyncMock()

        capture = OutcomeCapture(store=store)
        outcome = await capture.record(
            task_id=_task_id(),
            user_id=_user_id(),
            turn_number=1,
            conversation_id=uuid4(),
            latency_ms=450.0,
            user_engaged=True,
        )

        assert outcome.conversation_id is not None
        assert outcome.latency_ms == 450.0
        assert outcome.user_engaged is True


# ---------------------------------------------------------------------------
# 5. Sidecar / candidate semantics
# ---------------------------------------------------------------------------

class TestSidecarCandidateSemantics:
    """Dormant mode must remain sidecar/candidate, not frozen enum mutation."""

    def test_dormant_not_in_aurora_presence_level_enum(self):
        """DORMANT must not be added to AuroraPresenceLevel (frozen Gate 0)."""
        names = {e.value for e in AuroraPresenceLevel}
        assert "dormant" not in names
        assert "ambient" in names

    def test_dormant_not_in_ux_intent_enum(self):
        """DORMANT must not be added to UXIntent (frozen Gate 0)."""
        names = {e.value for e in UXIntent}
        assert "dormant" not in names

    @pytest.mark.asyncio
    async def test_injection_is_frozen_pydantic(self):
        """DormantInjection schema is frozen (immutable sidecar)."""
        injection = DormantInjection(
            task_id=uuid4(),
            user_id=uuid4(),
            items=[],
            ux_intent="routine",
            aurora_presence="ambient",
            generated_by="test",
            created_at=_utcnow(),
        )
        with pytest.raises(Exception):
            injection.task_id = uuid4()  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_outcome_is_frozen_pydantic(self):
        """AssistantOutcome schema is frozen (immutable sidecar)."""
        outcome = AssistantOutcome(
            id=uuid4(),
            task_id=uuid4(),
            user_id=uuid4(),
            turn_number=1,
            created_at=_utcnow(),
        )
        with pytest.raises(Exception):
            outcome.turn_number = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6. Store integration
# ---------------------------------------------------------------------------

class TestDormantStore:
    """Cache-backed store operations."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_injection(self):
        store = CacheBackedDormantStore()
        injection = DormantInjection(
            task_id=uuid4(),
            user_id=uuid4(),
            items=[
                DormantInjectionItem(
                    kind=DormantInjectionKind.FOCUS_CONTRACT_SUMMARY,
                    available=True,
                    payload={"focus_description": "test"},
                ),
            ],
            ux_intent="routine",
            aurora_presence="ambient",
            generated_by="test",
            created_at=_utcnow(),
        )

        with patch.object(store, "_store", create=True):
            with patch("app.task_assistant.store.cache_service") as mock_cache:
                mock_cache.get = AsyncMock(return_value=injection.model_dump(mode="json"))
                mock_cache.set = AsyncMock()

                await store.save_injection(injection)
                mock_cache.set.assert_called()

                retrieved = await store.get_injection(injection.task_id, injection.user_id)
                assert retrieved is not None
                assert retrieved.task_id == injection.task_id
                assert len(retrieved.items) == 1

    @pytest.mark.asyncio
    async def test_get_injection_returns_none_when_missing(self):
        store = CacheBackedDormantStore()
        with patch("app.task_assistant.store.cache_service") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            result = await store.get_injection(uuid4(), uuid4())
            assert result is None
