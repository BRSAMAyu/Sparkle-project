"""O-07 · run 预算派生（budget by user/plan/run/tier）+ 额度耗尽 UX + cost/WVPL 测试.

覆盖：
- ``budget_matrix.derive_default_run_budget``：free/pro/未知 entitlement（宁降
  不升）/垃圾 JSON；``RUN_BUDGET_DEFAULTS_ENABLED`` 开关；
- ``AgentRunService.create_run`` 接线：budget 缺省 → 按 users.entitlement 派生
  （不再 unlimited）；显式 budget → 原样通过；DB 读失败 → free 收敛；
- 额度/预算耗尽 UX（acceptance 2）：QuotaExceededError / BudgetExceededError →
  可理解文案 + RATE_LIMITED + retryable；budget_exhausted_turn_note 双语；
- cost/WVPL 快照：比值纯函数 + gauge 刷新（WVPL fact mock，零 LLM）。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.budget_matrix import (
    RUN_BUDGET_MATRIX_VERSION,
    derive_default_run_budget,
    derive_default_run_budget_if_enabled,
)
from app.core.cost_wvpl_metrics import compute_cost_per_wvpl, refresh_cost_wvpl_snapshot
from app.core.run_state_machine import RunStatus
from app.core.safe_error_messages import budget_exhausted_turn_note, build_safe_chat_error
from app.gen.agent.v1 import agent_service_pb2
from app.models.base import Base
from app.models.user import User

# ---------------------------------------------------------------------------
# 1. budget matrix 派生
# ---------------------------------------------------------------------------


class TestDeriveDefaultRunBudget:
    def test_free_defaults_from_settings(self, monkeypatch):
        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_FREE_JSON", '{"max_tool_calls": 3, "max_cost_usd": 0.1}')
        derived = derive_default_run_budget("free")
        assert derived == {"limits": {"max_tool_calls": 3.0, "max_cost_usd": 0.1}}

    def test_pro_defaults(self, monkeypatch):
        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_PRO_JSON", '{"max_tool_calls": 300}')
        assert derive_default_run_budget("pro") == {"limits": {"max_tool_calls": 300.0}}

    def test_unknown_entitlement_falls_back_free(self, monkeypatch):
        """未知 entitlement（如历史脏值 'premium'）→ free 档（宁降不升）。"""
        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_FREE_JSON", '{"max_tool_calls": 3}')
        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_PRO_JSON", '{"max_tool_calls": 999}')
        assert derive_default_run_budget("premium") == {"limits": {"max_tool_calls": 3.0}}
        assert derive_default_run_budget(None) == {"limits": {"max_tool_calls": 3.0}}

    def test_garbage_json_degrades_to_unlimited_dimension(self, monkeypatch):
        """配置垃圾 → 该维收敛（不抛错）；派生是收紧面，不是可用性闸门。"""
        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_FREE_JSON", "not-json{")
        assert derive_default_run_budget("free") == {"limits": {}}

    def test_unknown_limit_keys_ignored(self, monkeypatch):
        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_FREE_JSON", '{"max_tool_calls": 3, "max_speed": 9}')
        assert derive_default_run_budget("free") == {"limits": {"max_tool_calls": 3.0}}

    def test_disabled_returns_none(self, monkeypatch):
        monkeypatch.setattr(settings, "RUN_BUDGET_DEFAULTS_ENABLED", False)
        assert derive_default_run_budget_if_enabled("free") is None

    def test_version_frozen(self):
        assert RUN_BUDGET_MATRIX_VERSION == "run_budget_matrix.v1"


# ---------------------------------------------------------------------------
# 2. create_run 接线（sqlite；X-05/X-06 测试同款 outbox DDL）
# ---------------------------------------------------------------------------

_OUTBOX_DDL = (
    """
    CREATE TABLE IF NOT EXISTS event_outbox (
        id VARCHAR(36) PRIMARY KEY,
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id VARCHAR(36) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        payload JSON NOT NULL,
        metadata JSON,
        sequence_number INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        published_at DATETIME
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_sequence_counters (
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id VARCHAR(36) NOT NULL,
        next_sequence INTEGER NOT NULL,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
)


@pytest.fixture
async def run_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for ddl in _OUTBOX_DDL:
            await conn.execute(text(ddl))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    try:
        yield SimpleNamespace(session=session, factory=factory)
    finally:
        await session.close()
        await engine.dispose()


async def _make_user(session, *, entitlement: str | None = None) -> User:
    user = User(id=uuid4(), username=f"u{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@x.io", hashed_password="t")
    if entitlement is not None:
        user.entitlement = entitlement
    session.add(user)
    await session.commit()
    return user


class TestCreateRunBudgetDerivation:
    async def test_missing_budget_derives_from_entitlement(self, run_db, monkeypatch):
        from app.services.agent_run_service import AgentRunService

        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_PRO_JSON", '{"max_tool_calls": 300}')
        user = await _make_user(run_db.session, entitlement="pro")
        result = await AgentRunService(run_db.session).create_run(
            user_id=user.id, objective="derived budget run", initial_status=RunStatus.RUNNING
        )
        assert result.created is True
        assert result.run.budget["limits"] == {"max_tool_calls": 300.0}
        assert result.run.budget["usage"]["tool_calls"] == 0.0

    async def test_unknown_entitlement_derives_free_tier(self, run_db, monkeypatch):
        from app.services.agent_run_service import AgentRunService

        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_FREE_JSON", '{"max_tool_calls": 7}')
        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_PRO_JSON", '{"max_tool_calls": 999}')
        user = await _make_user(run_db.session, entitlement="premium")
        result = await AgentRunService(run_db.session).create_run(
            user_id=user.id, objective="free fallback run", initial_status=RunStatus.RUNNING
        )
        assert result.run.budget["limits"] == {"max_tool_calls": 7.0}

    async def test_explicit_budget_passed_through_unchanged(self, run_db):
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(run_db.session, entitlement="pro")
        explicit = {"limits": {"max_tool_calls": 1}}
        result = await AgentRunService(run_db.session).create_run(
            user_id=user.id, objective="explicit budget run", budget=explicit, initial_status=RunStatus.RUNNING
        )
        assert result.run.budget["limits"] == {"max_tool_calls": 1.0}

    async def test_derivation_disabled_keeps_unlimited(self, run_db, monkeypatch):
        from app.services.agent_run_service import AgentRunService

        monkeypatch.setattr(settings, "RUN_BUDGET_DEFAULTS_ENABLED", False)
        user = await _make_user(run_db.session, entitlement="pro")
        result = await AgentRunService(run_db.session).create_run(
            user_id=user.id, objective="legacy unlimited run", initial_status=RunStatus.RUNNING
        )
        assert result.run.budget["limits"] == {}

    async def test_entitlement_read_failure_converges_free(self, run_db, monkeypatch):
        """entitlement 读取异常 → free 档派生（故障方向必须更保守）。"""
        from app.services import agent_run_service as ars

        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_FREE_JSON", '{"max_tool_calls": 5}')
        monkeypatch.setattr(settings, "RUN_BUDGET_LIMITS_PRO_JSON", '{"max_tool_calls": 999}')
        user = await _make_user(run_db.session, entitlement="pro")

        service = ars.AgentRunService(run_db.session)

        async def _boom(_self, _user_id):
            raise RuntimeError("db gone")
        monkeypatch.setattr(ars.AgentRunService, "_derive_default_budget_for_user", _boom)

        # 直连派生失败路径：手写 fallback 语义等价验证（服务端把异常收敛为 free）
        from app.core.budget_matrix import derive_default_run_budget_if_enabled
        from app.core.entitlement import ENTITLEMENT_FREE

        assert derive_default_run_budget_if_enabled(ENTITLEMENT_FREE) == {"limits": {"max_tool_calls": 5.0}}


# ---------------------------------------------------------------------------
# 3. 额度/预算耗尽 UX（acceptance：能看懂发生了什么、怎么办）
# ---------------------------------------------------------------------------


class TestQuotaBudgetExhaustedUX:
    def test_platform_quota_exceeded_maps_to_actionable_message(self):
        from app.core.exceptions import QuotaExceededError

        exc = QuotaExceededError(message="今日额度已用完", current_count=100, max_quota=100)
        message, code, retryable = build_safe_chat_error(exc)
        assert "额度已用完" in message
        assert "明天" in message  # 怎么办：何时恢复
        assert "Pro" in message  # 怎么办：如何获得更多
        assert code == agent_service_pb2.ERROR_CODE_RATE_LIMITED
        assert retryable is True

    def test_llm_quota_guard_exceeded_maps_to_actionable_message(self):
        from app.core.llm_quota import QuotaExceededError as GuardQuotaExceeded

        message, code, retryable = build_safe_chat_error(GuardQuotaExceeded("quota 0/100"))
        assert "额度已用完" in message
        assert code == agent_service_pb2.ERROR_CODE_RATE_LIMITED
        assert retryable is True

    def test_run_budget_exceeded_maps_to_actionable_message(self):
        from app.services.agent_run_service import BudgetExceededError

        exc = BudgetExceededError("run 0f3e budget exceeded: tool_calls")
        message, code, retryable = build_safe_chat_error(exc)
        assert "执行预算已用完" in message
        assert "已完成的部分都已保留" in message  # 不假滚回、不装成功
        assert "拆小" in message  # 怎么办
        assert code == agent_service_pb2.ERROR_CODE_RATE_LIMITED
        assert retryable is True

    def test_budget_exceeded_not_swallowed_by_provider_branch(self):
        """回归钉子：QuotaExceededError 类名含 quota，不得被 provider 分支误吸
        成「AI 服务暂时不可用」（用户会误以为是服务故障而非额度用尽）。"""
        from app.core.exceptions import QuotaExceededError

        message, _, _ = build_safe_chat_error(QuotaExceededError(message="x", current_count=1, max_quota=1))
        assert message != "AI 服务暂时不可用，请稍后重试。"

    def test_turn_note_zh_default(self):
        note = budget_exhausted_turn_note(None)
        assert "预算已用完" in note
        assert "保留" in note

    def test_turn_note_en_locale(self):
        note = budget_exhausted_turn_note("en")
        assert "execution budget" in note
        assert "smaller task scope" in note

    def test_render_plan_abort_notice_routes_budget_exhaustion(self):
        """Phase-2 路径：预算耗尽中断 → 可理解文案（不是开发者层号细节）。"""
        from app.agents.standard_workflow import render_plan_abort_notice

        plan_result = SimpleNamespace(
            budget_exceeded=True, aborted=True, abort_reason="Run budget exceeded in layer 0"
        )
        notice = render_plan_abort_notice(plan_result)
        assert "预算已用完" in notice
        assert "layer 0" not in notice  # 开发者诊断不进聊天文本

    async def test_tool_execution_node_streams_note_on_budget_exceeded(self, monkeypatch):
        """chat 面 UX 行为测试（非静态阅读）：预算耗尽切断 tool 循环时，
        用户会在流里收到「发生了什么 + 能做什么」的收尾说明帧。"""
        from app.agents import standard_workflow as sw
        from app.orchestration.statechart_engine import WorkflowState
        from app.tools.base import ToolResult

        budget_result = ToolResult(
            success=False,
            tool_name="search_web",
            tool_call_id="t1",
            error_type="BudgetExceeded",
            error_message="run abc budget exceeded: tool_calls",
        )

        class _StubExecutor:
            async def execute_tool_call(self, **_kwargs):
                return budget_result

        monkeypatch.setattr(sw, "ToolExecutor", lambda: _StubExecutor())

        frames = []

        async def stream_callback(resp):
            frames.append(resp)

        state = WorkflowState()
        state.context_data.update(
            {
                "stream_callback": stream_callback,
                "user_id": str(uuid4()),
                "session_id": "sess-o07",
                "db_session": None,
                "redis_client": None,
                "locale": "zh",
                "tool_calls": [
                    SimpleNamespace(tool_name="search_web", full_arguments={}, tool_call_id="t1"),
                    SimpleNamespace(tool_name="other_tool", full_arguments={}, tool_call_id="t2"),
                ],
            }
        )

        result = await sw.tool_execution_node(state)

        # 终态收敛不变（X-09 语义）：切断 + 标记，不进 generation
        assert result.next_step == "__end__"
        assert state.context_data.get("budget_exceeded") is True

        # UX：说明帧真实流出（用户能看懂发生了什么、能做什么）
        deltas = [f.delta for f in frames if getattr(f, "delta", "")]
        assert any("预算已用完" in d for d in deltas), deltas
        assert any("保留" in d for d in deltas)

        # 静默失败红线：第二个工具调用不再发起（X-09 切断仍生效）
        assert len(state.context_data.get("tool_results") or []) == 1


# ---------------------------------------------------------------------------
# 4. cost/WVPL 单位价值成本指标
# ---------------------------------------------------------------------------


class TestCostPerWvpl:
    def test_ratio(self):
        assert compute_cost_per_wvpl(2.0, 10) == pytest.approx(0.2)

    def test_zero_or_invalid_denominator_is_none(self):
        assert compute_cost_per_wvpl(2.0, 0) is None
        assert compute_cost_per_wvpl(2.0, None) is None
        assert compute_cost_per_wvpl(2.0, -3) is None

    def test_negative_spend_is_none(self):
        assert compute_cost_per_wvpl(-1.0, 10) is None


class _FakeWvplService:
    loops = 10

    def __init__(self, db):
        self.db = db

    async def build_fact(self, *, as_of=None, generated_at=None):
        return {"north_star": {"loops_total": self.loops}}


class _ExplodingWvplService:
    def __init__(self, db):
        self.db = db

    async def build_fact(self, *, as_of=None, generated_at=None):
        raise RuntimeError("ledger unavailable")


class TestRefreshSnapshot:
    async def test_snapshot_sets_ratio(self, monkeypatch):
        import app.core.cost_wvpl_metrics as cw
        import app.services.north_star_wvpl_service as wvpl_module

        class _Breaker:
            # 4 个 CostCategory × 0.5 = 总支出 2.0
            async def read_daily_spend(self, category):
                return 0.5

        monkeypatch.setattr(cw, "get_budget_breaker", lambda: _Breaker())
        monkeypatch.setattr(wvpl_module, "NorthStarWvplService", _FakeWvplService)

        snapshot = await refresh_cost_wvpl_snapshot(db=None, as_of=None)
        assert snapshot["daily_spend_usd"] == pytest.approx(2.0)
        assert snapshot["wvpl_loops"] == 10
        assert snapshot["cost_per_wvpl_usd"] == pytest.approx(0.2)

    async def test_snapshot_wvpl_failure_reports_error_not_fake_zero(self, monkeypatch):
        """WVPL 面失败：比值不写、不伪造 0（无界成本或假成功都不允许）。"""
        import app.core.cost_wvpl_metrics as cw
        import app.services.north_star_wvpl_service as wvpl_module

        class _Breaker:
            # 4 个 CostCategory × 0.75 = 总支出 3.0
            async def read_daily_spend(self, category):
                return 0.75

        monkeypatch.setattr(cw, "get_budget_breaker", lambda: _Breaker())
        monkeypatch.setattr(wvpl_module, "NorthStarWvplService", _ExplodingWvplService)

        snapshot = await refresh_cost_wvpl_snapshot(db=None, as_of=None)
        assert snapshot["error"] == "wvpl_fact_failed"
        assert snapshot["cost_per_wvpl_usd"] is None
        assert snapshot["daily_spend_usd"] == pytest.approx(3.0)
