"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Models Package
导出所有数据库模型
"""

from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilitySlotType,
    AccountabilityStatus,
)
from app.models.accountability_policy import AccountabilityPolicy
from app.models.achievement import (
    Achievement,
    AchievementRarity,
    AchievementType,
    ContractStatus,
    GalaxySkin,
    SparkContract,
    StreakDayStatus,
    StudyBuddy,
    UserAchievement,
    UserGalaxySkin,
    UserStreakDay,
    UserStreakStats,
    UserTitle,
    VisualEffectType,
)
from app.models.analytics import UserDailyMetric
from app.models.audit_log import AdminAuditLog, ComplianceCheckLog, DataAccessLog, SecurityAuditLog, SystemConfigChangeLog
from app.models.aurora_stage20 import (
    AuroraJudgmentRecord,
    ConflictResolutionRecord,
    RoutingDecisionLog,
    UnresolvedConflict,
)
from app.models.aurora_stage21 import SharedSkill, SkillShareModerationQueue, UserSkill
from app.models.aurora_stage27 import PersDynAttractor
from app.models.aurora_stage31 import (
    DailyBehaviorVector,
    IdiographicAssociation,
    IdiographicChangepoint,
)
from app.models.auth_security import AuthAuditAction, AuthAuditLog, UserSession
from app.models.base import GUID, BaseModel
from app.models.calendar_event import CalendarEvent, EventSource
from app.models.candidate_action_feedback import CandidateActionFeedback
from app.models.capsule_favorite import CapsuleFavorite
from app.models.capsule_feedback import CapsuleFeedback, FeedbackCategory
from app.models.capsule_generation_job import CapsuleGenerationJob, GenerationType
from app.models.capsule_generation_job import JobStatus as CapsuleJobStatus
from app.models.card_protocol import (
    ArtifactStatus,
    ArtifactType,
    BindingMode,
    Card,
    CardAdoptionRecord,
    CardCreatedBy,
    CardEdge,
    CardLifecycleStatus,
    CardShareRecord,
    CardSnapshot,
    CardSourceType,
    CardType,
    CardVisibility,
    DeliveryChannel,
    DeliveryStrategy,
    EdgeType,
    ImportMode,
    InterventionAcceptanceStatus,
    InterventionOutcomeStatus,
    InterventionRecord,
    InterventionTriggerType,
    OccurrenceStatus,
    PlanningArtifact,
    SharePermission,
    ShareScope,
    TaskOccurrence,
)
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.cognitive import BehaviorPattern, CognitiveFragment
from app.models.community import (
    Friendship,
    FriendshipStatus,
    Group,
    GroupMember,
    GroupMessage,
    GroupMessageRead,
    GroupRole,
    GroupTask,
    GroupTaskClaim,
    GroupType,
    MessageType,
    Post,
    PostLike,
    PrivateMessage,
    SharedResource,
)
from app.models.community_privacy import CommunityAggregateSignal, PrivacyBudgetLedger
from app.models.community_strategy_outcome import CommunityStrategyOutcome
from app.models.compliance import (
    CryptoShreddingCertificate,
    DlqReplayAuditLog,
    LegalHold,
    PersonaSnapshot,
    UserPersonaKey,
)
from app.models.context_pack import ContextBudgetProfile, ContextPackFeedback, ContextPackRun
from app.models.curiosity_capsule import CuriosityCapsule, DepthLevel
from app.models.custom_expert import CustomExpertProfile, CustomExpertSource, CustomExpertTeam
from app.models.decision_record import DecisionRecord
from app.models.distilled_strategy_cache import DistilledStrategyCacheEntry
from app.models.document_chunks import DocumentChunk
from app.models.document_feedback import DocumentRetrievalFeedback
from app.models.error_book import ErrorRecord
from app.models.event import TrackingEvent
from app.models.event_bus_dlq import EventBusDLQEntry
from app.models.execution_audit_log import ExecutionAuditLog
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionTargetEnv,
    ExecutorType,
    TrustLevel,
)
from app.models.execution_record import ExecutionRecord
from app.models.execution_schedule import ExecutionSchedule
from app.models.experiment import (
    ABExperiment,
    ABExperimentAssignment,
    ABExperimentMetric,
    ABExperimentVariant,
    ExperimentStatus,
    MetricType,
)
from app.models.file_storage import StoredFile
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.goal import Goal
from app.models.galaxy import (
    ExpansionFeedback,
    KnowledgeNode,
    KnowledgeNodeDocument,
    NodeExpansionQueue,
    NodeRelation,
    StudyRecord,
    UserNodeStatus,
)
from app.models.group_files import GroupFile, GroupFileTrustLevel
from app.models.idempotency_key import IdempotencyKey
from app.models.intervention import (
    InterventionAuditLog,
    InterventionFeedback,
    InterventionRequest,
    UserInterventionSettings,
)
from app.models.intervention_adaptive import (
    BehavioralOutcome,
    InterventionTemplate,
    PassiveSignal,
    ScaffoldingState,
)
from app.models.intervention_strategy_outcome import InterventionStrategyOutcome
from app.models.irt import IRTItemParameter, UserIRTAbility
from app.models.job import Job, JobStatus, JobType
from app.models.ltm_daily_snapshot import LtmDailySnapshot
from app.models.memory import EpisodicMemory, MemoryCorrection, MemoryGoal, MemoryPreference
from app.models.memory_evolution import (
    EvolutionPrediction,
    MemoryEvolution,
)
from app.models.memory_rank_policy import MemoryRankPolicy
from app.models.marketplace import MarketplacePack, MarketplaceSkill, PackAdoptionHistory, UserSkillAdoption
from app.models.next_action_selection import NextActionSelection
from app.models.nightly_review import NightlyReview
from app.models.north_star_metrics import NorthStarMetricEvent
from app.models.notification import Notification, PushHistory
from app.models.notification_interaction import NotificationInteraction, NotificationPreferences
from app.models.plan import Plan, PlanStage, PlanType
from app.models.plan_execution_record import PlanExecutionRecord
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.push_delivery_record import PushDeliveryRecord
from app.models.recommendation import (
    ItemSimilarity,
    LeaderboardSnapshot,
    RecommendationCache,
    UserItemInteraction,
    UserLearningProfile,
    UserSimilarity,
)
from app.models.research_consent import ResearchConsentRecord
from app.models.report_snapshot import ReportSnapshot
from app.models.response_feedback import ResponseFeedback
from app.models.review_system import (
    ArbitrationCase,
    ArbitrationDecision,
    ReviewAppeal,
    ReviewFeedback,
    ReviewHistory,
    ReviewOverride,
)
from app.models.seed_content import (
    DifficultyLevel,
    ItemType,
    LibraryCategory,
    LibraryVisibility,
    SeedItem,
    SeedLibrary,
    UserLibrarySubscription,
)
from app.models.semantic_memory import SemanticLink, StrategyNode
from app.models.safe_experiment import SafeExperiment, SafeExperimentEpisode
from app.models.session_completion import SessionCompletion
from app.models.shop import PhotonTransactionHistory, ShopItem, ShopPurchase, UserConsumable
from app.models.simulation_run import SimulationRun
from app.models.subject import Subject
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_document import TaskDocument
from app.models.task_feedback import TaskFeedback, TaskFeedbackCategory
from app.models.task_resources import TaskKnowledgeLink, TaskResourceLink, TaskResourceType
_task_history_available = True
try:
    from app.models.task_history import TaskHistory
except ImportError:
    _task_history_available = False
    import logging
    logging.getLogger(__name__).debug("task_history model not available", exc_info=True)
    TaskHistory = None
from app.models.theater_prediction import TheaterPrediction
from app.models.tool_history import UserToolHistory
from app.models.user import PushPreference, User
from app.models.user_preferences import UserPreferencesCenter
from app.models.user_settings import UserSettings
from app.models.user_state import UserStateSnapshot
from app.models.visual_element import UserVisualConfig, UserVisualElement, VisualElement
from app.models.vocabulary import DictionaryEntry, WordBook
_workflow_conversation_available = True
try:
    from app.models.workflow_conversation import (
        ContentReview,
        ContentReviewFeedback,
        ConversationAnalysis,
        ConversationPattern,
        ConversationRoutine,
        ConversationTrace,
        ConversationTraceEvent,
        ConversationTurn,
        ConversationWorkflow,
        ConversationWorkflowEvent,
        ConversationWorkflowState,
        RegenerationRequest,
        ResponseFeedback as WorkflowResponseFeedback,
        ResponseQualityMeasure,
        WorkflowAgent,
        WorkflowCheckpoint,
    )
except ImportError:
    _workflow_conversation_available = False
    import logging
    logging.getLogger(__name__).debug("workflow_conversation model not available", exc_info=True)

__all__ = [
    # Base
    "BaseModel",
    "GUID",
    # Accountability
    "AccountabilityCheckin",
    "AccountabilityPartnership",
    "AccountabilityPolicy",
    "AccountabilitySlotType",
    "AccountabilityStatus",
    # Achievement
    "Achievement",
    "AchievementRarity",
    "AchievementType",
    "ContractStatus",
    "GalaxySkin",
    "SparkContract",
    "StreakDayStatus",
    "StudyBuddy",
    "UserAchievement",
    "UserGalaxySkin",
    "UserStreakDay",
    "UserStreakStats",
    "UserTitle",
    "VisualEffectType",
    # Analytics
    "UserDailyMetric",
    # Audit
    "AdminAuditLog",
    "ComplianceCheckLog",
    "DataAccessLog",
    "SecurityAuditLog",
    "SystemConfigChangeLog",
    # Aurora
    "AuroraJudgmentRecord",
    "ConflictResolutionRecord",
    "DailyBehaviorVector",
    "IdiographicAssociation",
    "IdiographicChangepoint",
    "PersDynAttractor",
    "RoutingDecisionLog",
    "SharedSkill",
    "SkillShareModerationQueue",
    "UnresolvedConflict",
    "UserSkill",
    # Auth
    "AuthAuditAction",
    "AuthAuditLog",
    "UserSession",
    # Calendar
    "CalendarEvent",
    "EventSource",
    # Candidate Action
    "CandidateActionFeedback",
    # Capsule
    "CapsuleFavorite",
    "CapsuleFeedback",
    "CapsuleGenerationJob",
    "CapsuleJobStatus",
    "FeedbackCategory",
    "GenerationType",
    # Card Protocol
    "ArtifactStatus",
    "ArtifactType",
    "BindingMode",
    "Card",
    "CardAdoptionRecord",
    "CardCreatedBy",
    "CardEdge",
    "CardLifecycleStatus",
    "CardShareRecord",
    "CardSnapshot",
    "CardSourceType",
    "CardType",
    "CardVisibility",
    "DeliveryChannel",
    "DeliveryStrategy",
    "EdgeType",
    "ImportMode",
    "InterventionAcceptanceStatus",
    "InterventionOutcomeStatus",
    "InterventionRecord",
    "InterventionTriggerType",
    "OccurrenceStatus",
    "PlanningArtifact",
    "SharePermission",
    "ShareScope",
    "TaskOccurrence",
    # Chat
    "ChatMessage",
    "ChatSession",
    "MessageRole",
    # Cognitive
    "BehaviorPattern",
    "CognitiveFragment",
    # Community
    "Friendship",
    "FriendshipStatus",
    "Group",
    "GroupMember",
    "GroupMessage",
    "GroupMessageRead",
    "GroupRole",
    "GroupTask",
    "GroupTaskClaim",
    "GroupType",
    "MessageType",
    "Post",
    "PostLike",
    "PrivateMessage",
    "SharedResource",
    # Community Privacy
    "CommunityAggregateSignal",
    "CommunityStrategyOutcome",
    "PrivacyBudgetLedger",
    # Compliance
    "CryptoShreddingCertificate",
    "DlqReplayAuditLog",
    "LegalHold",
    "PersonaSnapshot",
    "UserPersonaKey",
    # Context Pack
    "ContextBudgetProfile",
    "ContextPackFeedback",
    "ContextPackRun",
    # Curiosity
    "CuriosityCapsule",
    "DepthLevel",
    # Custom Expert
    "CustomExpertProfile",
    "CustomExpertSource",
    "CustomExpertTeam",
    # Decision
    "DecisionRecord",
    # Distilled Strategy
    "DistilledStrategyCacheEntry",
    # Document
    "DocumentChunk",
    "DocumentRetrievalFeedback",
    # Error Book
    "ErrorRecord",
    # Event
    "TrackingEvent",
    # Event Bus
    "EventBusDLQEntry",
    # Execution
    "ExecutionAuditLog",
    "ExecutionIntent",
    "ExecutionIntentStatus",
    "ExecutionMode",
    "ExecutionRecord",
    "ExecutionSchedule",
    "ExecutionTargetEnv",
    "ExecutorType",
    "TrustLevel",
    # Experiments
    "ABExperiment",
    "ABExperimentAssignment",
    "ABExperimentMetric",
    "ABExperimentVariant",
    "ExperimentStatus",
    "MetricType",
    # File Storage
    "StoredFile",
    # Focus
    "FocusSession",
    "FocusStatus",
    "FocusType",
    # Goal
    "Goal",
    # Galaxy
    "ExpansionFeedback",
    "KnowledgeNode",
    "KnowledgeNodeDocument",
    "NodeExpansionQueue",
    "NodeRelation",
    "StudyRecord",
    "UserNodeStatus",
    # Group Files
    "GroupFile",
    "GroupFileTrustLevel",
    # Idempotency
    "IdempotencyKey",
    # Intervention
    "InterventionAuditLog",
    "InterventionFeedback",
    "InterventionRequest",
    "UserInterventionSettings",
    # Intervention Adaptive
    "BehavioralOutcome",
    "InterventionTemplate",
    "PassiveSignal",
    "ScaffoldingState",
    # Intervention Strategy
    "InterventionStrategyOutcome",
    # IRT
    "IRTItemParameter",
    "UserIRTAbility",
    # Job
    "Job",
    "JobStatus",
    "JobType",
    # LTM
    "LtmDailySnapshot",
    # Memory
    "EpisodicMemory",
    "MemoryCorrection",
    "MemoryEvolution",
    "MemoryGoal",
    "MemoryPreference",
    "EvolutionPrediction",
    "MemoryRankPolicy",
    # Marketplace
    "MarketplacePack",
    "MarketplaceSkill",
    "PackAdoptionHistory",
    "UserSkillAdoption",
    # Next Action
    "NextActionSelection",
    # Nightly Review
    "NightlyReview",
    # North Star
    "NorthStarMetricEvent",
    # Notification
    "Notification",
    "NotificationInteraction",
    "NotificationPreferences",
    "PushHistory",
    # Plan
    "Plan",
    "PlanExecutionRecord",
    "PlanStage",
    "PlanState",
    "PlanStateStatus",
    "PlanType",
    # Push
    "PushDeliveryRecord",
    # Recommendation
    "ItemSimilarity",
    "LeaderboardSnapshot",
    "RecommendationCache",
    "UserItemInteraction",
    "UserLearningProfile",
    "UserSimilarity",
    # Research
    "ResearchConsentRecord",
    # Report
    "ReportSnapshot",
    # Response Feedback
    "ResponseFeedback",
    # Review System
    "ArbitrationCase",
    "ArbitrationDecision",
    "ReviewAppeal",
    "ReviewFeedback",
    "ReviewHistory",
    "ReviewOverride",
    # Seed Content
    "DifficultyLevel",
    "ItemType",
    "LibraryCategory",
    "LibraryVisibility",
    "SeedItem",
    "SeedLibrary",
    "UserLibrarySubscription",
    # Semantic Memory
    "SemanticLink",
    "StrategyNode",
    # Safe Experiment
    "SafeExperiment",
    "SafeExperimentEpisode",
    # Session
    "SessionCompletion",
    # Shop
    "PhotonTransactionHistory",
    "ShopItem",
    "ShopPurchase",
    "UserConsumable",
    # Simulation
    "SimulationRun",
    # Subject
    "Subject",
    # Task
    "Task",
    "TaskDocument",
    "TaskFeedback",
    "TaskFeedbackCategory",
    "TaskStatus",
    "TaskType",
    # Theater
    "TheaterPrediction",
    # Tool History
    "UserToolHistory",
    # User
    "PushPreference",
    "User",
    "UserPreferencesCenter",
    "UserSettings",
    "UserStateSnapshot",
    # Visual
    "UserVisualConfig",
    "UserVisualElement",
    "VisualElement",
    # Vocabulary
    "DictionaryEntry",
    "WordBook",
]

if _workflow_conversation_available:
    __all__.extend([
        "ContentReview",
        "ContentReviewFeedback",
        "ConversationAnalysis",
        "ConversationPattern",
        "ConversationRoutine",
        "ConversationTrace",
        "ConversationTraceEvent",
        "ConversationTurn",
        "ConversationWorkflow",
        "ConversationWorkflowEvent",
        "ConversationWorkflowState",
        "RegenerationRequest",
        "WorkflowResponseFeedback",
        "ResponseQualityMeasure",
        "WorkflowAgent",
        "WorkflowCheckpoint",
    ])

if _task_history_available:
    __all__.append("TaskHistory")
