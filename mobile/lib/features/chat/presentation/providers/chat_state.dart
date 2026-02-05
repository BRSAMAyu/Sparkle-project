import 'package:sparkle/core/models/intervention.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/widgets/content_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';

class ChatState {
  ChatState({
    this.isLoading = false,
    this.isSending = false,
    this.isLoadingMore = false,
    this.hasMoreMessages = true,
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
    this.pendingAchievementUnlock,
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
    this.dailyTokens,
    this.dailyTokenLimit,
    this.dailyCostMicroUsd,
    this.transparencyData,
    this.currentStepId,
    this.currentStepIndex,
  });

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
  final AchievementUnlockEvent? pendingAchievementUnlock;
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
  final int? dailyTokens;
  final int? dailyTokenLimit;
  final int? dailyCostMicroUsd;
  final TransparencyData? transparencyData;
  final int? currentStepId;
  final int? currentStepIndex;

  int get listItemCount =>
      messages.length +
      (isSending ? 1 : 0) +
      (aiStatus != null ? 1 : 0) +
      (isReasoningActive ? 1 : 0);

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
    AchievementUnlockEvent? pendingAchievementUnlock,
    int? lastPromptTokens,
    int? lastCompletionTokens,
    int? lastTotalTokens,
    String? currentAgentName,
    String? activeAgentType,
    List<String>? activeTools,
    int? dailyTokens,
    int? dailyTokenLimit,
    int? dailyCostMicroUsd,
    TransparencyData? transparencyData,
    int? currentStepId,
    int? currentStepIndex,
    bool clearTransparency = false,
  }) =>
      ChatState(
        isLoading: isLoading ?? this.isLoading,
        isSending: isSending ?? this.isSending,
        isLoadingMore: isLoadingMore ?? this.isLoadingMore,
        hasMoreMessages: hasMoreMessages ?? this.hasMoreMessages,
        conversationId:
            clearConversation ? null : conversationId ?? this.conversationId,
        messages: messages ?? this.messages,
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
        pendingAchievementUnlock:
            pendingAchievementUnlock ?? this.pendingAchievementUnlock,
        lastPromptTokens: lastPromptTokens ?? this.lastPromptTokens,
        lastCompletionTokens: lastCompletionTokens ?? this.lastCompletionTokens,
        lastTotalTokens: lastTotalTokens ?? this.lastTotalTokens,
        currentAgentName: currentAgentName ?? this.currentAgentName,
        activeAgentType: activeAgentType ?? this.activeAgentType,
        activeTools: activeTools ?? this.activeTools,
        dailyTokens: dailyTokens ?? this.dailyTokens,
        dailyTokenLimit: dailyTokenLimit ?? this.dailyTokenLimit,
        dailyCostMicroUsd: dailyCostMicroUsd ?? this.dailyCostMicroUsd,
        transparencyData: clearTransparency
            ? null
            : transparencyData ?? this.transparencyData,
        currentStepId: clearTransparency
            ? null
            : currentStepId ?? this.currentStepId,
        currentStepIndex: clearTransparency
            ? null
            : currentStepIndex ?? this.currentStepIndex,
      );
}
