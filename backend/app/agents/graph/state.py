import operator
from enum import Enum
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


# P1 Fix #6: Add Enum types for status fields
class PlanningStatus(str, Enum):
    """Planning status values (Vision Item 5a/8: Judge Loop & Review)"""
    GATHERING_INFO = "gathering_info"
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    EXECUTING = "executing"
    COMPLETED = "completed"


class PlanStatus(str, Enum):
    """Plan status values"""
    DRAFTING = "drafting"
    ACTIVE = "active"
    COMPLETED = "completed"


class ReviewDecisionType(str, Enum):
    """Review decision types"""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class ReviewFeedbackSource(str, Enum):
    """Review feedback source types"""
    USER = "user"
    REVIEWER_AGENT = "reviewer_agent"


# ============================================
# Review System Enums (Phase 1: 全流程审查系统)
# ============================================

class ReviewStatus(str, Enum):
    """审查状态 (Review Status)"""
    PENDING = "pending"           # 等待审查
    IN_PROGRESS = "in_progress"   # 审查中
    PASSED = "passed"             # 通过审查
    FAILED = "failed"             # 未通过审查
    REFLECTING = "reflecting"     # 自我反思修正中
    SKIPPED = "skipped"           # 跳过审查（轻量级模式）


class ReviewTargetType(str, Enum):
    """审查目标类型"""
    LLM_RESPONSE = "llm_response"  # LLM生成的响应
    PLAN = "plan"                  # 执行计划
    TOOL_RESULT = "tool_result"    # 工具执行结果
    COLLABORATION = "collaboration"  # 协作结果


class PlanContext(TypedDict, total=False):
    """计划上下文 (用于多计划并行)"""
    plan_id: str
    plan_type: str  # "sprint", "routine", "long_term"
    status: PlanStatus  # Now typed with Enum


class ReviewFeedback(TypedDict, total=False):
    """审查反馈 (Reviewer Agent 或 用户)"""
    source: ReviewFeedbackSource  # Now typed with Enum
    decision: ReviewDecisionType  # Now typed with Enum
    comments: str
    modified_plan: dict[str, Any] | None


class ReviewContext(TypedDict, total=False):
    """审查上下文 (Review Context) - Phase 1 全流程审查系统"""
    review_id: str                          # 审查ID
    status: ReviewStatus                    # 审查状态
    target_type: ReviewTargetType           # 目标类型
    result: dict[str, Any] | None        # 审查结果 (ReviewResult.to_dict())
    reflection_round: int                   # 反思修正轮次
    reviewer_model: str                     # 审查使用的模型
    original_content: str | None         # 原始内容（用于反思修正）
    reviewed_content: str | None         # 审查后的内容


class ReviewHistoryEntry(TypedDict, total=False):
    """审查历史条目 - 用于学习和优化"""
    review_id: str                          # 审查ID
    timestamp: str                          # 审查时间
    target_type: ReviewTargetType           # 目标类型
    decision: str                           # 审查决策
    overall_score: float                    # 总体评分
    issues_count: int                       # 问题数量
    user_satisfied: bool | None          # 用户是否满意（用于学习）


class SparkleState(TypedDict):
    """
    Sparkle 全局状态定义 (Enhanced for Full-Link Vision)
    承载整个对话生命周期的数据
    """
    # ==========================
    # 1. 基础消息历史 (Append-only)
    # ==========================
    # 自动合并历史消息，支持 OpenAI 格式
    messages: Annotated[list[BaseMessage], operator.add]

    # ==========================
    # 2. 上下文信息 (Context)
    # ==========================
    user_id: str
    session_id: str
    user_profile: dict[str, Any] | None # 用户画像(年级, 强弱项)

    # 计划上下文 (Vision Item 12: Multi-plan state)
    current_plan: PlanContext | None

    # 规划状态 (Vision Item 5a/8: Judge Loop & Review)
    # Values: "gathering_info", "drafting", "reviewing", "executing", "completed"
    planning_status: str | None

    # ==========================
    # 3. 路由与控制 (Control)
    # ==========================
    # 下一步的计划/意图，由 Router 生成
    next_step: str | None

    # 意图详情 (Vision Item 5c/5d: Translation/Sprint details)
    intent_data: dict[str, Any] | None

    # 当前激活的 Agent (用于 UI 展示)
    active_agent: str | None

    # 协作模式 (Phase 3 Collaboration)
    collaboration_mode: str | None      # "single", "sequential", "parallel"
    collaboration_agents: list[str] | None
    collaboration_order: list[str] | None
    collaboration_index: int | None

    # ==========================
    # 4. 审查与反馈 (Review & Feedback)
    # ==========================
    # 审查反馈 (Vision Item 8)
    review_feedback: ReviewFeedback | None

    # ==========================
    # 5. 人工介入 (Human-in-the-loop)
    # ==========================
    # 是否需要人工审批敏感操作
    require_approval: bool
    # 审批上下文 (如: "即将删除 5 个任务，是否确认？")
    approval_context: str | None
    # 用户的审批结果 (Approved/Rejected)
    approval_result: str | None

    # ==========================
    # 6. 错误处理 (Error Handling)
    # ==========================
    error: str | None

    # ==========================
    # 7. 审查系统 (Review System) - Phase 1 全流程审查
    # ==========================
    # 当前审查上下文
    review_context: ReviewContext | None

    # 审查历史（用于学习和优化）
    review_history: Annotated[list[ReviewHistoryEntry], operator.add]

    # 是否启用深度审查（可由用户或系统动态控制）
    enable_deep_review: bool

    # 审查配置
    review_config: dict[str, Any] | None  # 如：thresholds, skip_patterns等
