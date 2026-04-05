from __future__ import annotations
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
from enum import Enum

# ============ Phase 4: Plan Version Constants ============

# Version conflict handling thresholds
VERSION_CONFLICT_AUTO_REPLAN_THRESHOLD = 0.7  # confidence >= this value triggers auto-replan
VERSION_CONFLICT_HITL_THRESHOLD = 0.7  # confidence < this value requires user confirmation
MAX_REPLAN_ATTEMPTS = 2  # Maximum replan attempts before giving up

# Replan rate limiting
REPLAN_RATE_LIMIT_WINDOW = 60  # seconds
REPLAN_MAX_PER_WINDOW = 3  # max replans per window

import uuid
from datetime import timezone, datetime
from typing import Any, Literal


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


@dataclass
class RouteDecision:
    """路由决策输出

    决定请求如何路由和执行
    """
    execution_mode: Literal["direct", "langgraph", "hybrid"]  # Phase 1 只有 direct
    reason: str
    risk_level: Literal["low", "medium", "high"]
    confidence: float = 0.5
    context_version: str | None = None


class OrchestratorState(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    TOOL_EXECUTION = "tool_execution"
    LLM_INFERENCE = "llm_inference"
    COMPLETED = "completed"


@dataclass
class StepCriteria:
    """Per-step success/failure criteria for DAG execution.

    Defines what constitutes success for an individual tool call step,
    enabling fine-grained validation within a plan.
    """
    expected_output_keys: list[str] = field(default_factory=list)
    max_duration_ms: int = 30000
    required: bool = True  # If False, failure does not block dependents

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_output_keys": self.expected_output_keys,
            "max_duration_ms": self.max_duration_ms,
            "required": self.required,
        }


@dataclass
class ToolCallSpec:
    """工具调用规格 v2 — with DAG support

    定义单个工具调用的详细参数和约束。

    Phase 5 additions (backward-compatible defaults):
    - depends_on: list of ToolCallSpec.id values this step waits for
    - success_criteria: per-step pass/fail criteria
    - output_key: key under which this step's result is stored for dependents
    """
    id: str
    name: str
    params: dict[str, Any]
    timeout_ms: int = 10000
    priority: Literal["high", "normal", "low"] = "normal"
    allow_retry: bool = True
    max_retries: int = 2
    point_of_no_return: bool = False
    compensation_call: dict[str, Any] | None = None
    # Phase 5: DAG edges — list of ToolCallSpec.id values this step depends on
    depends_on: list[str] = field(default_factory=list)
    # Phase 5: Per-step success criteria
    success_criteria: StepCriteria | None = None
    # Phase 5: Key under which this step's output is stored for downstream steps
    output_key: str | None = None


@dataclass
class ExecutablePlan:
    """可执行计划 v1.0 ~ v5.0

    统一的执行计划结构，包含工具调用序列和元数据

    Phase 1 (v1.0): Basic plan structure
    Phase 2 (v2.0): Added snapshot_id, enhanced fallback_strategy
    Phase 3 (v3.0): Added agents_involved, collaboration_mode, circuit_breaker_status
    Phase 4 (v4.0): Added plan_version for version conflict detection
    Phase 5 (v5.0): DAG support — execution_order layers, per-step criteria, total_steps
    """
    schema_version: str = "5.0"
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context_version: str = ""
    snapshot_id: str = ""  # Phase 2: Associated snapshot_id

    source: Literal["langgraph", "fast_path", "shadow"] = "fast_path"
    confidence: float = 0.5
    rationale: str = ""

    # Phase 3: Multi-Agent Collaboration metadata
    agents_involved: list[str] = field(default_factory=list)  # NEW
    collaboration_mode: Literal["single", "sequential", "parallel", "debate", "delegation"] = "single"  # NEW
    collaboration_order: list[dict[str, str]] = field(default_factory=list)  # NEW
    collaboration_narrative: str | None = None  # Phase 3: Collaboration narrative

    risk_flags: list[str] = field(default_factory=list)
    tool_calls: list[ToolCallSpec] = field(default_factory=list)

    fallback_strategy: dict[str, str] = field(default_factory=lambda: {
        "on_validation_fail": "abort",  # Phase 2: also supports "replan"
        "on_execution_fail": "skip",
        "on_version_conflict": "replan"  # Phase 2: version conflict handling
    })
    success_criteria: dict[str, Any] = field(default_factory=dict)

    # Phase 3: Circuit breaker metadata
    circuit_breaker_status: dict[str, str] | None = None  # NEW

    # Phase 4: PlanState version at planning time
    plan_version: int = 1  # NEW: PlanState.version when plan was created

    # Phase 5: DAG execution support
    # Topologically sorted layers: [[step_id_1, step_id_2], [step_id_3], ...]
    # Steps within a layer can execute in parallel.
    execution_order: list[list[str]] = field(default_factory=list)
    total_steps: int = 0

    # ------------------------------------------------------------------
    # DAG helpers
    # ------------------------------------------------------------------

    def get_execution_layers(self) -> list[list["ToolCallSpec"]]:
        """Return tool calls organized by execution layer.

        Steps within a layer have no mutual dependencies and can run in
        parallel.  If *execution_order* is empty the entire list is treated
        as a single sequential layer (backward compatible).
        """
        if not self.execution_order:
            return [self.tool_calls] if self.tool_calls else []
        id_map = {tc.id: tc for tc in self.tool_calls}
        return [
            [id_map[tid] for tid in layer if tid in id_map]
            for layer in self.execution_order
        ]

    def to_dict(self) -> dict[str, Any]:
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
            "collaboration_narrative": self.collaboration_narrative,
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
                    "compensation_call": tc.compensation_call,
                    "depends_on": tc.depends_on,
                    "success_criteria": tc.success_criteria.to_dict() if tc.success_criteria else None,
                    "output_key": tc.output_key,
                }
                for tc in self.tool_calls
            ],
            "fallback_strategy": self.fallback_strategy,
            "success_criteria": self.success_criteria,
            "circuit_breaker_status": self.circuit_breaker_status,
            "plan_version": self.plan_version,
            "execution_order": self.execution_order,
            "total_steps": self.total_steps,
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
    timestamp: str = field(default_factory=_utcnow_iso)
    context_versions: dict[str, str] = field(default_factory=dict)
    active_focus_id: str | None = None
    pending_tasks_count: int = 0
    user_quota_remaining: int = 0

    def to_dict(self) -> dict[str, Any]:
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
    timestamp: str = field(default_factory=_utcnow_iso)
    feedback_type: Literal["explicit", "implicit"] = "implicit"
    rating: int | None = None
    comment: str | None = None
    completion: dict[str, Any] = field(default_factory=lambda: {
        "status": "completed",
        "duration_seconds": 0,
        "attempts": 1
    })
    signals: dict[str, bool] = field(default_factory=dict)
    predictive_hints: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
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
    failure_reason: str | None = None
    risk_flags: list[str] = None
    warnings: list[dict[str, Any]] = None
    requires_confirmation: bool = False
    requires_hitl: bool = False

    def __post_init__(self):
        if self.risk_flags is None:
            self.risk_flags = []
        if self.warnings is None:
            self.warnings = []


# ============ Phase 3: Circuit Breaker ============

@dataclass
class CircuitBreakerState:
    """熔断器状态 (Phase 3)"""
    name: str
    state: Literal["closed", "open", "half_open"]  # closed=正常, open=熔断, half_open=试探
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: str | None = None
    last_state_change: str = field(default_factory=_utcnow_iso)
    opened_count: int = 0  # 累计熔断次数


# ============ Phase 3: Shadow Prediction ============

@dataclass
class ShadowPrediction:
    """影子预测结果 (Phase 3)"""
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str = ""  # 关联的计划 ID
    user_id: str = ""
    session_id: str = ""
    timestamp: str = field(default_factory=_utcnow_iso)

    # 预测内容
    predicted_mode: str = ""  # 预测的最佳执行模式
    predicted_agents: list[str] = field(default_factory=list)
    predicted_tools: list[str] = field(default_factory=list)
    confidence: float = 0.0

    # 实际结果（用于对比）
    actual_mode: str = ""
    actual_agents: list[str] = field(default_factory=list)
    actual_tools: list[str] = field(default_factory=list)

    # 预测准确性
    is_correct: bool = False
    accuracy_score: float = 0.0


# ============ Phase 3: Observability Event ============

@dataclass
class ObservabilityEvent:
    """可观测性事件 (Phase 3)"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_utcnow_iso)
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
    data: dict[str, Any] = field(default_factory=dict)


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
    related_plan_id: str | None = None
    related_task_id: str | None = None
    timestamp: str = field(default_factory=_utcnow_iso)

    # Review-specific fields
    review_id: str | None = None
    review_decision: str | None = None  # APPROVED, REJECTED, etc.
    review_comments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
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

# ============ Phase A: User Insight Engine ============

@dataclass
class CompiledInsightState:
    """Compiled runtime truth layer reconcile signals from multiple sources.

    Phase A: User Insight Engine Strengthening
    """
    stable_traits: dict[str, Any] = field(default_factory=dict)
    current_state: dict[str, Any] = field(default_factory=dict)
    active_constraints: list[dict[str, Any]] = field(default_factory=list)
    active_bottlenecks: list[dict[str, Any]] = field(default_factory=list)
    key_uncertainties: list[dict[str, Any]] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    confidence_map: dict[str, float] = field(default_factory=dict)
    freshness_map: dict[str, str] = field(default_factory=dict)
    contradiction_map: list[dict[str, Any]] = field(default_factory=list)
    planning_readiness: dict[str, Any] = field(default_factory=dict)
    recommended_clarification: list[str] = field(default_factory=list)
    version: str = "1.0"
    generated_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stable_traits": self.stable_traits,
            "current_state": self.current_state,
            "active_constraints": self.active_constraints,
            "active_bottlenecks": self.active_bottlenecks,
            "key_uncertainties": self.key_uncertainties,
            "missing_information": self.missing_information,
            "confidence_map": self.confidence_map,
            "freshness_map": self.freshness_map,
            "contradiction_map": self.contradiction_map,
            "planning_readiness": self.planning_readiness,
            "recommended_clarification": self.recommended_clarification,
            "version": self.version,
            "generated_at": self.generated_at,
        }
