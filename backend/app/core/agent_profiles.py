"""
Agent Profile Configuration - 统一的Agent配置管理

管理所有Agent的：
- LLM模型选择
- 系统Prompt
- 工具列表
- 参数（temperature等）

支持运行时动态更新，无需重启服务。
"""

from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class AgentRole(str, Enum):
    """Agent角色定义"""
    # 主系统角色
    ORCHESTRATOR = "orchestrator"
    GENERATION = "generation"
    RETRIEVAL = "retrieval"
    TOOL_EXECUTION = "tool_execution"

    # LangGraph 专家角色
    ROUTER = "router"
    GALAXY_GUIDE = "galaxy_guide"
    EXAM_ORACLE = "exam_oracle"
    TIME_TUTOR = "time_tutor"
    STUDY_BUDDY = "study_buddy"

    # 协作工作流角色
    STUDY_PLANNER = "study_planner"
    PROBLEM_SOLVER = "problem_solver"
    MATH_AGENT = "math_agent"
    CODE_AGENT = "code_agent"
    WRITING_AGENT = "writing_agent"
    SCIENCE_AGENT = "science_agent"
    SEARCH_AGENT = "search_agent"


class TaskType(str, Enum):
    """任务类型（用于动态模型选择）"""
    # 简单任务 - 使用快速/廉价模型
    SIMPLE_CHAT = "simple_chat"           # 闲聊
    QUICK_QUERY = "quick_query"           # 快速查询
    ROUTING = "routing"                   # 路由决策

    # 中等任务 - 使用标准模型
    STANDARD_RESPONSE = "standard_response"  # 标准回答
    TOOL_PLANNING = "tool_planning"          # 工具规划
    RETRIEVAL = "retrieval"                  # 检索增强

    # 复杂任务 - 使用强推理模型
    DEEP_REASONING = "deep_reasoning"        # 深度推理
    TASK_DECOMPOSITION = "task_decomposition"  # 任务分解
    ERROR_DIAGNOSIS = "error_diagnosis"      # 错误诊断
    COLLABORATION = "collaboration"          # 多Agent协作


class ModelTier(str, Enum):
    """模型层级（按成本/能力分类）"""
    FAST = "fast"           # 快速响应（如 mimo-v2-flash）
    STANDARD = "standard"   # 标准模型（如 deepseek-chat, glm-4.7）
    REASONING = "reasoning" # 强推理（如 deepseek-reasoner）


@dataclass
class AgentProfile:
    """单个Agent的完整配置"""
    role: AgentRole
    display_name: str
    description: str

    # LLM 配置
    model_tier: ModelTier = ModelTier.STANDARD
    specific_model: Optional[str] = None  # 强制指定具体模型（覆盖 tier）
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    # 系统Prompt
    system_prompt_template: str = ""

    # 工具配置
    allowed_tools: List[str] = field(default_factory=list)
    tool_choice: Literal["auto", "required", "none"] = "auto"

    # 行为配置
    streaming: bool = True
    support_structured_output: bool = False

    # 成本控制
    cost_tier: int = 1  # 1=便宜, 2=中等, 3=昂贵

    def get_model_config(self, available_models: Dict[str, Any]) -> Dict[str, Any]:
        """获取实际模型配置（考虑 tier 和 specific_model）"""
        if self.specific_model:
            return available_models.get(self.specific_model, {})

        # 根据 tier 选择默认模型
        tier_defaults = {
            ModelTier.FAST: available_models.get("fast_model"),
            ModelTier.STANDARD: available_models.get("standard_model"),
            ModelTier.REASONING: available_models.get("reasoning_model"),
        }
        return tier_defaults.get(self.model_tier, {})

    def get_system_prompt(self, **kwargs) -> str:
        """渲染系统Prompt模板"""
        return self.system_prompt_template.format(**kwargs)


# ============================================
# 默认 Agent Profiles 配置
# ============================================

DEFAULT_AGENT_PROFILES: Dict[AgentRole, AgentProfile] = {
    # ==================== 主系统 Agents ====================
    AgentRole.ORCHESTRATOR: AgentProfile(
        role=AgentRole.ORCHESTRATOR,
        display_name="协调器",
        description="负责整体流程编排",
        model_tier=ModelTier.STANDARD,
        temperature=0.3,
        system_prompt_template="你是Sparkle的流程协调器，负责管理对话流程和工具调用。"
    ),

    AgentRole.GENERATION: AgentProfile(
        role=AgentRole.GENERATION,
        display_name="生成器",
        description="负责生成回复内容",
        model_tier=ModelTier.STANDARD,
        temperature=0.7,
        system_prompt_template="你是Sparkle（星火），一个智能学习助手。\n\n{user_context}\n\n{preference_instructions}"
    ),

    AgentRole.RETRIEVAL: AgentProfile(
        role=AgentRole.RETRIEVAL,
        display_name="检索器",
        description="负责知识检索",
        model_tier=ModelTier.FAST,
        temperature=0.2,
        system_prompt_template="你是知识检索专家，负责从知识图谱中查找相关信息。"
    ),

    # ==================== LangGraph 专家 Agents ====================
    AgentRole.ROUTER: AgentProfile(
        role=AgentRole.ROUTER,
        display_name="路由器",
        description="意图识别与路由分发",
        model_tier=ModelTier.FAST,
        temperature=0.1,
        support_structured_output=True,
        system_prompt_template="""You are the Dispatcher for Sparkle AI.

Route the query to the best specialist:
- galaxy_guide: Knowledge graph, concepts, prerequisites, learning paths
- time_tutor: Scheduling, tasks, planning, deadlines, tomato timer
- exam_oracle: Exam predictions, mock tests, past paper analysis
- study_buddy: General chat, emotional support, simple Q&A
- human_assist: User asks for human help or system cannot handle

Query: {query}"""
    ),

    AgentRole.GALAXY_GUIDE: AgentProfile(
        role=AgentRole.GALAXY_GUIDE,
        display_name="星图向导",
        description="知识图谱专家",
        model_tier=ModelTier.STANDARD,
        temperature=0.5,
        allowed_tools=["search_knowledge_graph", "get_prerequisites"],
        system_prompt_template="""你是星图向导，Sparkle AI的知识图谱专家。

你的职责：
1. 解释概念及其关联关系
2. 推荐学习路径
3. 识别前置知识
4. 回答"什么是X"类问题

用户问题：{query}"""
    ),

    AgentRole.EXAM_ORACLE: AgentProfile(
        role=AgentRole.EXAM_ORACLE,
        display_name="考试预言家",
        description="考试预测与分析",
        model_tier=ModelTier.REASONING,
        temperature=0.3,
        allowed_tools=["analyze_past_papers", "predict_exam_focus"],
        system_prompt_template="""你是考试预言家，Sparkle AI的考试分析专家。

你的职责：
1. 分析历年试卷
2. 预测考试重点
3. 生成模拟试题
4. 制定复习策略"""
    ),

    AgentRole.TIME_TUTOR: AgentProfile(
        role=AgentRole.TIME_TUTOR,
        display_name="时间导师",
        description="学习计划与时间管理",
        model_tier=ModelTier.STANDARD,
        temperature=0.6,
        allowed_tools=["create_study_task", "suggest_pomodoro_schedule"],
        system_prompt_template="""你是时间导师，Sparkle AI的学习计划专家。

你的职责：
1. 制定学习计划
2. 管理任务列表
3. 建议番茄钟安排
4. 监控学习进度"""
    ),

    # ==================== 协作工作流 Agents ====================
    AgentRole.STUDY_PLANNER: AgentProfile(
        role=AgentRole.STUDY_PLANNER,
        display_name="学习规划师",
        description="制定宏观学习计划",
        model_tier=ModelTier.REASONING,
        temperature=0.5,
        system_prompt_template="""你是学习规划师，负责制定宏观学习计划和分析学习状态。"""
    ),

    AgentRole.PROBLEM_SOLVER: AgentProfile(
        role=AgentRole.PROBLEM_SOLVER,
        display_name="问题解决者",
        description="错题诊断与解题分析",
        model_tier=ModelTier.REASONING,
        temperature=0.3,
        system_prompt_template="""你是问题解决者，负责分析错题和诊断知识缺陷。"""
    ),

    AgentRole.MATH_AGENT: AgentProfile(
        role=AgentRole.MATH_AGENT,
        display_name="数学专家",
        description="数学问题与练习",
        model_tier=ModelTier.STANDARD,
        temperature=0.4,
        system_prompt_template="""你是数学专家，负责生成数学练习和讲解数学概念。"""
    ),

    AgentRole.CODE_AGENT: AgentProfile(
        role=AgentRole.CODE_AGENT,
        display_name="编程专家",
        description="代码问题与项目",
        model_tier=ModelTier.STANDARD,
        temperature=0.4,
        system_prompt_template="""你是编程专家，负责设计编程项目和讲解代码概念。"""
    ),

    AgentRole.SEARCH_AGENT: AgentProfile(
        role=AgentRole.SEARCH_AGENT,
        display_name="搜索专家",
        description="知识检索与证据收集",
        model_tier=ModelTier.FAST,
        temperature=0.2,
        system_prompt_template="""你是搜索专家，负责检索背景知识和收集证据。"""
    ),
}


# ============================================
# 任务类型 -> Agent/Model 映射
# ============================================

TASK_TO_AGENT_PROFILE: Dict[TaskType, Dict[str, Any]] = {
    TaskType.SIMPLE_CHAT: {
        "default_agent": AgentRole.TIME_TUTOR,
        "fallback_agent": AgentRole.STUDY_BUDDY,
        "model_tier": ModelTier.FAST,
    },
    TaskType.QUICK_QUERY: {
        "default_agent": AgentRole.GALAXY_GUIDE,
        "fallback_agent": AgentRole.ROUTER,
        "model_tier": ModelTier.FAST,
    },
    TaskType.ROUTING: {
        "default_agent": AgentRole.ROUTER,
        "model_tier": ModelTier.FAST,
    },
    TaskType.STANDARD_RESPONSE: {
        "default_agent": AgentRole.GENERATION,
        "model_tier": ModelTier.STANDARD,
    },
    TaskType.TOOL_PLANNING: {
        "default_agent": AgentRole.ORCHESTRATOR,
        "model_tier": ModelTier.STANDARD,
    },
    TaskType.RETRIEVAL: {
        "default_agent": AgentRole.RETRIEVAL,
        "model_tier": ModelTier.FAST,
    },
    TaskType.DEEP_REASONING: {
        "default_agent": AgentRole.EXAM_ORACLE,
        "model_tier": ModelTier.REASONING,
    },
    TaskType.TASK_DECOMPOSITION: {
        "default_agent": AgentRole.STUDY_PLANNER,
        "model_tier": ModelTier.REASONING,
    },
    TaskType.ERROR_DIAGNOSIS: {
        "default_agent": AgentRole.PROBLEM_SOLVER,
        "model_tier": ModelTier.REASONING,
    },
    TaskType.COLLABORATION: {
        "default_agent": AgentRole.ORCHESTRATOR,
        "model_tier": ModelTier.STANDARD,
    },
}


class AgentProfileRegistry:
    """Agent配置注册表（支持运行时更新）"""

    def __init__(self):
        self._profiles: Dict[AgentRole, AgentProfile] = DEFAULT_AGENT_PROFILES.copy()
        self._model_configs: Dict[str, Any] = {}

    def register_model_configs(self, configs: Dict[str, Any]):
        """注册可用的模型配置"""
        self._model_configs.update(configs)

    def get_profile(self, role: AgentRole) -> AgentProfile:
        """获取Agent配置"""
        return self._profiles.get(role, DEFAULT_AGENT_PROFILES.get(AgentRole.GENERATION))

    def get_profile_for_task(self, task_type: TaskType) -> AgentProfile:
        """根据任务类型获取推荐的Agent配置"""
        task_config = TASK_TO_AGENT_PROFILE.get(task_type, {})
        agent_role = task_config.get("default_agent", AgentRole.GENERATION)
        return self.get_profile(agent_role)

    def update_profile(self, role: AgentRole, updates: Dict[str, Any]):
        """更新Agent配置（运行时）"""
        if role in self._profiles:
            current = self._profiles[role]
            for key, value in updates.items():
                setattr(current, key, value)
            logger.info(f"Updated profile for {role}: {updates}")

    def list_all_profiles(self) -> Dict[AgentRole, Dict[str, Any]]:
        """列出所有Agent配置（用于调试）"""
        return {
            role: {
                "display_name": p.display_name,
                "model_tier": p.model_tier,
                "temperature": p.temperature,
                "tools": p.allowed_tools,
            }
            for role, p in self._profiles.items()
        }


# 全局注册表实例
agent_profile_registry = AgentProfileRegistry()
