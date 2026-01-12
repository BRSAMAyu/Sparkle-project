from typing import Dict, List, Optional
from .base import BaseTool, ToolCategory

# 导入所有工具
from .task_tools import (
    CreateTaskTool,
    UpdateTaskStatusTool,
    BatchCreateTasksTool,
    SuggestQuickTaskTool,
    BreakdownTaskTool,
)
from .knowledge_tools import CreateKnowledgeNodeTool, QueryKnowledgeTool, LinkNodesTool
from .ops_tools import CheckSystemStatusTool, QueryErrorLogsTool
from .plan_tools import CreatePlanTool
from .focus_tools import SuggestFocusSessionTool

class ToolRegistry:
    """
    工具注册表
    管理所有可用工具，提供查询和调用接口
    """
    _instance: Optional["ToolRegistry"] = None
    _tools: Dict[str, BaseTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._register_all_tools()
        return cls._instance
    
    def _register_all_tools(self):
        """注册所有工具"""
        tools = [
            # 任务工具
            CreateTaskTool(),
            UpdateTaskStatusTool(),
            BatchCreateTasksTool(),
            SuggestQuickTaskTool(),
            BreakdownTaskTool(),
            # 知识图谱工具
            CreateKnowledgeNodeTool(),
            QueryKnowledgeTool(),
            LinkNodesTool(),
            # 计划工具
            CreatePlanTool(),
            # 专注工具
            SuggestFocusSessionTool(),
            # 运维工具 (AIOps)
            CheckSystemStatusTool(),
            QueryErrorLogsTool(),
            # TODO: 添加更多工具
            # CreatePlanTool(),
            # GenerateTasksForPlanTool(),
            # GetUserContextTool(),
        ]
        for tool in tools:
            self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """根据名称获取工具"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """按分类获取工具"""
        return [t for t in self._tools.values() if t.category == category]
    
    def get_openai_tools_schema(self) -> List[dict]:
        """
        获取所有工具的 OpenAI Function Calling 格式
        用于发送给 LLM
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    def get_tools_description(self) -> str:
        """
        生成工具描述文本，用于 System Prompt
        """
        lines = ["你可以使用以下工具来帮助用户：\n"]
        for tool in self._tools.values():
            lines.append(f"- **{tool.name}**: {tool.description}")
        return "\n".join(lines)

# 全局单例
tool_registry = ToolRegistry()
