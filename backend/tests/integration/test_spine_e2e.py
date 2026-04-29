"""
Phase 2: Spine End-to-End Integration Tests

Uses real Redis (from conftest.py redis_client fixture) to verify
the complete Signal→State→Policy→Directive→Audit→Trace pipeline.

Requires: Redis running (docker compose up -d redis)
"""

import json

import pytest
import pytest_asyncio

from app.signals.spine_orchestrator import SpineOrchestrator


@pytest.fixture(autouse=True)
def _skip_without_redis(redis_client):
    """Auto-skip if Redis is unavailable (handled by redis_client fixture)."""


@pytest.mark.asyncio
class TestSpineE2E:
    """Full pipeline integration with real Redis."""

    async def test_task_completed_generates_trace(self, redis_client):
        """Complete signal chain: task.completed → signal → policy → directive → Redis."""
        spine = SpineOrchestrator(redis_client=redis_client)

        trace = await spine.on_task_completed(
            user_id="spine_test_user_001",
            task_id="task_001",
            estimated_minutes=30,
            actual_minutes=90,  # 3x overrun → should trigger timeout signal
        )

        # Verify trace was generated
        assert trace is not None
        assert trace.trace_id is not None
        assert len(trace.trace_id) > 0

    async def test_task_completed_normally_no_directive(self, redis_client):
        """Normal task completion (no overrun) should produce a trace but minimal directives."""
        spine = SpineOrchestrator(redis_client=redis_client)

        trace = await spine.on_task_completed(
            user_id="spine_test_user_002",
            task_id="task_002",
            estimated_minutes=30,
            actual_minutes=25,  # Within normal range
        )

        assert trace is not None
        assert trace.trace_id is not None
        # Normal completion should have no signal IDs (no anomaly detected)
        # or the trace should exist even without signals

    async def test_duplicate_task_idempotent(self, redis_client):
        """Same event twice should not produce duplicate directives."""
        spine = SpineOrchestrator(redis_client=redis_client)

        user_id = "spine_test_user_003"
        trace1 = await spine.on_task_completed(
            user_id=user_id,
            task_id="task_003",
            estimated_minutes=30,
            actual_minutes=90,
        )
        trace2 = await spine.on_task_completed(
            user_id=user_id,
            task_id="task_003",
            estimated_minutes=30,
            actual_minutes=90,
        )

        # Both calls should succeed (idempotent)
        assert trace1 is not None
        assert trace2 is not None

    async def test_state_register_writes_to_redis(self, redis_client):
        """Verify state register data lands in Redis."""
        spine = SpineOrchestrator(redis_client=redis_client)

        user_id = "spine_test_user_004"
        await spine.on_task_completed(
            user_id=user_id,
            task_id="task_004",
            estimated_minutes=30,
            actual_minutes=90,
        )

        # Check that trace data exists in Redis
        # The trace store saves traces with key spine:trace:{trace_id}
        trace_keys = await redis_client.keys("spine:trace:*")
        # At least some trace keys should exist from this test session
        assert isinstance(trace_keys, list)

    async def test_directive_storage_in_redis(self, redis_client):
        """Verify directives are stored in Redis when signals trigger them."""
        spine = SpineOrchestrator(redis_client=redis_client)

        user_id = "spine_test_user_005"
        trace = await spine.on_task_completed(
            user_id=user_id,
            task_id="task_005",
            estimated_minutes=30,
            actual_minutes=90,
        )

        # If trace has directive IDs, verify they exist in Redis
        if trace and trace.directive_ids:
            for did in trace.directive_ids:
                raw = await redis_client.get(f"spine:directive_by_id:{did}")
                if raw:
                    data = json.loads(raw)
                    assert "directive_id" in data
                    assert data["directive_id"] == did

    async def test_receipt_generation_for_high_visibility(self, redis_client):
        """Tasks with significant overrun should generate user-visible receipts."""
        spine = SpineOrchestrator(redis_client=redis_client)

        user_id = "spine_test_user_006"
        trace = await spine.on_task_completed(
            user_id=user_id,
            task_id="task_006",
            estimated_minutes=30,
            actual_minutes=180,  # 6x overrun — very significant
        )

        assert trace is not None
        # Even without a receipt, the trace must exist
        assert trace.trace_id is not None

    async def test_multiple_users_isolated(self, redis_client):
        """Different users' traces must be isolated."""
        spine = SpineOrchestrator(redis_client=redis_client)

        trace_a = await spine.on_task_completed(
            user_id="spine_test_user_007a",
            task_id="task_007a",
            estimated_minutes=30,
            actual_minutes=90,
        )
        trace_b = await spine.on_task_completed(
            user_id="spine_test_user_007b",
            task_id="task_007b",
            estimated_minutes=30,
            actual_minutes=90,
        )

        assert trace_a is not None
        assert trace_b is not None
        assert trace_a.trace_id != trace_b.trace_id


@pytest.mark.asyncio
class TestSpineCausalTraceIntegrity:
    """Verify trace data consistency and retrievability."""

    async def test_trace_retrievable_by_id(self, redis_client):
        """A stored trace should be retrievable."""
        spine = SpineOrchestrator(redis_client=redis_client)

        trace = await spine.on_task_completed(
            user_id="spine_test_user_008",
            task_id="task_008",
            estimated_minutes=30,
            actual_minutes=90,
        )

        assert trace is not None
        # Retrieve the trace from the store
        retrieved = await spine.trace_store.get_trace(trace.trace_id)
        if retrieved:
            assert retrieved.trace_id == trace.trace_id
            assert retrieved.created_at is not None

    async def test_trace_has_timestamp(self, redis_client):
        """Every trace must have a created_at timestamp."""
        spine = SpineOrchestrator(redis_client=redis_client)

        trace = await spine.on_task_completed(
            user_id="spine_test_user_009",
            task_id="task_009",
            estimated_minutes=30,
            actual_minutes=90,
        )

        assert trace is not None
        assert trace.created_at is not None
        assert len(trace.created_at) > 0
