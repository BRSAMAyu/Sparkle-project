from typing import TypedDict, Annotated, List, Optional, Dict, Any, Union
import operator
from langchain_core.messages import BaseMessage

class PlanContext(TypedDict):
    """计划上下文 (用于多计划并行)"""
    plan_id: str
    plan_type: str  # "sprint", "routine", "long_term"
    status: str     # "drafting", "active", "completed"

class ReviewFeedback(TypedDict):
    """审查反馈 (Reviewer Agent 或 用户)"""
    source: str     # "user", "reviewer_agent"
    decision: str   # "approve", "reject", "modify"
    comments: str
    modified_plan: Optional[Dict[str, Any]]

class SparkleState(TypedDict):
    """
    Sparkle 全局状态定义 (Enhanced for Full-Link Vision)
    承载整个对话生命周期的数据
    """
    # ==========================
    # 1. 基础消息历史 (Append-only)
    # ==========================
    # 自动合并历史消息，支持 OpenAI 格式
    messages: Annotated[List[BaseMessage], operator.add]
    
    # ==========================
    # 2. 上下文信息 (Context)
    # ==========================
    user_id: str
    session_id: str
    user_profile: Optional[Dict[str, Any]] # 用户画像(年级, 强弱项)
    
    # 计划上下文 (Vision Item 12: Multi-plan state)
    current_plan: Optional[PlanContext]
    
    # 规划状态 (Vision Item 5a/8: Judge Loop & Review)
    # Values: "gathering_info", "drafting", "reviewing", "executing", "completed"
    planning_status: Optional[str]
    
    # ==========================
    # 3. 路由与控制 (Control)
    # ==========================
    # 下一步的计划/意图，由 Router 生成
    next_step: Optional[str] 
    
    # 意图详情 (Vision Item 5c/5d: Translation/Sprint details)
    intent_data: Optional[Dict[str, Any]]
    
    # 当前激活的 Agent (用于 UI 展示)
    active_agent: Optional[str]
    
    # 协作模式 (Phase 3 Collaboration)
    collaboration_mode: Optional[str]      # "single", "sequential", "parallel"
    collaboration_agents: Optional[List[str]]
    collaboration_order: Optional[List[str]]
    collaboration_index: Optional[int]
    
    # ==========================
    # 4. 审查与反馈 (Review & Feedback)
    # ==========================
    # 审查反馈 (Vision Item 8)
    review_feedback: Optional[ReviewFeedback]

    # ==========================
    # 5. 人工介入 (Human-in-the-loop)
    # ==========================
    # 是否需要人工审批敏感操作
    require_approval: bool
    # 审批上下文 (如: "即将删除 5 个任务，是否确认？")
    approval_context: Optional[str]
    # 用户的审批结果 (Approved/Rejected)
    approval_result: Optional[str]

    # ==========================
    # 6. 错误处理 (Error Handling)
    # ==========================
    error: Optional[str]
