import 'package:sparkle/core/models/intervention.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/widgets/content_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';

enum ChatRunPhase {
  idle,
  sending,
  streaming,
  finalizing,
  completed,
  cancelled,
  failed,
}

enum DocumentContextMode {
  auto,
  userSelected,
  taskScope,
  goalScope,
  off,
}

extension ChatRunPhaseX on ChatRunPhase {
  bool get isActive =>
      this == ChatRunPhase.sending ||
      this == ChatRunPhase.streaming ||
      this == ChatRunPhase.finalizing;

  bool get isTerminal =>
      this == ChatRunPhase.completed ||
      this == ChatRunPhase.cancelled ||
      this == ChatRunPhase.failed;
}

class ActiveRunSummary {
  const ActiveRunSummary({
    this.status,
    this.details,
    this.agentName,
    this.toolCount = 0,
    this.currentStepIndex,
    this.totalSteps,
    this.startedAtEpochMs,
  });

  final String? status;
  final String? details;
  final String? agentName;
  final int toolCount;
  final int? currentStepIndex;
  final int? totalSteps;
  final int? startedAtEpochMs;

  ActiveRunSummary copyWith({
    String? status,
    String? details,
    String? agentName,
    int? toolCount,
    int? currentStepIndex,
    int? totalSteps,
    int? startedAtEpochMs,
  }) =>
      ActiveRunSummary(
        status: status ?? this.status,
        details: details ?? this.details,
        agentName: agentName ?? this.agentName,
        toolCount: toolCount ?? this.toolCount,
        currentStepIndex: currentStepIndex ?? this.currentStepIndex,
        totalSteps: totalSteps ?? this.totalSteps,
        startedAtEpochMs: startedAtEpochMs ?? this.startedAtEpochMs,
      );
}

class TransparencyPresentationState {
  const TransparencyPresentationState({
    this.isExpanded = false,
    this.isDismissed = false,
    this.lastCompletedLabel,
  });

  final bool isExpanded;
  final bool isDismissed;
  final String? lastCompletedLabel;

  TransparencyPresentationState copyWith({
    bool? isExpanded,
    bool? isDismissed,
    String? lastCompletedLabel,
    bool clearLastCompletedLabel = false,
  }) =>
      TransparencyPresentationState(
        isExpanded: isExpanded ?? this.isExpanded,
        isDismissed: isDismissed ?? this.isDismissed,
        lastCompletedLabel: clearLastCompletedLabel
            ? null
            : lastCompletedLabel ?? this.lastCompletedLabel,
      );
}

class ChatState {
  ChatState({
    this.isLoading = false,
    this.isSending = false,
    this.isLoadingMore = false,
    this.hasMoreMessages = false,
    this.conversationId,
    this.messages = const [],
    this.error,
    this.errorCode,
    this.isErrorRetryable = false,
    this.streamingContent = '',
    this.aiStatus,
    this.aiStatusDetails,
    this.wsConnectionState = WsConnectionState.disconnected,
    this.graphragTrace,
    this.reasoningSteps = const [],
    this.isReasoningActive = false,
    this.reasoningStartTime,
    this.lastActionStatus,
    this.lastActionMessage,
    this.attachedFiles = const [],
    this.pendingPlanReview,
    this.pendingReviewActionId,
    this.pendingContentReview,
    this.pendingInterventions = const [],
    this.lastPromptTokens,
    this.lastCompletionTokens,
    this.lastTotalTokens,
    this.currentAgentName,
    this.activeAgentType,
    this.activeTools = const [],
    this.agentActivities = const [],
    this.routingPreview,
    this.roundtableTurns = const [],
    this.dailyTokens,
    this.dailyTokenLimit,
    this.dailyCostMicroUsd,
    this.transparencyData,
    this.runLedgerSummary,
    this.currentStepId,
    this.currentStepIndex,
    this.dagExecutionSignal,
    this.documentRetrievalEnabled = true,
    this.documentContextMode = DocumentContextMode.auto,
    this.activeRunId,
    this.runPhase = ChatRunPhase.idle,
    this.activeRunSummary,
    this.transparencyPresentationState = const TransparencyPresentationState(),
    this.dualCoreMode,
    this.pendingStaleCard,
    this.pendingSpineReceipt,
    this.pendingCommunityHint,
    this.pendingUXWarning,
    this.pendingGoalArbitration,
  });

  static const int maxRetainedMessages = 500;

  final bool isLoading;
  final bool isSending;
  final bool isLoadingMore;
  final bool hasMoreMessages;
  final String? conversationId;
  final List<ChatMessageModel> messages;
  final String? error;
  final String? errorCode;
  final bool isErrorRetryable;
  final String streamingContent;
  final String? aiStatus;
  final String? aiStatusDetails;
  final WsConnectionState wsConnectionState;
  final GraphRAGTrace? graphragTrace;
  final List<ReasoningStep> reasoningSteps;
  final bool isReasoningActive;
  final int? reasoningStartTime;
  final String? lastActionStatus;
  final String? lastActionMessage;
  final List<StoredFile> attachedFiles;
  final PlanReviewResult? pendingPlanReview;
  final String? pendingReviewActionId;
  final ContentReviewResult? pendingContentReview;
  final List<InterventionPushMessage> pendingInterventions;
  final int? lastPromptTokens;
  final int? lastCompletionTokens;
  final int? lastTotalTokens;
  final String? currentAgentName;
  final String? activeAgentType;
  final List<String> activeTools;
  final List<AgentActivityEvent> agentActivities;
  final Map<String, dynamic>? routingPreview;
  final List<Map<String, dynamic>> roundtableTurns;
  final int? dailyTokens;
  final int? dailyTokenLimit;
  final int? dailyCostMicroUsd;
  final TransparencyData? transparencyData;
  final RunLedgerSummary? runLedgerSummary;
  final int? currentStepId;
  final int? currentStepIndex;
  final DagExecutionSignal? dagExecutionSignal;
  final bool documentRetrievalEnabled;
  final DocumentContextMode documentContextMode;
  final String? activeRunId;
  final ChatRunPhase runPhase;
  final ActiveRunSummary? activeRunSummary;
  final TransparencyPresentationState transparencyPresentationState;

  /// Current dual-core routing mode: "execution" | "cognitive" | "balanced"
  /// Set from backend ux_turn.dual_core_mode on each AgentTurnEvent.
  final String? dualCoreMode;

  /// Spine: pending Time-Aware Recovery Card from StaleStateGuard.
  final StaleRecoveryEvent? pendingStaleCard;

  /// Spine: pending UserVisibleReceipt card from orchestrator.
  final SpineReceiptEvent? pendingSpineReceipt;

  /// Spine: pending community hint card — divine moment #6 "社群经验转策略".
  final CommunityHintEvent? pendingCommunityHint;

  /// Spine: pending UX risk warning card — divine moment #5 "阻止低收益".
  final UXWarningEvent? pendingUXWarning;

  /// Spine: pending multi-goal arbitration card — surfaces when ≥2 goals conflict.
  final GoalArbitrationEvent? pendingGoalArbitration;

  static List<ChatMessageModel> _boundedMessages(
    List<ChatMessageModel> messages,
  ) {
    if (messages.length <= maxRetainedMessages) {
      return messages;
    }
    return List<ChatMessageModel>.unmodifiable(
      messages.sublist(messages.length - maxRetainedMessages),
    );
  }

  bool get hasActiveRun => activeRunId != null && runPhase.isActive;
  bool get shouldShowStatusIndicator => hasActiveRun && aiStatus != null;
  bool get shouldShowReasoningIndicator => hasActiveRun && isReasoningActive;
  bool get shouldShowStreamingBubble => hasActiveRun && isSending;

  int get listItemCount =>
      messages.length +
      (shouldShowStreamingBubble ? 1 : 0) +
      (shouldShowStatusIndicator ? 1 : 0) +
      (shouldShowReasoningIndicator ? 1 : 0);

  ChatState copyWith({
    bool? isLoading,
    bool? isSending,
    bool? isLoadingMore,
    bool? hasMoreMessages,
    String? conversationId,
    bool clearConversation = false,
    List<ChatMessageModel>? messages,
    String? error,
    String? errorCode,
    bool? isErrorRetryable,
    bool clearError = false,
    String? streamingContent,
    String? aiStatus,
    bool clearAiStatus = false,
    String? aiStatusDetails,
    WsConnectionState? wsConnectionState,
    GraphRAGTrace? graphragTrace,
    bool clearGraphragTrace = false,
    List<ReasoningStep>? reasoningSteps,
    bool? isReasoningActive,
    int? reasoningStartTime,
    bool clearReasoning = false,
    String? lastActionStatus,
    String? lastActionMessage,
    bool clearActionFeedback = false,
    List<StoredFile>? attachedFiles,
    bool clearAttachments = false,
    PlanReviewResult? pendingPlanReview,
    bool clearPendingReview = false,
    String? pendingReviewActionId,
    ContentReviewResult? pendingContentReview,
    bool clearPendingContentReview = false,
    List<InterventionPushMessage>? pendingInterventions,
    int? lastPromptTokens,
    int? lastCompletionTokens,
    int? lastTotalTokens,
    String? currentAgentName,
    String? activeAgentType,
    List<String>? activeTools,
    List<AgentActivityEvent>? agentActivities,
    Map<String, dynamic>? routingPreview,
    List<Map<String, dynamic>>? roundtableTurns,
    int? dailyTokens,
    int? dailyTokenLimit,
    int? dailyCostMicroUsd,
    TransparencyData? transparencyData,
    RunLedgerSummary? runLedgerSummary,
    int? currentStepId,
    int? currentStepIndex,
    bool clearTransparency = false,
    DagExecutionSignal? dagExecutionSignal,
    bool clearDagExecution = false,
    bool? documentRetrievalEnabled,
    DocumentContextMode? documentContextMode,
    String? activeRunId,
    bool clearActiveRunId = false,
    ChatRunPhase? runPhase,
    ActiveRunSummary? activeRunSummary,
    bool clearActiveRunSummary = false,
    TransparencyPresentationState? transparencyPresentationState,
    bool clearRoundtable = false,
    String? dualCoreMode,
    bool clearDualCoreMode = false,
    StaleRecoveryEvent? pendingStaleCard,
    bool clearStaleCard = false,
    SpineReceiptEvent? pendingSpineReceipt,
    bool clearSpineReceipt = false,
    CommunityHintEvent? pendingCommunityHint,
    bool clearCommunityHint = false,
    UXWarningEvent? pendingUXWarning,
    bool clearUXWarning = false,
    GoalArbitrationEvent? pendingGoalArbitration,
    bool clearGoalArbitration = false,
  }) =>
      ChatState(
        isLoading: isLoading ?? this.isLoading,
        isSending: isSending ?? this.isSending,
        isLoadingMore: isLoadingMore ?? this.isLoadingMore,
        hasMoreMessages: hasMoreMessages ?? this.hasMoreMessages,
        conversationId:
            clearConversation ? null : conversationId ?? this.conversationId,
        messages: _boundedMessages(messages ?? this.messages),
        error: clearError ? null : error ?? this.error,
        errorCode: clearError ? null : errorCode ?? this.errorCode,
        isErrorRetryable:
            clearError ? false : isErrorRetryable ?? this.isErrorRetryable,
        streamingContent: streamingContent ?? this.streamingContent,
        aiStatus: clearAiStatus ? null : aiStatus ?? this.aiStatus,
        aiStatusDetails:
            clearAiStatus ? null : aiStatusDetails ?? this.aiStatusDetails,
        wsConnectionState: wsConnectionState ?? this.wsConnectionState,
        graphragTrace:
            clearGraphragTrace ? null : graphragTrace ?? this.graphragTrace,
        reasoningSteps:
            clearReasoning ? [] : reasoningSteps ?? this.reasoningSteps,
        isReasoningActive: clearReasoning
            ? false
            : isReasoningActive ?? this.isReasoningActive,
        reasoningStartTime: clearReasoning
            ? null
            : reasoningStartTime ?? this.reasoningStartTime,
        lastActionStatus: clearActionFeedback
            ? null
            : lastActionStatus ?? this.lastActionStatus,
        lastActionMessage: clearActionFeedback
            ? null
            : lastActionMessage ?? this.lastActionMessage,
        attachedFiles:
            clearAttachments ? [] : attachedFiles ?? this.attachedFiles,
        pendingPlanReview: clearPendingReview
            ? null
            : pendingPlanReview ?? this.pendingPlanReview,
        pendingReviewActionId: clearPendingReview
            ? null
            : pendingReviewActionId ?? this.pendingReviewActionId,
        pendingContentReview: clearPendingContentReview
            ? null
            : pendingContentReview ?? this.pendingContentReview,
        pendingInterventions: pendingInterventions ?? this.pendingInterventions,
        lastPromptTokens: lastPromptTokens ?? this.lastPromptTokens,
        lastCompletionTokens: lastCompletionTokens ?? this.lastCompletionTokens,
        lastTotalTokens: lastTotalTokens ?? this.lastTotalTokens,
        currentAgentName: currentAgentName ?? this.currentAgentName,
        activeAgentType: activeAgentType ?? this.activeAgentType,
        activeTools: activeTools ?? this.activeTools,
        agentActivities: agentActivities ?? this.agentActivities,
        routingPreview:
            clearRoundtable ? null : routingPreview ?? this.routingPreview,
        roundtableTurns:
            clearRoundtable ? [] : roundtableTurns ?? this.roundtableTurns,
        dailyTokens: dailyTokens ?? this.dailyTokens,
        dailyTokenLimit: dailyTokenLimit ?? this.dailyTokenLimit,
        dailyCostMicroUsd: dailyCostMicroUsd ?? this.dailyCostMicroUsd,
        transparencyData: clearTransparency
            ? null
            : transparencyData ?? this.transparencyData,
        runLedgerSummary: clearTransparency
            ? null
            : runLedgerSummary ?? this.runLedgerSummary,
        currentStepId:
            clearTransparency ? null : currentStepId ?? this.currentStepId,
        currentStepIndex: clearTransparency
            ? null
            : currentStepIndex ?? this.currentStepIndex,
        dagExecutionSignal: clearDagExecution
            ? null
            : dagExecutionSignal ?? this.dagExecutionSignal,
        documentRetrievalEnabled:
            documentRetrievalEnabled ?? this.documentRetrievalEnabled,
        documentContextMode:
            documentContextMode ?? this.documentContextMode,
        activeRunId: clearActiveRunId ? null : activeRunId ?? this.activeRunId,
        runPhase: runPhase ?? this.runPhase,
        activeRunSummary: clearActiveRunSummary
            ? null
            : activeRunSummary ?? this.activeRunSummary,
        transparencyPresentationState:
            transparencyPresentationState ?? this.transparencyPresentationState,
        dualCoreMode:
            clearDualCoreMode ? null : dualCoreMode ?? this.dualCoreMode,
        pendingStaleCard:
            clearStaleCard ? null : pendingStaleCard ?? this.pendingStaleCard,
        pendingSpineReceipt: clearSpineReceipt
            ? null
            : pendingSpineReceipt ?? this.pendingSpineReceipt,
        pendingCommunityHint: clearCommunityHint
            ? null
            : pendingCommunityHint ?? this.pendingCommunityHint,
        pendingUXWarning: clearUXWarning
            ? null
            : pendingUXWarning ?? this.pendingUXWarning,
        pendingGoalArbitration: clearGoalArbitration
            ? null
            : pendingGoalArbitration ?? this.pendingGoalArbitration,
      );
}
