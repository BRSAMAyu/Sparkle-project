"""
Core: execution
Phase: sense
Stage: Signal-to-Action Spine M1-Step1

7 核心数据对象 — Causal Control Pipeline 的脊柱。
每个对象必须绑定一个 P0 用户可见变化，否则不引入。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ── 1. ActionableSignal ──────────────────────────────────────────────
# 只有"可能改变行动"的事件才转 Signal。
# 用户可见变化：用户的下一步变了。

@dataclass
class ActionableSignal:
    signal_id: str
    source_event_ids: list[str]
    source_system: str          # e.g. "task_service"
    state_key: str              # e.g. "task_granularity_fit"
    claim: str                  # e.g. "recent_task_too_large"
    confidence: float
    scope: str                  # e.g. "current_sprint"
    ttl_hours: int
    evidence_summary: str
    possible_effects: list[str]
    priority: str               # "high" | "medium" | "low"
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source_event_ids": self.source_event_ids,
            "source_system": self.source_system,
            "state_key": self.state_key,
            "claim": self.claim,
            "confidence": self.confidence,
            "scope": self.scope,
            "ttl_hours": self.ttl_hours,
            "evidence_summary": self.evidence_summary,
            "possible_effects": self.possible_effects,
            "priority": self.priority,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ActionableSignal:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 2. ActionableStatePacket ──────────────────────────────────────────
# 只放影响本轮/近期控制决策的状态位。不是用户画像。

@dataclass
class StateEntry:
    state_key: str
    value: str
    confidence: float
    scope: str
    ttl_hours: int = 72
    supporting_evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    last_updated_at: str = field(default_factory=_utcnow)
    can_affect: list[str] = field(default_factory=list)
    user_visible: bool = True
    requires_confirmation_if_high_impact: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_key": self.state_key,
            "value": self.value,
            "confidence": self.confidence,
            "scope": self.scope,
            "ttl_hours": self.ttl_hours,
            "supporting_evidence": self.supporting_evidence,
            "counter_evidence": self.counter_evidence,
            "last_updated_at": self.last_updated_at,
            "can_affect": self.can_affect,
            "user_visible": self.user_visible,
            "requires_confirmation_if_high_impact": self.requires_confirmation_if_high_impact,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StateEntry:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ActionableStatePacket:
    user_id: str
    goal_frame: dict[str, Any]          # mode, subject, deadline_days, target
    top_states: list[StateEntry]
    risk_flags: list[str]
    current_bottleneck: dict[str, Any] | None = None
    next_best_action: dict[str, Any] | None = None
    updated_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "goal_frame": self.goal_frame,
            "top_states": [s.to_dict() for s in self.top_states],
            "risk_flags": self.risk_flags,
            "current_bottleneck": self.current_bottleneck,
            "next_best_action": self.next_best_action,
            "updated_at": self.updated_at,
        }


# ── 3. PolicyDecision ─────────────────────────────────────────────────
# 不是 LLM 摘要。必须输出结构化 hard_constraints / soft_biases。
# 用户可见变化：任务/计划/资料调用变了。

@dataclass
class PolicyDecision:
    policy_decision_id: str
    primary_strategy: str               # e.g. "recover_execution_rhythm"
    secondary_strategy: str | None
    hard_constraints: dict[str, Any]    # e.g. {"max_task_duration_min": 25}
    soft_biases: dict[str, Any]         # e.g. {"tone": "direct_but_reassuring"}
    visibility: str                     # "receipt" | "silent" | "log"
    requires_user_confirmation: bool
    reasoning_summary: str
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_decision_id": self.policy_decision_id,
            "primary_strategy": self.primary_strategy,
            "secondary_strategy": self.secondary_strategy,
            "hard_constraints": self.hard_constraints,
            "soft_biases": self.soft_biases,
            "visibility": self.visibility,
            "requires_user_confirmation": self.requires_user_confirmation,
            "reasoning_summary": self.reasoning_summary,
            "created_at": self.created_at,
        }


# ── 4. ExecutionDirective ──────────────────────────────────────────────
# 不是 prompt 片段。下游模块必须以结构化参数消费。
# 用户可见变化：任务参数真的变了。

@dataclass
class ExecutionDirective:
    directive_id: str
    policy_decision_id: str
    target_module: str                  # e.g. "task_generator"
    scope: str                          # "today" | "current_sprint"
    hard_constraints: dict[str, Any]
    user_visible_reason: str
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "policy_decision_id": self.policy_decision_id,
            "target_module": self.target_module,
            "scope": self.scope,
            "hard_constraints": self.hard_constraints,
            "user_visible_reason": self.user_visible_reason,
            "created_at": self.created_at,
        }


# ── 4b. ResponseDirective ────────────────────────────────────────────────
# 控制回复层的语气、长度、确认、避免项。
# 用户可见变化：回复语气和内容风格变了。

@dataclass
class ResponseDirective:
    directive_id: str
    policy_decision_id: str
    target_module: str = "response_layer"
    tone: str = "calm_direct"                 # calm_direct / calm_urgent / encouraging_diagnostic / recognition_not_praise / encouraging_low_pressure
    length: str = "medium"                    # short / medium / long
    must_acknowledge: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    include_user_options: bool = True
    scope: str = "turn"
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "policy_decision_id": self.policy_decision_id,
            "target_module": self.target_module,
            "tone": self.tone,
            "length": self.length,
            "must_acknowledge": self.must_acknowledge,
            "avoid": self.avoid,
            "include_user_options": self.include_user_options,
            "scope": self.scope,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ResponseDirective:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 4c. NotificationDirective ────────────────────────────────────────────
# 控制推送通知：是否允许、渠道、静默时间、触发条件、频率。
# 用户可见变化：收到或不收到合适的提醒。

@dataclass
class NotificationDirective:
    directive_id: str
    policy_decision_id: str
    target_module: str = "notification_service"
    allowed: bool = True
    channel: str = "push"                       # push / in_app / silent
    respect_quiet_hours: bool = True
    trigger: str = ""                           # first_task_not_started / undigested_material / pre_exam_silence / task_missed
    message_strategy: str = "low_effort_next_step"  # low_effort_next_step / recovery_offer / quick_review_offer
    max_frequency: str = "1_per_day"            # 1_per_day / 2_per_day / 1_per_sprint
    scope: str = "today"
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "policy_decision_id": self.policy_decision_id,
            "target_module": self.target_module,
            "allowed": self.allowed,
            "channel": self.channel,
            "respect_quiet_hours": self.respect_quiet_hours,
            "trigger": self.trigger,
            "message_strategy": self.message_strategy,
            "max_frequency": self.max_frequency,
            "scope": self.scope,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NotificationDirective:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 4d. PlanDirective ────────────────────────────────────────────────────
# 控制计划和重规划。
# 用户可见变化：计划不被无故推倒重来，错过的任务有恢复路径。

@dataclass
class PlanDirective:
    directive_id: str
    policy_decision_id: str
    target_module: str = "planning_service"
    plan_action: str = "local_replan"              # local_replan / full_replan / insert_task / remove_task
    scope: str = "next_48h"                        # next_48h / current_sprint / goal
    constraints: dict[str, Any] = field(default_factory=dict)  # e.g. {"do_not_rebuild_entire_plan": True}
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "policy_decision_id": self.policy_decision_id,
            "target_module": self.target_module,
            "plan_action": self.plan_action,
            "scope": self.scope,
            "constraints": self.constraints,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PlanDirective:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 4e. ModelWriteDirective ──────────────────────────────────────────────
# 控制写入哪个模型、写入多深。
# 用户可见变化：系统状态更新有审计记录，高影响写入需用户确认。

@dataclass
class ModelWriteEntry:
    target_model: str              # user_state / sparkle_self_model / cognitive_profile
    claim: str
    scope: str                     # turn / current_sprint / strategy / long_term
    confidence: float
    needs_user_confirmation: bool = False
    ttl: str = "72h"

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_model": self.target_model,
            "claim": self.claim,
            "scope": self.scope,
            "confidence": self.confidence,
            "needs_user_confirmation": self.needs_user_confirmation,
            "ttl": self.ttl,
        }


@dataclass
class ModelWriteDirective:
    directive_id: str
    policy_decision_id: str
    target_module: str = "state_aggregator"
    writes: list[ModelWriteEntry] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "policy_decision_id": self.policy_decision_id,
            "target_module": self.target_module,
            "writes": [w.to_dict() for w in self.writes],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModelWriteDirective:
        writes_data = d.get("writes", [])
        writes = [ModelWriteEntry(**{k: v for k, v in w.items() if k in ModelWriteEntry.__dataclass_fields__}) for w in writes_data]
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__ and k != "writes"}, writes=writes)


# ── 4f. UXDirective ─────────────────────────────────────────────────────
# 控制状态带、回执、预测选项、Aurora 是否显性出现。
# 用户可见变化：UI 状态带显示当前风险，回执可点击纠正。

@dataclass
class UXDirective:
    directive_id: str
    policy_decision_id: str
    target_module: str = "ux_layer"
    status_band_state: str = "normal"              # normal / risk_detected / strategy_active / milestone
    show_context_receipt: bool = True
    show_strategy_receipt: bool = False
    predicted_reply_options: list[str] = field(default_factory=list)
    allow_full_aurora_wake: bool = False
    scope: str = "turn"
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "policy_decision_id": self.policy_decision_id,
            "target_module": self.target_module,
            "status_band_state": self.status_band_state,
            "show_context_receipt": self.show_context_receipt,
            "show_strategy_receipt": self.show_strategy_receipt,
            "predicted_reply_options": self.predicted_reply_options,
            "allow_full_aurora_wake": self.allow_full_aurora_wake,
            "scope": self.scope,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UXDirective:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 5. DirectiveApplicationAudit ───────────────────────────────────────
# 不是日志装饰。验证输出是否满足 directive。
# 用户可见变化：团队/开发者能审计为什么变了。

@dataclass
class DirectiveApplicationAudit:
    audit_id: str
    directive_id: str
    target_module: str
    applied: bool
    applied_constraints: list[str]
    violations: list[dict[str, Any]]
    generated_output_id: str | None
    generated_output_summary: dict[str, Any]
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "directive_id": self.directive_id,
            "target_module": self.target_module,
            "applied": self.applied,
            "applied_constraints": self.applied_constraints,
            "violations": self.violations,
            "generated_output_id": self.generated_output_id,
            "generated_output_summary": self.generated_output_summary,
            "created_at": self.created_at,
        }


# ── 6. UserVisibleReceipt ──────────────────────────────────────────────
# 短、具体、可纠正。不是长篇解释。
# 用户可见变化：用户知道为什么变了。

@dataclass
class UserVisibleReceipt:
    receipt_id: str
    receipt_type: str                   # e.g. "strategy_adjustment"
    message: str
    actions: list[str]                  # ["confirm", "correct", "dismiss"]
    related_state_keys: list[str]
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "receipt_type": self.receipt_type,
            "message": self.message,
            "actions": self.actions,
            "related_state_keys": self.related_state_keys,
            "created_at": self.created_at,
        }


# ── 7. CausalTrace ─────────────────────────────────────────────────────
# 审计链路骨架。每个 stage 逐步填充。

@dataclass
class CausalTrace:
    trace_id: str
    raw_event_ids: list[str] = field(default_factory=list)
    signal_ids: list[str] = field(default_factory=list)
    state_keys_changed: list[str] = field(default_factory=list)
    policy_decision_id: str | None = None
    directive_ids: list[str] = field(default_factory=list)
    audit_ids: list[str] = field(default_factory=list)
    receipt_ids: list[str] = field(default_factory=list)
    outcome_to_measure: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "raw_event_ids": self.raw_event_ids,
            "signal_ids": self.signal_ids,
            "state_keys_changed": self.state_keys_changed,
            "policy_decision_id": self.policy_decision_id,
            "directive_ids": self.directive_ids,
            "audit_ids": self.audit_ids,
            "receipt_ids": self.receipt_ids,
            "outcome_to_measure": self.outcome_to_measure,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CausalTrace:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
