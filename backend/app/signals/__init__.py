"""
Core: execution
Phase: sense→clarify→plan→execute→reflect→adapt
Stage: Signal-to-Action Spine

Signal-to-Action Spine — causal control pipeline.

Pipeline: RawEvent → ActionableSignal → SignalRanker → StateRegister → PolicyDecision
          → Directive (9 types) → DirectiveApplicationAudit → UserVisibleReceipt → CausalTrace
          → OutcomeRecord

Layers:
  1. RawEvent (entry points in orchestrator + event consumers)
  2. ActionableSignal (signal detectors)
  3. SignalRanker (priority + conflict resolution)
  4. StateRegister (per-user persistent state)
  5. PolicyEngine (deterministic rule arbitration)
  6. Directives (Response / Execution / Plan / Retrieval / Notification / ModelWrite / UX / Community / Skill)
  7. DirectiveAuditor + SpineOrchestrator (actuation + audit)
  8. OutcomeRecorder (causal attribution)
"""

from app.signals.types import (
    ActionableSignal,
    ActionableStatePacket,
    CausalTrace,
    CommunityDirective,
    DirectiveApplicationAudit,
    ExecutionDirective,
    ModelWriteDirective,
    NotificationDirective,
    OutcomeRecord,
    PlanDirective,
    PolicyDecision,
    PolicyEffectEntry,
    ResponseDirective,
    RetrievalDirective,
    SkillDirective,
    SourceAsset,
    SourceSlice,
    SourceTraySelection,
    SourceTrayState,
    StateEntry,
    UserVisibleReceipt,
    UXDirective,
)
from app.signals.exam_sprint_policy import ExamSprintDirective, ExamSprintPhase, ExamSprintPolicyService

__all__ = [
    "ActionableSignal",
    "ActionableStatePacket",
    "CausalTrace",
    "CommunityDirective",
    "DirectiveApplicationAudit",
    "ExecutionDirective",
    "ModelWriteDirective",
    "NotificationDirective",
    "OutcomeRecord",
    "PlanDirective",
    "PolicyDecision",
    "PolicyEffectEntry",
    "ResponseDirective",
    "RetrievalDirective",
    "SkillDirective",
    "SourceAsset",
    "SourceSlice",
    "SourceTraySelection",
    "SourceTrayState",
    "StateEntry",
    "UserVisibleReceipt",
    "UXDirective",
]
