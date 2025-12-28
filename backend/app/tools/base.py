from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from enum import Enum

class ToolCategory(str, Enum):
    """工具分类"""
    TASK = "task"
    PLAN = "plan"
    KNOWLEDGE = "knowledge"
    QUERY = "query"
    FOCUS = "focus"
    
class ToolResult(BaseModel):
    """工具执行结果的统一格式"""
    success: bool
    tool_name: str
    data: Optional[Dict[str, Any]] = None      # 成功时返回的数据
    error_message: Optional[str] = None         # 失败时的错误信息
    widget_type: Optional[str] = None           # 前端渲染组件类型
    widget_data: Optional[Dict[str, Any]] = None  # 组件渲染数据
    suggestion: Optional[str] = None            # LLM 可用于自我修正的建议
    
class BaseTool(ABC):
    """
    工具基类
    所有元能力工具必须继承此类
    """
    name: str                           # 工具名称（唯一标识）
    description: str                    # 工具描述（LLM 理解用途）
    category: ToolCategory              # 工具分类
    parameters_schema: Type[BaseModel]  # 参数 Schema（Pydantic Model）
    requires_confirmation: bool = False # 是否需要用户确认（高风险操作）
    
    @abstractmethod
    async def execute(
        self, 
        params: BaseModel, 
        user_id: str,
        db_session: Any
    ) -> ToolResult:
        """
        执行工具逻辑
        
        Args:
            params: 经过验证的参数对象
            user_id: 当前用户 ID
            db_session: 数据库会话
            
        Returns:
            ToolResult: 统一格式的执行结果
        """
        pass
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """
        转换为 OpenAI Function Calling 格式
        兼容 Qwen/DeepSeek 的 OpenAI 兼容 API
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema.model_json_schema()
            }
        }
