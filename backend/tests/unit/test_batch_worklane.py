"""
E-06 Async Batch Cognitive Worklane 单元测试（全程 mock，零真实 LLM/零真实 broker）。

锁定验收面：
1. 三类任务真走 batch 车道：reflection 触达路径 LLM 注入车道客户端；
   profile aggregation 批任务 model_key 经车道解析（MiniMax 优先）；
   analytics 批任务路由到 glm_batch 队列。变异：拔掉 batch 路由 → 必红。
2. 前台零挤占：车道模型池与前台池隔离；batch 独立预算桶与前台 LLM 桶互不影响。
3. 失败语义：有界重试 → dead_letter 终态登记；幂等重放恰一次；并发同 key 去重。
4. 可观测：business_metrics 落 sparkle_batch_lane_* 指标。
5. 新鲜度/explicit-correction：stale 结果可判别；batch 老结果不得覆盖新显式修正。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from prometheus_client import REGISTRY

from app.config import settings
from app.core.agent_profiles import ModelTier
from app.core.cost_controller import BudgetCircuitBreaker, CostCategory
from app.services.batch_worklane import (
    BatchLaneChatClient,
    BatchLaneOutcome,
    BatchWorkloadKind,
    BatchWorklaneService,
    batch_worklane,
)
from app.services.llm.providers import OpenAICompatibleProvider


# =============================================================================
# 测试替身
# =============================================================================


class FakeRedis:
    """覆盖 batch_worklane 用面的最小异步 redis 替身。"""

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def get(self, key: str):
        return self.kv.get(key)

    async def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        if nx and key in self.kv:
            return None
        self.kv[key] = value
        return True

    async def setex(self, key: str, ttl: int, value: str):
        self.kv[key] = value

    async def delete(self, *keys: str):
        for key in keys:
            self.kv.pop(key, None)

    async def lpush(self, key: str, value: str):
        self.lists.setdefault(key, []).insert(0, value)
        return len(self.lists[key])

    async def ltrim(self, key: str, start: int, stop: int):
        lst = self.lists.get(key, [])
        self.lists[key] = lst[start : stop + 1]

    async def lrange(self, key: str, start: int, stop: int):
        lst = self.lists.get(key, [])
        end = len(lst) if stop < 0 else stop + 1
        return lst[start:end]

    async def exists(self, key: str):
        return 1 if key in self.kv else 0

    async def incrbyfloat(self, key: str, amount: float):
        value = float(self.kv.get(key, "0")) + amount
        self.kv[key] = str(value)
        return value

    async def expire(self, key: str, ttl: int):
        pass


def _rebuild_router(minimax_key: str):
    """以指定 MINIMAX_API_KEY 重建路由器（模拟进程启动 settings 快照）。"""
    from app.core.llm_router import LLMRouter

    with patch.object(settings, "MINIMAX_API_KEY", minimax_key):
        return LLMRouter()


class _ExecutorSpy:
    """记录调用次数/参数的可编程 chat executor。"""

    def __init__(self, responses: list[str] | None = None, exc: Exception | None = None):
        self.calls: list[dict] = []
        self._responses = list(responses or [])
        self._exc = exc

    async def __call__(self, messages, *, model, temperature, max_tokens):
        self.calls.append({"messages": messages, "model": model, "temperature": temperature})
        if self._exc is not None:
            raise self._exc
        if len(self.calls) <= len(self._responses):
            return self._responses[len(self.calls) - 1]
        return self._responses[-1] if self._responses else "ok"


_LANE_CANNED = '{"summary": "批量车道反思摘要", "reasoning": "r", "confidence": 0.8, "evidence": ["e1"]}'


@pytest.fixture
def lane_credentials(monkeypatch):
    """给 GLM_BATCH 链条目注入凭据，使车道可用性门放行（单元测试用假 key）。

    路由器在构造时快照 api_key，因此需同步重建 batch_worklane 引用的路由器。
    """
    monkeypatch.setattr(settings, "ZHIPU_API_KEY", "test-key")
    router = _rebuild_router("")  # 无 MINIMAX key → glm 链（带 test-key 凭据）
    monkeypatch.setattr("app.services.batch_worklane.llm_router", router)


# =============================================================================
# 1) 三类任务真走 batch 车道
# =============================================================================


class TestLaneRouting:
    @pytest.mark.parametrize("kind", list(BatchWorkloadKind))
    def test_lane_selection_resolves_glm_batch_tier_with_minimax_key(self, kind):
        router = _rebuild_router("test-key")
        with patch("app.services.batch_worklane.llm_router", router):
            selection = batch_worklane.resolve_selection(kind)
        assert selection.model_key == "minimax_m3_batch"
        assert selection.config.tier == ModelTier.GLM_BATCH
        assert selection.config.provider.value == "minimax"
        assert selection.config.model_name == settings.MINIMAX_CHAT_MODEL

    @pytest.mark.parametrize("kind", list(BatchWorkloadKind))
    def test_lane_selection_falls_back_to_glm_chain_without_key(self, kind):
        router = _rebuild_router("")
        with patch("app.services.batch_worklane.llm_router", router):
            selection = batch_worklane.resolve_selection(kind)
        assert selection.model_key == "glm_4_7_no_thinking"  # E-02 原链不变
        assert selection.config.tier == ModelTier.GLM_BATCH

    def test_profile_batch_task_model_key_resolution_uses_lane(self):
        """celery 批任务 model_key 缺省时必须经车道解析（MiniMax 优先）。"""
        from app.core.celery_app import resolve_profile_batch_model_key

        router = _rebuild_router("test-key")
        with patch("app.services.batch_worklane.llm_router", router):
            assert resolve_profile_batch_model_key(None) == "minimax_m3_batch"
            # 显式指定优先，不被车道覆盖
            assert resolve_profile_batch_model_key("glm_4_6_batch") == "glm_4_6_batch"

    def test_profile_batch_task_model_key_untouched_when_lane_disabled(self, monkeypatch):
        from app.core.celery_app import resolve_profile_batch_model_key

        monkeypatch.setattr(settings, "BATCH_LANE_ENABLED", False)
        assert resolve_profile_batch_model_key(None) is None

    def test_analytics_tasks_routed_to_glm_batch_queue(self):
        """E-06 变异面：analytics 批任务路由回 default 队列时本测试必红。"""
        from app.core.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert routes["batch_error_analysis"]["queue"] == "glm_batch"
        assert routes["analyze_error_batch"]["queue"] == "glm_batch"
        # profile aggregation 批任务保持 glm_batch 车道队列
        assert routes["analyze_cognitive_fragment_batch"]["queue"] == "glm_batch"
        assert routes["classify_node_sector_batch"]["queue"] == "glm_batch"
        assert "glm_batch" in set(celery_app.conf.task_queues.keys())

    async def test_reflection_wiring_disabled_lane_falls_back_to_foreground_agent(
        self, db_session, monkeypatch
    ):
        """车道关闭时触达反思回退前台 agent（行为与 E-06 之前一致）。"""
        from uuid import uuid4 as _uuid4

        from app.agents.reflection_agent import TriggeredReflectionResult
        from app.core.cache import cache_service
        from app.services.task_reflection_service import TaskReflectionService

        calls: dict[str, int] = {"foreground": 0, "lane": 0}

        def _make_reflector(source: str):
            class _R:
                async def reflect(self, **kwargs):
                    calls[source] += 1
                    return TriggeredReflectionResult(
                        reflection_id=f"reflection-{source}",
                        user_id=str(kwargs["user_id"]),
                        category=str(kwargs["trigger_category"]),
                        summary=f"{source}-summary",
                        confidence=0.8,
                        reasoning="r",
                        evidence=["e1"],
                        llm_latency_ms=10,
                        estimated_cost_usd=0.0,
                        context_tokens=16,
                        context_truncated=False,
                        raw_payload={"summary": f"{source}-summary"},
                    )

            return _R()

        class _StubLane:
            def enabled(self, kind):
                return False  # 车道关闭

            def lane_available(self, kind):
                return (True, None)

            def chat_client(self, kind):
                calls["lane"] += 1
                raise AssertionError("lane client must not be built when lane disabled")

        redis = FakeRedis()
        monkeypatch.setattr(cache_service, "redis", redis)
        service = TaskReflectionService(db_session, redis=redis)

        import app.services.task_reflection_service as trs

        monkeypatch.setattr(trs, "get_reflection_agent", lambda: _make_reflector("foreground"))
        monkeypatch.setattr(trs, "batch_worklane", _StubLane())
        monkeypatch.setattr(service.kill_switch, "is_trigger_enabled", AsyncMock(return_value=True))
        monkeypatch.setattr(service.kill_switch, "get_mode", AsyncMock(return_value="shadow"))
        monkeypatch.setattr(service, "_trigger_on_cooldown", AsyncMock(return_value=False))

        result = await service.handle_triggered_reflection(
            user_id=_uuid4(), category="plan_stall", trigger_payload={}
        )
        assert calls["foreground"] == 1  # 前台 agent 兜底
        assert calls["lane"] == 0
        assert result["summary"] == "foreground-summary"

    async def test_reflection_llm_goes_through_batch_lane_client(self, db_session, monkeypatch):
        """E-06 变异面：拔掉 reflection→batch 车道接线后，前台哨兵触发 AssertionError
        且 lane 命中数归零，本测试必红。"""
        from app.core.cache import cache_service
        from app.services.task_reflection_service import TaskReflectionService

        calls: dict[str, int] = {"lane": 0}

        class _LaneClient:
            async def chat(self, messages, temperature=0.3, **kwargs):
                calls["lane"] += 1
                return _LANE_CANNED

        class _StubLane:
            def enabled(self, kind):
                return True  # 车道启用

            def lane_available(self, kind):
                return (True, None)

            def chat_client(self, kind):
                assert kind == BatchWorkloadKind.REFLECTION
                return _LaneClient()

        redis = FakeRedis()
        monkeypatch.setattr(cache_service, "redis", redis)
        service = TaskReflectionService(db_session, redis=redis)

        import app.services.task_reflection_service as trs

        def _unexpected_foreground():
            raise AssertionError("foreground agent must not be used when lane enabled")

        monkeypatch.setattr(trs, "get_reflection_agent", _unexpected_foreground)
        monkeypatch.setattr(trs, "batch_worklane", _StubLane())
        monkeypatch.setattr(service.kill_switch, "is_trigger_enabled", AsyncMock(return_value=True))
        monkeypatch.setattr(service.kill_switch, "get_mode", AsyncMock(return_value="shadow"))
        monkeypatch.setattr(service, "_trigger_on_cooldown", AsyncMock(return_value=False))

        result = await service.handle_triggered_reflection(
            user_id=uuid4(), category="plan_stall", trigger_payload={}
        )
        assert calls["lane"] == 1  # LLM 经车道客户端执行恰一次
        assert result["summary"] == "批量车道反思摘要"


# =============================================================================
# 2) 前台零挤占：并发池隔离 + 预算核算分离
# =============================================================================


class TestForegroundIsolation:
    @pytest.mark.parametrize(
        "model_key,expected_pool",
        [
            ("minimax_m3_batch", "minimax"),
            ("glm_4_7_no_thinking", "zhipu_coding"),
            ("glm_4_5_air_batch", "zhipu_coding"),
        ],
    )
    def test_lane_provider_pools_are_isolated_from_foreground(self, model_key, expected_pool):
        """batch 车道只落 minimax / zhipu_coding 池，绝不占前台池。"""
        router = _rebuild_router("test-key")
        config = router._available_models[model_key]
        provider = OpenAICompatibleProvider(api_key="k", base_url=config.base_url)
        pool = provider._get_provider_name()
        assert pool == expected_pool
        foreground_pools = {"deepseek", "dashscope", "xiaomi", "zhipu", "siliconflow"}
        assert pool not in foreground_pools

    def test_batch_budget_bucket_isolated_from_foreground(self, monkeypatch):
        """GLM_BATCH 桶耗尽不占用前台 LLM 桶，反之亦然。"""
        from app.core import cache as cache_module

        redis = FakeRedis()
        monkeypatch.setattr(cache_module.cache_service, "redis", redis)
        breaker = BudgetCircuitBreaker(
            budgets={CostCategory.GLM_BATCH: 1.0, CostCategory.LLM: 1.0}
        )

        async def _scenario():
            await breaker.record_spend(CostCategory.GLM_BATCH, 1.5, operation="batch/x")
            batch_within = await breaker.check_budget(CostCategory.GLM_BATCH)
            foreground_within = await breaker.check_budget(CostCategory.LLM)
            return batch_within, foreground_within

        batch_within, foreground_within = asyncio.run(_scenario())
        assert batch_within is False  # batch 桶已超支
        assert foreground_within is True  # 前台桶分毫未动


# =============================================================================
# 3) 失败语义：有界重试 + 死信终态 + 幂等重放恰一次
# =============================================================================


class TestFailureSemantics:
    async def test_run_chat_completes_and_caches_result(self, monkeypatch, lane_credentials):
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)
        spy = _ExecutorSpy(responses=["批次结果"])
        result = await lane.run_chat(
            BatchWorkloadKind.ANALYTICS,
            [{"role": "user", "content": "analyze"}],
            idempotency_key="k1",
            chat_executor=spy,
        )
        assert result.outcome == BatchLaneOutcome.COMPLETED
        assert result.content == "批次结果"
        assert result.source == "batch_worklane"
        assert result.model and result.model_key  # 结果带 model/version 溯源
        assert len(spy.calls) == 1
        # 结果落缓存（重放面）
        raw = store.kv["batch_worklane:result:k1"]
        assert json.loads(raw)["content"] == "批次结果"

    async def test_run_chat_retries_bounded_then_dead_letter(self, monkeypatch, lane_credentials):
        monkeypatch.setattr(settings, "BATCH_LANE_MAX_ATTEMPTS", 3)
        monkeypatch.setattr(settings, "BATCH_LANE_RETRY_BACKOFF_SECONDS", 0.0)
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)
        spy = _ExecutorSpy(exc=RuntimeError("provider down"))
        result = await lane.run_chat(
            BatchWorkloadKind.ANALYTICS,
            [{"role": "user", "content": "analyze"}],
            idempotency_key="k-dead",
            chat_executor=spy,
        )
        assert result.outcome == BatchLaneOutcome.DEAD_LETTER
        assert result.attempts == 3  # 有界：恰 3 次，不无限循环
        assert len(spy.calls) == 3
        assert "provider down" in (result.error or "")
        # 死信登记（不静默丢）
        letters = store.lists["batch_worklane:dead_letters"]
        assert len(letters) == 1
        entry = json.loads(letters[0])
        assert entry["kind"] == "analytics"
        assert entry["idempotency_key"] == "k-dead"

    async def test_replay_exactly_once(self, monkeypatch, lane_credentials):
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)
        spy = _ExecutorSpy(responses=["唯一执行"])
        first = await lane.run_chat(
            BatchWorkloadKind.REFLECTION,
            [{"role": "user", "content": "reflect"}],
            idempotency_key="k-replay",
            chat_executor=spy,
        )
        second = await lane.run_chat(
            BatchWorkloadKind.REFLECTION,
            [{"role": "user", "content": "reflect"}],
            idempotency_key="k-replay",
            chat_executor=spy,
        )
        assert first.outcome == BatchLaneOutcome.COMPLETED
        assert second.outcome == BatchLaneOutcome.REPLAYED
        assert second.replayed is True
        assert second.content == first.content
        assert len(spy.calls) == 1  # LLM 恰好执行一次

    async def test_duplicate_in_flight_is_skipped(self, monkeypatch, lane_credentials):
        store = FakeRedis()
        store.kv["batch_worklane:claim:k-dup"] = "1"  # 另一执行在途
        lane = BatchWorklaneService(store=store)
        spy = _ExecutorSpy()
        result = await lane.run_chat(
            BatchWorkloadKind.PROFILE_AGGREGATION,
            [{"role": "user", "content": "agg"}],
            idempotency_key="k-dup",
            chat_executor=spy,
        )
        assert result.outcome == BatchLaneOutcome.DUPLICATE_SKIPPED
        assert len(spy.calls) == 0

    async def test_lane_cost_accounted_to_glm_batch_bucket_not_foreground(self, monkeypatch, lane_credentials):
        """E-06 守卫：车道成本必须记入 GLM_BATCH 独立预算桶，前台 LLM 桶分文不动。
        （M8 变异：_record_cost 改记 CostCategory.LLM 时本测试必红。）"""
        from datetime import UTC as _UTC, datetime as _datetime

        from app.core import cache as cache_module

        redis = FakeRedis()
        monkeypatch.setattr(cache_module.cache_service, "redis", redis)
        breaker = BudgetCircuitBreaker(
            budgets={CostCategory.GLM_BATCH: 10.0, CostCategory.LLM: 10.0}
        )
        monkeypatch.setattr("app.services.batch_worklane.get_budget_breaker", lambda: breaker)

        store = FakeRedis()
        lane = BatchWorklaneService(store=store)
        spy = _ExecutorSpy(responses=["批次产出" * 100])
        await lane.run_chat(
            BatchWorkloadKind.ANALYTICS,
            [{"role": "user", "content": "analyze" * 50}],
            idempotency_key="k-cost",
            chat_executor=spy,
        )
        date_key = _datetime.now(_UTC).strftime("%Y-%m-%d")
        batch_spend = float(redis.kv.get(f"cost:daily:glm_batch:{date_key}", "0"))
        foreground_spend = float(redis.kv.get(f"cost:daily:llm:{date_key}", "0"))
        assert batch_spend > 0  # 成本落 batch 独立桶
        assert foreground_spend == 0  # 前台桶分文未动

    async def test_lane_semaphore_caps_inflight(self, monkeypatch, lane_credentials):
        """E-06 守卫：车道级总并发闸生效（前台零挤占的并发面）。
        （变异：去掉 semaphore 包裹时本测试必红。）"""
        monkeypatch.setattr(settings, "BATCH_LANE_MAX_CONCURRENCY", 1)
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)

        inflight = {"now": 0, "max": 0}

        async def _slow_execute(selection, messages, temperature, max_tokens):
            inflight["now"] += 1
            inflight["max"] = max(inflight["max"], inflight["now"])
            await asyncio.sleep(0.02)
            inflight["now"] -= 1
            return "ok"

        monkeypatch.setattr(lane, "_execute_once", _slow_execute)

        async def _one(i: int):
            return await lane.run_chat(
                BatchWorkloadKind.ANALYTICS,
                [{"role": "user", "content": f"m{i}"}],
                idempotency_key=f"k-c{i}",
            )

        results = await asyncio.gather(*[_one(i) for i in range(4)])
        assert all(r.outcome == BatchLaneOutcome.COMPLETED for r in results)
        assert inflight["max"] == 1  # 并发闸=1：串行执行，绝不超发

    async def test_budget_exhausted_short_circuits_and_releases_claim(self, monkeypatch, lane_credentials):
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)

        class _ExhaustedBreaker:
            async def check_budget(self, category):
                return category is not CostCategory.GLM_BATCH

        monkeypatch.setattr(
            "app.services.batch_worklane.get_budget_breaker", lambda: _ExhaustedBreaker()
        )
        spy = _ExecutorSpy()
        result = await lane.run_chat(
            BatchWorkloadKind.REFLECTION,
            [{"role": "user", "content": "reflect"}],
            idempotency_key="k-budget",
            chat_executor=spy,
        )
        assert result.outcome == BatchLaneOutcome.BUDGET_EXHAUSTED
        assert len(spy.calls) == 0
        assert "batch_worklane:claim:k-budget" not in store.kv  # claim 已释放

    async def test_disabled_lane_short_circuits(self, monkeypatch):
        monkeypatch.setattr(settings, "BATCH_LANE_ENABLED", False)
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)
        spy = _ExecutorSpy()
        result = await lane.run_chat(
            BatchWorkloadKind.ANALYTICS,
            [{"role": "user", "content": "analyze"}],
            idempotency_key="k-off",
            chat_executor=spy,
        )
        assert result.outcome == BatchLaneOutcome.DISABLED
        assert len(spy.calls) == 0

    async def test_lane_unavailable_without_provider_credentials(self, monkeypatch):
        """无 key 环境（dev/测试）：GLM_BATCH 链上无凭据 → 车道不可用、调用方
        走前台兜底，与 E-06 之前行为一致（不得对空 key 的 provider 发真实请求）。
        路由器构造时快照 api_key（见 lane_credentials fixture 注释），故清空
        key 后必须重建路由器——否则主仓 shell 的 .env 真实 key 仍生效。"""
        monkeypatch.setattr(settings, "ZHIPU_API_KEY", "")
        router = _rebuild_router("")
        monkeypatch.setattr("app.services.batch_worklane.llm_router", router)
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)
        spy = _ExecutorSpy()
        result = await lane.run_chat(
            BatchWorkloadKind.REFLECTION,
            [{"role": "user", "content": "reflect"}],
            idempotency_key="k-nokey",
            chat_executor=spy,
        )
        assert result.outcome == BatchLaneOutcome.DISABLED
        assert result.reason == "no_provider_credentials"
        assert len(spy.calls) == 0  # 绝不打无凭据的真实请求


# =============================================================================
# 4) 可观测：business_metrics 落点
# =============================================================================


class TestObservability:
    def test_batch_lane_metrics_registered_in_business_metrics(self):
        expected = {
            "sparkle_batch_lane_dispatch_total",
            "sparkle_batch_lane_retries_total",
            "sparkle_batch_lane_dead_letter_total",
            "sparkle_batch_lane_cost_usd_total",
            "sparkle_batch_lane_latency_seconds",
            "sparkle_batch_lane_inflight",
            "sparkle_batch_lane_stale_rejected_total",
            "sparkle_batch_lane_budget_rejected_total",
            "sparkle_batch_lane_duplicate_skipped_total",
            "sparkle_batch_lane_disabled_total",
        }
        registered = set(REGISTRY._names_to_collectors.keys())
        assert expected.issubset(registered)

    async def test_dispatch_and_cost_metrics_move_on_lane_run(self, monkeypatch, lane_credentials):
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)
        spy = _ExecutorSpy(responses=["ok"])

        def _sample_total(name: str) -> float:
            collector = REGISTRY._names_to_collectors[name]
            return sum(
                sample.value
                for sample in collector.collect()[0].samples
                if sample.name.endswith("_total") and sample.labels.get("kind") == "analytics"
            )

        before_dispatch = _sample_total("sparkle_batch_lane_dispatch_total")
        before_cost = _sample_total("sparkle_batch_lane_cost_usd_total")
        await lane.run_chat(
            BatchWorkloadKind.ANALYTICS,
            [{"role": "user", "content": "analyze"}],
            idempotency_key="k-metric",
            chat_executor=spy,
        )
        after_dispatch = _sample_total("sparkle_batch_lane_dispatch_total")
        after_cost = _sample_total("sparkle_batch_lane_cost_usd_total")
        assert after_dispatch == before_dispatch + 1
        assert after_cost >= before_cost


# =============================================================================
# 5) 新鲜度 SLA / explicit-correction 覆盖守卫
# =============================================================================


class TestFreshnessAndCorrectionGuard:
    def test_freshness_sla_per_kind(self):
        assert batch_worklane.sla_seconds(BatchWorkloadKind.REFLECTION) <= (
            batch_worklane.sla_seconds(BatchWorkloadKind.PROFILE_AGGREGATION)
        )
        assert batch_worklane.sla_seconds(BatchWorkloadKind.PROFILE_AGGREGATION) <= (
            batch_worklane.sla_seconds(BatchWorkloadKind.ANALYTICS)
        )

    def test_is_result_stale_by_sla(self, monkeypatch):
        monkeypatch.setattr(settings, "BATCH_LANE_FRESHNESS_SLA_ANALYTICS_SECONDS", 3600)
        now = datetime.utcnow()
        fresh = now - timedelta(minutes=30)
        stale = now - timedelta(hours=2)
        assert batch_worklane.is_result_stale(BatchWorkloadKind.ANALYTICS, fresh, now=now) is False
        assert batch_worklane.is_result_stale(BatchWorkloadKind.ANALYTICS, stale, now=now) is True
        assert batch_worklane.is_result_stale(BatchWorkloadKind.ANALYTICS, None, now=now) is True

    def test_should_apply_rejects_newer_explicit_correction(self, monkeypatch):
        started = datetime(2026, 9, 20, 10, 0, 0)
        corrected_after = datetime(2026, 9, 20, 10, 5, 0)  # batch 开始后的人类修正
        can_apply, reason = batch_worklane.should_apply(
            BatchWorkloadKind.REFLECTION,
            batch_started_at=started,
            target_updated_at=corrected_after,
        )
        assert can_apply is False
        assert reason == "newer_explicit_correction"

    def test_should_apply_allows_older_or_absent_target(self):
        started = datetime(2026, 9, 20, 10, 0, 0)
        older = datetime(2026, 9, 20, 9, 0, 0)
        ok_new, _ = batch_worklane.should_apply(
            BatchWorkloadKind.REFLECTION, batch_started_at=started, target_updated_at=older
        )
        ok_none, _ = batch_worklane.should_apply(
            BatchWorkloadKind.REFLECTION, batch_started_at=started, target_updated_at=None
        )
        assert ok_new is True
        assert ok_none is True

    async def test_triggered_reflection_skips_write_when_newer_explicit_correction_exists(
        self, db_session, monkeypatch
    ):
        """E-06 变异面：拔掉守卫（恒放行）时 skip 断言必红。"""
        from app.core.cache import cache_service
        from app.services.task_reflection_service import TaskReflectionService

        class _LaneClient:
            async def chat(self, messages, temperature=0.3, **kwargs):
                return _LANE_CANNED

        class _StubLane:
            def enabled(self, kind):
                return True

            def lane_available(self, kind):
                return (True, None)

            def chat_client(self, kind):
                return _LaneClient()

            def should_apply(self, kind, *, batch_started_at, target_updated_at):
                # 模拟 batch 开始后出现了显式修正
                return (
                    False,
                    "newer_explicit_correction",
                )

        redis = FakeRedis()
        monkeypatch.setattr(cache_service, "redis", redis)
        service = TaskReflectionService(db_session, redis=redis)

        import app.services.task_reflection_service as trs

        monkeypatch.setattr(trs, "batch_worklane", _StubLane())
        monkeypatch.setattr(service.kill_switch, "is_trigger_enabled", AsyncMock(return_value=True))
        monkeypatch.setattr(service.kill_switch, "get_mode", AsyncMock(return_value="live"))
        monkeypatch.setattr(service, "_trigger_on_cooldown", AsyncMock(return_value=False))

        result = await service.handle_triggered_reflection(
            user_id=uuid4(), category="plan_stall", trigger_payload={}
        )
        assert result["status"] == "skipped"
        assert result["reason"] == "newer_explicit_correction"


# =============================================================================
# 6) 车道客户端适配器（ReflectionAgent generator 插槽兼容面）
# =============================================================================


class TestBatchLaneChatClient:
    async def test_client_returns_content_and_uses_lane(self, monkeypatch, lane_credentials):
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)
        monkeypatch.setattr(
            lane, "_execute_once", AsyncMock(return_value="车道内容")
        )
        client = BatchLaneChatClient(BatchWorkloadKind.REFLECTION, lane)
        content = await client.chat(
            [{"role": "user", "content": "hi"}],
            temperature=0.2,
            idempotency_key="k-client",
        )
        assert content == "车道内容"
        # 结果经幂等缓存落库
        raw = store.kv["batch_worklane:result:k-client"]
        assert json.loads(raw)["content"] == "车道内容"

    async def test_client_raises_on_dead_letter(self, monkeypatch, lane_credentials):
        monkeypatch.setattr(settings, "BATCH_LANE_MAX_ATTEMPTS", 1)
        monkeypatch.setattr(settings, "BATCH_LANE_RETRY_BACKOFF_SECONDS", 0.0)
        store = FakeRedis()
        lane = BatchWorklaneService(store=store)
        monkeypatch.setattr(lane, "_execute_once", AsyncMock(side_effect=RuntimeError("boom")))
        client = BatchLaneChatClient(BatchWorkloadKind.REFLECTION, lane)
        with pytest.raises(RuntimeError, match="dead_letter"):
            await client.chat([{"role": "user", "content": "hi"}], idempotency_key="k-client-2")
