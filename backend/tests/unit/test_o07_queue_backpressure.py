"""O-07 · 队列背压测试（上限/丢弃策略/可观测/有界降级）.

覆盖卡面 acceptance「queue 故障不会无界成本」的投递面：
- 上限解析：按队列覆盖、默认上限、显式不限（0/负）、垃圾 JSON 容错；
- 丢弃策略：深度 ≥ 上限 → 投递被拒（不 send_task）+ drops 指标 + False；
- 可观测：探测成功回写 depth gauge；探测失败记 probe_failures；
- 有界降级：探测失败（broker 不可达）→ 放行投递（send_task 自会失败，
  不存在无界堆积路径）；
- choke point 接线：``celery_dispatch.dispatch_task_async`` 超限丢弃 /
  未超限照常投递。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.core import queue_backpressure as qbp


class TestParseQueueLimits:
    def test_valid_json_parsed(self):
        limits = qbp.parse_queue_limits('{"glm_batch": 200, "default": 1000}')
        assert limits == {"glm_batch": 200, "default": 1000}

    def test_invalid_json_returns_empty(self):
        assert qbp.parse_queue_limits("not-json{") == {}
        assert qbp.parse_queue_limits("") == {}
        assert qbp.parse_queue_limits(None) == {}

    def test_non_object_json_returns_empty(self):
        assert qbp.parse_queue_limits("[1, 2]") == {}

    def test_bad_values_dropped_per_key(self):
        limits = qbp.parse_queue_limits('{"a": true, "b": "x", "c": 1.5, "d": 10}')
        assert limits == {"d": 10}

    def test_zero_and_negative_are_explicit_unlimited(self):
        limits = qbp.parse_queue_limits('{"glm_batch": 0, "low_priority": -1}')
        assert limits == {"glm_batch": 0, "low_priority": -1}


class TestQueueLimitResolution:
    def test_override_beats_default(self, monkeypatch):
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_LIMITS_JSON", '{"glm_batch": 7}')
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_DEFAULT_MAX_DEPTH", 100)
        assert qbp.get_queue_limit("glm_batch") == 7
        assert qbp.get_queue_limit("default") == 100

    def test_explicit_zero_disables_queue_cap(self, monkeypatch):
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_LIMITS_JSON", '{"glm_batch": 0}')
        assert qbp.get_queue_limit("glm_batch") == 0


class TestBackpressureDecision:
    async def test_disabled_flag_allows(self, monkeypatch):
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_ENABLED", False)
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_LIMITS_JSON", '{"glm_batch": 1}')
        decision = await qbp.check_queue_backpressure("glm_batch")
        assert decision.allowed is True
        assert decision.reason == "disabled"

    async def test_probe_failure_degrades_bounded_allow(self, monkeypatch):
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_ENABLED", True)
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_LIMITS_JSON", '{"glm_batch": 5}')
        async def _boom(_queue):
            raise ConnectionError("broker down")
        monkeypatch.setattr(qbp, "_llen_off_loop", _boom)
        before = qbp.QUEUE_BACKPRESSURE_PROBE_FAILURES_TOTAL.labels(queue="glm_batch")._value.get()
        decision = await qbp.check_queue_backpressure("glm_batch")
        assert decision.allowed is True
        assert decision.depth is None
        assert decision.reason == "probe_failed"
        after = qbp.QUEUE_BACKPRESSURE_PROBE_FAILURES_TOTAL.labels(queue="glm_batch")._value.get()
        assert after == before + 1

    async def test_over_cap_rejected_with_drop_metric(self, monkeypatch):
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_ENABLED", True)
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_LIMITS_JSON", '{"glm_batch": 5}')
        async def _llen(_queue):
            return 5
        monkeypatch.setattr(qbp, "_llen_off_loop", _llen)
        before = qbp.QUEUE_BACKPRESSURE_DROPS_TOTAL.labels(queue="glm_batch")._value.get()
        allowed = await qbp.enforce_queue_backpressure("glm_batch")
        assert allowed is False
        after = qbp.QUEUE_BACKPRESSURE_DROPS_TOTAL.labels(queue="glm_batch")._value.get()
        assert after == before + 1

    async def test_under_cap_allows_and_records_depth(self, monkeypatch):
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_ENABLED", True)
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_LIMITS_JSON", '{"glm_batch": 5}')
        async def _llen(_queue):
            return 2
        monkeypatch.setattr(qbp, "_llen_off_loop", _llen)
        decision = await qbp.check_queue_backpressure("glm_batch")
        assert decision.allowed is True
        assert decision.depth == 2
        assert decision.reason == "within_cap"


class TestDispatchChokePointWiring:
    """dispatch_task_async 必须经背压门：超限丢弃（不 send_task）、未超限投递。"""

    def _patch_settings(self, monkeypatch):
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_ENABLED", True)
        monkeypatch.setattr(settings, "QUEUE_BACKPRESSURE_LIMITS_JSON", '{"glm_batch": 5}')

    async def test_dispatch_dropped_when_over_cap(self, monkeypatch):
        self._patch_settings(monkeypatch)
        async def _over(_queue):
            return 99
        monkeypatch.setattr(qbp, "_llen_off_loop", _over)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import dispatch_task_async

        sent = MagicMock()
        monkeypatch.setattr(celery_app, "send_task", sent)

        ok = await dispatch_task_async("classify_node_sector_batch", args=(1,), queue="glm_batch")
        assert ok is False
        sent.assert_not_called()  # 丢弃 = 消息根本不入队（无界堆积被掐断）

    async def test_dispatch_proceeds_when_under_cap(self, monkeypatch):
        self._patch_settings(monkeypatch)
        async def _under(_queue):
            return 1
        monkeypatch.setattr(qbp, "_llen_off_loop", _under)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import dispatch_task_async

        sent = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(celery_app, "send_task", sent)

        ok = await dispatch_task_async("classify_node_sector_batch", args=(1,), queue="glm_batch")
        assert ok is True
        assert sent.call_count == 1

    async def test_dispatch_skips_backpressure_for_unrouted_send(self, monkeypatch):
        """queue=None（不指定队列）不探测，直接走原路径。"""
        self._patch_settings(monkeypatch)
        probes = MagicMock()

        async def _llen(_queue):
            probes()
            return 99
        monkeypatch.setattr(qbp, "_llen_off_loop", _llen)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import dispatch_task_async

        sent = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(celery_app, "send_task", sent)

        ok = await dispatch_task_async("some_task", args=None, queue=None)
        assert ok is True
        probes.assert_not_called()
        sent.assert_called_once()

    async def test_backpressure_crash_falls_back_to_dispatch(self, monkeypatch):
        """背压面自身故障不得打断投递路径（降级到原 send_task 语义）。"""
        self._patch_settings(monkeypatch)
        async def _boom(_queue):
            raise RuntimeError("probe crashed")
        monkeypatch.setattr(qbp, "_llen_off_loop", _boom)

        from app.core.celery_app import celery_app
        from app.core.celery_dispatch import dispatch_task_async

        sent = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(celery_app, "send_task", sent)

        ok = await dispatch_task_async("classify_node_sector_batch", args=(1,), queue="glm_batch")
        assert ok is True
        sent.assert_called_once()
