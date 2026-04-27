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
    retract_if: list[str] = field(default_factory=list)  # conditions under which this state should be retracted

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
            "retract_if": self.retract_if,
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
    time_context: dict[str, Any] = field(default_factory=dict)
    execution_pattern: dict[str, Any] = field(default_factory=dict)
    context_recommendation: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "goal_frame": self.goal_frame,
            "top_states": [s.to_dict() for s in self.top_states],
            "risk_flags": self.risk_flags,
            "current_bottleneck": self.current_bottleneck,
            "next_best_action": self.next_best_action,
            "time_context": self.time_context,
            "execution_pattern": self.execution_pattern,
            "context_recommendation": self.context_recommendation,
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
    visibility: str                     # "receipt" | "silent" | "log" | "status_band" | "inline_hint"
    requires_user_confirmation: bool
    reasoning_summary: str
    risk_level: str = "medium"          # "critical" | "high" | "medium" | "low"
    which_directives: dict[str, bool] = field(default_factory=dict)  # which of 9 directive types to generate
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
            "risk_level": self.risk_level,
            "which_directives": self.which_directives,
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


# ── 4d2. RetrievalDirective ─────────────────────────────────────────────
# 控制资料、RAG、知识星图、社群信号如何进入上下文。
# 用户可见变化：ContextReceipt 显示用了什么/没用什么/为什么。

@dataclass
class RetrievalDirective:
    directive_id: str
    policy_decision_id: str
    target_module: str = "retrieval_service"
    retrieval_mode: str = "targeted_source_rag"   # targeted_source_rag / task_bound_graph_rag / full_rag / no_rag
    source_scope: str = "user_selected"            # user_selected / task_bound / full_library
    must_load: list[str] = field(default_factory=list)
    may_load: list[str] = field(default_factory=list)
    do_not_load: list[str] = field(default_factory=list)
    token_budget: int = 3600
    citation_required: bool = True
    pollution_guard: str = "strict"                # strict / permissive / off
    scope: str = "turn"
    reason_for_user: str = ""
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "policy_decision_id": self.policy_decision_id,
            "target_module": self.target_module,
            "retrieval_mode": self.retrieval_mode,
            "source_scope": self.source_scope,
            "must_load": self.must_load,
            "may_load": self.may_load,
            "do_not_load": self.do_not_load,
            "token_budget": self.token_budget,
            "citation_required": self.citation_required,
            "pollution_guard": self.pollution_guard,
            "scope": self.scope,
            "reason_for_user": self.reason_for_user,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RetrievalDirective:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

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
# D3 Ruling: 三层写入。不能只写 Redis。
#   Hot  = Redis / StateRegister — turn/session/task/day 短期状态
#   Warm = PostgreSQL — goal/sprint/strategy/source/skill/policy effect
#   Cold = GrowthChronicle / LearningBase — 用户确认过的长期洞察
#
# 写入规则：
#   turn/session/task/day → Redis with TTL
#   goal/sprint → Postgres + valid_until
#   relationship → Postgres + decay
#   long_term → 必须是 candidate，用户确认后才正式进入
#   community_signal → aggregate-only，不写个人长期模型

_VALID_WRITE_TARGETS = frozenset({
    "state_register", "goal_state", "sparkle_self_model",
    "learning_base", "growth_chronicle_candidate",
})

_VALID_WRITE_SCOPES = frozenset({
    "turn", "session", "task", "day", "sprint",
    "goal", "domain", "relationship", "long_term",
})

# Map scope → write layer
_SCOPE_TO_LAYER = {
    "turn": "hot",
    "session": "hot",
    "task": "hot",
    "day": "hot",
    "sprint": "warm",
    "goal": "warm",
    "domain": "warm",
    "relationship": "warm",
    "long_term": "cold",
}


@dataclass
class ModelWriteEntry:
    target: str = ""               # state_register / goal_state / sparkle_self_model / learning_base / growth_chronicle_candidate
    scope: str = "session"         # turn / session / task / day / sprint / goal / domain / relationship / long_term
    claim: str = ""
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    requires_user_confirmation: bool = False
    retract_if: list[str] = field(default_factory=list)
    ttl: str = "72h"               # e.g. "24h", "7d", "30d"

    # Backwards compat — old callers pass target_model instead of target
    target_model: str = ""
    needs_user_confirmation: bool = False

    def __post_init__(self):
        # Backwards compat: if target_model is set but target is not, derive
        if self.target_model and not self.target:
            self.target = self.target_model
        if not self.target_model and self.target:
            self.target_model = self.target
        if self.needs_user_confirmation and not self.requires_user_confirmation:
            self.requires_user_confirmation = self.needs_user_confirmation

    @property
    def write_layer(self) -> str:
        """D3: Determine write layer (hot/warm/cold) from scope."""
        return _SCOPE_TO_LAYER.get(self.scope, "warm")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "scope": self.scope,
            "claim": self.claim,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "counter_evidence": self.counter_evidence,
            "requires_user_confirmation": self.requires_user_confirmation,
            "retract_if": self.retract_if,
            "ttl": self.ttl,
            "write_layer": self.write_layer,
            # Backwards compat
            "target_model": self.target_model or self.target,
            "needs_user_confirmation": self.requires_user_confirmation,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModelWriteEntry:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


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
        writes = [ModelWriteEntry.from_dict(w) for w in d.get("writes", [])]
        kwargs = {k: v for k, v in d.items() if k in cls.__dataclass_fields__ and k != "writes"}
        return cls(writes=writes, **kwargs)


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


# ── 4g. CommunityDirective ──────────────────────────────────────────────
# 控制社群信号如何进入个人上下文（匿名化、频率、优先级）。
# 用户可见变化：用户看到匿名同学的经验，但不暴露个人隐私。

@dataclass
class CommunityDirective:
    directive_id: str
    policy_decision_id: str
    target_module: str = "community_service"
    cohort_hint_shown: bool = False        # 是否展示同伴错因提示
    resource_quality_filter: float = 0.5   # 最低推荐质量分
    peer_context_mode: str = "anonymous"   # anonymous / identified / off
    max_frequency: str = "3_per_week"      # 3_per_week / 1_per_day / 1_per_sprint
    scope: str = "current_sprint"
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "policy_decision_id": self.policy_decision_id,
            "target_module": self.target_module,
            "cohort_hint_shown": self.cohort_hint_shown,
            "resource_quality_filter": self.resource_quality_filter,
            "peer_context_mode": self.peer_context_mode,
            "max_frequency": self.max_frequency,
            "scope": self.scope,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CommunityDirective:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 4h. SkillDirective ──────────────────────────────────────────────────
# 控制技能系统何时注入/提取/推荐技能。
# 用户可见变化：用户看到可复用的学习策略建议。

@dataclass
class SkillDirective:
    directive_id: str
    policy_decision_id: str
    target_module: str = "skill_service"
    skill_action: str = "none"             # none / inject / extract / recommend
    skill_scope: str = "current_sprint"    # current_sprint / goal / subject
    relevant_skill_ids: list[str] = field(default_factory=list)
    extraction_trigger: str = ""           # explicit_phrase / feedback_opt_in / outcome_positive
    scope: str = "turn"
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "policy_decision_id": self.policy_decision_id,
            "target_module": self.target_module,
            "skill_action": self.skill_action,
            "skill_scope": self.skill_scope,
            "relevant_skill_ids": self.relevant_skill_ids,
            "extraction_trigger": self.extraction_trigger,
            "scope": self.scope,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SkillDirective:
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


# ── 8. OutcomeRecord ────────────────────────────────────────────────────
# 记录干预的实际结果，用于因果归因。
# 用户可见变化：系统知道自己的干预有没有用。

@dataclass
class OutcomeRecord:
    outcome_id: str
    causal_trace_id: str
    intervention: str                   # e.g. "max_task_duration_25min"
    reason: str                         # e.g. "recent_task_overrun"
    expected_outcome: str               # e.g. "task_started_and_completed"
    actual_outcome: dict[str, Any]      # e.g. {"started": true, "completed": false, "time_spent_min": 12}
    attribution: str = "inconclusive"   # effective / insufficient / inconclusive
    attribution_confidence: float = 0.0
    new_hypothesis: str | None = None
    next_policy_suggestion: str | None = None
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "causal_trace_id": self.causal_trace_id,
            "intervention": self.intervention,
            "reason": self.reason,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "attribution": self.attribution,
            "attribution_confidence": self.attribution_confidence,
            "new_hypothesis": self.new_hypothesis,
            "next_policy_suggestion": self.next_policy_suggestion,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OutcomeRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 9. PolicyEffectLedger ────────────────────────────────────────────────
# 记录策略执行效果，用于 PolicyEngine 影子模式规则偏置。
# 不是直接改规则，而是记录+查询+影响下一次决策。

@dataclass
class PolicyEffectEntry:
    entry_id: str
    policy_key: str                          # e.g. "recover_execution_rhythm"
    intervention_summary: str                # e.g. "max_task_duration_min=25, avoid_new_chapter"
    attribution: str                         # effective / insufficient / inconclusive
    attribution_confidence: float
    user_feedback_signal: str | None = None  # "看不懂" / "too_short" / "completed" / None
    new_hypothesis: str | None = None
    scope: str = "current_sprint"
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "policy_key": self.policy_key,
            "intervention_summary": self.intervention_summary,
            "attribution": self.attribution,
            "attribution_confidence": self.attribution_confidence,
            "user_feedback_signal": self.user_feedback_signal,
            "new_hypothesis": self.new_hypothesis,
            "scope": self.scope,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PolicyEffectEntry:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 10. SourceAsset / SourceSlice / Source Tray ────────────────────────
# Adapter-first: wraps DocumentChunk with structured metadata for the Spine.
# Does NOT replace DocumentChunk — these are lightweight wrappers for context routing.

@dataclass
class SourceSlice:
    """A structured slice of a source document, mapped to knowledge nodes."""
    slice_id: str
    source_id: str
    location: str                     # e.g. "p32-p45", "chap3.sec2"
    summary: str
    concepts: list[str]
    knowledge_nodes: list[str]        # Galaxy node IDs
    evidence_type: str = "definition_and_example"  # definition/worked_example/exercise/explanation
    noise_risk: str = "low"           # low/medium/high

    def to_dict(self) -> dict[str, Any]:
        return {
            "slice_id": self.slice_id,
            "source_id": self.source_id,
            "location": self.location,
            "summary": self.summary,
            "concepts": self.concepts,
            "knowledge_nodes": self.knowledge_nodes,
            "evidence_type": self.evidence_type,
            "noise_risk": self.noise_risk,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceSlice:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SourceAsset:
    """A source document with structured metadata for the Spine."""
    source_id: str
    title: str
    source_type: str                  # slides/textbook/notes/exam_paper/homework
    course: str = ""
    goal_id: str = ""
    owner: str = "user"               # user / community / system
    visibility: str = "private"       # private / cohort / public
    parsed_status: str = "parsed"     # pending / parsed / failed
    quality_score: float = 1.0        # 0.0 - 1.0
    mapped_nodes: list[str] | None = None
    slices: list[SourceSlice] | None = None
    recommended_uses: list[str] | None = None
    not_recommended_uses: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "source_id": self.source_id,
            "title": self.title,
            "source_type": self.source_type,
            "course": self.course,
            "goal_id": self.goal_id,
            "owner": self.owner,
            "visibility": self.visibility,
            "parsed_status": self.parsed_status,
            "quality_score": self.quality_score,
        }
        if self.mapped_nodes is not None:
            d["mapped_nodes"] = self.mapped_nodes
        if self.slices is not None:
            d["slices"] = [s.to_dict() for s in self.slices]
        if self.recommended_uses is not None:
            d["recommended_uses"] = self.recommended_uses
        if self.not_recommended_uses is not None:
            d["not_recommended_uses"] = self.not_recommended_uses
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceAsset:
        slices = None
        if "slices" in d and d["slices"] is not None:
            slices = [SourceSlice.from_dict(s) for s in d["slices"]]
        return cls(
            **{k: v for k, v in d.items() if k in cls.__dataclass_fields__ and k != "slices"},
            slices=slices,
        )

    def relevance_for_nodes(self, target_nodes: list[str]) -> float:
        """Compute relevance score for a set of target knowledge nodes."""
        if not self.mapped_nodes or not target_nodes:
            return 0.0
        overlap = len(set(self.mapped_nodes) & set(target_nodes))
        return overlap / max(len(target_nodes), 1)


@dataclass
class SourceTraySelection:
    """A user's material selection with scope binding."""
    source_id: str
    action: str                       # include / exclude / auto
    scope: str = "this_task"          # this_turn / this_task / today / this_goal
    user_initiated: bool = True       # True = user explicitly chose; False = system default

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "action": self.action,
            "scope": self.scope,
            "user_initiated": self.user_initiated,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceTraySelection:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SourceTrayState:
    """Current state of the user's source tray — what's included, excluded, and why."""
    mode: str = "auto"                # auto / manual_only / no_materials
    selections: list[SourceTraySelection] | None = None
    available_sources: list[SourceAsset] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "selections": [s.to_dict() for s in (self.selections or [])],
            "available_sources": [s.to_dict() for s in (self.available_sources or [])],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceTrayState:
        selections = None
        if "selections" in d and d["selections"] is not None:
            selections = [SourceTraySelection.from_dict(s) for s in d["selections"]]
        sources = None
        if "available_sources" in d and d["available_sources"] is not None:
            sources = [SourceAsset.from_dict(s) for s in d["available_sources"]]
        return cls(
            mode=d.get("mode", "auto"),
            selections=selections,
            available_sources=sources,
        )

    def get_included_source_ids(self) -> list[str]:
        """Get source IDs that are explicitly included."""
        return [s.source_id for s in (self.selections or []) if s.action == "include"]

    def get_excluded_source_ids(self) -> list[str]:
        """Get source IDs that are explicitly excluded."""
        return [s.source_id for s in (self.selections or []) if s.action == "exclude"]


# ── 11. SkillEntry — extracted strategy asset ──────────────────────────
# Created when a policy strategy proves effective repeatedly.

@dataclass
class SkillEntry:
    """A strategy that has been proven effective and extracted for reuse."""
    skill_id: str
    scope: str                           # personal / cohort / system
    source_policy_key: str               # The policy that was proven effective
    strategy: dict[str, Any]             # The effective strategy parameters
    applicable_when: dict[str, Any]      # Conditions under which this skill applies
    evidence: dict[str, Any]             # Effectiveness metrics
    privacy: dict[str, bool] | None = None  # contains_personal_data / shareable
    effective_count: int = 0
    sample_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "skill_id": self.skill_id,
            "scope": self.scope,
            "source_policy_key": self.source_policy_key,
            "strategy": self.strategy,
            "applicable_when": self.applicable_when,
            "evidence": self.evidence,
            "effective_count": self.effective_count,
            "sample_size": self.sample_size,
        }
        if self.privacy is not None:
            d["privacy"] = self.privacy
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SkillEntry:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 12. AuroraControlSignal — Layer 6 envelope ────────────────────────
# Final Spec Section 6: Aurora outputs a control envelope wrapping all directives.

@dataclass
class AuroraControlSignal:
    """总控 envelope — Aurora 的结构化输出，不是自然语言 prompt。"""
    control_id: str
    energy: str                              # "light" | "medium" | "full"
    policy_decision_id: str
    response_policy: str                     # e.g. "task_recovery_support"
    directive_ids: dict[str, str]            # directive_type → directive_id
    risk_level: str = "medium"               # from PolicyDecision
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "energy": self.energy,
            "policy_decision_id": self.policy_decision_id,
            "response_policy": self.response_policy,
            "directive_ids": self.directive_ids,
            "risk_level": self.risk_level,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AuroraControlSignal:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 13. AuroraAgenda — multi-message session management ────────────────
# Final Spec Section 9: Aurora Core Session needs structured agenda management.

@dataclass
class AuroraAgendaItem:
    """Single agenda item in an Aurora Core Session."""
    item_id: str
    item_type: str               # explain_conflict | confirm_available_time | update_strategy |
                                  # confirm_hypothesis | relationship_check | motivation_check
    status: str                  # pending | in_progress | waiting_user | done | interrupted
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "status": self.status,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AuroraAgendaItem:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AuroraAgenda:
    """Aurora Core Session agenda — tracks what Aurora needs to accomplish."""
    session_id: str
    scope: str                                    # Human-readable scope description
    agenda_items: list[AuroraAgendaItem] = field(default_factory=list)
    interruption_policy: str = "answer_then_resume"  # answer_then_resume | defer
    status: str = "active"                         # active | paused | completed | abandoned
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "scope": self.scope,
            "agenda_items": [item.to_dict() for item in self.agenda_items],
            "interruption_policy": self.interruption_policy,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AuroraAgenda:
        items = [AuroraAgendaItem.from_dict(i) for i in d.get("agenda_items", [])]
        return cls(
            session_id=d["session_id"],
            scope=d["scope"],
            agenda_items=items,
            interruption_policy=d.get("interruption_policy", "answer_then_resume"),
            status=d.get("status", "active"),
            created_at=d.get("created_at", ""),
        )

    def current_item(self) -> AuroraAgendaItem | None:
        """Return the first non-done agenda item."""
        return next((i for i in self.agenda_items if i.status not in ("done", "interrupted")), None)

    def advance(self, item_id: str, new_status: str) -> None:
        """Update an agenda item's status."""
        for item in self.agenda_items:
            if item.item_id == item_id:
                item.status = new_status
                return


# ── P3-5: Generalized Task Protocol ──────────────────────────────────────────

TASK_TYPES = frozenset({
    "study",               # Learn new material (most common for exam sprint)
    "practice",            # Practice problems / drills
    "artifact_build",      # Create a tangible output (code, doc, design)
    "habit_action",        # Perform a habit/routine action
    "review",              # Review previously learned material
    "feedback_collection", # Gather feedback from external sources
})

TASK_TYPE_NODE_BINDINGS: dict[str, list[str]] = {
    "study":               ["knowledge", "capability"],
    "practice":            ["capability", "knowledge"],
    "artifact_build":      ["artifact", "milestone"],
    "habit_action":        ["habit"],
    "review":              ["knowledge", "capability", "feedback"],
    "feedback_collection": ["feedback", "relationship"],
}


@dataclass
class WhyThisTask:
    """Explains why this task exists — audit trail for task generation decisions."""
    signal_ids: list[str] = field(default_factory=list)
    policy_decision_id: str | None = None
    bottleneck_node_id: str | None = None
    reasoning_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_ids": self.signal_ids,
            "policy_decision_id": self.policy_decision_id,
            "bottleneck_node_id": self.bottleneck_node_id,
            "reasoning_summary": self.reasoning_summary,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WhyThisTask:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class MaterialsProtocol:
    """How materials should be used for this task."""
    retrieval_mode: str = "task_bound_graph_rag"  # task_bound_graph_rag | user_pinned | none
    must_load_node_ids: list[str] = field(default_factory=list)
    may_load_node_ids: list[str] = field(default_factory=list)
    source_tray_selection: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval_mode": self.retrieval_mode,
            "must_load_node_ids": self.must_load_node_ids,
            "may_load_node_ids": self.may_load_node_ids,
            "source_tray_selection": self.source_tray_selection,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MaterialsProtocol:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class StuckProtocol:
    """What to do when the user is stuck on this task."""
    escalation_after_min: int = 15
    hint_strategy: str = "worked_example"  # worked_example | simplify | skip | ask_peer
    fallback_task_type: str | None = None
    aurora_wake_on_stuck: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "escalation_after_min": self.escalation_after_min,
            "hint_strategy": self.hint_strategy,
            "fallback_task_type": self.fallback_task_type,
            "aurora_wake_on_stuck": self.aurora_wake_on_stuck,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StuckProtocol:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class TaskCardProtocol:
    """P3-5 Generalized Task Card — binds tasks to GoalWorldGraph nodes.

    No longer assumes all tasks are knowledge-learning. Supports 6 task types
    across exam, job search, project, fitness, and general goal domains.
    """
    task_id: str = ""
    goal_id: str = ""
    bound_nodes: list[str] = field(default_factory=list)  # GoalWorldGraph node IDs
    task_type: str = "study"                              # One of TASK_TYPES
    why_this_task: WhyThisTask = field(default_factory=WhyThisTask)
    materials_protocol: MaterialsProtocol = field(default_factory=MaterialsProtocol)
    steps: list[str] = field(default_factory=list)
    stuck_protocol: StuckProtocol = field(default_factory=StuckProtocol)
    success_criteria: list[str] = field(default_factory=list)
    minimum_output: str = ""
    updates_after_completion: list[str] = field(default_factory=list)  # State keys to update
    fallback_if_failed: list[str] = field(default_factory=list)        # Alternative task IDs

    def __post_init__(self):
        if self.task_type not in TASK_TYPES:
            raise ValueError(f"task_type must be one of {TASK_TYPES}, got {self.task_type}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal_id": self.goal_id,
            "bound_nodes": self.bound_nodes,
            "task_type": self.task_type,
            "why_this_task": self.why_this_task.to_dict(),
            "materials_protocol": self.materials_protocol.to_dict(),
            "steps": self.steps,
            "stuck_protocol": self.stuck_protocol.to_dict(),
            "success_criteria": self.success_criteria,
            "minimum_output": self.minimum_output,
            "updates_after_completion": self.updates_after_completion,
            "fallback_if_failed": self.fallback_if_failed,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TaskCardProtocol:
        return cls(
            task_id=d.get("task_id", ""),
            goal_id=d.get("goal_id", ""),
            bound_nodes=d.get("bound_nodes", []),
            task_type=d.get("task_type", "study"),
            why_this_task=WhyThisTask.from_dict(d.get("why_this_task", {})),
            materials_protocol=MaterialsProtocol.from_dict(d.get("materials_protocol", {})),
            steps=d.get("steps", []),
            stuck_protocol=StuckProtocol.from_dict(d.get("stuck_protocol", {})),
            success_criteria=d.get("success_criteria", []),
            minimum_output=d.get("minimum_output", ""),
            updates_after_completion=d.get("updates_after_completion", []),
            fallback_if_failed=d.get("fallback_if_failed", []),
        )

    def is_knowledge_task(self) -> bool:
        return self.task_type in ("study", "practice")

    def is_artifact_task(self) -> bool:
        return self.task_type == "artifact_build"

    def is_habit_task(self) -> bool:
        return self.task_type == "habit_action"

    def binds_to_node_type(self, node_type: str) -> bool:
        allowed = TASK_TYPE_NODE_BINDINGS.get(self.task_type, [])
        return node_type in allowed
