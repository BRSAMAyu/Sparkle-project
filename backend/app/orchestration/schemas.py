"""
Phase 1 Schemas for Full-Loop Closed System

Defines core data structures for:
- RouteDecision: Routing decision output
- ToolCallSpec: Tool call specification
- ExecutablePlan: Unified executable plan structure
- FeedbackPayload: Feedback payload structure
- ValidationResult: Validation result from GroundingValidator
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal, Set
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
    """可执行计划 v1

    统一的执行计划结构，包含工具调用序列和元数据
    """
    schema_version: str = "1.0"
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context_version: str = ""
    source: Literal["langgraph", "fast_path"] = "fast_path"
    confidence: float = 0.5
    rationale: str = ""
    risk_flags: List[str] = field(default_factory=list)
    tool_calls: List[ToolCallSpec] = field(default_factory=list)
    fallback_strategy: Dict[str, str] = field(default_factory=lambda: {
        "on_validation_fail": "abort",
        "on_execution_fail": "skip"
    })
    success_criteria: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "context_version": self.context_version,
            "source": self.source,
            "confidence": self.confidence,
            "rationale": self.rationale,
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
            "success_criteria": self.success_criteria
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
