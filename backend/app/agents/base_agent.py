"""
Base Agent - 智能体基类

定义所有专业智能体的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class AgentRole(Enum):
    """智能体角色"""
    ORCHESTRATOR = "orchestrator"  # 协调者
    MATH = "math"  # 数学专家
    CODE = "code"  # 编程专家
    WRITING = "writing"  # 写作专家
    SCIENCE = "science"  # 科学专家


@dataclass
class AgentContext:
    """智能体上下文"""
    user_id: str
    session_id: str
    conversation_history: List[Dict[str, Any]]
    user_query: str

    # 可选上下文
    knowledge_context: Optional[str] = None
    user_preferences: Optional[Dict[str, Any]] = None
    previous_agent_outputs: Optional[List[Dict[str, Any]]] = None


@dataclass
class AgentResponse:
    """智能体响应"""
    agent_role: str
    agent_name: str
    response_text: str

    # 可选输出
    tool_calls: Optional[List[Dict[str, Any]]] = None
    reasoning: Optional[str] = None  # 推理过程
    confidence: Optional[float] = None  # 置信度 0-1
    needs_handoff: bool = False  # 是否需要移交给其他智能体
    handoff_target: Optional[str] = None  # 移交目标智能体
    metadata: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """智能体基类"""

    def __init__(self):
        self.role: AgentRole = AgentRole.ORCHESTRATOR
        self.name: str = "BaseAgent"
        self.description: str = "Base agent template"
        self.capabilities: List[str] = []

    @abstractmethod
    async def process(self, context: AgentContext) -> AgentResponse:
        """
        处理请求（核心方法）

        Args:
            context: 智能体上下文

        Returns:
            AgentResponse
        """
        pass

    @abstractmethod
    def can_handle(self, query: str) -> float:
        """
        判断是否能处理该查询

        Args:
            query: 用户查询

        Returns:
            float: 置信度分数 (0-1)，越高表示越适合处理
        """
        pass

    def get_system_prompt(self) -> str:
        """获取智能体的系统提示词"""
        return f"""You are {self.name}, a specialist AI assistant.

Role: {self.role.value}
Description: {self.description}

Your capabilities:
{chr(10).join('- ' + cap for cap in self.capabilities)}

Your goal is to provide expert assistance in your domain while collaborating
with other specialist agents when needed.
"""

    def format_response(
        self,
        text: str,
        reasoning: Optional[str] = None,
        confidence: float = 0.9,
        **kwargs
    ) -> AgentResponse:
        """格式化响应（辅助方法）"""
        return AgentResponse(
            agent_role=self.role.value,
            agent_name=self.name,
            response_text=text,
            reasoning=reasoning,
            confidence=confidence,
            **kwargs
        )
