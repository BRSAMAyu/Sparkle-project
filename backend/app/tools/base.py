from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

TOOL_RUNTIME_CONTEXT_KEY = "tool_runtime_context"


class ToolCategory(StrEnum):
    """工具分类"""

    TASK = "task"
    PLAN = "plan"
    KNOWLEDGE = "knowledge"
    QUERY = "query"
    FOCUS = "focus"
    GROWTH = "growth"


class ToolResult(BaseModel):
    """工具执行结果的统一格式"""

    success: bool
    tool_name: str
    tool_call_id: str | None = None  # 工具调用ID，用于追踪
    data: dict[str, Any] | None = None  # 成功时返回的数据
    error_message: str | None = None  # 失败时的错误信息
    error_type: str | None = None  # 错误类型分类
    widget_type: str | None = None  # 前端渲染组件类型
    widget_data: dict[str, Any] | None = None  # 组件渲染数据
    suggestion: str | None = None  # LLM 可用于自我修正的建议


class ToolContext(BaseModel):
    """工具执行上下文"""

    user_id: str
    db_session: Any


def get_tool_runtime_context(db_session: Any) -> dict[str, Any]:
    """Return request-scoped runtime context injected for tool execution."""
    sync_session = getattr(db_session, "sync_session", None)
    info = getattr(sync_session, "info", None)
    if not isinstance(info, dict):
        info = getattr(db_session, "info", None)
    if not isinstance(info, dict):
        return {}
    payload = info.get(TOOL_RUNTIME_CONTEXT_KEY)
    return dict(payload) if isinstance(payload, dict) else {}


class BaseTool(ABC):
    """
    工具基类
    所有元能力工具必须继承此类
    """

    name: str  # 工具名称（唯一标识）
    description: str  # 工具描述（LLM 理解用途）
    category: ToolCategory  # 工具分类
    parameters_schema: type[BaseModel]  # 参数 Schema（Pydantic Model）
    requires_confirmation: bool = False  # 是否需要用户确认（高风险操作）
    timeout_seconds: float | None = None  # Override per-tool timeout (default 120s)

    @abstractmethod
    async def execute(
        self, params: BaseModel, user_id: str, db_session: Any, tool_call_id: str | None = None
    ) -> ToolResult:
        """
        执行工具逻辑

        Args:
            params: 经过验证的参数对象
            user_id: 当前用户 ID
            db_session: 数据库会话
            tool_call_id: 当前工具调用的唯一 ID

        Returns:
            ToolResult: 统一格式的执行结果
        """
        pass

    def to_openai_schema(self) -> dict[str, Any]:
        """
        转换为 OpenAI Function Calling 格式
        兼容 Qwen/DeepSeek 的 OpenAI 兼容 API
        """
        parameters_schema = self.parameters_schema
        if hasattr(parameters_schema, "model_json_schema"):
            parameters = parameters_schema.model_json_schema()
        elif isinstance(parameters_schema, dict):
            parameters = parameters_schema
        else:
            parameters = {"type": "object", "properties": {}}

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }
