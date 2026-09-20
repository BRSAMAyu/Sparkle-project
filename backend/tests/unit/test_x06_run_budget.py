"""X-06 · Run Budget 契约测试（token/cost/time/tool_calls 四维 → BUDGET_EXCEEDED）.

覆盖卡面验收：
- budget 超限进入**明确终态**（BUDGET_EXCEEDED）：状态机合法迁移 + 审计行 +
  run.status_changed 事件（D-01 36 词表内事件名，零新事件）+ to_dict().is_terminal
  （mobile 读服务 agent_run_read_service.dart 直接消费该字段——投影可见）；
- 非静默截断：超限抛 BudgetExceededError / executor 拒绝调用（error_type=
  BudgetExceeded），run 停在终态，绝不无限执行；
- fail-closed：垃圾 budget / 越表能力词在 create_run 即拒绝；
- usage 记账：tool_calls/cost/tokens 递增；终态 run 拒绝记账；
- resume 闸门：等待中的 run 时间预算耗尽 → resume 落 BUDGET_EXCEEDED 而非复活。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.run_state_machine import RunStatus
from app.models.agent_run import AgentRun
from app.models.base import Base
from app.models.user import User
from app.orchestration import executor as executor_module
from app.orchestration.executor import ToolExecutor
from app.services.agent_run_service import (
    AgentRunService,
    BudgetExceededError,
    evaluate_budget,
    normalize_budget,
)
from app.tools.base import ToolCategory, ToolResult

# event_outbox / event_sequence_counters 最小 sqlite 表（X-05 测试同款 DDL）。
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
async def budget_db():
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


async def _make_user(session) -> User:
    user = User(id=uuid4(), username=f"u{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@x.io", hashed_password="t")
    session.add(user)
    await session.commit()
    return user


async def _make_run(session, user: User, *, budget: dict | None = None, status=RunStatus.RUNNING, started_at=None):
    service = AgentRunService(session)
    result = await service.create_run(
        user_id=user.id,
        objective="budget test run",
        budget=budget,
        initial_status=status,
    )
    run = result.run
    if started_at is not None:
        run.started_at = started_at
        await session.commit()
    return run


# ---------------------------------------------------------------------------
# 1. budget 形状归一化（fail-closed）
# ---------------------------------------------------------------------------


class TestBudgetNormalization:
    def test_empty_budget_is_unlimited(self):
        canonical = normalize_budget(None)
        assert canonical == {"limits": {}, "usage": {"tool_calls": 0.0, "total_tokens": 0.0, "cost_usd": 0.0}}

    def test_full_shape_normalizes(self):
        canonical = normalize_budget(
            {"limits": {"max_tool_calls": 5, "max_total_tokens": 1000, "max_cost_usd": 0.5, "max_duration_seconds": 600}}
        )
        assert set(canonical["limits"]) == {"max_tool_calls", "max_total_tokens", "max_cost_usd", "max_duration_seconds"}

    @pytest.mark.parametrize(
        "bad",
        [
            {"limits": {"max_tool_calls": 0}},  # 非正数
            {"limits": {"max_tool_calls": -1}},
            {"limits": {"max_speed": 5}},  # 越词表
            {"limits": {"max_tool_calls": "5"}},  # 非数值
            {"limits": {"max_tool_calls": True}},  # bool 伪装
            {"totally_unknown": 1},  # 顶层未知键
            {"usage": {"tool_calls": -1}},  # 负计数
            {"usage": {"energy": 1}},  # usage 越词表
        ],
    )
    def test_garbage_budgets_rejected(self, bad):
        with pytest.raises(ValueError):
            normalize_budget(bad)

    async def test_create_run_rejects_garbage_budget(self, budget_db):
        user = await _make_user(budget_db.session)
        service = AgentRunService(budget_db.session)
        with pytest.raises(ValueError, match="closed vocabulary"):
            await service.create_run(user_id=user.id, objective="x", budget={"limits": {"max_speed": 5}})

    async def test_create_run_rejects_unknown_capability(self, budget_db):
        user = await _make_user(budget_db.session)
        service = AgentRunService(budget_db.session)
        with pytest.raises(ValueError, match="unknown capability"):
            await service.create_run(user_id=user.id, objective="x", permissions={"granted": ["god.mode"]})

    async def test_create_run_canonicalizes_budget(self, budget_db):
        user = await _make_user(budget_db.session)
        service = AgentRunService(budget_db.session)
        result = await service.create_run(
            user_id=user.id, objective="x", budget={"limits": {"max_tool_calls": 3}}
        )
        assert result.run.budget == {
            "limits": {"max_tool_calls": 3.0},
            "usage": {"tool_calls": 0.0, "total_tokens": 0.0, "cost_usd": 0.0},
        }


# ---------------------------------------------------------------------------
# 2. 评估与记账
# ---------------------------------------------------------------------------


class TestBudgetEvaluation:
    def _run_with(self, *, limits=None, usage=None, started_minutes_ago=None):
        run = AgentRun(
            user_id=uuid4(),
            objective="eval",
            budget={"limits": limits or {}, "usage": usage or {}},
            status=RunStatus.RUNNING,
            heartbeat_at=datetime.now(UTC).replace(tzinfo=None),
        )
        if started_minutes_ago is not None:
            run.created_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=started_minutes_ago)
            run.started_at = run.created_at
        return run

    def test_under_budget_passes(self):
        evaluation = evaluate_budget(self._run_with(limits={"max_tool_calls": 5}, usage={"tool_calls": 3}))
        assert evaluation.is_exceeded is False

    def test_prospective_tool_call_counts(self):
        run = self._run_with(limits={"max_tool_calls": 5}, usage={"tool_calls": 3})
        assert evaluate_budget(run, prospective_tool_calls=2).is_exceeded is False  # 3+2=5 未越限
        assert evaluate_budget(run, prospective_tool_calls=3).is_exceeded is True  # 3+3 > 5
        assert evaluate_budget(run, prospective_tool_calls=3).exceeded == ["tool_calls"]

    def test_tokens_dimension(self):
        run = self._run_with(limits={"max_total_tokens": 100}, usage={"total_tokens": 101})
        assert evaluate_budget(run).exceeded == ["total_tokens"]

    def test_cost_dimension(self):
        run = self._run_with(limits={"max_cost_usd": 0.5}, usage={"cost_usd": 0.6})
        assert evaluate_budget(run).exceeded == ["cost_usd"]

    def test_time_dimension(self):
        run = self._run_with(limits={"max_duration_seconds": 60}, started_minutes_ago=5)
        evaluation = evaluate_budget(run)
        assert evaluation.exceeded == ["duration_seconds"]
        assert evaluation.elapsed_seconds is not None and evaluation.elapsed_seconds > 300

    def test_no_limits_is_unlimited(self):
        run = self._run_with(usage={"tool_calls": 10_000, "total_tokens": 10**9})
        assert evaluate_budget(run).is_exceeded is False

    async def test_record_run_usage_increments(self, budget_db):
        user = await _make_user(budget_db.session)
        run = await _make_run(budget_db.session, user, budget={"limits": {"max_tool_calls": 10}})
        service = AgentRunService(budget_db.session)
        await service.record_run_usage(run.id, user_id=user.id, tool_calls=1, cost_usd=0.002)
        await service.record_run_usage(run.id, user_id=user.id, tool_calls=1, tokens=500)
        refreshed = await service.get_run(run.id)
        assert refreshed.budget["usage"] == {"tool_calls": 2.0, "total_tokens": 500.0, "cost_usd": 0.002}

    async def test_record_run_usage_rejected_on_terminal(self, budget_db):
        user = await _make_user(budget_db.session)
        run = await _make_run(budget_db.session, user)
        service = AgentRunService(budget_db.session)
        await service.transition(run.id, RunStatus.SUCCEEDED, actor="worker")
        with pytest.raises(ValueError, match="terminal"):
            await service.record_run_usage(run.id, user_id=user.id, tool_calls=1)


# ---------------------------------------------------------------------------
# 3. 超限 → BUDGET_EXCEEDED 明确终态（迁移/审计/事件/读面同构）
# ---------------------------------------------------------------------------


class TestBudgetExceededTerminal:
    async def test_enforce_budget_transitions_to_terminal_with_audit_and_event(self, budget_db):
        user = await _make_user(budget_db.session)
        run = await _make_run(budget_db.session, user, budget={"limits": {"max_tool_calls": 2}})
        service = AgentRunService(budget_db.session)
        await service.record_run_usage(run.id, user_id=user.id, tool_calls=2)

        with pytest.raises(BudgetExceededError):
            await service.enforce_budget(run.id, user_id=user.id, prospective_tool_calls=1)

        refreshed = await service.get_run(run.id)
        assert refreshed.status is RunStatus.BUDGET_EXCEEDED  # 明确终态
        assert refreshed.terminal_reason == "budget_exceeded"
        assert refreshed.completed_at is not None
        assert refreshed.error_category == "budget_exceeded"

        # 审计行（append-only，from RUNNING → BUDGET_EXCEEDED）
        transitions = await service.list_transitions(run.id)
        budget_rows = [t for t in transitions if t.to_status == "BUDGET_EXCEEDED"]
        assert len(budget_rows) == 1
        assert budget_rows[0].from_status == "RUNNING"
        assert budget_rows[0].event_name == "run.status_changed"  # 36 词表内事件名
        assert budget_rows[0].reason == "budget_exceeded"

        # outbox 事件（同事务写入；payload 含 from/to/reason）
        events = (
            await budget_db.session.execute(
                text("SELECT event_type, payload FROM event_outbox WHERE aggregate_id = :rid"),
                {"rid": str(run.id)},
            )
        ).all()
        status_changed = [e for e in events if e[0] == "run.status_changed"]
        assert status_changed, f"expected run.status_changed in outbox, got {[e[0] for e in events]}"
        payload = json.loads(status_changed[-1][1])
        assert payload["to"] == "BUDGET_EXCEEDED"
        assert payload["reason"] == "budget_exceeded"
        assert payload["terminal"] is True

        # 读面（mobile agent_run_read_service.dart 消费 to_dict 的 status/is_terminal）
        run_dict = refreshed.to_dict()
        assert run_dict["status"] == "BUDGET_EXCEEDED"
        assert run_dict["is_terminal"] is True

    async def test_enforce_budget_idempotent_on_already_terminal(self, budget_db):
        user = await _make_user(budget_db.session)
        run = await _make_run(budget_db.session, user, budget={"limits": {"max_tool_calls": 1}})
        service = AgentRunService(budget_db.session)
        await service.record_run_usage(run.id, user_id=user.id, tool_calls=1)
        with pytest.raises(BudgetExceededError):
            await service.enforce_budget(run.id, user_id=user.id)
        # 第二次强制（重放）：仍抛超限，但不铸第二行审计
        with pytest.raises(BudgetExceededError):
            await service.enforce_budget(run.id, user_id=user.id)
        transitions = await service.list_transitions(run.id)
        assert len([t for t in transitions if t.to_status == "BUDGET_EXCEEDED"]) == 1

    async def test_enforce_budget_under_limit_allows(self, budget_db):
        user = await _make_user(budget_db.session)
        run = await _make_run(budget_db.session, user, budget={"limits": {"max_tool_calls": 5}})
        service = AgentRunService(budget_db.session)
        evaluation = await service.enforce_budget(run.id, user_id=user.id, prospective_tool_calls=1)
        assert evaluation.is_exceeded is False
        assert (await service.get_run(run.id)).status is RunStatus.RUNNING

    async def test_time_budget_exceeded_on_resume(self, budget_db):
        """resume 闸门：等待中的 run 时间预算已耗尽 → 落终态而非复活执行。"""
        user = await _make_user(budget_db.session)
        service = AgentRunService(budget_db.session)
        result = await service.create_run(
            user_id=user.id,
            objective="stale waiting run",
            budget={"limits": {"max_duration_seconds": 60}},
            initial_status=RunStatus.AWAITING_USER,
        )
        run = result.run
        run.started_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10)
        await budget_db.session.commit()

        with pytest.raises(BudgetExceededError):
            await service.resume(run.id, user_id=user.id)
        assert (await service.get_run(run.id)).status is RunStatus.BUDGET_EXCEEDED

    async def test_budget_terminal_blocks_further_transitions(self, budget_db):
        """终态封闭：BUDGET_EXCEEDED 后不可再迁移（含伪造 SUCCEEDED）。"""
        user = await _make_user(budget_db.session)
        run = await _make_run(budget_db.session, user, budget={"limits": {"max_tool_calls": 1}})
        service = AgentRunService(budget_db.session)
        await service.record_run_usage(run.id, user_id=user.id, tool_calls=1)
        with pytest.raises(BudgetExceededError):
            await service.enforce_budget(run.id, user_id=user.id)
        from app.core.run_state_machine import IllegalRunTransitionError

        with pytest.raises(IllegalRunTransitionError):
            await service.transition(run.id, RunStatus.SUCCEEDED, actor="worker")


# ---------------------------------------------------------------------------
# 4. executor × budget 集成（闸门拒绝 + usage 记账全链）
# ---------------------------------------------------------------------------


class _Params(BaseModel):
    title: str = "t"


class _BudgetedWriteTool:
    name = "stub_write"
    description = "stub"
    category = ToolCategory.TASK
    parameters_schema = _Params
    requires_confirmation = False
    timeout_seconds = 5.0
    effect = "write"
    risk = "medium"
    reversible = True
    required_permission = "task.write"
    cost_usd = 0.01

    def __init__(self):
        self.execute_count = 0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id)


_METADATA = SimpleNamespace(
    name="stub_write",
    effect="write",
    risk="medium",
    reversible=True,
    required_permission="task.write",
    cost_usd=0.01,
    is_side_effect=True,
    to_dict=lambda: {
        "name": "stub_write", "effect": "write", "risk": "medium",
        "reversible": True, "required_permission": "task.write", "cost_usd": 0.01,
    },
)


class TestExecutorBudgetIntegration:
    @pytest.fixture(autouse=True)
    def _wire(self, monkeypatch, budget_db):
        tool = _BudgetedWriteTool()
        self.tool = tool
        monkeypatch.setattr(
            executor_module,
            "tool_registry",
            SimpleNamespace(get_tool=lambda name: tool, get_tool_metadata=lambda name: _METADATA),
        )
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", budget_db.factory)
        self.db = budget_db
        self.executor = ToolExecutor()

    async def test_tool_calls_dimension_enforced_end_to_end(self):
        """验收 3 全链：max_tool_calls=1 → 第 1 次放行记账，第 2 次拒绝且 run 落终态。"""
        user = await _make_user(self.db.session)
        run = await _make_run(self.db.session, user, budget={"limits": {"max_tool_calls": 1}})

        first = await self.executor.execute_tool_call(
            self.tool.name, {"title": "a"}, str(user.id), self.db.session,
            tool_call_id="c1", idempotency_key="k1",
            runtime_context={"run_id": str(run.id)},
        )
        assert first.success is True
        assert self.tool.execute_count == 1
        async with self.db.factory() as check:  # run 权威走独立会话（与生产同构）
            refreshed = await AgentRunService(check).get_run(run.id)
            assert refreshed.budget["usage"]["tool_calls"] == 1.0
            assert refreshed.budget["usage"]["cost_usd"] == 0.01  # metadata cost 记账

        second = await self.executor.execute_tool_call(
            self.tool.name, {"title": "b"}, str(user.id), self.db.session,
            tool_call_id="c2", idempotency_key="k2",
            runtime_context={"run_id": str(run.id)},
        )
        assert second.success is False
        assert second.error_type == "BudgetExceeded"
        assert self.tool.execute_count == 1  # 未执行（非静默截断——显式拒绝）

        async with self.db.factory() as check:
            final = await AgentRunService(check).get_run(run.id)
            assert final.status is RunStatus.BUDGET_EXCEEDED
            assert final.to_dict()["is_terminal"] is True

    async def test_time_dimension_enforced_end_to_end(self):
        user = await _make_user(self.db.session)
        run = await _make_run(
            self.db.session,
            user,
            budget={"limits": {"max_duration_seconds": 60}},
            started_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5),
        )
        result = await self.executor.execute_tool_call(
            self.tool.name, {"title": "a"}, str(user.id), self.db.session,
            tool_call_id="c1", idempotency_key="k1",
            runtime_context={"run_id": str(run.id)},
        )
        assert result.success is False
        assert result.error_type == "BudgetExceeded"
        assert self.tool.execute_count == 0
        async with self.db.factory() as check:
            assert (await AgentRunService(check).get_run(run.id)).status is RunStatus.BUDGET_EXCEEDED

    async def test_no_run_context_means_no_budget_gate(self):
        """无 run 上下文（chat 轨道现状）→ 预算闸门不启用（零行为回归）。"""
        user = await _make_user(self.db.session)
        results = [
            await self.executor.execute_tool_call(
                self.tool.name, {"title": str(i)}, str(user.id), self.db.session,
                tool_call_id=f"c{i}", idempotency_key=f"k{i}",
            )
            for i in range(3)
        ]
        assert all(r.success for r in results)
        assert self.tool.execute_count == 3
