"""wt596 — requires_hitl/requires_confirmation 确定性闸门主链接线回归。

诚实性猎缺 F3（wt587 发现、wt591 二轮复核 303 存活）：
GroundingValidator.validate_plan 对 confirm 级工具（batch_create_tasks /
generate_tasks_for_plan，均 requires_confirmation=True 且在注册表）确定性返回
requires_hitl=True + risk_flags=confirm:*，但主链 _plan_and_validate 此前只消费
is_valid/failure_reason/warnings——闸门输出被整段丢弃，计划原样进入 DAG 自动执行，
违背 DoD Gate V3-3（高风险不可逆行为 autonomous execution = 0）。

红→绿断言（与 standard_workflow 既有 enforcing 语义一致：
queue HITL action + 流 requires_hitl 帧 + 停止，不发明新协议）：
- F3-0: 真实 validate_plan + 真实 38 工具注册表的前提下确在亮——batch_create_tasks
  计划 requires_hitl=True；受控规划链 create_plan -> generate_tasks_for_plan 命中
  既有 bypass（requires_hitl=False）。
- F3-1: confirm 级计划无用户确认时不得静默放行——必须 queue HITL action、
  流 requires_hitl 帧、should_return=True、executable_plan 不落入 state、
  且确定性闸门先于 LLM plan review 生效（封住降级链叠加 F1 的路径）。
- F3-2: 闸门不误伤正常计划——无风险判定时计划照常进入执行。
"""

from __future__ import annotations

import importlib
import importlib.util
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestration.schemas import ExecutablePlan, RouteDecision, ToolCallSpec, ValidationResult
from app.orchestration.statechart_engine import WorkflowState
from tests.orchestration.test_orchestrator_process_stream_integration import (
    _install_import_stubs,
    orchestrator_factory,  # noqa: F401 — pytest fixture re-export
)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _load_real_grounding_validator_class() -> type:
    """加载真实 GroundingValidator（私有模块名，不污染 sys.modules 的 stub 状态）。

    orchestrator_factory 的 import stubs 会把 sys.modules 里的
    app.orchestration.grounding_validator 换成 SimpleNamespace 桩；按文件路径以私有
    名重载真实实现，绕开该桩，也不影响同进程其他测试的桩假设。
    """
    real_path = _BACKEND_ROOT / "app" / "orchestration" / "grounding_validator.py"
    spec = importlib.util.spec_from_file_location("_wt596_real_grounding_validator", real_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GroundingValidator


def _kwargs(stream_callback, session_id: str):
    return {
        "user_message": "帮我批量创建 5 个学习任务",
        "user_id": str(uuid.uuid4()),
        "session_id": session_id,
        "active_db": None,
        "plan_id": None,
        "conversation_context": None,
        "plan_context": None,
        "stream_callback": stream_callback,
        "user_context_payload": {},
        "orchestration_trace": None,
    }


def _approved_review(plan_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        decision="approved",
        confidence=0.9,
        alignment_score=0.9,
        alignment_summary="stub review",
        reasoning_summary="",
        reasoning_details=[],
        reasoning_source="stub",
        user_facing_reason="",
        review_id="review-wt596",
        plan_id=plan_id,
        quality_report={},
        review_feedback_entry={},
        to_dict=lambda: {"decision": "approved", "confidence": 0.9},
    )


def _install_engine_happy_path_stubs(orchestrator, monkeypatch, *, plan, review_mock):
    """与 test_rb13 同构的 _plan_and_validate happy-path 外围 stub；validate_plan/review 由调用方注入。"""
    orchestrator.langgraph_breaker.allow_request = AsyncMock(return_value=(True, "closed"))
    orchestrator.langgraph_breaker.on_failure = AsyncMock(return_value=None)
    orchestrator.langgraph_breaker.on_success = AsyncMock(return_value=None)
    orchestrator._load_recent_execution_feedback = AsyncMock(return_value=None)
    orchestrator._load_context_versions = AsyncMock(return_value={})
    orchestrator._emit_roundtable_preview = AsyncMock(return_value=None)
    orchestrator._track_task = MagicMock()
    orchestrator.lang_graph_planner.plan = AsyncMock(return_value=plan)
    orchestrator.lang_graph_planner.pop_rendered_plan_artifact = MagicMock(return_value=None)
    orchestrator.lang_graph_planner.get_plan_summary = MagicMock(return_value="summary")
    orchestrator.snapshot_manager.create_snapshot = AsyncMock(
        return_value=SimpleNamespace(snapshot_id="snap-wt596")
    )
    orchestrator.version_conflict_service.check_all_conflicts = AsyncMock(
        return_value=SimpleNamespace(has_conflict=False)
    )
    orchestrator.grounding_validator.preflight_check = AsyncMock(
        return_value={"is_ready": True, "blocked_by": []}
    )

    execution_engine_module = importlib.import_module("app.orchestration.execution_engine")
    monkeypatch.setattr(
        execution_engine_module,
        "plan_review_service",
        SimpleNamespace(review_plan=review_mock, store_review_result=AsyncMock(return_value="review-action-1")),
    )

    observability_module = importlib.import_module("app.orchestration.observability_mixin")
    actions_store = SimpleNamespace(save=AsyncMock(return_value="action-wt596-hitl"))
    monkeypatch.setattr(observability_module, "pending_actions_store", actions_store)
    return actions_store


@pytest.mark.asyncio
async def test_f3_0_real_validator_flags_confirm_tools():
    """F3-0 前提：真实 validate_plan + 真实注册表对 confirm 级工具确定性亮灯，bypass 链不亮。"""
    from app.orchestration.dynamic_tool_registry import dynamic_tool_registry

    dynamic_tool_registry.ensure_package_registered("app.tools")
    assert "batch_create_tasks" in {t.name for t in dynamic_tool_registry.get_all_tools()}

    validator_cls = _load_real_grounding_validator_class()
    validator = validator_cls(redis_client=None)

    confirm_plan = ExecutablePlan(
        schema_version="5.0",
        source="langgraph",
        confidence=0.9,
        rationale="wt596 repro",
        tool_calls=[
            ToolCallSpec(id="t1", name="batch_create_tasks", params={"tasks": [{"title": "任务一"}]}),
        ],
    )
    verdict = await validator.validate_plan(plan=confirm_plan)
    assert verdict.is_valid is True
    assert verdict.requires_hitl is True, "batch_create_tasks 计划必须被判 requires_hitl"
    assert "confirm:batch_create_tasks" in verdict.risk_flags

    planning_chain = ExecutablePlan(
        schema_version="5.0",
        source="langgraph",
        confidence=0.9,
        rationale="wt596 planning chain",
        tool_calls=[
            ToolCallSpec(id="t0", name="create_plan", params={"goal": "两周掌握排队论"}),
            ToolCallSpec(
                id="t1",
                name="generate_tasks_for_plan",
                params={"plan_id": "plan-1"},
                depends_on=["t0"],
            ),
        ],
    )
    chain_verdict = await validator.validate_plan(plan=planning_chain)
    assert chain_verdict.is_valid is True
    assert chain_verdict.requires_hitl is False, "受控规划链必须命中既有 bypass"
    assert chain_verdict.requires_confirmation is False


@pytest.mark.asyncio
async def test_f3_1_confirm_level_plan_must_not_silently_execute(orchestrator_factory, monkeypatch):  # noqa: F811
    """F3-1 主链红→绿：validate_plan 判定 requires_hitl 的计划不得原样放行。"""
    _install_import_stubs()
    orchestrator, _, _ = orchestrator_factory()

    plan = ExecutablePlan(
        schema_version="5.0",
        source="langgraph",
        confidence=0.9,
        rationale="wt596 repro",
        collaboration_mode="single",
        agents_involved=[],
        tool_calls=[
            ToolCallSpec(id="t1", name="batch_create_tasks", params={"tasks": [{"title": "任务一"}]}),
        ],
    )

    review_mock = AsyncMock(return_value=_approved_review(plan.plan_id))
    actions_store = _install_engine_happy_path_stubs(orchestrator, monkeypatch, plan=plan, review_mock=review_mock)
    # 真实闸门判定形态（F3-0 已证）：is_valid=True 且 requires_hitl=True。
    orchestrator.grounding_validator.validate_plan = AsyncMock(
        return_value=ValidationResult(
            is_valid=True,
            risk_flags=["confirm:batch_create_tasks"],
            requires_confirmation=True,
            requires_hitl=True,
        )
    )

    frames: list = []

    async def stream_callback(response) -> None:
        frames.append(response)

    state = WorkflowState()
    _decision, executable_plan, _snapshot, should_return = await orchestrator._plan_and_validate(
        route_decision=RouteDecision(execution_mode="langgraph", reason="complex", risk_level="low"),
        state=state,
        **_kwargs(stream_callback, "sess-wt596-f3-1"),
    )

    assert should_return is True, "confirm 级计划无用户确认时不得放行进入自动执行"
    assert "executable_plan" not in state.context_data, "被拦截的计划不得落入 state 进入 DAG 执行"
    actions_store.save.assert_awaited_once()
    save_kwargs = actions_store.save.await_args.kwargs
    assert save_kwargs.get("tool_name") == "__plan__", "HITL action 须按 standard_workflow __plan__ 语义入队"
    assert save_kwargs.get("arguments", {}).get("reason") == "risk_flags"

    hitl_frames = [f for f in frames if f.HasField("delta") and f.metadata.get("requires_hitl") == "true"]
    assert hitl_frames, "必须向用户流 requires_hitl 确认帧（与 standard_workflow 既有语义一致）"
    assert hitl_frames[0].metadata.get("action_id") == "action-wt596-hitl"
    assert hitl_frames[0].metadata.get("reason") == "risk_flags"

    review_mock.assert_not_awaited(), (
        "确定性闸门必须先于 LLM plan review 生效（封住降级链/合成回退自动批准的叠加路径）"
    )


@pytest.mark.asyncio
async def test_f3_2_clean_plan_still_auto_executes(orchestrator_factory, monkeypatch):  # noqa: F811
    """F3-2 邻域保护：无风险判定（含 bypass 链的判定结果）不得被闸门误拦。"""
    _install_import_stubs()
    orchestrator, _, _ = orchestrator_factory()

    plan = ExecutablePlan(
        schema_version="5.0",
        source="langgraph",
        confidence=0.9,
        rationale="wt596 planning chain",
        collaboration_mode="single",
        agents_involved=[],
        tool_calls=[
            ToolCallSpec(id="t0", name="create_plan", params={"goal": "两周掌握排队论"}),
            ToolCallSpec(
                id="t1",
                name="generate_tasks_for_plan",
                params={"plan_id": "plan-1"},
                depends_on=["t0"],
            ),
        ],
    )

    review_mock = AsyncMock(return_value=_approved_review(plan.plan_id))
    actions_store = _install_engine_happy_path_stubs(orchestrator, monkeypatch, plan=plan, review_mock=review_mock)
    # 受控规划链经真实 bypass 后的判定形态（F3-0 已证）：requires_hitl=False。
    orchestrator.grounding_validator.validate_plan = AsyncMock(
        return_value=ValidationResult(is_valid=True, requires_confirmation=False, requires_hitl=False)
    )

    frames: list = []

    async def stream_callback(response) -> None:
        frames.append(response)

    state = WorkflowState()
    _decision, executable_plan, _snapshot, should_return = await orchestrator._plan_and_validate(
        route_decision=RouteDecision(execution_mode="langgraph", reason="complex", risk_level="low"),
        state=state,
        **_kwargs(stream_callback, "sess-wt596-f3-2"),
    )

    assert should_return is False, "无风险判定的计划必须照常自动执行"
    assert executable_plan is not None
    assert state.context_data.get("executable_plan") is executable_plan, "计划照常进入执行"
    actions_store.save.assert_not_awaited(), "无风险判定不得误触 HITL 入队"
    assert not [f for f in frames if f.HasField("delta") and f.metadata.get("requires_hitl") == "true"]
    review_mock.assert_awaited_once()
