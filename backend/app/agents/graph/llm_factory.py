"""
LLM Factory - LangGraph 兼容的模型工厂

重构说明：
- 现在统一使用 LLMRouter 进行模型选择
- 与主系统 (llm_service.py) 共享同一套配置
- 保持与 LangGraph 的兼容接口

使用方式：
    llm = LLMFactory.get_llm("galaxy_guide")  # 推荐方式
    llm = LLMFactory.get_llm_for_task(TaskType.DEEP_REASONING)  # 按任务选择
"""

from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings
from app.core.llm_router import llm_router, LLMSelection
from app.core.agent_profiles import AgentRole, TaskType


if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
else:
    BaseChatModel = Any

class LLMFactory:
    """
    LLM 模型工厂 (LangGraph 兼容)

    职责：
    1. 根据Agent角色获取合适的LangChain ChatModel
    2. 与主系统共享 LLMRouter 配置
    3. 支持任务级动态模型选择
    """

    @staticmethod
    def get_llm(
        agent_role: str,
        override_model: Optional[str] = None,
        task_type: Optional[TaskType] = None,
    ) -> BaseChatModel:
        """
        根据 Agent 角色获取 LangChain ChatModel

        Args:
            agent_role: Agent 角色名称 (router, galaxy_guide, time_tutor, exam_oracle 等)
            override_model: 强制指定模型名称（不推荐，仅用于调试）
            task_type: 任务类型（用于更精细的模型选择）

        Returns:
            LangChain ChatOpenAI 实例

        Example:
            # 基本用法
            llm = LLMFactory.get_llm("galaxy_guide")

            # 按任务选择
            from app.core.agent_profiles import TaskType
            llm = LLMFactory.get_llm("orchestrator", task_type=TaskType.DEEP_REASONING)
        """
        # 标准化角色名称
        if isinstance(agent_role, str):
            # 兼容旧的角色命名
            role_mapping = {
                "planner": "study_planner",
                "oracle": "exam_oracle",
                "time": "time_tutor",
                "galaxy": "galaxy_guide",
            }
            agent_role = role_mapping.get(agent_role.lower(), agent_role.lower())

        try:
            role_enum = AgentRole(agent_role)
        except ValueError:
            # 如果不是预定义角色，作为字符串传递给router
            role_enum = AgentRole.GENERATION  # 默认

        # 使用 LLMRouter 选择模型
        if task_type:
            selection = llm_router.select_model(role_enum, task_type)
        elif override_model:
            # 强制指定已注册模型key（调试用）
            selection = llm_router.select_specific_model(
                override_model,
                agent_role=role_enum,
                task_type=task_type,
            )
        else:
            selection = llm_router.select_model(role_enum)

        # 获取 LangChain 兼容的参数
        kwargs = llm_router.get_langchain_client_kwargs(selection)

        # 创建 LangChain ChatOpenAI 实例
        return ChatOpenAI(**kwargs)

    @staticmethod
    def get_llm_for_task(task_type: TaskType) -> BaseChatModel:
        """
        根据任务类型直接获取模型

        Args:
            task_type: 任务类型

        Example:
            from app.core.agent_profiles import TaskType
            llm = LLMFactory.get_llm_for_task(TaskType.DEEP_REASONING)
        """
        return LLMFactory.get_llm("orchestrator", task_type=task_type)


# ============================================
# 向后兼容的别名（旧代码可能用到）
# ============================================

# 模型配置字典（仅用于向后兼容旧代码的读取）
MODEL_CONFIGS = {
    "deepseek-chat": {
        "model": settings.DEEPSEEK_CHAT_MODEL,
        "base_url": settings.DEEPSEEK_BASE_URL,
        "api_key": settings.DEEPSEEK_API_KEY,
        "temperature": 0.3
    },
    "deepseek-reason": {
        "model": settings.DEEPSEEK_REASON_MODEL,
        "base_url": settings.DEEPSEEK_BASE_URL,
        "api_key": settings.DEEPSEEK_API_KEY,
        "temperature": 0.2
    },
    "default": {
        "model": settings.LLM_MODEL_NAME,
        "base_url": settings.LLM_API_BASE_URL,
        "api_key": settings.LLM_API_KEY,
        "temperature": 0.7
    }
}
