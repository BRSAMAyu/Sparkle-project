"""
Tool Registry - 统一工具注册表

这是一个向后兼容的包装器，将静态注册表接口委托给动态注册表。
所有工具现在由 DynamicToolRegistry 自动发现和注册。

推荐使用: from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
"""
from __future__ import annotations

from .base import BaseTool, ToolCategory


class ToolRegistry:
    """
    工具注册表（向后兼容包装器）

    此类提供向后兼容的接口，内部委托给 DynamicToolRegistry。
    所有工具由 DynamicToolRegistry 自动从 app.tools 包发现。
    """
    _instance: ToolRegistry | None = None
    _dynamic_registry = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_dynamic_registry(self):
        """延迟导入动态注册表以避免循环导入"""
        if self._dynamic_registry is None:
            from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
            self._dynamic_registry = dynamic_tool_registry
            # 确保动态工具已注册
            self._dynamic_registry.ensure_package_registered("app.tools")
        return self._dynamic_registry

    def get_tool(self, name: str) -> BaseTool | None:
        """根据名称获取工具"""
        return self._get_dynamic_registry().get_tool(name)

    def get_all_tools(self) -> list[BaseTool]:
        """获取所有工具"""
        return self._get_dynamic_registry().get_all_tools()

    def get_tools_by_category(self, category: ToolCategory) -> list[BaseTool]:
        """按分类获取工具"""
        return self._get_dynamic_registry().get_tools_by_category(category)

    def get_openai_tools_schema(self) -> list[dict]:
        """
        获取所有工具的 OpenAI Function Calling 格式
        用于发送给 LLM
        """
        return self._get_dynamic_registry().get_openai_tools_schema()

    def get_tools_description(self) -> str:
        """
        生成工具描述文本，用于 System Prompt
        """
        return self._get_dynamic_registry().get_tools_description()

    def list_tools(self, verbose: bool = False) -> list[dict]:
        """列出所有工具信息"""
        return self._get_dynamic_registry().list_tools(verbose=verbose)

    def get_stats(self) -> dict:
        """获取注册表统计信息"""
        return self._get_dynamic_registry().get_stats()


# 全局单例（向后兼容）
tool_registry = ToolRegistry()
