"""演示缺陷 ❌#4 · 确认门中断的文案路由契约测试.

背景（docs/competition/大创市赛/演示路径盘点_2026-09-20.md §❌#4）：
确认门工具（requires_confirmation 且用户未批准）被当成失败 abort 后，
开发者文案「⚠️ 计划执行中断: Required step failed in layer 0」直接进入
聊天流。本套测试钉住：

1. 确认门中断置 ``awaiting_user_confirmation``，用户可见文案是自然话术，
   不含任何开发者词汇（layer/failed/Required step/ConfirmationRequired 等）；
2. 开发者诊断（abort_reason 含 layer 细节）保留在 abort_reason / 日志侧，
   不出现在用户文案里；
3. 非确认门的普通失败仍走既有「⚠️ 计划执行中断」格式（行为不回退）；
4. 确认门 ToolResult 的 error_message/suggestion 也是面向用户的话术
   （会进 tool_result 帧被用户看到）。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.orchestration import executor as executor_module
from app.orchestration.executor import CONFIRMATION_REQUIRED_ERROR_TYPE, ToolExecutor
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.tools.base import ToolCategory, ToolResult

# ---------------------------------------------------------------------------
# 开发者词汇黑名单（用户可见文案中禁止出现；大小写不敏感）
# ---------------------------------------------------------------------------
_DEV_VOCABULARY = (
    "layer",
    "failed",
    "failure",
    "required step",
    "error",
    "exception",
    "stack",
    "traceback",
    "confirmationrequired",
    "abort",
    "步骤失败",
    "执行中断",
    "执行失败",
)


class _Params(BaseModel):
    title: str = "t"


class _StubGatedWriteTool:
    """requires_confirmation 写工具桩：用户未批准时执行器必须拦截。"""

    name = "stub_delete_task"
    description = "stub gated write tool"
    category = ToolCategory.TASK
    parameters_schema = _Params
    requires_confirmation = True
    timeout_seconds = 5.0
    effect = "write"
    risk = "high"
    reversible = False
    required_permission = "task.write"
    cost_usd = 0.0

    def __init__(self):
        self.execute_count = 0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data={"ok": True})


class _StubPlainFailingTool:
    """普通失败工具桩（非确认门）：钉住既有中断文案不回退。"""

    name = "stub_failing_tool"
    description = "stub plain failing tool"
    category = ToolCategory.TASK
    parameters_schema = _Params
    requires_confirmation = False
    timeout_seconds = 5.0
    effect = "read"
    risk = "low"
    reversible = True
    required_permission = "task.read"
    cost_usd = 0.0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        return ToolResult(
            success=False,
            tool_name=self.name,
            tool_call_id=tool_call_id,
            error_type="ValidationError",
            error_message="bad input",
        )


def _install_registry(monkeypatch, tool) -> None:
    monkeypatch.setattr(
        executor_module,
        "tool_registry",
        SimpleNamespace(
            get_tool=lambda name: tool if name == tool.name else None,
            get_tool_metadata=lambda name: None,
        ),
    )


def _plan(tool_name: str) -> ExecutablePlan:
    return ExecutablePlan(
        plan_id="p-confirm",
        context_version="v0",
        source="test",
        rationale="",
        execution_order=[["s1"], ["s2"]],
        tool_calls=[
            ToolCallSpec(id="s1", name=tool_name, params={"title": "a"}),
            ToolCallSpec(id="s2", name="whatever_other", params={"title": "b"}, depends_on=["s1"]),
        ],
    )


def _assert_no_dev_vocabulary(text: str) -> None:
    lowered = text.lower()
    for word in _DEV_VOCABULARY:
        assert word.lower() not in lowered, f"用户可见文案含开发者词汇 {word!r}: {text!r}"


@pytest.mark.asyncio
async def test_confirmation_gate_aborts_with_user_facing_notice(monkeypatch):
    """确认门中断：awaiting_user_confirmation 置位 + 用户文案零开发者词汇."""
    tool = _StubGatedWriteTool()
    _install_registry(monkeypatch, tool)

    # 单层即可触发确认门（第二层不应启动）
    plan = ExecutablePlan(
        plan_id="p-confirm",
        context_version="v0",
        source="test",
        rationale="",
        execution_order=[["s1"]],
        tool_calls=[ToolCallSpec(id="s1", name=tool.name, params={"title": "a"})],
    )
    result = await ToolExecutor().execute_plan(
        plan,
        "user-1",
        None,
        runtime_context={},  # 无 user_approved → 确认门拦截
    )

    assert result.aborted is True
    assert result.awaiting_user_confirmation is True
    assert tool.execute_count == 0  # 工具本体从未执行
    # 开发者诊断保留在 abort_reason（含 layer 细节，供日志/内部排查）
    assert "layer 0" in (result.abort_reason or "")

    from app.agents.standard_workflow import render_plan_abort_notice

    notice = render_plan_abort_notice(result)
    _assert_no_dev_vocabulary(notice)
    assert "确认" in notice


@pytest.mark.asyncio
async def test_confirmation_gate_skips_remaining_layers(monkeypatch):
    """确认门中断后，后续层不再发起（与失败 abort 同样的层切断语义）."""
    tool = _StubGatedWriteTool()
    _install_registry(monkeypatch, tool)
    result = await ToolExecutor().execute_plan(
        _plan(tool.name),
        "user-1",
        None,
        runtime_context={},
    )
    assert result.aborted is True
    assert result.awaiting_user_confirmation is True
    assert len(result.step_results) == 1  # 第二层被跳过


@pytest.mark.asyncio
async def test_plain_failure_keeps_existing_notice(monkeypatch):
    """非确认门的普通失败：保持既有「⚠️ 计划执行中断」格式（不回退）."""
    tool = _StubPlainFailingTool()
    _install_registry(monkeypatch, tool)
    result = await ToolExecutor().execute_plan(
        _plan(tool.name),
        "user-1",
        None,
        runtime_context={},
    )
    assert result.aborted is True
    assert result.awaiting_user_confirmation is False

    from app.agents.standard_workflow import render_plan_abort_notice

    notice = render_plan_abort_notice(result)
    assert notice.startswith("\n\n⚠️ 计划执行中断:")
    assert "layer 0" in notice  # 开发者通道保留诊断信息


@pytest.mark.asyncio
async def test_confirmation_gate_tool_result_copy_is_user_facing(monkeypatch):
    """确认门 ToolResult 的 error_message/suggestion 是用户话术（进 tool_result 帧）."""
    tool = _StubGatedWriteTool()
    _install_registry(monkeypatch, tool)
    result = await ToolExecutor().execute_plan(
        _plan(tool.name),
        "user-1",
        None,
        runtime_context={},
    )
    gate_result = result.step_results[0].tool_result
    assert gate_result.success is False
    assert gate_result.error_type == CONFIRMATION_REQUIRED_ERROR_TYPE
    _assert_no_dev_vocabulary(gate_result.error_message or "")
    _assert_no_dev_vocabulary(gate_result.suggestion or "")
    assert "确认" in (gate_result.error_message or "")
