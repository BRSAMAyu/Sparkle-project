"""G13 — Learning Style Persistence: Aurora remembers user preferred strategy.

Verification:
1. When a strategy flag (e.g. problem_first=True) appears >=80% in recent 10 telemetry
   rounds, an InferenceClaim(domain="preferred_strategy", value="problem_first",
   confidence=0.85) is submitted to Redis.
2. DashboardReadoutBuilder._extract_cold_start_context reads the claim from Redis
   and injects cold_start_context["confirmed_strategy_preference"].
3. AuroraDecisionLoop._strategy_defaults_for_readout applies the confirmed preference
   as baseline, overriding surface-based defaults.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.control_surface import AuroraHardBounds
from app.aurora.runtime_v1.dashboard import DashboardReadout, DashboardReadoutBuilder
from app.aurora.runtime_v1.decision_loop import (
    AuroraDecision,
    AuroraDecisionLoop,
    STRATEGY_FIELDS,
)
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.write_pipeline import (
    AURORA_CLAIM_KEY_TEMPLATE,
    InferenceClaim,
    submit_claim,
)


class _FakeRedis:
    """Minimal async FakeRedis supporting get/set/setex/lpush/lrange/ltrim/expire."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def lpush(self, key: str, value: str) -> None:
        bucket = self.lists.setdefault(key, [])
        bucket.insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        bucket = self.lists.setdefault(key, [])
        self.lists[key] = bucket[start : end + 1]

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        bucket = self.lists.get(key, [])
        if end == -1:
            return bucket[start:]
        return bucket[start : end + 1]

    async def expire(self, key: str, seconds: int) -> None:
        del key, seconds


def _make_telemetry_record(*, problem_first: bool = False, concept_first: bool = False) -> str:
    """Create a JSON telemetry record as stored by AuroraDecisionTelemetryService."""
    return json.dumps({
        "decision_id": str(uuid4()),
        "strategy_payload": {
            "problem_first": problem_first,
            "concept_first": concept_first,
            "worked_example_first": False,
            "retrieval_practice": False,
            "interleaving": False,
            "spaced_review": False,
            "error_analysis_required": False,
            "drop_low_roi_topics": False,
            "new_topic_allowed": True,
        },
        "response_type": "task_help",
        "target_domain": "baseline",
        "covered_domains": [],
    })


# ---------------------------------------------------------------------------
# Test 1: Strategy pattern detection → InferenceClaim submitted
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_check_strategy_pattern_submits_claim_on_80_percent():
    """8/10 rounds with problem_first=True → claim submitted."""
    redis = _FakeRedis()
    user_id = "user-g13-test"
    conversation_id = "conv-g13"

    # Seed 10 telemetry records: 8 with problem_first=True, 2 without
    records = [
        _make_telemetry_record(problem_first=True),   # 1
        _make_telemetry_record(problem_first=True),   # 2
        _make_telemetry_record(problem_first=False),  # 3
        _make_telemetry_record(problem_first=True),   # 4
        _make_telemetry_record(problem_first=True),   # 5
        _make_telemetry_record(problem_first=True),   # 6
        _make_telemetry_record(problem_first=False),  # 7
        _make_telemetry_record(problem_first=True),   # 8
        _make_telemetry_record(problem_first=True),   # 9
        _make_telemetry_record(problem_first=True),   # 10
    ]
    from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
    key = AuroraDecisionTelemetryService.recent_telemetry_key(
        user_id=user_id, conversation_id=conversation_id,
    )
    for record in records:
        await redis.lpush(key, record)

    # Invoke _check_strategy_pattern via service
    service = AuroraRuntimeV1Service(redis_client=redis)
    decision = AuroraDecision(
        action="emit_message",
        harness_updates={"strategy": {"problem_first": True}},
    )
    await service._check_strategy_pattern(
        user_id=user_id,
        conversation_id=conversation_id,
        decision=decision,
    )

    # Verify the claim was written to Redis
    claim_key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=user_id, domain="preferred_strategy")
    raw = await redis.get(claim_key)
    assert raw is not None, "Expected InferenceClaim to be submitted to Redis"

    payload = json.loads(raw)
    assert payload.get("domain") == "preferred_strategy"
    assert payload.get("value") == "problem_first"
    # Verify via claims list
    claims = payload.get("claims", [])
    assert len(claims) >= 1
    claim = claims[-1]
    assert claim["value"] == "problem_first"
    assert claim["confidence"] == 0.85
    assert claim["status"] == "confirmed"
    assert claim["source"] == "aurora_runtime_v1_g13"


@pytest.mark.asyncio
async def test_check_strategy_pattern_no_claim_below_threshold():
    """5/10 rounds with problem_first=True (50%) → no claim submitted."""
    redis = _FakeRedis()
    user_id = "user-g13-no"
    conversation_id = "conv-g13-no"

    from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
    key = AuroraDecisionTelemetryService.recent_telemetry_key(
        user_id=user_id, conversation_id=conversation_id,
    )
    for i in range(10):
        await redis.lpush(key, _make_telemetry_record(problem_first=(i < 5)))

    service = AuroraRuntimeV1Service(redis_client=redis)
    decision = AuroraDecision(
        action="emit_message",
        harness_updates={"strategy": {"problem_first": True}},
    )
    await service._check_strategy_pattern(
        user_id=user_id,
        conversation_id=conversation_id,
        decision=decision,
    )

    claim_key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=user_id, domain="preferred_strategy")
    raw = await redis.get(claim_key)
    assert raw is None, "No claim should be submitted when below 80% threshold"


@pytest.mark.asyncio
async def test_check_strategy_pattern_no_claim_below_min_rounds():
    """Fewer than 5 rounds → no claim submitted."""
    redis = _FakeRedis()
    user_id = "user-g13-min"
    conversation_id = "conv-g13-min"

    from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
    key = AuroraDecisionTelemetryService.recent_telemetry_key(
        user_id=user_id, conversation_id=conversation_id,
    )
    for _ in range(4):
        await redis.lpush(key, _make_telemetry_record(problem_first=True))

    service = AuroraRuntimeV1Service(redis_client=redis)
    decision = AuroraDecision(
        action="emit_message",
        harness_updates={"strategy": {"problem_first": True}},
    )
    await service._check_strategy_pattern(
        user_id=user_id,
        conversation_id=conversation_id,
        decision=decision,
    )

    claim_key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=user_id, domain="preferred_strategy")
    raw = await redis.get(claim_key)
    assert raw is None, "No claim should be submitted when below min rounds"


# ---------------------------------------------------------------------------
# Test 2: Dashboard reads confirmed strategy preference from Redis
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dashboard_reads_confirmed_strategy_preference():
    """_extract_cold_start_context injects confirmed_strategy_preference from Redis."""
    redis = _FakeRedis()
    user_id = "user-g13-dash"

    # Pre-populate the claim in Redis
    claim_key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=user_id, domain="preferred_strategy")
    claim_data = {
        "user_id": user_id,
        "domain": "preferred_strategy",
        "value": "problem_first",
        "confidence": 0.85,
        "claims": [{
            "value": "problem_first",
            "confidence": 0.85,
            "status": "confirmed",
            "domain": "preferred_strategy",
        }],
    }
    await redis.setex(claim_key, 86400, json.dumps(claim_data))

    builder = DashboardReadoutBuilder(redis_client=redis)
    cold_start = builder._extract_cold_start_context(
        {},
        {},
        user_id=user_id,
    )
    assert cold_start.get("confirmed_strategy_preference") == "problem_first"


@pytest.mark.asyncio
async def test_dashboard_prefetches_confirmed_strategy_preference_for_async_redis():
    """Async Redis path preloads the preference so build-time cold_start can reuse it."""
    redis = _FakeRedis()
    user_id = "user-g13-prefetch"
    claim_key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=user_id, domain="preferred_strategy")
    await redis.setex(
        claim_key,
        86400,
        json.dumps(
            {
                "user_id": user_id,
                "domain": "preferred_strategy",
                "value": "problem_first",
                "confidence": 0.85,
            }
        ),
    )

    builder = DashboardReadoutBuilder(redis_client=redis)
    user_context_payload = await builder.with_confirmed_strategy_preference_from_redis(
        user_id=user_id,
        user_context_payload={},
        redis_client=redis,
    )
    cold_start = builder._extract_cold_start_context(
        {},
        user_context_payload,
        user_id=user_id,
        redis_client=redis,
    )
    assert cold_start.get("confirmed_strategy_preference") == "problem_first"


@pytest.mark.asyncio
async def test_dashboard_no_preference_when_redis_empty():
    """No crash and no preference when Redis has no claim."""
    redis = _FakeRedis()
    builder = DashboardReadoutBuilder(redis_client=redis)
    cold_start = builder._extract_cold_start_context(
        {},
        {},
        user_id="user-no-pref",
    )
    assert "confirmed_strategy_preference" not in cold_start


# ---------------------------------------------------------------------------
# Test 3: Decision loop applies confirmed preference as baseline
# ---------------------------------------------------------------------------
def _readout(
    *,
    cold_start_context: dict[str, Any] | None = None,
    surface: str = "aurora_modeling",
) -> DashboardReadout:
    return DashboardReadout(
        surface=surface,
        user_id="user-1",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="继续做题",
        activity_profile={},
        hard_bounds=AuroraHardBounds(),
        cold_start_context=dict(cold_start_context or {}),
        covered_domains=["goal", "scope", "baseline", "time"],
        missing_domains=[],
    )


def test_strategy_defaults_apply_confirmed_preference():
    """When cold_start_context has confirmed_strategy_preference='problem_first',
    _strategy_defaults_for_readout sets problem_first=True as baseline,
    overriding the surface default of concept_first=True for aurora_modeling."""
    loop = AuroraDecisionLoop()
    readout = _readout(
        cold_start_context={"confirmed_strategy_preference": "problem_first"},
        surface="aurora_modeling",
    )
    defaults = loop._strategy_defaults_for_readout(readout)
    assert defaults["problem_first"] is True, "problem_first should be True from confirmed preference"
    assert defaults.get("concept_first") is not True, "concept_first should not be True when problem_first is confirmed"


def test_strategy_defaults_no_override_without_preference():
    """Without confirmed_strategy_preference, surface defaults apply normally."""
    loop = AuroraDecisionLoop()
    readout = _readout(
        cold_start_context={},
        surface="aurora_modeling",
    )
    defaults = loop._strategy_defaults_for_readout(readout)
    assert defaults["concept_first"] is True, "aurora_modeling surface should default to concept_first=True"


def test_strategy_defaults_invalid_preference_ignored():
    """An invalid flag name in confirmed_strategy_preference is safely ignored."""
    loop = AuroraDecisionLoop()
    readout = _readout(
        cold_start_context={"confirmed_strategy_preference": "nonexistent_flag"},
        surface="aurora_modeling",
    )
    defaults = loop._strategy_defaults_for_readout(readout)
    # Should fall through to surface default
    assert defaults["concept_first"] is True


# ---------------------------------------------------------------------------
# Test 4: Full flow integration (FakeRedis end-to-end)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_full_flow_strategy_preference_persistence():
    """End-to-end: simulate 10 telemetry rounds → claim submitted →
    dashboard reads it → decision loop applies it."""

    redis = _FakeRedis()
    user_id = "user-g13-e2e"
    conversation_id = "conv-g13-e2e"

    # Step 1: Seed 10 telemetry rounds (8 with problem_first=True)
    from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
    key = AuroraDecisionTelemetryService.recent_telemetry_key(
        user_id=user_id, conversation_id=conversation_id,
    )
    for i in range(10):
        await redis.lpush(key, _make_telemetry_record(problem_first=(i < 8)))

    # Step 2: Run _check_strategy_pattern
    service = AuroraRuntimeV1Service(redis_client=redis)
    decision = AuroraDecision(
        action="emit_message",
        harness_updates={"strategy": {"problem_first": True}},
    )
    await service._check_strategy_pattern(
        user_id=user_id,
        conversation_id=conversation_id,
        decision=decision,
    )

    # Step 3: Dashboard reads preference
    builder = DashboardReadoutBuilder(redis_client=redis)
    cold_start = builder._extract_cold_start_context(
        {},
        {},
        user_id=user_id,
    )
    assert cold_start.get("confirmed_strategy_preference") == "problem_first"

    # Step 4: Decision loop applies it
    loop = AuroraDecisionLoop()
    readout = DashboardReadout(
        surface="aurora_modeling",
        user_id=user_id,
        conversation_id=conversation_id,
        request_id="req-e2e",
        user_message="继续学习",
        activity_profile={},
        hard_bounds=AuroraHardBounds(),
        cold_start_context=cold_start,
        covered_domains=["goal", "scope", "baseline", "time"],
        missing_domains=[],
    )
    defaults = loop._strategy_defaults_for_readout(readout)
    assert defaults["problem_first"] is True, (
        "problem_first should be True from confirmed preference in cold_start_context"
    )
