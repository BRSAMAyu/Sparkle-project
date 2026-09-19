"""V3-FIX-13 / D-15-7: executor 向工具 execute() 传参须按签名探测。

ToolExecutor 曾无条件向 tool.execute() 传 locale=（及 long-running 分支的
progress_callback=）；任何签名未声明 locale 的工具（现存 25 个注册工具中 23 个，
如 create_task / query_all_tasks / web_search_pro / get_persona_snapshot）都会
TypeError → 被兜底 except 吞成"工具执行失败"。修复：按 inspect 签名（含
**kwargs）探测后再传。
"""

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from app.orchestration import executor as executor_module
from app.orchestration.executor import ToolExecutor
from app.tools.base import ToolResult


class _FakeParams(BaseModel):
    value: str = "ok"


class _StrictTool:
    """忠实复刻现存生产工具签名：无 locale、无 **kwargs。"""

    name = "fake_tool"
    description = "fake"
    category = None
    parameters_schema = _FakeParams
    requires_confirmation = False
    is_long_running = False
    timeout_seconds = None

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    async def execute(self, params, user_id, db_session, tool_call_id=None) -> ToolResult:
        self.calls.append({"tool_call_id": tool_call_id})
        return ToolResult(success=True, tool_name=self.name, data={"value": params.value})


class _LocaleTool:
    """声明了 locale 形参的工具（BaseTool 抽象签名）。"""

    name = "fake_localized_tool"
    description = "fake"
    category = None
    parameters_schema = _FakeParams
    requires_confirmation = False
    is_long_running = False
    timeout_seconds = None

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en") -> ToolResult:
        self.calls.append({"tool_call_id": tool_call_id, "locale": locale})
        return ToolResult(success=True, tool_name=self.name, data={"value": params.value})


class _LongRunningStrictTool:
    """long-running 工具：只接受 progress_callback，不认识 locale。"""

    name = "fake_long_tool"
    description = "fake"
    category = None
    parameters_schema = _FakeParams
    requires_confirmation = False
    is_long_running = True
    timeout_seconds = None

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    async def execute(self, params, user_id, db_session, tool_call_id=None, progress_callback=None) -> ToolResult:
        self.calls.append({"tool_call_id": tool_call_id, "got_callback": progress_callback is not None})
        return ToolResult(success=True, tool_name=self.name, data={"value": params.value})


def _install(monkeypatch, tool) -> ToolExecutor:
    """屏蔽 executor 的基础设施依赖，只留被测调用链。"""

    async def _noop_async(*args, **kwargs):
        return None

    monkeypatch.setattr(executor_module, "refresh_llm_safety_mode", _noop_async)
    monkeypatch.setattr(
        executor_module,
        "tool_registry",
        SimpleNamespace(get_tool=lambda name: tool),
    )
    exec_instance = ToolExecutor()
    monkeypatch.setattr(exec_instance, "_record_tool_execution", _noop_async)
    monkeypatch.setattr(exec_instance, "_publish_tool_event", _noop_async)
    monkeypatch.setattr(exec_instance, "_commit_if_owned", _noop_async)
    monkeypatch.setattr(exec_instance, "_safe_rollback", _noop_async)
    monkeypatch.setattr(exec_instance, "_maybe_execute_compensation", _noop_async)
    return exec_instance


async def _run(exec_instance: ToolExecutor, tool_call_id: str) -> ToolResult:
    return await exec_instance._execute_tool_call_with_session(
        tool_name="fake_tool",
        arguments={},
        user_id="00000000-0000-0000-0000-000000000001",
        db_session=object(),
        progress_callback=None,
        tool_call_id=tool_call_id,
        owns_session=False,
        compensation_call=None,
        runtime_context={"locale": "zh"},
    )


@pytest.mark.asyncio
async def test_executor_tolerates_tool_without_locale_kwarg(monkeypatch):
    """无 locale 形参的工具：不再被硬塞 locale 打成 TypeError。"""
    tool = _StrictTool()
    exec_instance = _install(monkeypatch, tool)

    result = await _run(exec_instance, "call-1")

    assert result.success is True, f"工具被 locale 硬传打挂: {result.error_message!r}"
    assert tool.calls and tool.calls[0]["tool_call_id"] == "call-1"


@pytest.mark.asyncio
async def test_executor_still_passes_locale_to_tools_that_accept_it(monkeypatch):
    """声明了 locale 形参的工具：照常收到 locale（本地化能力不回退）。"""
    tool = _LocaleTool()
    exec_instance = _install(monkeypatch, tool)

    result = await _run(exec_instance, "call-2")

    assert result.success is True, f"带 locale 的工具反而挂了: {result.error_message!r}"
    assert tool.calls and tool.calls[0]["locale"] == "zh"


@pytest.mark.asyncio
async def test_executor_long_running_branch_signature_probe(monkeypatch):
    """long-running 分支：progress_callback/locale 同样按签名探测。"""
    tool = _LongRunningStrictTool()
    exec_instance = _install(monkeypatch, tool)

    async def _cb(progress: int) -> None:
        return None

    result = await exec_instance._execute_tool_call_with_session(
        tool_name="fake_long_tool",
        arguments={},
        user_id="00000000-0000-0000-0000-000000000001",
        db_session=object(),
        progress_callback=_cb,
        tool_call_id="call-3",
        owns_session=False,
        compensation_call=None,
        runtime_context={"locale": "zh"},
    )

    assert result.success is True, f"long-running 工具被多余 kwargs 打挂: {result.error_message!r}"
    assert tool.calls and tool.calls[0]["got_callback"] is True
