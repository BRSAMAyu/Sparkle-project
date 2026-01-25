"""
Phase 1, Phase 2 & Phase 3 Schemas for Full-Loop Closed System

Defines core data structures for:
- RouteDecision: Routing decision output
- ToolCallSpec: Tool call specification
- ExecutablePlan: Unified executable plan structure (v1.0, v2.0, v3.0)
- StateSnapshot: State snapshot for version tracking (Phase 2)
- FeedbackPayload: Feedback payload structure
- ValidationResult: Validation result from GroundingValidator
- CircuitBreakerState: Circuit breaker state (Phase 3)
- ShadowPrediction: Shadow prediction result (Phase 3)
- ObservabilityEvent: Observability event (Phase 3)
- PlanFeedback: Plan feedback entry (Phase 4)
"""
from dataclasses import dataclass, field

# ============ Phase 4: Plan Version Constants ============

# Version conflict handling thresholds
VERSION_CONFLICT_AUTO_REPLAN_THRESHOLD = 0.7  # confidence >= this value triggers auto-replan
VERSION_CONFLICT_HITL_THRESHOLD = 0.7  # confidence < this value requires user confirmation
MAX_REPLAN_ATTEMPTS = 2  # Maximum replan attempts before giving up

# Replan rate limiting
REPLAN_RATE_LIMIT_WINDOW = 60  # seconds
REPLAN_MAX_PER_WINDOW = 3  # max replans per window

from typing import Dict, Any, List, Optional, Literal, Set, TYPE_CHECKING
from datetime import datetime
import uuid


@dataclass
class RouteDecision:
    """路由决策输出

    决定请求如何路由和执行
    """
    execution_mode: Literal["direct", "langgraph", "hybrid"]  # Phase 1 只有 direct
    reason: str
    risk_level: Literal["low", "medium", "high"]
    confidence: float = 0.5
    context_version: Optional[str] = None


@dataclass
class ToolCallSpec:
    """工具调用规格

    定义单个工具调用的详细参数和约束
    """
    id: str
    name: str
    params: Dict[str, Any]
    timeout_ms: int = 10000
    priority: Literal["high", "normal", "low"] = "normal"
    allow_retry: bool = True
    max_retries: int = 2
    point_of_no_return: bool = False
    compensation_call: Optional[Dict[str, Any]] = None


@dataclass
class ExecutablePlan:
    """可执行计划 v1.0/v2.0/v3.0/v4.0

    统一的执行计划结构，包含工具调用序列和元数据

    Phase 1 (v1.0): Basic plan structure
    Phase 2 (v2.0): Added snapshot_id, enhanced fallback_strategy
    Phase 3 (v3.0): Added agents_involved, collaboration_mode, circuit_breaker_status
    Phase 4 (v4.0): Added plan_version for version conflict detection
    """
    schema_version: str = "1.0"
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context_version: str = ""
    snapshot_id: str = ""  # Phase 2: Associated snapshot_id

    source: Literal["langgraph", "fast_path", "shadow"] = "fast_path"
    confidence: float = 0.5
    rationale: str = ""

    # Phase 3: Multi-Agent Collaboration metadata
    agents_involved: List[str] = field(default_factory=list)  # NEW
    collaboration_mode: Literal["single", "sequential", "parallel"] = "single"  # NEW
    collaboration_order: List[Dict[str, str]] = field(default_factory=list)  # NEW

    risk_flags: List[str] = field(default_factory=list)
    tool_calls: List[ToolCallSpec] = field(default_factory=list)

    fallback_strategy: Dict[str, str] = field(default_factory=lambda: {
        "on_validation_fail": "abort",  # Phase 2: also supports "replan"
        "on_execution_fail": "skip",
        "on_version_conflict": "replan"  # Phase 2: version conflict handling
    })
    success_criteria: Dict[str, Any] = field(default_factory=dict)

    # Phase 3: Circuit breaker metadata
    circuit_breaker_status: Optional[Dict[str, str]] = None  # NEW

    # Phase 4: PlanState version at planning time
    plan_version: int = 1  # NEW: PlanState.version when plan was created

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "context_version": self.context_version,
            "snapshot_id": self.snapshot_id,
            "source": self.source,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "agents_involved": self.agents_involved,
            "collaboration_mode": self.collaboration_mode,
            "collaboration_order": self.collaboration_order,
            "risk_flags": self.risk_flags,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "params": tc.params,
                    "timeout_ms": tc.timeout_ms,
                    "priority": tc.priority,
                    "allow_retry": tc.allow_retry,
                    "max_retries": tc.max_retries,
                    "point_of_no_return": tc.point_of_no_return,
                    "compensation_call": tc.compensation_call
                }
                for tc in self.tool_calls
            ],
            "fallback_strategy": self.fallback_strategy,
            "success_criteria": self.success_criteria,
            "circuit_breaker_status": self.circuit_breaker_status,
            "plan_version": self.plan_version,  # Phase 4
        }


@dataclass
class StateSnapshot:
    """State Snapshot (Phase 2)

    Captures the state at a point in time for version tracking.
    Used to detect conflicts between planning and execution.
    """
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    session_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    context_versions: Dict[str, str] = field(default_factory=dict)
    active_focus_id: Optional[str] = None
    pending_tasks_count: int = 0
    user_quota_remaining: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "snapshot_id": self.snapshot_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "context_versions": self.context_versions,
            "active_focus_id": self.active_focus_id,
            "pending_tasks_count": self.pending_tasks_count,
            "user_quota_remaining": self.user_quota_remaining
        }


@dataclass
class FeedbackPayload:
    """反馈载荷 v1

    记录执行结果和反馈信号
    """
    schema_version: str = "1.0"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    user_id: str = ""
    session_id: str = ""
    context_version: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    feedback_type: Literal["explicit", "implicit"] = "implicit"
    rating: Optional[int] = None
    comment: Optional[str] = None
    completion: Dict[str, Any] = field(default_factory=lambda: {
        "status": "completed",
        "duration_seconds": 0,
        "attempts": 1
    })
    signals: Dict[str, bool] = field(default_factory=dict)
    predictive_hints: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "context_version": self.context_version,
            "timestamp": self.timestamp,
            "feedback_type": self.feedback_type,
            "rating": self.rating,
            "comment": self.comment,
            "completion": self.completion,
            "signals": self.signals,
            "predictive_hints": self.predictive_hints
        }


@dataclass
class ValidationResult:
    """验证结果

    GroundingValidator 的输出
    """
    is_valid: bool
    failure_reason: Optional[str] = None
    risk_flags: List[str] = None
    requires_confirmation: bool = False
    requires_hitl: bool = False

    def __post_init__(self):
        if self.risk_flags is None:
            self.risk_flags = []


# ============ Phase 3: Circuit Breaker ============

@dataclass
class CircuitBreakerState:
    """熔断器状态 (Phase 3)"""
    name: str
    state: Literal["closed", "open", "half_open"]  # closed=正常, open=熔断, half_open=试探
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[str] = None
    last_state_change: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    opened_count: int = 0  # 累计熔断次数


# ============ Phase 3: Shadow Prediction ============

@dataclass
class ShadowPrediction:
    """影子预测结果 (Phase 3)"""
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str = ""  # 关联的计划 ID
    user_id: str = ""
    session_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # 预测内容
    predicted_mode: str = ""  # 预测的最佳执行模式
    predicted_agents: List[str] = field(default_factory=list)
    predicted_tools: List[str] = field(default_factory=list)
    confidence: float = 0.0

    # 实际结果（用于对比）
    actual_mode: str = ""
    actual_agents: List[str] = field(default_factory=list)
    actual_tools: List[str] = field(default_factory=list)

    # 预测准确性
    is_correct: bool = False
    accuracy_score: float = 0.0


# ============ Phase 3: Observability Event ============

@dataclass
class ObservabilityEvent:
    """可观测性事件 (Phase 3)"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: Literal[
        "route_decision", "langgraph_plan", "validation_failed",
        "circuit_state_change", "collaboration_start", "collaboration_end",
        "shadow_prediction", "tool_execution"
    ] = "route_decision"

    # 事件数据
    user_id: str = ""
    session_id: str = ""
    plan_id: str = ""

    # 事件详情
    data: Dict[str, Any] = field(default_factory=dict)


# ============ Phase 4: Plan Feedback ============

@dataclass
class PlanFeedback:
    """计划反馈条目 (Phase 4)

    用于记录审查意见和用户反馈到 PlanState.feedback_log
    """
    feedback_id: str = field(default_factory=lambda: f"fb-{uuid.uuid4().hex[:8]}")
    feedback_type: Literal["review", "user_feedback", "plan_disagree"] = "review"
    content: str = ""
    decision: Literal["accept", "reject", "supplement"] = "accept"
    priority: Literal["high", "normal"] = "normal"
    source: Literal["reviewer", "user"] = "reviewer"
    related_plan_id: Optional[str] = None
    related_task_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Review-specific fields
    review_id: Optional[str] = None
    review_decision: Optional[str] = None  # APPROVED, REJECTED, etc.
    review_comments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "feedback_type": self.feedback_type,
            "content": self.content,
            "decision": self.decision,
            "priority": self.priority,
            "source": self.source,
            "related_plan_id": self.related_plan_id,
            "related_task_id": self.related_task_id,
            "timestamp": self.timestamp,
            "review_id": self.review_id,
            "review_decision": self.review_decision,
            "review_comments": self.review_comments,
        }

    @classmethod
    def from_review_result(cls, review_result: Any) -> "PlanFeedback":
        """从 PlanReviewResult 创建 PlanFeedback

        Args:
            review_result: PlanReviewResult instance from plan_review_service

        Returns:
            PlanFeedback instance
        """
        return cls(
            feedback_type="review",
            content=f"Plan review completed: {review_result.decision}",
            decision="accept" if review_result.decision == "approved" else "supplement",
            priority="high" if review_result.decision == "rejected" else "normal",
            source="reviewer",
            related_plan_id=review_result.plan_id,
            review_id=review_result.review_id,
            review_decision=review_result.decision,
            review_comments=[c.to_dict() for c in review_result.comments],
        )
