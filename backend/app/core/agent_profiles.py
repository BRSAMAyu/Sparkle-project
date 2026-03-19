from __future__ import annotations
"""
Agent Profile Configuration - 统一的Agent配置管理

管理所有Agent的：
- LLM模型选择
- 系统Prompt
- 工具列表
- 参数（temperature等）

支持运行时动态更新，无需重启服务。
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal

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
    DEEP_ANALYST = "deep_analyst"
    ERROR_ANALYST = "error_analyst"
    STUDY_BUDDY = "study_buddy"

    # 协作工作流角色
    STUDY_PLANNER = "study_planner"
    PROBLEM_SOLVER = "problem_solver"
    MATH_AGENT = "math_agent"
    CODE_AGENT = "code_agent"
    WRITING_AGENT = "writing_agent"
    SCIENCE_AGENT = "science_agent"
    SEARCH_AGENT = "search_agent"

    # 审查角色
    REVIEWER = "reviewer"                  # 内容审查专家（使用独立模型）


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

    # 审查任务 - 使用专门模型进行质量审查
    REVIEW = "review"                        # 内容审查（需要不同模型）


class ModelTier(str, Enum):
    """模型层级（按成本/能力分类）"""
    FAST = "fast"           # 快速响应（如 mimo-v2-flash, qwen3.5-flash）
    FREE_FAST = "free_fast" # 免费快速（如 glm-4.7-flash 非思考模式）
    STANDARD = "standard"   # 标准模型（如 deepseek-chat, qwen3.5-plus）
    REASONING = "reasoning" # 强推理（如 deepseek-reasoner, qwen3.5-plus）
    FREE_REASONING = "free_reasoning" # 免费推理（如 glm-4.7-flash 思考模式）
    GLM_BATCH = "glm_batch" # GLM批量处理（glm-4.7 非思考+思考模式）
    SPECIALIST = "specialist" # 专家模型（如 OCR、翻译等专用模型）


@dataclass
class AgentModelPolicy:
    """Agent级模型策略。

    用于解决“所有 agent 只是共用 tier 顺序降级”的问题。
    每个 agent 可以声明：
    - 首选模型 key
    - 首选 tier
    - tier fallback 链
    - 禁用模型
    """

    preferred_models: list[str] = field(default_factory=list)
    preferred_tier: ModelTier | None = None
    fallback_tiers: list[ModelTier] = field(default_factory=list)
    blocked_models: list[str] = field(default_factory=list)
    lock_to_policy: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.preferred_tier is not None:
            payload["preferred_tier"] = self.preferred_tier.value
        payload["fallback_tiers"] = [tier.value for tier in self.fallback_tiers]
        return payload


@dataclass
class AgentProfile:
    """单个Agent的完整配置"""
    role: AgentRole
    display_name: str
    description: str
    public_entry: bool = False
    entry_tags: list[str] = field(default_factory=list)
    entry_rank: int = 999
    entry_enabled: bool = False

    # LLM 配置
    model_tier: ModelTier = ModelTier.STANDARD
    specific_model: str | None = None  # 强制指定具体模型（覆盖 tier）
    model_policy: AgentModelPolicy | None = None
    temperature: float = 0.7
    max_tokens: int | None = None

    # 系统Prompt
    system_prompt_template: str = ""

    # 工具配置
    allowed_tools: list[str] = field(default_factory=list)
    tool_choice: Literal["auto", "required", "none"] = "auto"

    # 行为配置
    streaming: bool = True
    support_structured_output: bool = False

    # 成本控制
    cost_tier: int = 1  # 1=便宜, 2=中等, 3=昂贵

    def get_model_config(self, available_models: dict[str, Any]) -> dict[str, Any]:
        """获取实际模型配置（考虑 tier 和 specific_model）"""
        if self.specific_model:
            return available_models.get(self.specific_model, {})

        # 根据 tier 选择默认模型
        tier_defaults = {
            ModelTier.FAST: available_models.get("fast_model"),
            ModelTier.STANDARD: available_models.get("standard_model"),
            ModelTier.REASONING: available_models.get("reasoning_model"),
            ModelTier.GLM_BATCH: available_models.get("glm_batch_model"),
        }
        return tier_defaults.get(self.model_tier, {})

    def get_system_prompt(self, **kwargs) -> str:
        """渲染系统Prompt模板"""
        return self.system_prompt_template.format(**kwargs)


# ============================================
# 默认 Agent Profiles 配置
# ============================================

DEFAULT_AGENT_PROFILES: dict[AgentRole, AgentProfile] = {
    # ==================== 主系统 Agents ====================
    AgentRole.ORCHESTRATOR: AgentProfile(
        role=AgentRole.ORCHESTRATOR,
        display_name="协调器",
        description="负责整体流程编排",
        model_tier=ModelTier.STANDARD,
        model_policy=AgentModelPolicy(
            preferred_models=["mimo_pro", "dashscope_chat"],
            preferred_tier=ModelTier.STANDARD,
            fallback_tiers=[ModelTier.REASONING],
        ),
        temperature=0.3,
        system_prompt_template="你是Sparkle的流程协调器，负责管理对话流程和工具调用。"
    ),

    AgentRole.GENERATION: AgentProfile(
        role=AgentRole.GENERATION,
        display_name="生成器",
        description="负责生成回复内容",
        model_tier=ModelTier.STANDARD,
        model_policy=AgentModelPolicy(
            preferred_models=["mimo_pro", "dashscope_chat", "deepseek_chat"],
            preferred_tier=ModelTier.STANDARD,
            fallback_tiers=[ModelTier.REASONING, ModelTier.FAST],
        ),
        temperature=0.7,
        system_prompt_template="你是Sparkle（星火），一个智能学习助手。\n\n{user_context}\n\n{preference_instructions}"
    ),

    AgentRole.RETRIEVAL: AgentProfile(
        role=AgentRole.RETRIEVAL,
        display_name="检索器",
        description="负责知识检索",
        model_tier=ModelTier.FREE_FAST,
        model_policy=AgentModelPolicy(
            preferred_models=["glm_4_7_flash_no_thinking", "dashscope_fast", "xiaomi_chat"],
            preferred_tier=ModelTier.FREE_FAST,
            fallback_tiers=[ModelTier.FAST, ModelTier.STANDARD],
        ),
        temperature=0.2,
        system_prompt_template="你是知识检索专家，负责从知识图谱中查找相关信息。"
    ),

    # ==================== LangGraph 专家 Agents ====================
    AgentRole.ROUTER: AgentProfile(
        role=AgentRole.ROUTER,
        display_name="路由器",
        description="意图识别与路由分发",
        model_tier=ModelTier.FREE_FAST,
        model_policy=AgentModelPolicy(
            preferred_models=["glm_4_7_flash_no_thinking", "dashscope_fast"],
            preferred_tier=ModelTier.FREE_FAST,
            fallback_tiers=[ModelTier.FAST],
        ),
        temperature=0.1,
        support_structured_output=True,
        system_prompt_template="""You are the Dispatcher for Sparkle AI. Output JSON only, no explanation.

Specialists:
- galaxy_guide: knowledge graph, concepts, prerequisites, learning paths
- time_tutor: scheduling, tasks, planning, deadlines, focus timer
- exam_oracle: exam predictions, mock tests, past paper analysis
- study_buddy: general chat, emotional support, simple Q&A
- human_assist: user requests human help or system cannot handle

Examples:
{{"query": "微积分求导怎么做", "route": "galaxy_guide", "confidence": 0.9}}
{{"query": "帮我安排明天学习时间", "route": "time_tutor", "confidence": 0.95}}
{{"query": "你好啊", "route": "study_buddy", "confidence": 0.85}}
{{"query": "预测期末考重点", "route": "exam_oracle", "confidence": 0.9}}

Query: {query}
Output: {{"route": "<specialist>", "confidence": <0-1>}}"""
    ),

    AgentRole.GALAXY_GUIDE: AgentProfile(
        role=AgentRole.GALAXY_GUIDE,
        display_name="星图向导",
        description="知识图谱专家",
        public_entry=True,
        entry_enabled=True,
        entry_rank=10,
        entry_tags=["knowledge", "prerequisite", "learning-path"],
        model_tier=ModelTier.STANDARD,
        model_policy=AgentModelPolicy(
            preferred_models=["dashscope_chat", "mimo_pro"],
            preferred_tier=ModelTier.STANDARD,
            fallback_tiers=[ModelTier.REASONING, ModelTier.FAST],
        ),
        temperature=0.5,
        allowed_tools=["query_knowledge", "create_knowledge_node", "link_nodes"],
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
        public_entry=True,
        entry_enabled=True,
        entry_rank=20,
        entry_tags=["exam", "strategy", "mock"],
        model_tier=ModelTier.REASONING,
        model_policy=AgentModelPolicy(
            preferred_models=["dashscope_reason", "mimo_pro", "deepseek_reason"],
            preferred_tier=ModelTier.REASONING,
            fallback_tiers=[ModelTier.STANDARD],
        ),
        temperature=0.3,
        allowed_tools=["create_plan", "generate_tasks_for_plan", "create_task", "query_knowledge"],
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
        public_entry=True,
        entry_enabled=True,
        entry_rank=30,
        entry_tags=["schedule", "tasks", "focus"],
        model_tier=ModelTier.STANDARD,
        model_policy=AgentModelPolicy(
            preferred_models=["mimo_pro", "dashscope_chat"],
            preferred_tier=ModelTier.STANDARD,
            fallback_tiers=[ModelTier.REASONING, ModelTier.FAST],
        ),
        temperature=0.6,
        allowed_tools=[
            "create_plan",
            "generate_tasks_for_plan",
            "create_task",
            "batch_create_tasks",
            "suggest_focus_session",
        ],
        system_prompt_template="""你是时间导师，Sparkle AI的学习计划专家。

你的职责：
1. 制定学习计划
2. 管理任务列表
3. 建议番茄钟安排
4. 监控学习进度"""
    ),

    AgentRole.DEEP_ANALYST: AgentProfile(
        role=AgentRole.DEEP_ANALYST,
        display_name="深度分析师",
        description="多视角结构化分析专家",
        public_entry=True,
        entry_enabled=True,
        entry_rank=40,
        entry_tags=["analysis", "reasoning", "evidence"],
        model_tier=ModelTier.REASONING,
        model_policy=AgentModelPolicy(
            preferred_models=["dashscope_reason", "mimo_pro", "deepseek_reason"],
            preferred_tier=ModelTier.REASONING,
            fallback_tiers=[ModelTier.STANDARD],
        ),
        temperature=0.4,
        allowed_tools=["query_knowledge", "create_knowledge_node"],
        system_prompt_template="""你是深度分析师，负责基于证据进行多角度分析。

你的职责：
1. 提炼关键论点与证据链
2. 分析边界条件与反例
3. 给出可执行应用建议"""
    ),

    AgentRole.ERROR_ANALYST: AgentProfile(
        role=AgentRole.ERROR_ANALYST,
        display_name="错题分析师",
        description="错题诊断与根因分析",
        public_entry=True,
        entry_enabled=True,
        entry_rank=50,
        entry_tags=["error-diagnosis", "remediation", "root-cause"],
        model_tier=ModelTier.REASONING,
        model_policy=AgentModelPolicy(
            preferred_models=["dashscope_reason", "deepseek_reason", "mimo_pro"],
            preferred_tier=ModelTier.REASONING,
            fallback_tiers=[ModelTier.STANDARD],
        ),
        temperature=0.3,
        allowed_tools=["query_error_history", "record_error", "query_knowledge", "create_task"],
        system_prompt_template="""你是错题分析师，负责识别错误类型并输出补救策略。

诊断格式（必须严格遵守）：
① 错误类型（知识性/理解性/计算性/粗心）
② 根因定位：具体指出哪个步骤、哪个概念存在偏差
③ 正确解法对齐：给出完整的正确思路
④ 同类题变式：设计1道针对性练习题

[DO] 具体定位到步骤和概念
[DON'T] 只说"注意审题"等泛泛建议"""
    ),

    # ==================== 协作工作流 Agents ====================
    AgentRole.STUDY_PLANNER: AgentProfile(
        role=AgentRole.STUDY_PLANNER,
        display_name="学习规划师",
        description="制定宏观学习计划",
        model_tier=ModelTier.REASONING,
        model_policy=AgentModelPolicy(
            preferred_models=["mimo_pro", "deepseek_reason", "dashscope_reason"],
            preferred_tier=ModelTier.REASONING,
            fallback_tiers=[ModelTier.STANDARD],
        ),
        temperature=0.5,
        system_prompt_template="""你是学习规划师，负责制定宏观学习计划和分析学习状态。"""
    ),

    AgentRole.PROBLEM_SOLVER: AgentProfile(
        role=AgentRole.PROBLEM_SOLVER,
        display_name="问题解决者",
        description="错题诊断与解题分析",
        model_tier=ModelTier.REASONING,
        model_policy=AgentModelPolicy(
            preferred_models=["deepseek_reason", "mimo_pro", "dashscope_reason"],
            preferred_tier=ModelTier.REASONING,
            fallback_tiers=[ModelTier.STANDARD],
        ),
        temperature=0.3,
        system_prompt_template="""你是问题解决者，负责分析错题和诊断知识缺陷。"""
    ),

    AgentRole.MATH_AGENT: AgentProfile(
        role=AgentRole.MATH_AGENT,
        display_name="数学专家",
        description="数学问题与练习",
        public_entry=True,
        entry_enabled=True,
        entry_rank=60,
        entry_tags=["math", "practice", "derivation"],
        model_tier=ModelTier.STANDARD,
        model_policy=AgentModelPolicy(
            preferred_models=["deepseek_chat", "dashscope_reason", "dashscope_chat"],
            preferred_tier=ModelTier.STANDARD,
            fallback_tiers=[ModelTier.REASONING],
        ),
        temperature=0.4,
        system_prompt_template="""你是数学专家，负责生成数学练习和讲解数学概念。

解题规范：
1. 必须写出完整步骤，每步标注所用定理/公式名称
2. 计算题先列公式，再代入数值
3. 答案必须包含单位（适用时）
4. 结尾给出验证方法或同类题提示"""
    ),

    AgentRole.CODE_AGENT: AgentProfile(
        role=AgentRole.CODE_AGENT,
        display_name="编程专家",
        description="代码问题与项目",
        public_entry=True,
        entry_enabled=True,
        entry_rank=70,
        entry_tags=["code", "debugging", "projects"],
        model_tier=ModelTier.STANDARD,
        model_policy=AgentModelPolicy(
            preferred_models=["deepseek_chat", "dashscope_chat", "mimo_pro"],
            preferred_tier=ModelTier.STANDARD,
            fallback_tiers=[ModelTier.REASONING, ModelTier.GLM_BATCH],
        ),
        temperature=0.4,
        system_prompt_template="""你是编程专家，负责设计编程项目和讲解代码概念。"""
    ),

    AgentRole.SEARCH_AGENT: AgentProfile(
        role=AgentRole.SEARCH_AGENT,
        display_name="搜索专家",
        description="知识检索与证据收集",
        public_entry=True,
        entry_enabled=True,
        entry_rank=90,
        entry_tags=["search", "evidence", "retrieval"],
        model_tier=ModelTier.FREE_FAST,
        model_policy=AgentModelPolicy(
            preferred_models=["glm_4_7_flash_no_thinking", "dashscope_fast", "xiaomi_chat"],
            preferred_tier=ModelTier.FREE_FAST,
            fallback_tiers=[ModelTier.FAST, ModelTier.STANDARD],
        ),
        temperature=0.2,
        system_prompt_template="""你是搜索专家，负责检索背景知识和收集证据。"""
    ),

    # ==================== 审查 Agents ====================
    AgentRole.REVIEWER: AgentProfile(
        role=AgentRole.REVIEWER,
        display_name="审查专家",
        description="AI内容质量审查（使用独立模型）",
        model_tier=ModelTier.REASONING,  # 使用强推理模型
        model_policy=AgentModelPolicy(
            preferred_models=["deepseek_reason", "dashscope_reason", "mimo_pro"],
            preferred_tier=ModelTier.REASONING,
            fallback_tiers=[ModelTier.STANDARD],
        ),
        temperature=0.2,  # 低温确保客观
        support_structured_output=True,
        system_prompt_template="""你是内容审查专家，负责评估AI生成内容的质量。

审查原则：
1. 客观性：基于事实和标准进行评估，不带偏见
2. 建设性：指出问题时必须给出可操作的改进建议
3. 精准性：问题描述要具体，定位到具体位置
4. 用户视角：始终考虑最终用户的需求和体验"""
    ),

    # ==================== 其他 Agents ====================
    AgentRole.TOOL_EXECUTION: AgentProfile(
        role=AgentRole.TOOL_EXECUTION,
        display_name="工具执行",
        description="执行工具调用",
        model_tier=ModelTier.STANDARD,
        model_policy=AgentModelPolicy(
            preferred_models=["mimo_pro", "dashscope_chat", "deepseek_chat"],
            preferred_tier=ModelTier.STANDARD,
            fallback_tiers=[ModelTier.REASONING, ModelTier.FAST],
        ),
        temperature=0.3,
        system_prompt_template="""你是工具执行专家，负责调用外部工具并解析结果。"""
    ),

    AgentRole.STUDY_BUDDY: AgentProfile(
        role=AgentRole.STUDY_BUDDY,
        display_name="学习伙伴",
        description="日常学习陪伴与闲聊",
        public_entry=True,
        entry_enabled=True,
        entry_rank=80,
        entry_tags=["chat", "coaching", "support"],
        model_tier=ModelTier.FREE_FAST,
        model_policy=AgentModelPolicy(
            preferred_models=["glm_4_7_flash_no_thinking", "xiaomi_chat", "dashscope_fast"],
            preferred_tier=ModelTier.FREE_FAST,
            fallback_tiers=[ModelTier.FAST, ModelTier.STANDARD],
        ),
        temperature=0.7,
        system_prompt_template="""你是学习伙伴，一个友好、轻松的AI助手。

[DO] 回复控制在3句话以内，使用口语化表达，像朋友而非老师
[DO] 遇到简单问题直接回答；遇到情绪问题先共情再建议
[DON'T] 主动展开学术话题，除非用户明确提问
[DON'T] 给出冗长的解释和列表

遇到复杂学术问题时，简单回应后建议："这个问题我帮你转给专家模式~"
"""
    ),

    AgentRole.WRITING_AGENT: AgentProfile(
        role=AgentRole.WRITING_AGENT,
        display_name="写作专家",
        description="写作指导与文本优化",
        public_entry=True,
        entry_enabled=True,
        entry_rank=100,
        entry_tags=["writing", "editing", "expression"],
        model_tier=ModelTier.STANDARD,
        model_policy=AgentModelPolicy(
            preferred_models=["deepseek_chat", "dashscope_chat", "mimo_pro"],
            preferred_tier=ModelTier.STANDARD,
            fallback_tiers=[ModelTier.REASONING, ModelTier.FAST],
        ),
        temperature=0.8,
        system_prompt_template="""你是写作专家，负责指导写作和优化文本。

你的职责：
1. 提供写作建议
2. 优化文本表达
3. 修正语法错误
4. 提升文章结构"""
    ),

    AgentRole.SCIENCE_AGENT: AgentProfile(
        role=AgentRole.SCIENCE_AGENT,
        display_name="科学专家",
        description="科学概念讲解与实验设计",
        public_entry=True,
        entry_enabled=True,
        entry_rank=110,
        entry_tags=["science", "concepts", "experiments"],
        model_tier=ModelTier.REASONING,
        model_policy=AgentModelPolicy(
            preferred_models=["dashscope_reason", "mimo_pro", "deepseek_reason"],
            preferred_tier=ModelTier.REASONING,
            fallback_tiers=[ModelTier.STANDARD],
        ),
        temperature=0.5,
        system_prompt_template="""你是科学专家，负责讲解科学概念和设计实验。

你的职责：
1. 讲解物理、化学、生物等科学概念
2. 设计实验方案
3. 分析实验数据
4. 解释科学原理"""
    ),
}


# ============================================
# 任务类型 -> Agent/Model 映射
# ============================================

TASK_TO_AGENT_PROFILE: dict[TaskType, dict[str, Any]] = {
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
    TaskType.REVIEW: {
        "default_agent": AgentRole.REVIEWER,
        "model_tier": ModelTier.REASONING,  # 审查使用强推理模型
    },
}


class AgentProfileRegistry:
    """Agent配置注册表（支持运行时更新）"""

    def __init__(self):
        self._profiles: dict[AgentRole, AgentProfile] = DEFAULT_AGENT_PROFILES.copy()
        self._model_configs: dict[str, Any] = {}

    def register_model_configs(self, configs: dict[str, Any]):
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

    def update_profile(self, role: AgentRole, updates: dict[str, Any]):
        """更新Agent配置（运行时）"""
        if role in self._profiles:
            current = self._profiles[role]
            for key, value in updates.items():
                setattr(current, key, value)
            logger.info(f"Updated profile for {role}: {updates}")

    def list_all_profiles(self) -> dict[AgentRole, dict[str, Any]]:
        """列出所有Agent配置（用于调试）"""
        return {
            role: {
                "display_name": p.display_name,
                "model_tier": p.model_tier,
                "model_policy": p.model_policy.to_dict() if p.model_policy else None,
                "temperature": p.temperature,
                "tools": p.allowed_tools,
            }
            for role, p in self._profiles.items()
        }

    def list_public_entry_profiles(self) -> list[tuple[AgentRole, AgentProfile]]:
        profiles = [
            (role, profile)
            for role, profile in self._profiles.items()
            if profile.public_entry and profile.entry_enabled
        ]
        return sorted(profiles, key=lambda item: (item[1].entry_rank, item[1].display_name))


def get_public_agent_catalog() -> list[dict[str, Any]]:
    """Unified expert catalog for public entry and routing."""
    catalog: list[dict[str, Any]] = []
    for role, profile in agent_profile_registry.list_public_entry_profiles():
        expert_id = role.value
        catalog.append({
            "id": expert_id,
            "display_name": profile.display_name,
            "description": profile.description,
            "tags": profile.entry_tags,
            "entry_chat_mode": f"expert::{expert_id}",
            "recommended_scenarios": profile.entry_tags[:3],
            "enabled": profile.entry_enabled,
            "rank": profile.entry_rank,
            "source": "official",
            "official": True,
            "model_tier": profile.model_tier.value,
            "specific_model": profile.specific_model,
            "model_policy": profile.model_policy.to_dict() if profile.model_policy else None,
        })
    return catalog


def get_public_mode_catalog() -> list[dict[str, Any]]:
    """Stable mode catalog returned by /multi-agent/catalog."""
    return [
        {
            "id": "deep_analysis",
            "label": "深度解析",
            "description": "多专家协作深度解析问题",
            "entry_chat_mode": "deep_analysis",
            "enabled": True,
        },
        {
            "id": "study_plan",
            "label": "学习计划",
            "description": "任务分解与学习计划协作",
            "entry_chat_mode": "study_plan",
            "enabled": True,
        },
        {
            "id": "error_diagnosis",
            "label": "错题分析",
            "description": "错题诊断与分析循环",
            "entry_chat_mode": "error_diagnosis",
            "enabled": True,
        },
        {
            "id": "expert_auto",
            "label": "专家自动路由",
            "description": "自动选择最合适专家组合",
            "entry_chat_mode": "expert_auto",
            "enabled": True,
        },
    ]


# 全局注册表实例
agent_profile_registry = AgentProfileRegistry()
