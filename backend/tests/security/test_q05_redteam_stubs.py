"""Q-05 红队桩工具：X-06 同款五元数据显式声明桩（只提供被测执行链的靶子，
不 mock 任何业务语义——权限/幂等/账本全部走真实 ToolExecutor 链路）。"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from app.tools.base import ToolCategory, ToolResult
from app.tools.metadata import ToolEffect, ToolMetadata, ToolRiskLevel


class _WriteParams(BaseModel):
    title: str = "t"


class _StubWriteTool:
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


class _StubReadTool:
    name = "stub_get_task"
    description = "stub read tool"
    category = ToolCategory.TASK
    parameters_schema = _WriteParams
    requires_confirmation = False
    timeout_seconds = 5.0
    effect = "read"
    risk = "low"
    reversible = True
    required_permission = "task.read"
    cost_usd = 0.0

    def __init__(self):
        self.execute_count = 0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data={"ok": True})


class IdentityProbeTool(_StubWriteTool):
    """回显执行链传入身份的写桩（验证调用方身份绑定）。"""

    name = "stub_identity_probe"

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        return ToolResult(
            success=True,
            tool_name=self.name,
            tool_call_id=tool_call_id,
            data={"executed_as": str(user_id), "attempt": self.execute_count},
        )


_WRITE_METADATA = ToolMetadata(
    name="stub_create_task",
    effect=ToolEffect.WRITE,
    risk=ToolRiskLevel.MEDIUM,
    reversible=True,
    required_permission="task.write",
    cost_usd=0.0,
)
_READ_METADATA = ToolMetadata(
    name="stub_get_task",
    effect=ToolEffect.READ,
    risk=ToolRiskLevel.LOW,
    reversible=True,
    required_permission="task.read",
    cost_usd=0.0,
)
_IDENTITY_METADATA = ToolMetadata(
    name="stub_identity_probe",
    effect=ToolEffect.WRITE,
    risk=ToolRiskLevel.MEDIUM,
    reversible=True,
    required_permission="task.write",
    cost_usd=0.0,
)


def install_registry(monkeypatch, *, write: Any = None, read: Any = None, identity: Any = None) -> None:
    """monkeypatch executor 的 registry 依赖（X-06 同款，不污染全局单例）。"""
    from app.orchestration import executor as executor_module

    tools: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
    for tool, meta in ((write, _WRITE_METADATA), (read, _READ_METADATA), (identity, _IDENTITY_METADATA)):
        if tool is not None:
            tools[tool.name] = tool
            metadata[tool.name] = meta
    monkeypatch.setattr(
        executor_module,
        "tool_registry",
        SimpleNamespace(
            get_tool=lambda name: tools.get(name),
            get_tool_metadata=lambda name: metadata.get(name),
        ),
    )
