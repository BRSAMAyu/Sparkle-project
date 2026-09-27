"""V3-FIX-335 · executable_plan 入 checkpoint —— 中断恢复幂等回归测试.

背景（v3-output/WT634-VERIFY2/verdicts.md §3/§4 + WT631-PROMISE/findings.md 面 3）：
- executable_plan 原被 KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS 整体跳过（结构性不入
  checkpoint）；同 request_id 中断恢复（load_interrupted）拿到的存档态没有计划 →
  generation_node 判缺失重跑 LLM 规划 → 新 plan_id / 新 spec.id → 执行器幂等键
  （DAG 轨 tool_call_id=spec.id）全部换新 → 中断前已执行的写工具在恢复后以新键
  再次执行（与 V3-FIX-336 叠加成 duplicate side effect 实害通道，round-2 sqlite
  运行级红测已实证）。
- 修复语义（轨道 A，最小面）：计划随 checkpoint 持久化、恢复时还原为
  ExecutablePlan；恢复合并（_merge_checkpoint_state）时 checkpoint 计划优先于
  fresh 侧重跑计划 —— 键随之稳定，既有「同键 replay 恰一次」语义自然兜底，
  X-06 守卫零放松（interrupted 同键重放仍拒、显式换键重试语义不变）。
- 兼容：旧 checkpoint（无计划字段）与损坏计划 dict 必须照常恢复（回退重规划
  语义），不得崩。

红→绿锚点：修前 roundtrip / 恢复合并 / 运行级通道三测红（计划丢失、fresh 重跑
计划胜出、写副作用重复执行）；修后全绿，X-06 / FIX-223 基线不破。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.checkpoint.redis_checkpointer import RedisCheckpointer
from app.models.agent_tool_call import AgentToolCall
from app.models.base import Base
from app.models.user import User
from app.orchestration import executor as executor_module
from app.orchestration.executor import ToolExecutor
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.orchestration.statechart_engine import StateGraph, WorkflowState
from app.tools.base import ToolCategory, ToolResult
from app.tools.metadata import ToolEffect, ToolMetadata, ToolRiskLevel

# ---------------------------------------------------------------------------
# 桩工具 / 账本库（镜像 test_x06_tool_call_safety.py 的 guard_db 形态）
# ---------------------------------------------------------------------------


class _WriteParams(BaseModel):
    title: str = "t"


class _StubWriteTool:
    """side-effect 工具桩（effect=write, required_permission=task.write）。"""

    name = "stub_create_task"
    description = "stub write tool"
    category = ToolCategory.TASK
    parameters_schema = _WriteParams
    requires_confirmation = False
    timeout_seconds = 5.0
    effect = "write"
    risk = "medium"
    reversible = True
    required_permission = "task.write"
    cost_usd = 0.0

    def __init__(self):
        self.execute_count = 0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        return ToolResult(
            success=True,
            tool_name=self.name,
            tool_call_id=tool_call_id,
            data={"title": params.title, "attempt": self.execute_count},
        )


_WRITE_METADATA = ToolMetadata(
    name="stub_create_task",
    effect=ToolEffect.WRITE,
    risk=ToolRiskLevel.MEDIUM,
    reversible=True,
    required_permission="task.write",
    cost_usd=0.0,
)


@pytest.fixture
async def guard_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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


def _install_registry(monkeypatch, write: _StubWriteTool):
    monkeypatch.setattr(
        executor_module,
        "tool_registry",
        SimpleNamespace(
            get_tool=lambda name: write if name == write.name else None,
            get_tool_metadata=lambda name: _WRITE_METADATA if name == write.name else None,
        ),
    )


class _RecordingRedis:
    def __init__(self) -> None:
        self.stored: dict[str, str] = {}

    async def set(self, key, value, ex=None):
        self.stored[key] = value
        return True

    async def get(self, key):
        return self.stored.get(key)


def _state(context_data: dict) -> WorkflowState:
    return WorkflowState(messages=[], context_data=context_data, next_step=None, errors=[], is_finished=False)


def _two_step_plan(plan_id: str, *, suffix: str = "") -> ExecutablePlan:
    """DAG 轨计划：两层顺序执行（execution_order 强制串行，测试确定性）。"""
    return ExecutablePlan(
        plan_id=plan_id,
        source="langgraph",
        execution_order=[["spec-a" + suffix], ["spec-b" + suffix]],
        tool_calls=[
            ToolCallSpec(id="spec-a" + suffix, name="stub_create_task", params={"title": "a"}),
            ToolCallSpec(id="spec-b" + suffix, name="stub_create_task", params={"title": "b"}),
        ],
    )


# ---------------------------------------------------------------------------
# 1. 计划骨架持久化（save → load roundtrip）
# ---------------------------------------------------------------------------


class TestPlanCheckpointRoundtrip:
    @pytest.mark.asyncio
    async def test_save_then_load_restores_executable_plan_identity(self):
        """计划必须随 checkpoint 持久化，load 还原出同 plan_id / 同 spec.id 的对象."""
        rdb = _RecordingRedis()
        checkpointer = RedisCheckpointer(rdb)
        plan = _two_step_plan("plan-orig")
        state = _state({"session_id": "s1", "request_id": "r1", "executable_plan": plan})

        await checkpointer.save(state, "tool_execution")
        loaded = await checkpointer.load("s1")

        assert loaded is not None
        restored = loaded.context_data.get("executable_plan")
        assert isinstance(restored, ExecutablePlan), (
            "executable_plan 必须入 checkpoint 并在 load 时还原（V3-FIX-335）"
        )
        assert restored.plan_id == "plan-orig"
        assert [tc.id for tc in restored.tool_calls] == ["spec-a", "spec-b"]
        assert [tc.params for tc in restored.tool_calls] == [{"title": "a"}, {"title": "b"}]
        assert restored.execution_order == [["spec-a"], ["spec-b"]]

    @pytest.mark.asyncio
    async def test_load_interrupted_restores_executable_plan(self):
        """334 恢复链入口 load_interrupted 同样必须还原计划（键稳定的前提）."""
        rdb = _RecordingRedis()
        checkpointer = RedisCheckpointer(rdb)
        state = _state({"session_id": "s2", "request_id": "r2", "executable_plan": _two_step_plan("plan-orig")})

        await checkpointer.save(state, "tool_execution")
        loaded = await checkpointer.load_interrupted(session_id="s2", request_id="r2", max_age_seconds=1800)

        assert loaded is not None
        restored = loaded[0].context_data.get("executable_plan")
        assert isinstance(restored, ExecutablePlan)
        assert restored.plan_id == "plan-orig"

    @pytest.mark.asyncio
    async def test_plan_clear_position_stays_falsy_after_roundtrip(self):
        """清理位（executable_plan=None）roundtrip 后仍为 None —— 恢复面继续走重规划."""
        rdb = _RecordingRedis()
        checkpointer = RedisCheckpointer(rdb)
        state = _state({"session_id": "s3", "request_id": "r3", "executable_plan": None})

        await checkpointer.save(state, "generation")
        loaded = await checkpointer.load("s3")

        assert loaded is not None
        assert loaded.context_data.get("executable_plan") is None

    def test_from_dict_rejects_missing_plan_identity(self):
        """计划骨架缺 plan_id / spec.id 即拒还原（身份不可再生，宁可回退重规划）."""
        with pytest.raises(ValueError):
            ExecutablePlan.from_dict({"tool_calls": []})
        with pytest.raises(ValueError):
            ExecutablePlan.from_dict({"plan_id": "p1", "tool_calls": [{"name": "t", "params": {}}]})

    def test_from_dict_ignores_unknown_fields(self):
        """schema 漂移容忍：未知字段忽略，不炸恢复面."""
        plan = ExecutablePlan.from_dict(
            {
                "plan_id": "p1",
                "future_field": {"whatever": True},
                "tool_calls": [{"id": "s1", "name": "t", "params": {"a": 1}, "future": 1}],
            }
        )
        assert plan.plan_id == "p1"
        assert plan.tool_calls[0].id == "s1"
        assert plan.tool_calls[0].params == {"a": 1}


# ---------------------------------------------------------------------------
# 2. 旧 checkpoint 兼容（恢复路径不崩）
# ---------------------------------------------------------------------------


class TestOldCheckpointCompat:
    @pytest.mark.asyncio
    async def test_old_checkpoint_without_plan_still_loads(self):
        """旧格式（无 executable_plan 字段）照常恢复 —— 计划缺失即回退重规划语义."""
        rdb = _RecordingRedis()
        rdb.stored["checkpoint:s-old"] = json.dumps(
            {
                "node_id": "tool_execution",
                "session_id": "s-old",
                "request_id": "r-old",
                "checkpoint_kind": "stategraph_node_pre_execute",
                "incomplete": True,
                "saved_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
                "messages": [],
                "context_data": {"session_id": "s-old", "request_id": "r-old"},
                "next_step": None,
                "errors": [],
                "is_finished": False,
                "trace_id": "",
            }
        )
        checkpointer = RedisCheckpointer(rdb)

        loaded = await checkpointer.load_interrupted(session_id="s-old", request_id="r-old", max_age_seconds=1800)

        assert loaded is not None
        assert "executable_plan" not in loaded[0].context_data

    @pytest.mark.asyncio
    async def test_corrupt_plan_payload_falls_back_to_replan_semantics(self):
        """损坏的计划 dict：丢弃该键回退重规划，不得崩、不得还原出假计划."""
        rdb = _RecordingRedis()
        checkpointer = RedisCheckpointer(rdb)
        state = _state(
            {
                "session_id": "s4",
                "request_id": "r4",
                "executable_plan": {"plan_id": "", "tool_calls": "not-a-list"},
            }
        )
        await checkpointer.save(state, "tool_execution")
        # save 侧对损坏 plan 骨架不走 to_dict 特例（非 ExecutablePlan 实例即按
        # 原值序列化），此处直接注入损坏 payload 模拟历史/异常存量。
        payload = json.loads(rdb.stored["checkpoint:s4"])
        payload["context_data"]["executable_plan"] = {"plan_id": "", "tool_calls": "not-a-list"}
        rdb.stored["checkpoint:s4"] = json.dumps(payload)

        loaded = await checkpointer.load_interrupted(session_id="s4", request_id="r4", max_age_seconds=1800)

        assert loaded is not None
        assert not isinstance(loaded[0].context_data.get("executable_plan"), ExecutablePlan)


# ---------------------------------------------------------------------------
# 3. 恢复合并：checkpoint 计划优先于 fresh 重跑计划
# ---------------------------------------------------------------------------


class TestResumeMergePlanPriority:
    def test_resume_merge_prefers_checkpoint_plan_over_fresh_replan(self):
        """恢复 = 续跑原尝试：orchestrator 重跑规划产出的新计划不得顶掉存档计划."""
        graph = StateGraph("resume-test")
        checkpoint_state = _state(
            {
                "session_id": "s5",
                "request_id": "r5",
                "executable_plan": _two_step_plan("plan-orig"),
            }
        )
        fresh_state = _state(
            {
                "session_id": "s5",
                "request_id": "r5",
                "executable_plan": _two_step_plan("plan-replan", suffix="2"),
            }
        )

        merged = graph._merge_checkpoint_state(checkpoint_state, fresh_state)

        resumed = merged.context_data.get("executable_plan")
        assert isinstance(resumed, ExecutablePlan)
        assert resumed.plan_id == "plan-orig", (
            "恢复合并必须以 checkpoint 计划为准（fresh 重跑计划换 spec.id = duplicate 通道）"
        )
        assert [tc.id for tc in resumed.tool_calls] == ["spec-a", "spec-b"]

    def test_resume_merge_none_plan_does_not_override_fresh(self):
        """清理位 None 不回填：fresh 侧有新计划时维持 fresh（正常多轮推进语义）."""
        graph = StateGraph("resume-test")
        checkpoint_state = _state({"session_id": "s6", "request_id": "r6", "executable_plan": None})
        fresh_state = _state(
            {"session_id": "s6", "request_id": "r6", "executable_plan": _two_step_plan("plan-fresh")}
        )

        merged = graph._merge_checkpoint_state(checkpoint_state, fresh_state)

        assert merged.context_data["executable_plan"].plan_id == "plan-fresh"


# ---------------------------------------------------------------------------
# 4. 运行级通道（钱测）：中断 → 恢复 → 写副作用恰一次
# ---------------------------------------------------------------------------


class TestInterruptedResumeNoDuplicateSideEffect:
    @pytest.mark.asyncio
    async def test_resume_replays_original_plan_without_duplicate_writes(self, guard_db, monkeypatch):
        """中断前已执行的写工具，恢复后必须同键 replay 而非换键重执行.

        通道还原（round-2 红测的 repo 固化）：
        - 尝试 1：计划 P1（spec-a/spec-b）入 checkpoint 后执行 spec-a（副作用落账本）→ 进程中断；
        - 尝试 2（同 request_id 恢复）：orchestrator 重跑规划产出 P2（spec-a2/spec-b2，新键）；
        - 修复前：checkpoint 无计划 → 合并后 P2 胜出 → 同意图再执行两次（红）；
        - 修复后：存档 P1 胜出 → spec-a 同键 replay、spec-b 首次执行 → 每意图恰一次（绿）。
        """
        tool = _StubWriteTool()
        _install_registry(monkeypatch, write=tool)
        session = guard_db.session
        user = await _make_user(session)

        rdb = _RecordingRedis()
        checkpointer = RedisCheckpointer(rdb)

        # 尝试 1：checkpoint 存档于 tool_execution 节点前执行（save-before-execute 语义）
        original = _two_step_plan("plan-orig")
        checkpoint_state = _state(
            {"session_id": "s-run", "request_id": "r-run", "executable_plan": original}
        )
        await checkpointer.save(checkpoint_state, "tool_execution")

        executor = ToolExecutor()
        first = await executor.execute_tool_call(
            "stub_create_task",
            {"title": "a"},
            str(user.id),
            session,
            tool_call_id="spec-a",
        )
        assert first.success and first.data["attempt"] == 1

        # —— 进程中断 ——

        # 尝试 2：fresh 侧重跑规划（新 plan_id / 新 spec.id，同工具同参数 = 同意图）
        replanned = _two_step_plan("plan-replan", suffix="2")
        fresh_state = _state(
            {"session_id": "s-run", "request_id": "r-run", "executable_plan": replanned}
        )
        loaded = await checkpointer.load_interrupted(session_id="s-run", request_id="r-run", max_age_seconds=1800)
        assert loaded is not None
        graph = StateGraph("resume-test")
        merged = graph._merge_checkpoint_state(loaded[0], fresh_state)

        resumed_plan = merged.context_data.get("executable_plan")
        assert isinstance(resumed_plan, ExecutablePlan)
        assert resumed_plan.plan_id == "plan-orig", "恢复必须续跑原计划（键稳定前提）"

        result = await executor.execute_plan(plan=resumed_plan, user_id=str(user.id), db_session=session)
        assert result.aborted is False
        # spec-a 同键 replay（不重执行）+ spec-b 首次执行 → 每个写意图恰一次
        assert tool.execute_count == 2, (
            f"duplicate side effect on resume: write executed {tool.execute_count} times (expected 2)"
        )

        rows = (await session.execute(select(AgentToolCall))).scalars().all()
        assert sorted(str(r.idempotency_key) for r in rows) == ["spec-a", "spec-b"]
        assert all(r.status == "succeeded" for r in rows)
