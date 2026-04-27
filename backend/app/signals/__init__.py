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
    AuroraAgendaItem,
    AuroraControlSignal,
    CausalTrace,
    CommunityDirective,
    DirectiveApplicationAudit,
    ExecutionDirective,
    MaterialsProtocol,
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
    StuckProtocol,
    TaskCardProtocol,
    TASK_TYPES,
    TASK_TYPE_NODE_BINDINGS,
    UserVisibleReceipt,
    UXDirective,
    WhyThisTask,
)
from app.signals.community_loops import CommunityLoopManager
from app.signals.core_session import CoreSession, CoreSessionManager
from app.signals.exam_sprint_policy import ExamSprintDirective, ExamSprintPhase, ExamSprintPolicyService
from app.signals.external_integration import (
    CalendarEvent,
    CalendarSignalBridge,
    EmailDeadlineExtractor,
    EmailDeadlineHint,
    ExternalIntegrationGateway,
    ExternalRawEvent,
    ExternalToolBridge,
    ExternalToolSignal,
    FileIntegration,
    FileReference,
    GitHubRepoBridge,
    GitHubRepoSummary,
)
from app.signals.goal_type_adapter import GOAL_TYPE_PROFILES, GoalTypeAdapter, GoalTypeProfile
from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService
from app.signals.learning_base import LearningBase, StrategyBelief
from app.signals.policy_experiments import PolicyExperiment, PolicyExperimentManager
from app.signals.privacy_community_intelligence import (
    AnonymizedCohortStat,
    PrivacyBudget,
    PrivacyPreservingCohort,
    PrivacyPreservingCommunityEngine,
)
from app.signals.recall_notification import RecallMessage, RecallNotificationBuilder
from app.signals.relationship_model import RelationshipModelService, RelationshipState
from app.signals.research_experiment_platform import (
    ExperimentConclusion,
    ExperimentVariant,
    MultivariateExperiment,
    MultivariateExperimentEngine,
    UserSegment,
)
from app.signals.safe_experiment_platform import (
    BanditActionStats,
    ExperimentDesignValidator,
    ExperimentGuardrails,
    RewardModel,
    SafeBanditController,
    SafeExperimentRegistry,
    SafePolicyExperiment,
)
from app.signals.research_grade import (
    CounterfactualEngine,
    CounterfactualResult,
    DomainPack,
    DomainPackMarketplace,
    SimulatedUserProfile,
    UserSimulator,
)
from app.signals.skill_lifecycle import SkillLifecycleManager
from app.signals.source_tray_integration import SourceEffectivenessTracker
from app.signals.spine_quality_guard import (
    QualityCheck,
    QualityReport,
    SpineQualityGuard,
)
from app.signals.task_card_protocol import TaskCardBuilder, TaskCardValidator
from app.signals.goal_world_graph import GoalWorldGraph, GoalWorldGraphService, GraphNode
from app.signals.intervention_episode import (
    AgencyOutcome,
    ContextSignature,
    EvidenceQuality,
    ExecutionOutcome,
    GoalProgressOutcome,
    InterventionEpisode,
    InterventionEpisodeLedger,
    LearningOutcome,
    LoadOutcome,
    OutcomeVector,
    SustainabilityOutcome,
    TrustOutcome,
)
from app.signals.counterfactual_evaluation import (
    CounterfactualEstimate,
    CounterfactualIronLawEnforcer,
    EvidenceGrade,
    MatchedContextEvaluator,
    MetricEffect,
    PolicyComparisonReport,
    PolicyUpdateCandidate,
    PolicyUpdateCandidateBuilder,
)
from app.signals.multi_goal_arbitration import ActiveGoal, GoalArbitrationResult, MultiGoalArbitrator
from app.signals.spine_aurora_bridge import SpineAuroraBridge

__all__ = [
    "ActionableSignal",
    "ActionableStatePacket",
    "ActiveGoal",
    "AgencyOutcome",
    "AnonymizedCohortStat",
    "AuroraAgendaItem",
    "AuroraControlSignal",
    "BanditActionStats",
    "CalendarEvent",
    "CalendarSignalBridge",
    "CausalTrace",
    "ChronicleEntry",
    "CoreSession",
    "CoreSessionManager",
    "CommunityDirective",
    "CommunityLoopManager",
    "ContextSignature",
    "CounterfactualEngine",
    "CounterfactualEstimate",
    "CounterfactualIronLawEnforcer",
    "CounterfactualResult",
    "DirectiveApplicationAudit",
    "DomainPack",
    "DomainPackMarketplace",
    "EmailDeadlineExtractor",
    "EmailDeadlineHint",
    "EvidenceGrade",
    "EvidenceQuality",
    "ExecutionDirective",
    "ExecutionOutcome",
    "ExperimentConclusion",
    "ExperimentDesignValidator",
    "ExperimentGuardrails",
    "ExperimentVariant",
    "ExternalIntegrationGateway",
    "ExternalRawEvent",
    "ExternalToolBridge",
    "ExternalToolSignal",
    "FileIntegration",
    "FileReference",
    "GitHubRepoBridge",
    "GitHubRepoSummary",
    "GOAL_TYPE_PROFILES",
    "GoalTypeAdapter",
    "GoalTypeProfile",
    "GoalProgressOutcome",
    "GoalWorldGraph",
    "GoalWorldGraphService",
    "GraphNode",
    "GrowthChronicleService",
    "InterventionEpisode",
    "InterventionEpisodeLedger",
    "LearningBase",
    "LearningOutcome",
    "LoadOutcome",
    "MatchedContextEvaluator",
    "MaterialsProtocol",
    "MetricEffect",
    "ModelWriteDirective",
    "MultivariateExperiment",
    "MultivariateExperimentEngine",
    "MultiGoalArbitrator",
    "NotificationDirective",
    "OutcomeRecord",
    "OutcomeVector",
    "PlanDirective",
    "PolicyDecision",
    "PolicyEffectEntry",
    "PolicyComparisonReport",
    "PolicyExperiment",
    "PolicyExperimentManager",
    "PolicyUpdateCandidate",
    "PolicyUpdateCandidateBuilder",
    "PrivacyBudget",
    "PrivacyPreservingCohort",
    "PrivacyPreservingCommunityEngine",
    "QualityCheck",
    "QualityReport",
    "RelationshipModelService",
    "RelationshipState",
    "ResponseDirective",
    "RetrievalDirective",
    "RewardModel",
    "RecallMessage",
    "RecallNotificationBuilder",
    "SafeBanditController",
    "SafeExperimentRegistry",
    "SafePolicyExperiment",
    "SimulatedUserProfile",
    "SkillDirective",
    "SkillEntry",
    "SkillLifecycleManager",
    "SourceEffectivenessTracker",
    "SourceAsset",
    "SourceSlice",
    "SourceTraySelection",
    "SourceTrayState",
    "SpineAuroraBridge",
    "SpineQualityGuard",
    "StateEntry",
    "StuckProtocol",
    "StrategyBelief",
    "SustainabilityOutcome",
    "TaskCardBuilder",
    "TaskCardProtocol",
    "TaskCardValidator",
    "TASK_TYPES",
    "TrustOutcome",
    "TASK_TYPE_NODE_BINDINGS",
    "UserSegment",
    "UserSimulator",
    "UserVisibleReceipt",
    "UXDirective",
    "WhyThisTask",
]
