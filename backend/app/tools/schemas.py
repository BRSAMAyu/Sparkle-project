from __future__ import annotations
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ============ 任务工具参数 ============

class TaskType(str, Enum):
    LEARNING = "learning"
    TRAINING = "training"
    ERROR_FIX = "error_fix"
    REFLECTION = "reflection"
    SOCIAL = "social"
    PLANNING = "planning"

class CreateTaskParams(BaseModel):
    """创建任务的参数"""
    title: str = Field(..., description="任务标题", max_length=100)
    description: str | None = Field(None, description="任务详细描述")
    task_type: TaskType = Field(default=TaskType.LEARNING, description="任务类型")
    estimated_minutes: int | None = Field(None, description="预估时长（分钟）", ge=1, le=480)
    subject_id: str | None = Field(None, description="关联科目 ID")
    due_date: datetime | None = Field(None, description="截止日期")
    priority: int = Field(default=2, description="优先级 1-5，5 最高", ge=1, le=5)

class UpdateTaskStatusParams(BaseModel):
    """更新任务状态的参数"""
    task_id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="新状态: pending/in_progress/completed/abandoned")
    actual_minutes: int | None = Field(None, description="实际耗时（完成时填写）")

class BatchCreateTasksParams(BaseModel):
    """批量创建任务的参数"""
    tasks: list[CreateTaskParams] = Field(..., description="任务列表", min_length=1, max_length=10)

# ============ 碎片时间/微任务参数 ============

class SuggestQuickTaskParams(BaseModel):
    """碎片时间推荐任务参数"""
    available_minutes: int = Field(..., description="可用时间（分钟）", ge=5, le=120)
    include_in_progress: bool = Field(default=False, description="是否包含进行中的任务")
    preferred_types: list[TaskType] | None = Field(default=None, description="优先任务类型")

class BreakdownTaskParams(BaseModel):
    """任务拆解参数"""
    title: str = Field(..., description="任务标题", max_length=100)
    description: str | None = Field(None, description="任务描述")
    task_type: TaskType = Field(default=TaskType.LEARNING, description="任务类型")
    max_tasks: int = Field(default=5, description="最多拆解数量", ge=2, le=8)

# ============ 计划工具参数 ============

class PlanType(str, Enum):
    SPRINT = "sprint"    # 考试冲刺
    GROWTH = "growth"    # 长期成长


class PlanStage(str, Enum):
    SPRINT = "sprint"
    DAILY = "daily"
    REVIEW = "review"
    PAUSED = "paused"

class CreatePlanParams(BaseModel):
    """创建计划的参数"""
    title: str = Field(..., description="计划名称")
    plan_type: PlanType = Field(..., description="计划类型")
    plan_stage: PlanStage | None = Field(default=None, description="计划阶段")
    subject_id: str | None = Field(None, description="关联科目 ID")
    target_date: datetime | None = Field(None, description="目标日期（冲刺计划必填）")
    target_mastery: float | None = Field(None, description="目标掌握度 0-1", ge=0, le=1)
    description: str | None = Field(None, description="计划描述")

class GenerateTasksForPlanParams(BaseModel):
    """为计划生成任务的参数"""
    plan_id: str = Field(..., description="计划 ID")
    topic: str = Field(..., description="学习主题/知识点")
    difficulty: str = Field(default="medium", description="难度: easy/medium/hard")
    task_count: int = Field(default=5, description="生成任务数量", ge=1, le=10)

# ============ 专注工具参数 ============

class SuggestFocusSessionParams(BaseModel):
    """专注会话建议参数"""
    duration_minutes: int = Field(default=25, description="专注时长（分钟）", ge=10, le=90)
    task_id: str | None = Field(default=None, description="关联任务 ID")
    task_title: str | None = Field(default=None, description="任务标题（无任务时备用）")

# ============ 知识图谱工具参数 ============

class CreateKnowledgeNodeParams(BaseModel):
    """创建知识节点的参数"""
    title: str = Field(..., description="知识点标题")
    summary: str = Field(..., description="知识点摘要/核心内容")
    subject_id: str | None = Field(None, description="所属科目 ID")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    parent_node_id: str | None = Field(None, description="父节点 ID（用于构建层级）")

class LinkNodesParams(BaseModel):
    """关联知识节点的参数"""
    source_node_id: str = Field(..., description="源节点 ID")
    target_node_id: str = Field(..., description="目标节点 ID")
    relation_type: str = Field(..., description="关系类型: prerequisite/related/derived")

class QueryKnowledgeParams(BaseModel):
    """查询知识图谱的参数"""
    query: str = Field(..., description="搜索关键词或语义查询")
    subject_id: str | None = Field(None, description="限定科目范围")
    limit: int = Field(default=10, description="返回结果数量", ge=1, le=50)
    use_vector_search: bool = Field(default=True, description="是否使用向量语义搜索")

# ============ 查询工具参数 ============

class GetUserContextParams(BaseModel):
    """获取用户上下文的参数"""
    include_recent_tasks: bool = Field(default=True, description="是否包含近期任务")
    include_active_plans: bool = Field(default=True, description="是否包含进行中的计划")
    include_error_records: bool = Field(default=False, description="是否包含错题记录")
    days_range: int = Field(default=7, description="查询天数范围", ge=1, le=30)

# ============ 翻译工具参数 ============

class TranslateParams(BaseModel):
    """翻译参数"""
    text: str = Field(..., description="需要翻译的文本", max_length=5000)
    target_language: str = Field(..., description="目标语言", examples=["中文", "English", "日本語"])
    source_language: str = Field(default="auto", description="源语言，默认为自动检测")

# ============ 联网搜索工具参数 ============

class WebSearchRecencyFilter(str, Enum):
    """搜索时间范围"""
    ONE_DAY = "oneDay"
    ONE_WEEK = "oneWeek"
    ONE_MONTH = "oneMonth"
    ONE_YEAR = "oneYear"
    NO_LIMIT = "noLimit"

class WebSearchContentSize(str, Enum):
    """返回内容长度"""
    MEDIUM = "medium"   # 摘要信息
    HIGH = "high"       # 详细内容


# ============ P0-3: 任务查询和修改工具参数 ============

class TaskStatusFilter(str, Enum):
    """任务状态筛选"""
    ALL = "all"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class QueryPlanTasksParams(BaseModel):
    """查询计划内任务列表的参数"""
    plan_id: str = Field(..., description="计划 ID (必填)")
    status_filter: TaskStatusFilter = Field(
        default=TaskStatusFilter.ALL,
        description="任务状态筛选：all/pending/in_progress/completed/abandoned"
    )
    type_filter: TaskType | None = Field(
        default=None,
        description="任务类型筛选 (可选)"
    )
    limit: int = Field(
        default=10,
        description="返回数量限制",
        ge=1,
        le=50
    )


class ModifyPlanTaskParams(BaseModel):
    """修改计划内任务属性的参数"""
    task_id: str = Field(..., description="任务 ID (必填)")
    title: str | None = Field(None, description="新标题", max_length=100)
    status: str | None = Field(
        None,
        description="新状态: pending/in_progress/completed/abandoned"
    )
    priority: int | None = Field(
        None,
        description="新优先级 1-5，5 最高",
        ge=1,
        le=5
    )
    guide_content: str | None = Field(
        None,
        description="执行指南内容 (Markdown)"
    )


# ============ P0-4: 任务详情查询和跨计划查询参数 ============

class GetTaskDetailsParams(BaseModel):
    """获取任务完整详情的参数"""
    task_id: str = Field(..., description="任务 ID (必填)")
    include_guide: bool = Field(
        default=True,
        description="是否包含执行指南内容"
    )
    include_subtasks: bool = Field(
        default=True,
        description="是否包含子任务列表"
    )
    include_knowledge_context: bool = Field(
        default=True,
        description="是否包含关联的知识节点信息"
    )
    include_learning_resources: bool = Field(
        default=True,
        description="是否包含关联学习资源/种子库信息"
    )
    include_progress_history: bool = Field(
        default=False,
        description="是否包含任务执行历史（反馈记录等）"
    )


class QueryAllTasksParams(BaseModel):
    """跨计划查询用户所有任务的参数"""
    include_inactive_plans: bool = Field(
        default=False,
        description="是否包含非活跃计划的任务"
    )
    status_filter: TaskStatusFilter = Field(
        default=TaskStatusFilter.PENDING,
        description="任务状态筛选"
    )
    limit_per_plan: int = Field(
        default=5,
        description="每个计划返回的任务数量",
        ge=1,
        le=20
    )
    total_limit: int = Field(
        default=30,
        description="总返回数量限制",
        ge=1,
        le=100
    )


# ============ 错题工具参数 ============


class RecordErrorParams(BaseModel):
    """记录错题参数"""
    question: str = Field(..., description="题目内容", min_length=1, max_length=5000)
    wrong_answer: str | None = Field(default=None, description="错误答案", max_length=2000)
    correct_answer: str | None = Field(default=None, description="正确答案", max_length=2000)
    error_type: str | None = Field(default=None, description="错因类型")
    root_cause: str | None = Field(default=None, description="根因分析")
    subject: str = Field(default="math", description="科目编码")
    chapter: str | None = Field(default=None, description="章节")


class QueryErrorHistoryParams(BaseModel):
    """查询错题历史参数"""
    subject: str | None = Field(default=None, description="科目编码")
    error_type: str | None = Field(default=None, description="错因类型")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量")
