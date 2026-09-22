"""
PROD-FIX-1 回归测试 — 活栈巡检两大 P1 生产缺陷。

缺陷 1（SecurityMonitor 全死，安全面）：
    main.py 启动时以传参方式调用 ``security_monitor.initialize(cache_service.redis)``，
    而 ``SecurityMonitor.initialize`` 签名无参 → 每次引擎启动 TypeError 被吞成
    warning，登录爆破 / 可疑 IP 监控后台协程从未运行。

缺陷 2（user_state_v1 整体缺失，核心链路）：
    predictive_service 引用了不存在的列 ``KnowledgeNode.importance``（真实列
    ``importance_level``），AttributeError 逃出 PREDICTION_DATA_ERRORS 降级护栏，
    沿 state_aggregator → profile_context_service 一路上抛后吞掉 → 整个
    user_state_v1 上下文从未产出。

本文件钉住修复后的契约：
  1. initialize 接受调用方注入的 redis（对齐 main.py 调用契约）且无参兼容；
  2. 启动成功有可观测标记（initialized / 后台任务登记），失败不再静默
     （计数器 + ERROR 级日志 + 上抛）；
  3. 后台监控协程运行期死亡也可观测（计数器 + ERROR 日志）；
  4. predict_difficulty 按 importance_level 列取数（正常路径语义），
     属性错误类失败降级为默认难度而不是炸穿；
  5. foresight_hint 构建失败时 get_user_state 降级返回完整 user_state_v1
     （默认权重），并打可观测计数；
  6. profile_context 的 user_state_v1 payload 失败可观测（计数 + ERROR 日志）。
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from loguru import logger
from prometheus_client import REGISTRY
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.profile_context import ProfileContext
from app.core.security_monitor import SecurityMonitor
from app.models.galaxy import KnowledgeNode
from app.models.subject import Subject
from app.services.predictive_service import PredictiveService
from app.services.profile_context_service import ProfileContextService
from app.state_aggregator.service import StateAggregatorService


def _counter_total(name: str, labels: dict[str, str] | None = None) -> float | None:
    """读取 prometheus 计数器当前值（不存在时返回 None）。"""
    return REGISTRY.get_sample_value(name, labels or {})


def _capture_error_logs():
    """loguru ERROR 级日志捕获（sink 收到 str 子类 Message）。"""
    records: list = []
    handler_id = logger.add(records.append, level="ERROR")
    return records, lambda: logger.remove(handler_id)


def _log_text(records: list) -> str:
    return "\n".join(str(rec) for rec in records)


# ---------------------------------------------------------------------------
# 缺陷 1：SecurityMonitor 启动契约
# ---------------------------------------------------------------------------


class TestSecurityMonitorStartup:
    def _fresh_monitor(self) -> SecurityMonitor:
        # 单测不污染全局单例：每次用新实例
        return SecurityMonitor()

    @pytest.mark.asyncio
    async def test_initialize_accepts_caller_redis_and_marks_started(self, monkeypatch):
        """main.py 调用契约：initialize(cache_service.redis) 必须成功并留下启动标记。

        缺陷 1 红证：修复前本测试以
        ``TypeError: initialize() takes 1 positional argument but 2 were given``
        失败——即生产每次启动被吞成 warning 的同一异常。
        """
        monitor = self._fresh_monitor()
        sentinel_redis = object()  # 调用方注入（main.py 传 cache_service.redis）

        await monitor.initialize(sentinel_redis)

        assert monitor.initialized is True, "启动成功标记缺失（启动即验）"
        assert monitor.redis is sentinel_redis, "调用方注入的 redis 未被采纳"
        assert len(monitor._background_tasks) == 2, "监控/清理两个后台协程未全部登记"
        assert monitor.get_startup_status()["initialized"] is True

        await monitor.shutdown()
        assert monitor.get_startup_status()["background_tasks"] == 0

    @pytest.mark.asyncio
    async def test_initialize_without_argument_still_works(self):
        """向后兼容：无参调用（类自取 cache_service.redis）也必须可用。"""
        monitor = self._fresh_monitor()
        await monitor.initialize()
        assert monitor.initialized is True
        await monitor.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_failure_is_observable_and_reraises(self, monkeypatch):
        """启动失败不再静默：计数器 + ERROR 日志 + 异常上抛（由 lifespan 收敛）。"""
        monitor = self._fresh_monitor()

        def _explode(coro=None, *args, **kwargs):
            # 先关闭未消费的协程，避免 GC 期 "never awaited" 噪音
            if coro is not None and hasattr(coro, "close"):
                coro.close()
            raise RuntimeError("event loop closed (simulated startup failure)")

        monkeypatch.setattr(asyncio, "create_task", _explode)
        before = _counter_total("sparkle_security_monitor_start_failures_total")
        records, remove = _capture_error_logs()
        try:
            with pytest.raises(RuntimeError):
                await monitor.initialize(object())
        finally:
            remove()

        after = _counter_total("sparkle_security_monitor_start_failures_total")
        assert monitor.initialized is False
        assert (after or 0) - (before or 0) == 1, "启动失败未计数（静默失败）"
        assert (
            "Security Monitor" in _log_text(records)
            or "安全监控" in _log_text(records)
        ), "启动失败未打 ERROR 级日志"

    @pytest.mark.asyncio
    async def test_background_task_death_is_observable(self, monkeypatch):
        """后台监控协程运行期死亡 → 计数器 + ERROR 日志（不许再次静默裸奔）。"""
        monitor = self._fresh_monitor()

        async def _die(self):
            raise RuntimeError("monitor loop died (simulated runtime crash)")

        monkeypatch.setattr(SecurityMonitor, "_monitor_security_events", _die)
        before = _counter_total("sparkle_security_monitor_background_task_failures_total")
        records, remove = _capture_error_logs()
        try:
            await monitor.initialize(object())
            await asyncio.sleep(0.1)  # 让任务实际跑炸、done-callback 落账
        finally:
            remove()

        after = _counter_total("sparkle_security_monitor_background_task_failures_total")
        assert (after or 0) - (before or 0) == 1, "后台协程死亡未计数"
        assert (
            "security monitor background task" in _log_text(records).lower()
            or "安全监控后台" in _log_text(records)
        ), "后台协程死亡未打 ERROR 级日志"
        await monitor.shutdown()


# ---------------------------------------------------------------------------
# 缺陷 2：importance_level 列语义 + 降级护栏
# ---------------------------------------------------------------------------


class TestPredictDifficultyImportanceLevel:
    @pytest.mark.asyncio
    async def test_predict_difficulty_uses_importance_level_column(self, db_session: AsyncSession):
        """正常路径：前置知识按 importance_level 取数，估算时长按 1-5 → 2-10 小时。

        缺陷 2 红证：修复前查询构造即抛
        ``AttributeError: type object 'KnowledgeNode' has no attribute 'importance'``。
        """
        subject = Subject(name="prodfix-subject")
        db_session.add(subject)
        await db_session.flush()

        topic = KnowledgeNode(
            name="topic", subject_id=subject.id, importance_level=2
        )
        prereq_high = KnowledgeNode(
            name="prereq_high", subject_id=subject.id, importance_level=3
        )
        prereq_low = KnowledgeNode(
            name="prereq_low", subject_id=subject.id, importance_level=1
        )
        db_session.add_all([topic, prereq_high, prereq_low])
        await db_session.commit()

        service = PredictiveService(db_session)
        prediction = await service.predict_difficulty(uuid4(), topic.id)

        # 未降级（降级默认的 topic_name 是 "Unknown"）
        assert prediction.topic_name == "topic"
        # 只选中 importance_level 更高的前置（语义按真实列跑通）
        assert prediction.suggested_prerequisites == ["prereq_high"]
        # 前置存在但用户无掌握度记录 → mastery 记 0 → 难度 1.0；
        # base_hours = importance_level(2)*2 = 4 → 4*(1+1.0) = 8.0
        assert prediction.predicted_difficulty == pytest.approx(1.0)
        assert prediction.estimated_time_hours == pytest.approx(8.0)

    @pytest.mark.asyncio
    async def test_predict_difficulty_degrades_on_attribute_error(
        self, db_session: AsyncSession, monkeypatch
    ):
        """防御：属性漂移类失败（AttributeError）必须走默认难度降级，不许炸穿调用方。"""
        subject = Subject(name="prodfix-subject-2")
        db_session.add(subject)
        await db_session.flush()
        topic = KnowledgeNode(name="topic", subject_id=subject.id, importance_level=2)
        db_session.add(topic)
        await db_session.commit()

        service = PredictiveService(db_session)
        monkey_target = AsyncMock(side_effect=AttributeError("simulated column drift"))
        monkeypatch.setattr(service.db, "execute", monkey_target)

        prediction = await service.predict_difficulty(uuid4(), topic.id)

        assert prediction.predicted_difficulty == pytest.approx(0.5)
        assert prediction.topic_name == "Unknown"


# ---------------------------------------------------------------------------
# 缺陷 2：get_user_state 降级与 user_state_v1 可观测性
# ---------------------------------------------------------------------------


class TestUserStateDegradationAndObservability:
    @pytest.mark.asyncio
    async def test_get_user_state_degrades_foresight_hint_to_default(
        self, db_session: AsyncSession, monkeypatch
    ):
        """foresight snapshot 构建失败 → get_user_state 仍返回完整 user_state_v1：
        foresight_hint 为默认（空）权重 + 失败计数 +1。"""
        service = StateAggregatorService(db_session)
        monkeypatch.setattr(
            service.predictive_service,
            "build_foresight_snapshot",
            AsyncMock(
                side_effect=AttributeError(
                    "type object 'KnowledgeNode' has no attribute 'importance'"
                )
            ),
        )

        labels = {"field": "foresight_hint"}
        metric = "sparkle_user_state_field_build_failures_total"
        before = _counter_total(metric, labels)

        state = await service.get_user_state(uuid4(), required_fields=("foresight_hint",))

        after = _counter_total(metric, labels)
        assert state.foresight_hint is not None, "降级失败：字段整体缺失"
        assert state.foresight_hint.value.hint_text is None
        assert state.foresight_hint.value.deviation_count == 0
        assert state.foresight_hint.value.attractor_confidences == ()
        assert (after or 0) - (before or 0) == 1, "降级未打可观测计数"

    @pytest.mark.asyncio
    async def test_user_state_v1_payload_failure_is_observable(
        self, db_session: AsyncSession, monkeypatch
    ):
        """profile_context 的 user_state_v1 payload 失败：计数 + ERROR 日志，不许再是一行无指标 warning。"""
        from app.services import profile_context_service as pcs_module

        metric = "sparkle_user_state_v1_payload_failures_total"
        assert hasattr(pcs_module, "USER_STATE_V1_PAYLOAD_FAILURES_TOTAL"), (
            "user_state_v1 失败计数指标缺失（可观测性未落地）"
        )

        async def _boom(self, *args, **kwargs):
            raise RuntimeError("simulated user_state_v1 failure")

        monkeypatch.setattr(StateAggregatorService, "get_user_state", _boom)

        service = ProfileContextService(db_session, redis={})
        context = ProfileContext()

        before = _counter_total(metric)
        records, remove = _capture_error_logs()
        try:
            await service._populate_user_state_v1_payload(uuid4(), context)
        finally:
            remove()

        after = _counter_total(metric)
        assert context.user_state_v1 is None
        assert (after or 0) - (before or 0) == 1, "user_state_v1 失败未计数"
        assert (
            "user_state_v1" in _log_text(records)
        ), "user_state_v1 失败未打 ERROR 级日志"
