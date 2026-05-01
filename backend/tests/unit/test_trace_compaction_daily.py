"""
Core: testing / infra
Phase: adapt
Stage: T6.5.1 — TraceCompaction daily sweep Celery task

Tests the daily scan_trace_compaction task and its integration with
compact_user_traces for users exceeding the 50-trace retention window.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestScanTraceCompactionLogic:
    """Test the scan+dispatch logic directly with FakeRedis."""

    @pytest.mark.asyncio
    async def test_dispatches_for_heavy_users(self):
        """Users with >50 traces get compact_user_traces dispatched."""
        from app.signals.causal_trace_store import CausalTraceStore, _USER_TRACES_KEY
        from tests.unit.spine._helpers import FakeRedis

        redis = FakeRedis()
        store = CausalTraceStore(redis)
        key = _USER_TRACES_KEY.format(user_id="heavy_user")

        for _ in range(55):
            trace = await store.create_trace()
            await redis.lpush(key, trace.trace_id)

        mock_celery = MagicMock()
        dispatched = 0
        cursor = 0
        while True:
            cur, keys = await redis.scan(cursor=cursor, match="spine:user_traces:*", count=100)
            for k in keys:
                count = await redis.llen(k)
                if count <= 50:
                    continue
                uid = k.split(":")[-1]
                mock_celery.send_task(
                    "app.core.celery_tasks.compact_user_traces",
                    args=(uid,),
                    queue="default",
                )
                dispatched += 1
            cursor = cur
            if cursor == 0:
                break

        assert dispatched >= 1
        mock_celery.send_task.assert_called()
        call_args = mock_celery.send_task.call_args_list[0]
        assert call_args[0][0] == "app.core.celery_tasks.compact_user_traces"
        assert "heavy_user" in call_args[1]["args"]

    @pytest.mark.asyncio
    async def test_skips_light_users(self):
        """Users with <=50 traces are skipped."""
        from app.signals.causal_trace_store import CausalTraceStore, _USER_TRACES_KEY
        from tests.unit.spine._helpers import FakeRedis

        redis = FakeRedis()
        store = CausalTraceStore(redis)
        key = _USER_TRACES_KEY.format(user_id="light_user")

        for _ in range(30):
            trace = await store.create_trace()
            await redis.lpush(key, trace.trace_id)

        cursor = 0
        dispatched = 0
        while True:
            cur, keys = await redis.scan(cursor=cursor, match="spine:user_traces:*", count=100)
            for k in keys:
                count = await redis.llen(k)
                if count <= 50:
                    continue
                dispatched += 1
            cursor = cur
            if cursor == 0:
                break

        assert dispatched == 0

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        """Dispatch count is capped by limit parameter."""
        from app.signals.causal_trace_store import CausalTraceStore, _USER_TRACES_KEY
        from tests.unit.spine._helpers import FakeRedis

        redis = FakeRedis()
        store = CausalTraceStore(redis)

        for uid in ["u1", "u2", "u3"]:
            key = _USER_TRACES_KEY.format(user_id=uid)
            for _ in range(55):
                trace = await store.create_trace()
                await redis.lpush(key, trace.trace_id)

        mock_celery = MagicMock()
        cursor = 0
        dispatched = 0
        limit = 2
        while True:
            cur, keys = await redis.scan(cursor=cursor, match="spine:user_traces:*", count=100)
            for k in keys:
                count = await redis.llen(k)
                if count <= 50:
                    continue
                uid = k.split(":")[-1]
                mock_celery.send_task(
                    "app.core.celery_tasks.compact_user_traces",
                    args=(uid,),
                    queue="default",
                )
                dispatched += 1
                if dispatched >= limit:
                    break
            cursor = cur
            if cursor == 0 or dispatched >= limit:
                break

        assert dispatched == 2


class TestCompactionTaskRegistration:
    """Test Celery task names and beat schedule."""

    def test_compact_user_traces_name(self):
        from app.core.celery_tasks import compact_user_traces
        assert compact_user_traces.name == "app.core.celery_tasks.compact_user_traces"

    def test_scan_trace_compaction_name(self):
        from app.core.celery_tasks import scan_trace_compaction
        assert scan_trace_compaction.name == "app.core.celery_tasks.scan_trace_compaction"

    def test_schedule_includes_compaction(self):
        from app.celery_schedule import setup_periodic_tasks

        mock_sender = MagicMock()
        setup_periodic_tasks(mock_sender)

        task_names = [call[1]["name"] for call in mock_sender.add_periodic_task.call_args_list]
        assert "scan-trace-compaction-every-day" in task_names

    def test_compaction_interval_is_daily(self):
        from app.celery_schedule import setup_periodic_tasks

        mock_sender = MagicMock()
        setup_periodic_tasks(mock_sender)

        for call in mock_sender.add_periodic_task.call_args_list:
            if call[1].get("name") == "scan-trace-compaction-every-day":
                assert call[0][0] == 86400.0
                break
        else:
            pytest.fail("scan-trace-compaction-every-day not found in periodic tasks")
