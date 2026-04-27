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
    SkillEntry,
    SourceAsset,
    SourceSlice,
    SourceTraySelection,
    SourceTrayState,
    StateEntry,
    UserVisibleReceipt,
    UXDirective,
)
from app.signals.community_loops import CommunityLoopManager
from app.signals.core_session import CoreSession, CoreSessionManager
from app.signals.exam_sprint_policy import ExamSprintDirective, ExamSprintPhase, ExamSprintPolicyService
from app.signals.goal_type_adapter import GOAL_TYPE_PROFILES, GoalTypeAdapter, GoalTypeProfile
from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService
from app.signals.learning_base import LearningBase, StrategyBelief
from app.signals.policy_experiments import PolicyExperiment, PolicyExperimentManager
from app.signals.recall_notification import RecallMessage, RecallNotificationBuilder
from app.signals.relationship_model import RelationshipModelService, RelationshipState
from app.signals.research_grade import (
    CounterfactualEngine,
    CounterfactualResult,
    DomainPack,
    DomainPackMarketplace,
    SimulatedUserProfile,
    UserSimulator,
)
from app.signals.skill_lifecycle import SkillLifecycleManager

__all__ = [
    "ActionableSignal",
    "ActionableStatePacket",
    "CausalTrace",
    "ChronicleEntry",
    "CoreSession",
    "CoreSessionManager",
    "CommunityDirective",
    "CommunityLoopManager",
    "CounterfactualEngine",
    "CounterfactualResult",
    "DirectiveApplicationAudit",
    "DomainPack",
    "DomainPackMarketplace",
    "ExecutionDirective",
    "GOAL_TYPE_PROFILES",
    "GoalTypeAdapter",
    "GoalTypeProfile",
    "LearningBase",
    "ModelWriteDirective",
    "NotificationDirective",
    "OutcomeRecord",
    "PlanDirective",
    "PolicyDecision",
    "PolicyEffectEntry",
    "PolicyExperiment",
    "PolicyExperimentManager",
    "RelationshipModelService",
    "RelationshipState",
    "ResponseDirective",
    "RetrievalDirective",
    "RecallMessage",
    "RecallNotificationBuilder",
    "SimulatedUserProfile",
    "SkillDirective",
    "SkillEntry",
    "SkillLifecycleManager",
    "SourceAsset",
    "SourceSlice",
    "SourceTraySelection",
    "SourceTrayState",
    "StateEntry",
    "StrategyBelief",
    "UserSimulator",
    "UserVisibleReceipt",
    "UXDirective",
    "GrowthChronicleService",
]
