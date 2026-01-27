import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/plan_review_grpc_service.dart';
import 'package:sparkle/features/chat/data/services/review_grpc_service.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/agent_session_provider.dart';
import 'package:sparkle/features/chat/data/services/agent_session_store.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/content_review_card.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';

// 1. ChatState Class
class ChatState {
  // Timestamp for duration calculation

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
    this.lastPromptTokens,
    this.lastCompletionTokens,
    this.lastTotalTokens,
    this.currentAgentName,
    this.activeAgentType,
    this.activeTools = const [],
    this.dailyTokens,
    this.dailyTokenLimit,
    this.dailyCostMicroUsd,
    // Transparency fields
    this.transparencyData,
    this.currentStepId,
    this.currentStepIndex,
  });
  final bool isLoading;
  final bool isSending;
  final bool isLoadingMore; // 加载更多历史消息
  final bool hasMoreMessages; // 是否还有更多消息
  final String? conversationId;
  final List<ChatMessageModel> messages;
  final String? error;
  final String? errorCode; // 错误代码
  final bool isErrorRetryable; // 错误是否可重试
  final String streamingContent;
  final String? aiStatus; // THINKING, GENERATING, etc.
  final String? aiStatusDetails;
  final WsConnectionState wsConnectionState; // WebSocket 连接状态
  final GraphRAGTrace? graphragTrace; // 🔥 必杀技 A: GraphRAG 追踪信息

  // New: Chain of Thought Visualization
  final List<ReasoningStep> reasoningSteps; // Real-time reasoning steps
  final bool isReasoningActive; // Currently showing reasoning
  final int? reasoningStartTime;

  // New: Action status feedback for UI
  final String? lastActionStatus;
  final String? lastActionMessage;
  final List<StoredFile> attachedFiles;

  // Achievement Unlock state
  final AchievementUnlockEvent? pendingAchievementUnlock;

  // Plan Review state
  final PlanReviewResult? pendingPlanReview;
  final String? pendingReviewActionId;

  // Content Review state (Phase 2b)
  final ContentReviewResult? pendingContentReview;
  final int? lastPromptTokens;
  final int? lastCompletionTokens;
  final int? lastTotalTokens;
  final String? currentAgentName;
  final String? activeAgentType;
  final List<String> activeTools;
  final int? dailyTokens;
  final int? dailyTokenLimit;
  final int? dailyCostMicroUsd;

  // Transparency fields
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
    // Transparency fields
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
        pendingPlanReview:
            clearPendingReview ? null : pendingPlanReview ?? this.pendingPlanReview,
        pendingReviewActionId:
            clearPendingReview ? null : pendingReviewActionId ?? this.pendingReviewActionId,
        pendingContentReview: clearPendingContentReview
            ? null
            : pendingContentReview ?? this.pendingContentReview,
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

// 2. ChatNotifier Class
class ChatNotifier extends StateNotifier<ChatState> {
  ChatNotifier(this._chatRepository, this._ref) : super(ChatState()) {
    if (DemoDataService.isDemoMode) {
      // Load demo history
      state = state.copyWith(
          messages: DemoDataService().demoChatHistory,
          conversationId: 'demo_conv_1',);
    }

    // 监听 WebSocket 连接状态
    _connectionStateSubscription =
        _chatRepository.connectionStateStream.listen((connectionState) {
      if (_isDisposed) return;
      state = state.copyWith(wsConnectionState: connectionState);
    });
  }
  final ChatRepository _chatRepository;
  final Ref _ref;
  StreamSubscription<WsConnectionState>? _connectionStateSubscription;
  final _Debouncer _streamDebouncer =
      _Debouncer(const Duration(milliseconds: 50));
  bool _isDisposed = false;
  static const String _dailyUsageDateKey = 'chat_daily_usage_date';
  static const String _dailyUsageTokensKey = 'chat_daily_usage_tokens';
  static const String _dailyUsageCostKey = 'chat_daily_usage_cost_micro_usd';
  static const int _dailyTokenLimitDefault = 50000;

  // Plan review service (lazy initialized)
  PlanReviewGrpcService? _planReviewService;

  // Review service (lazy initialized)
  ReviewGrpcService? _reviewService;

  /// Submit plan review decision via gRPC
  Future<bool> submitPlanReview({
    required ReviewDecision decision,
    String? userComment,
    Map<String, String>? meta,
  }) async {
    final review = state.pendingPlanReview;
    if (review == null) {
      debugPrint('⚠️ No pending plan review to submit');
      return false;
    }

    // Get current user
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '请先登录',
      );
      return false;
    }

    // Get access token
    final authRepository = _ref.read(authRepositoryProvider);
    final authToken = await authRepository.getAccessToken();

    try {
      _planReviewService ??= PlanReviewGrpcService();

      // Map ReviewDecision to UserReviewDecision
      final grpcDecision = _mapReviewDecision(decision);

      final result = await _planReviewService!.submitReview(
        userId: user.id,
        planId: review.planId,
        reviewId: review.reviewId,
        decision: grpcDecision,
        userComment: userComment,
        authToken: authToken,
        meta: meta,
      );

      if (result.success) {
        // Update state with success message
        state = state.copyWith(
          lastActionStatus: 'submitted',
          lastActionMessage: result.message ?? _getSuccessMessageKey(decision),
          clearPendingReview: true,
        );

        // Clear feedback message after delay
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) {
            state = state.copyWith(clearActionFeedback: true);
          }
        });

        debugPrint('✅ Plan review submitted: ${decision.name}');
        return true;
      } else {
        // Update state with error message
        state = state.copyWith(
          lastActionStatus: 'error',
          lastActionMessage: result.message ?? 'submit_failed',
        );
        debugPrint('❌ Plan review failed: ${result.message}');
        return false;
      }
    } catch (e) {
      debugPrint('❌ Plan review error: $e');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: 'network_error_retry',
      );
      return false;
    }
  }

  /// Map ReviewDecision from UI to UserReviewDecision for gRPC
  UserReviewDecision _mapReviewDecision(ReviewDecision decision) {
    switch (decision) {
      case ReviewDecision.approved:
        return UserReviewDecision.approve;
      case ReviewDecision.rejected:
        return UserReviewDecision.reject;
      case ReviewDecision.needsModification:
        return UserReviewDecision.modify;
      case ReviewDecision.requiresConfirmation:
        return UserReviewDecision.acknowledge;
    }
  }

  /// Get user-friendly success message key (to be localized by UI)
  String _getSuccessMessageKey(ReviewDecision decision) {
    switch (decision) {
      case ReviewDecision.approved:
        return 'review_approved';
      case ReviewDecision.rejected:
        return 'review_rejected';
      case ReviewDecision.needsModification:
        return 'review_modification_requested';
      case ReviewDecision.requiresConfirmation:
        return 'review_confirmed';
    }
  }

  /// 手动触发重连
  Future<void> reconnect() async {
    await _chatRepository.reconnect();
  }

  @override
  void dispose() {
    _isDisposed = true;
    unawaited(_connectionStateSubscription?.cancel());
    _streamDebouncer.cancel();
    _chatRepository.dispose();
    super.dispose();
  }

  bool _shouldIncludeSystemUpdate(Map<String, dynamic> data) {
    final level = _ref.read(systemUpdateLevelProvider);
    if (level <= 0) {
      return false;
    }
    if (level == 1) {
      final priority = data['priority']?.toString().toLowerCase() ?? 'low';
      return priority != 'low';
    }
    return true;
  }

  Future<void> _updateDailyUsage(UsageEvent event) async {
    final prefs = await SharedPreferences.getInstance();
    final today = _dateKey(DateTime.now());
    final storedDate = prefs.getString(_dailyUsageDateKey);

    var totalTokens = prefs.getInt(_dailyUsageTokensKey) ?? 0;
    var totalCost = prefs.getInt(_dailyUsageCostKey) ?? 0;

    if (storedDate != today) {
      totalTokens = 0;
      totalCost = 0;
      await prefs.setString(_dailyUsageDateKey, today);
    }

    totalTokens += event.totalTokens;
    if (event.costMicroUsd != null) {
      totalCost += event.costMicroUsd!;
      await prefs.setInt(_dailyUsageCostKey, totalCost);
    }
    await prefs.setInt(_dailyUsageTokensKey, totalTokens);

    state = state.copyWith(
      dailyTokens: totalTokens,
      dailyTokenLimit: _dailyTokenLimitDefault,
      dailyCostMicroUsd: totalCost,
    );
  }

  String _dateKey(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  /// 加载历史对话
  Future<void> loadConversationHistory(String conversationId) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final history =
          await _chatRepository.getConversationHistory(conversationId);
      state = state.copyWith(
        isLoading: false,
        messages: history,
        conversationId: conversationId,
      );
    } catch (e) {
      final errorMessage = ErrorMessages.getUserFriendlyMessage(
        'UNKNOWN',
        '加载历史失败: $e',
      );

      state = state.copyWith(
        isLoading: false,
        error: errorMessage,
        errorCode: 'UNKNOWN',
        isErrorRetryable: true,
      );
    }
  }

  void addAttachment(StoredFile file) {
    if (state.attachedFiles.any((item) => item.id == file.id)) {
      return;
    }
    state = state.copyWith(attachedFiles: [...state.attachedFiles, file]);
  }

  void removeAttachment(String fileId) {
    state = state.copyWith(
      attachedFiles:
          state.attachedFiles.where((file) => file.id != fileId).toList(),
    );
  }

  void clearAttachments() {
    state = state.copyWith(clearAttachments: true);
  }

  /// 获取最近对话列表
  Future<List<Map<String, dynamic>>> getRecentConversations() async =>
      _chatRepository.getRecentConversations();

  /// 加载更多历史消息（分页）
  Future<void> loadMoreHistory() async {
    // 如果没有对话 ID 或正在加载或没有更多消息，则不加载
    if (state.conversationId == null ||
        state.isLoadingMore ||
        !state.hasMoreMessages) {
      return;
    }

    state = state.copyWith(isLoadingMore: true);

    try {
      const pageSize = 20;
      final currentCount = state.messages.length;

      final moreMessages = await _chatRepository.getConversationHistory(
        state.conversationId!,
        limit: pageSize,
        offset: currentCount,
      );

      // 如果返回的消息少于 pageSize，说明没有更多消息了
      final hasMore = moreMessages.length >= pageSize;

      state = state.copyWith(
        isLoadingMore: false,
        messages: [...state.messages, ...moreMessages],
        hasMoreMessages: hasMore,
      );
    } catch (e) {
      final errorMessage = ErrorMessages.getUserFriendlyMessage(
        'UNKNOWN',
        '加载更多消息失败: $e',
      );

      state = state.copyWith(
        isLoadingMore: false,
        error: errorMessage,
        errorCode: 'UNKNOWN',
        isErrorRetryable: true,
      );
    }
  }

  /// 发送消息 (使用 SSE/WebSocket 流式响应)
  Future<void> sendMessage(String content, {String? taskId}) async {
    // 获取当前用户信息
    final authState = _ref.read(authProvider);
    final user = authState.user;

    // 如果未登录，使用持久化的访客 ID
    String userId;
    String nickname;
    if (user != null) {
      userId = user.id;
      nickname = (user.nickname != null && user.nickname!.isNotEmpty)
          ? user.nickname!
          : user.username;
    } else {
      final guestService = _ref.read(guestServiceProvider);
      userId = await guestService.getGuestId();
      nickname = guestService.getGuestNickname();
    }

    // 1. 立即添加用户消息到 UI
    final userMessage = ChatMessageModel(
      id: 'temp_user_${DateTime.now().millisecondsSinceEpoch}',
      userId: userId,
      conversationId: state.conversationId ?? 'temp_conversation',
      role: MessageRole.user,
      content: content,
      taskId: taskId,
      createdAt: DateTime.now(),
    );

    state = state.copyWith(
      messages: [...state.messages, userMessage],
      isSending: true,
      streamingContent: '',
      activeTools: const [],
      clearError: true,
    );

      var accumulatedContent = '';
      String? responseId;
      String? traceId;
      String? workflowId;
      String? promptVersion;
    String? lastAiStatus;
    final accumulatedWidgets = <WidgetPayload>[];
    final accumulatedReasoningSteps = <ReasoningStep>[];
    int? reasoningStartTime;
    String? pendingStreamingContent;
    String? pendingAiStatus;
    String? pendingAiStatusDetails;
    List<ReasoningStep>? pendingReasoningSteps;
    bool? pendingReasoningActive;
    int? pendingReasoningStartTime;
    var planContextInjected = false;

    void flushPending({bool immediate = false}) {
      void applyPending() {
        if (_isDisposed) return;
        if (pendingStreamingContent == null &&
            pendingAiStatus == null &&
            pendingAiStatusDetails == null &&
            pendingReasoningSteps == null &&
            pendingReasoningActive == null &&
            pendingReasoningStartTime == null) {
          return;
        }
        state = state.copyWith(
          streamingContent: pendingStreamingContent,
          aiStatus: pendingAiStatus,
          aiStatusDetails: pendingAiStatusDetails,
          reasoningSteps: pendingReasoningSteps,
          isReasoningActive: pendingReasoningActive,
          reasoningStartTime: pendingReasoningStartTime,
        );
        pendingStreamingContent = null;
        pendingAiStatus = null;
        pendingAiStatusDetails = null;
        pendingReasoningSteps = null;
        pendingReasoningActive = null;
        pendingReasoningStartTime = null;
      }

      if (immediate) {
        _streamDebouncer.flush(applyPending);
      } else {
        _streamDebouncer.run(applyPending);
      }
    }

    try {
      final token = await _ref.read(authRepositoryProvider).getAccessToken();
      final fileIds = state.attachedFiles.map((file) => file.id).toList();
      state = state.copyWith(clearAttachments: true);

      // Get selected plan for chat context
      final selectedPlanId = _ref.read(activePlanProvider);
      final extraContext = selectedPlanId != null
          ? {'plan_id': selectedPlanId}
          : null;

      // Get selected chat mode
      final chatMode = _ref.read(chatModeProvider);
      final chatModeValue = chatMode.apiValue;

      await for (final event in _chatRepository.chatStream(
        content,
        state.conversationId,
        userId: userId,
        nickname: nickname,
        token: token,
        fileIds: fileIds,
        includeReferences: fileIds.isNotEmpty,
        extraContext: extraContext,
        chatMode: chatModeValue,
      )) {
        if (event.responseId != null && event.responseId!.isNotEmpty) {
          responseId = event.responseId;
        }
        if (event.traceId != null && event.traceId!.isNotEmpty) {
          traceId = event.traceId;
        }
        if (event.workflowId != null && event.workflowId!.isNotEmpty) {
          workflowId = event.workflowId;
        }
        if (event.promptVersion != null && event.promptVersion!.isNotEmpty) {
          promptVersion = event.promptVersion;
        }

        if (event is TextEvent) {
          final metadata = event.metadata;
          final planContext = metadata?['plan_context'];
          final showPlanContext = metadata?['show_plan_context'] == true;
          if (!planContextInjected &&
              (planContext is Map<String, dynamic> || showPlanContext)) {
            final data = planContext is Map<String, dynamic>
                ? planContext
                : {
                    if (metadata?['plan_id'] is String)
                      'plan_id': metadata?['plan_id'],
                  };
            if (data.isNotEmpty) {
              accumulatedWidgets.add(
                WidgetPayload(
                  type: 'plan_context_summary',
                  data: data,
                ),
              );
              planContextInjected = true;
            }
          }
          // 流式文本片段（delta）
          accumulatedContent += event.content;
          pendingStreamingContent = accumulatedContent;
          flushPending();
        } else if (event is StatusUpdateEvent) {
          // AI 状态更新（THINKING, GENERATING 等）
          lastAiStatus = event.state;
          pendingAiStatus = event.state;
          pendingAiStatusDetails = event.details;
          state = state.copyWith(
            currentAgentName: event.currentAgentName,
            activeAgentType: event.activeAgentType,
          );
          flushPending();
        } else if (event is FullTextEvent) {
          // 完整文本（通常在流结束时）
          accumulatedContent = event.content;
          pendingStreamingContent = accumulatedContent;
          flushPending(immediate: true);
        } else if (event is ErrorEvent) {
          // 错误事件 - 使用用户友好的错误消息
          _streamDebouncer.cancel();
          final userFriendlyMessage = ErrorMessages.getUserFriendlyMessage(
            event.code,
            event.message,
          );
          final isRetryable = ErrorMessages.isRetryable(event.code);

          state = state.copyWith(
            error: userFriendlyMessage,
            errorCode: event.code,
            isErrorRetryable: isRetryable,
            isSending: false,
            streamingContent: '',
            clearAiStatus: true,
            clearReasoning: true,
          );
          return; // 提前退出
        } else if (event is WidgetEvent) {
          if (event.widgetType == 'system_update' &&
              !_shouldIncludeSystemUpdate(event.widgetData)) {
            continue;
          }
          accumulatedWidgets.add(
            WidgetPayload(
              type: event.widgetType,
              data: event.widgetData,
            ),
          );
        } else if (event is ToolStartEvent) {
          // 显示"正在使用工具: xxx"
          lastAiStatus = 'EXECUTING_TOOL';
          pendingAiStatus = 'EXECUTING_TOOL';
          pendingAiStatusDetails = '正在使用 ${event.toolName}...';
          final nextTools = List<String>.from(state.activeTools);
          if (!nextTools.contains(event.toolName)) {
            nextTools.add(event.toolName);
          }
          state = state.copyWith(activeTools: nextTools);
          flushPending();
        } else if (event is ToolResultEvent) {
          final widgetType = event.result.widgetType;
          final widgetData = event.result.widgetData;
          final toolName = event.result.toolName;
          if (toolName.isNotEmpty) {
            final nextTools = List<String>.from(state.activeTools)
              ..removeWhere((tool) => tool == toolName);
            state = state.copyWith(activeTools: nextTools);
          }
          if (widgetType != null && widgetData != null) {
            if (widgetType == 'system_update' &&
                !_shouldIncludeSystemUpdate(widgetData)) {
              continue;
            }
            accumulatedWidgets.add(
              WidgetPayload(
                type: widgetType,
                data: widgetData,
              ),
            );
          }
        } else if (event is UsageEvent) {
          state = state.copyWith(
            lastPromptTokens: event.promptTokens,
            lastCompletionTokens: event.completionTokens,
            lastTotalTokens: event.totalTokens,
          );
          await _updateDailyUsage(event);
        } else if (event is ReasoningStepEvent) {
          // 🆕 推理步骤事件 - Chain of Thought Visualization
          reasoningStartTime ??= DateTime.now().millisecondsSinceEpoch;

          // Add timestamp to step
          final stepWithTime = event.step.copyWith(
            createdAt: event.step.createdAt ?? DateTime.now(),
          );

          accumulatedReasoningSteps.add(stepWithTime);

          pendingReasoningSteps = List.from(accumulatedReasoningSteps);
          pendingReasoningActive = true;
          pendingReasoningStartTime = reasoningStartTime;
          flushPending();
        } else if (event is ActionStatusEvent) {
          // ActionCard 状态更新事件
          _handleActionStatus(event);
          flushPending();
        } else if (event is PlanReviewWidgetEvent) {
          // Plan Review Widget Event
          _handlePlanReviewWidget(event);
          flushPending();
        } else if (event is PlanReviewStatusEvent) {
          // Plan Review Status Event
          _handlePlanReviewStatus(event);
          flushPending();
        } else if (event is ContentReviewWidgetEvent) {
          // Content Review Widget Event (Phase 2b)
          _handleContentReviewWidget(event);
          flushPending();
        } else if (event is ContentReflectionResultEvent) {
          // Content Reflection Result Event (Phase 2b)
          _handleContentReflectionResult(event);
          flushPending();
        } else if (event is AchievementUnlockEvent) {
          // Achievement Unlock Event
          _handleAchievementUnlock(event);
          flushPending();
        } else if (event is TransparencyStepEvent) {
          // Transparency Step Event
          state = state.copyWith(
            currentStepId: event.currentStep,
            currentStepIndex: event.stepIndex,
          );
          flushPending();
        } else if (event is TransparencyCompleteEvent) {
          // Transparency Complete Event
          state = state.copyWith(
            transparencyData: event.transparencyData,
          );
          flushPending();
        } else if (event is SprintModeSwitchEvent) {
          // Sprint Mode Switch Event
          _handleSprintModeSwitch(event);
          flushPending();
        } else if (event is DoneEvent) {
          // 流结束
          // finishReason: event.finishReason
          flushPending(immediate: true);
          if (state.activeTools.isNotEmpty) {
            state = state.copyWith(activeTools: []);
          }
        }
      }

      _streamDebouncer.cancel();
      // 流结束后，将累积的内容转为正式消息
      if (accumulatedContent.isNotEmpty || accumulatedWidgets.isNotEmpty) {
        // Calculate total duration if reasoning steps exist
        String? reasoningSummary;
        if (accumulatedReasoningSteps.isNotEmpty &&
            reasoningStartTime != null) {
          final durationMs =
              DateTime.now().millisecondsSinceEpoch - reasoningStartTime;
          reasoningSummary =
              '完成于 ${(durationMs / 1000).toStringAsFixed(1)}s，${accumulatedReasoningSteps.length}个步骤';
        }

        final aiMessage = ChatMessageModel(
          id: 'ai_${DateTime.now().millisecondsSinceEpoch}',
          userId: 'ai_assistant',
          conversationId: state.conversationId ?? 'temp_conversation',
          role: MessageRole.assistant,
          content: accumulatedContent,
          createdAt: DateTime.now(),
          widgets: accumulatedWidgets.isNotEmpty ? accumulatedWidgets : null,
          aiStatus: lastAiStatus, // 持久化最后的 AI 状态（如：EXECUTING_TOOL）
          reasoningSteps: accumulatedReasoningSteps.isNotEmpty
              ? accumulatedReasoningSteps
              : null,
          reasoningSummary: reasoningSummary,
          isReasoningComplete: accumulatedReasoningSteps.isNotEmpty,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

        state = state.copyWith(
          isSending: false,
          messages: [...state.messages, aiMessage],
          streamingContent: '',
          clearAiStatus: true,
          clearReasoning: true, // Clear real-time reasoning state
        );
      } else {
        state = state.copyWith(
          isSending: false,
          streamingContent: '',
          clearAiStatus: true,
          clearReasoning: true,
        );
      }
    } catch (e) {
      _streamDebouncer.cancel();
      // 捕获未处理的异常，提供友好的错误提示
      final errorMessage = ErrorMessages.getUserFriendlyMessage(
        'UNKNOWN',
        e.toString(),
      );

      state = state.copyWith(
        isSending: false,
        streamingContent: '',
        error: errorMessage,
        errorCode: 'UNKNOWN',
        isErrorRetryable: true, // 未知错误默认可重试
      );
    }
  }

  void startNewSession() {
    state = state.copyWith(clearConversation: true, messages: []);
    if (DemoDataService.isDemoMode) {
      // Keep demo history? Or clear?
      // Usually "Start New Session" means clear.
    }
  }

  Future<void> switchPlanSession(String? planId) async {
    if (planId == null) {
      state = state.copyWith(clearConversation: true, messages: []);
      return;
    }

    final authState = _ref.read(authProvider);
    final user = authState.user;
    final userId = user?.id ?? await _ref.read(guestServiceProvider).getGuestId();
    final sessionId = _ref.read(agentSessionStoreProvider).getOrCreateSessionId(
          AgentSessionScope.plan,
          planId,
          userId,
        );

    if (state.conversationId == sessionId) {
      return;
    }

    state = state.copyWith(
      conversationId: sessionId,
      messages: [],
      clearError: true,
      streamingContent: '',
      clearAiStatus: true,
      clearReasoning: true,
    );

    await loadConversationHistory(sessionId);
  }

  /// 确认 ActionCard
  void confirmAction(WidgetPayload action) {
    if (action.type == 'nightly_review') {
      final reviewId = action.data['review_id']?.toString() ?? '';
      if (reviewId.isNotEmpty) {
        _markNightlyReviewed(reviewId);
        return;
      }
    }

    final interventionId = action.data['intervention_id']?.toString() ??
        action.data['request_id']?.toString() ??
        '';
    if (interventionId.isNotEmpty) {
      _chatRepository.sendInterventionFeedback(
        requestId: interventionId,
        feedbackType: 'accept',
        extraData: {'widget_type': action.type},
      );
      debugPrint('✅ Intervention accepted: $interventionId');
      return;
    }

    // 从 WidgetPayload 中提取 tool_result_id
    final toolResultId = action.data['id']?.toString() ??
        action.data['tool_result_id']?.toString() ??
        '';

    if (toolResultId.isEmpty) {
      debugPrint('⚠️ Warning: Cannot confirm action - missing tool_result_id');
      return;
    }

    // 发送确认反馈到后端
    _chatRepository.sendActionFeedback(
      action: 'confirm',
      toolResultId: toolResultId,
      widgetType: action.type,
    );

    debugPrint(
        '✅ Action confirmed: ${action.type} (tool_result_id: $toolResultId)',);

    // TODO: 可以添加乐观更新 - 立即在 UI 中标记为已确认
    // state = state.copyWith(messages: _updateActionStatus(toolResultId, confirmed: true));
  }

  /// 忽略 ActionCard
  void dismissAction(WidgetPayload action) {
    if (action.type == 'nightly_review') {
      debugPrint('ℹ️ Nightly review dismissed');
      return;
    }

    final interventionId = action.data['intervention_id']?.toString() ??
        action.data['request_id']?.toString() ??
        '';
    if (interventionId.isNotEmpty) {
      _chatRepository.sendInterventionFeedback(
        requestId: interventionId,
        feedbackType: 'reject',
        extraData: {'widget_type': action.type},
      );
      debugPrint('❌ Intervention dismissed: $interventionId');
      return;
    }

    final toolResultId = action.data['id']?.toString() ??
        action.data['tool_result_id']?.toString() ??
        '';

    if (toolResultId.isEmpty) {
      debugPrint('⚠️ Warning: Cannot dismiss action - missing tool_result_id');
      return;
    }

    // 发送忽略反馈到后端
    _chatRepository.sendActionFeedback(
      action: 'dismiss',
      toolResultId: toolResultId,
      widgetType: action.type,
    );

    debugPrint(
        '❌ Action dismissed: ${action.type} (tool_result_id: $toolResultId)',);

    // TODO: 可以添加乐观更新 - 从 UI 中移除或标记为已忽略
    // state = state.copyWith(messages: _updateActionStatus(toolResultId, confirmed: false));
  }

  void sendResponseFeedback(ChatMessageModel message, String feedbackType) {
    final responseId = message.responseId ?? '';
    if (responseId.isEmpty) {
      debugPrint('⚠️ Missing response_id for feedback');
      return;
    }

    _chatRepository.sendResponseFeedback(
      responseId: responseId,
      feedbackType: feedbackType,
      workflowId: message.workflowId,
      promptVersion: message.promptVersion,
      traceId: message.traceId,
      meta: {'message_id': message.id},
    );
    debugPrint('📤 Response feedback sent: $feedbackType for $responseId');
  }

  /// 发送计划审查反馈
  void sendPlanReviewFeedback({
    required String reviewId,
    required String userDecision,
    String? userComment,
  }) {
    _chatRepository.sendPlanReviewFeedback(
      reviewId: reviewId,
      userDecision: userDecision,
      userComment: userComment,
    );
    debugPrint('📤 Plan review feedback sent: $userDecision for $reviewId');

    // Clear the pending review after sending feedback
    state = state.copyWith(clearPendingReview: true);
  }

  Future<void> _markNightlyReviewed(String reviewId) async {
    try {
      await _ref.read(nightlyReviewActionsProvider).markReviewed(reviewId);
      debugPrint('✅ Nightly review marked as reviewed: $reviewId');
    } catch (e) {
      debugPrint('❌ Nightly review feedback failed: $e');
    }
  }

  /// 处理成就解锁事件
  void _handleAchievementUnlock(AchievementUnlockEvent event) {
    debugPrint('🏆 Achievement unlocked: ${event.name}');

    state = state.copyWith(
      pendingAchievementUnlock: event,
      lastActionStatus: 'achievement_unlocked',
      lastActionMessage: '${event.name} 解锁！',
    );

    // Clear after delay
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        state = state.copyWith(
          clearActionFeedback: true,
        );
      }
    });
  }

  void _handleSprintModeSwitch(SprintModeSwitchEvent event) {
    debugPrint('🔄 Sprint mode switch event received');

    // Switch to Sprint View
    _ref.read(taskBoardProvider.notifier).switchView(TaskViewMode.sprint);
  }

  /// 处理 ActionCard 状态更新
  void _handleActionStatus(ActionStatusEvent event) {
    debugPrint(
        '📥 Action status received: ${event.status} for ${event.actionId}',);

    // 显示用户友好的提示消息
    final message = event.message ?? _getDefaultStatusMessage(event.status);

    // 更新状态以触发 UI 反馈
    state = state.copyWith(
      lastActionStatus: event.status,
      lastActionMessage: message,
    );

    // 延迟清除反馈状态
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    debugPrint('💬 Status message: $message');

    // TODO: 更新 UI 中对应 ActionCard 的状态
    // 例如：标记为已确认、已忽略，或者从列表中移除
    // state = state.copyWith(messages: _updateMessageActionStatus(event.actionId, event.status));
  }

  String _getDefaultStatusMessage(String status) {
    switch (status) {
      case 'confirmed':
        return '✅ 已确认';
      case 'dismissed':
        return '❌ 已忽略';
      case 'processing':
        return '⏳ 处理中...';
      case 'completed':
        return '✅ 已完成';
      case 'failed':
        return '❌ 操作失败';
      default:
        return '📝 状态更新: $status';
    }
  }

  /// 处理 Plan Review Widget Event
  void _handlePlanReviewWidget(PlanReviewWidgetEvent event) {
    debugPrint('📥 Plan review widget received');

    // Parse review data
    final reviewData = event.reviewData;
    final review = PlanReviewResult.fromJson(reviewData);

    // Update state with pending review
    state = state.copyWith(
      pendingPlanReview: review,
      pendingReviewActionId: review.actionId,
    );

    debugPrint('📋 Plan review ready: ${review.decision} (review_id: ${review.reviewId})');
  }

  /// 处理 Plan Review Status Event
  void _handlePlanReviewStatus(PlanReviewStatusEvent event) {
    debugPrint(
        '📥 Plan review status received: ${event.status} for ${event.reviewId}',);

    // Show user-friendly message
    final message = event.message ?? _getPlanReviewStatusMessage(event.status);

    // Update state to trigger UI feedback
    state = state.copyWith(
      lastActionStatus: event.status,
      lastActionMessage: message,
    );

    // Clear pending review if status indicates completion
    if (event.status == 'approved' || event.status == 'rejected') {
      state = state.copyWith(clearPendingReview: true);
    }

    // Delay clearing feedback state
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    debugPrint('💬 Plan review status message: $message');
  }

  String _getPlanReviewStatusMessage(String status) {
    switch (status) {
      case 'approved':
        return '✅ 计划已批准';
      case 'rejected':
        return '❌ 计划已取消';
      case 'modify_requested':
        return '📝 请提供修改要求...';
      case 'acknowledged':
        return '✅ 反馈已收到';
      default:
        return '📋 计划状态更新: $status';
    }
  }

  // ============================================
  // Phase 2b: Content Review Handlers
  // ============================================

  /// 处理 Content Review Widget Event
  void _handleContentReviewWidget(ContentReviewWidgetEvent event) {
    debugPrint('📥 Content review widget received');

    // Parse review data
    final reviewData = event.reviewData;
    final review = ContentReviewResult.fromJson(reviewData);

    // Update state with pending content review
    state = state.copyWith(pendingContentReview: review);

    debugPrint('📋 Content review ready: ${review.decision} (review_id: ${review.reviewId})');
  }

  /// 处理 Content Reflection Result Event
  void _handleContentReflectionResult(ContentReflectionResultEvent event) {
    debugPrint('📥 Content reflection result received');

    final reflectionData = event.reflectionData;
    final outcome = reflectionData['outcome'] as String? ?? 'unknown';
    final scoreDelta = (reflectionData['score_delta'] as num?)?.toDouble() ?? 0.0;
    final rounds = reflectionData['rounds'] as int? ?? 0;

    // Show user-friendly message about reflection result
    final message = _getReflectionResultMessage(outcome, scoreDelta, rounds);

    state = state.copyWith(
      lastActionStatus: outcome,
      lastActionMessage: message,
    );

    // Update pending content review with reflection status
    final currentReview = state.pendingContentReview;
    if (currentReview != null) {
      // Create updated review with reflection status
      final updatedReview = ContentReviewResult(
        reviewId: currentReview.reviewId,
        decision: currentReview.decision,
        overallScore: currentReview.overallScore + scoreDelta,
        metrics: currentReview.metrics,
        issues: currentReview.issues,
        suggestions: currentReview.suggestions,
        reviewedAt: currentReview.reviewedAt,
        reflectionStatus: outcome == 'fixed' || outcome == 'improved' ? 'completed' : 'failed',
        scoreLabel: _getScoreLabelForScore(currentReview.overallScore + scoreDelta),
      );

      state = state.copyWith(pendingContentReview: updatedReview);
    }

    // Delay clearing feedback state
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    debugPrint('💬 Reflection result: $message');
  }

  /// Get user-friendly reflection result message
  String _getReflectionResultMessage(String outcome, double scoreDelta, int rounds) {
    final roundsInfo = rounds > 1 ? ' ($rounds轮)' : '';
    switch (outcome) {
      case 'fixed':
        return '✅ 内容已优化$roundsInfo，分数提升 +${(scoreDelta * 100).toInt()}%';
      case 'improved':
        return '📈 内容有所改善$roundsInfo，分数提升 +${(scoreDelta * 100).toInt()}%';
      case 'no_change':
        return 'ℹ️ 优化尝试完成，内容无明显变化';
      case 'degraded':
        return '⚠️ 优化尝试未达预期，保留原内容';
      case 'failed':
        return '❌ 优化失败，请稍后重试';
      default:
        return '🔄 反思处理完成: $outcome';
    }
  }

  /// Get score label for a given score
  String _getScoreLabelForScore(double score) {
    if (score >= 0.9) return '优秀';
    if (score >= 0.7) return '良好';
    if (score >= 0.5) return '及格';
    return '需改进';
  }

  /// 用户接受审查后的内容（不采取行动）
  void acceptContentReview() {
    state = state.copyWith(clearPendingContentReview: true);
    debugPrint('✅ Content review accepted');
  }

  /// 用户拒绝内容，请求重新生成
  void rejectContentReview() {
    final review = state.pendingContentReview;
    if (review == null) return;

    state = state.copyWith(
      clearPendingContentReview: true,
      lastActionStatus: 'rejected',
      lastActionMessage: '已请求重新生成',
    );

    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    requestRegeneration(
      originalContentId: 'content_from_review_${review.reviewId}',
      reviewId: review.reviewId,
      regenerationType: 'fix_issues',
    ).then((result) {
      if (result == null || result['success'] != true) {
        debugPrint('❌ Regeneration request failed for ${review.reviewId}');
      }
    });

    debugPrint('❌ Content review rejected, requesting regeneration');
  }

  /// 用户请求人工审查
  void requestHumanReview() {
    state = state.copyWith(
      lastActionStatus: 'human_review_requested',
      lastActionMessage: '已提交人工审查请求',
    );

    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    debugPrint('👤 Human review requested');
  }

  // ============================================
  // Phase 2e: Review Override & Appeal
  // ============================================

  /// 用户覆盖审查决策
  Future<bool> submitReviewOverride({
    required String reviewId,
    required String originalDecision,
    required String newDecision,
    required String reason,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '请先登录',
      );
      return false;
    }

    try {
      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.submitReviewOverride(
        userId: user.id,
        reviewId: reviewId,
        originalDecision: originalDecision,
        newDecision: newDecision,
        reason: reason,
        authToken: authToken,
      );

      if (result.success) {
        state = state.copyWith(
          lastActionStatus: 'override_submitted',
          lastActionMessage: result.message ??
              (newDecision == 'passed'
                  ? '已接受内容（尽管未通过审查）'
                  : '已拒绝内容（尽管审查通过）'),
          clearPendingContentReview: true,
        );

        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) {
            state = state.copyWith(clearActionFeedback: true);
          }
        });

        debugPrint('✅ Review override submitted: $originalDecision -> $newDecision');
        return true;
      } else {
        state = state.copyWith(
          lastActionStatus: 'error',
          lastActionMessage: result.message ?? '提交失败，请重试',
        );
        return false;
      }
    } catch (e) {
      debugPrint('❌ Review override error: $e');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '提交失败，请重试',
      );
      return false;
    }
  }

  /// 用户提交审查申诉
  Future<bool> submitReviewAppeal({
    required String reviewId,
    required String reason,
    required List<String> issues,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '请先登录',
      );
      return false;
    }

    try {
      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.submitReviewAppeal(
        userId: user.id,
        reviewId: reviewId,
        appealReason: reason,
        issuesWithReview: issues,
        authToken: authToken,
      );

      if (result.success) {
        state = state.copyWith(
          lastActionStatus: 'appeal_submitted',
          lastActionMessage: result.message ?? '申诉已提交，正在处理...',
        );

        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) {
            state = state.copyWith(clearActionFeedback: true);
          }
        });

        debugPrint('✅ Review appeal submitted for review $reviewId');
        return true;
      } else {
        state = state.copyWith(
          lastActionStatus: 'error',
          lastActionMessage: result.message ?? '提交失败，请重试',
        );
        return false;
      }
    } catch (e) {
      debugPrint('❌ Review appeal error: $e');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '提交失败，请重试',
      );
      return false;
    }
  }

  /// 获取申诉状态
  Future<Map<String, dynamic>?> getAppealStatus(String appealId) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      return null;
    }

    try {
      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.getAppealStatus(
        userId: user.id,
        appealId: appealId,
        authToken: authToken,
      );

      if (result != null) {
        return {
          'appeal_id': result.appealId,
          'review_id': result.reviewId,
          'status': result.status,
          'submitted_at': result.submittedAt,
          'appeal_reason': result.appealReason,
          'resolution': result.resolution,
          'resolved_by': result.resolvedBy,
          'resolved_at': result.resolvedAt,
          'secondary_decision': result.secondaryDecision,
          'secondary_score': result.secondaryScore,
        };
      }
      return null;
    } catch (e) {
      debugPrint('❌ Get appeal status error: $e');
      return null;
    }
  }

  // ============================================
  // Phase 2f: Feedback Complete Integration
  // ============================================

  /// 提交审查反馈（评分）
  ///
  /// 允许用户对审查结果进行评分和反馈
  Future<bool> submitReviewFeedback({
    required String reviewId,
    int? rating,
    bool? wasHelpful,
    bool? wasAccurate,
    List<String>? inaccuratePoints,
    String? specificityLevel,
    String? comments,
    List<String>? tags,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      return false;
    }

    try {
      debugPrint('[ChatProvider] Submitting review feedback for $reviewId');

      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.submitReviewFeedback(
        userId: user.id,
        reviewId: reviewId,
        rating: rating,
        wasHelpful: wasHelpful,
        wasAccurate: wasAccurate,
        inaccuratePoints: inaccuratePoints,
        specificityLevel: specificityLevel,
        comments: comments,
        tags: tags,
        authToken: authToken,
      );

      debugPrint('[ChatProvider] Feedback ${result.success ? "submitted" : "failed"}');
      return result.success;
    } catch (e) {
      debugPrint('[ChatProvider] Failed to submit feedback: $e');
      return false;
    }
  }

  /// 为审查评分（简化接口）
  Future<bool> rateReview({
    required String reviewId,
    required int rating,
    String? comments,
  }) async => submitReviewFeedback(
      reviewId: reviewId,
      rating: rating,
      wasHelpful: rating >= 4,
      comments: comments,
    );

  /// 请求内容重新生成
  ///
  /// 基于用户反馈请求AI重新生成内容
  Future<Map<String, dynamic>?> requestRegeneration({
    required String originalContentId,
    required String reviewId,
    required String regenerationType,
    List<String>? improvementHints,
    List<String>? focusAreas,
    String? customInstructions,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      return null;
    }

    try {
      debugPrint(
        '[ChatProvider] Requesting regeneration for content $originalContentId',
      );

      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.requestRegeneration(
        userId: user.id,
        originalContentId: originalContentId,
        reviewId: reviewId,
        regenerationType: regenerationType,
        improvementHints: improvementHints,
        focusAreas: focusAreas,
        customInstructions: customInstructions,
        authToken: authToken,
      );

      if (result.success) {
        final resultMap = {
          'request_id': result.requestId,
          'success': true,
          'new_content': result.newContent,
          'new_content_id': result.newContentId,
          'improvement_summary': result.improvementSummary,
          'changes_made': result.changesMade,
          'score_improvement': result.scoreImprovement,
          'generation_time_ms': result.generationTimeMs,
        };
        debugPrint('[ChatProvider] Regeneration completed: $resultMap');
        return resultMap;
      } else {
        debugPrint('[ChatProvider] Regeneration failed: ${result.message}');
        return {
          'success': false,
          'message': result.message,
        };
      }
    } catch (e) {
      debugPrint('[ChatProvider] Failed to request regeneration: $e');
      return null;
    }
  }

  /// 获取用户反馈模式
  ///
  /// 返回用户的历史反馈模式，用于个性化审查
  Future<Map<String, dynamic>?> getUserFeedbackPattern() async {
    try {
      // TODO: Implement gRPC call to GetUserFeedbackPattern
      // For now, return null (no pattern yet)
      return null;
    } catch (e) {
      debugPrint('[ChatProvider] Failed to get feedback pattern: $e');
      return null;
    }
  }

  /// 获取反馈统计
  ///
  /// 返回用户反馈的整体统计数据
  Future<Map<String, dynamic>?> getFeedbackStatistics({
    int days = 30,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      return null;
    }

    try {
      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.getFeedbackStatistics(
        userId: user.id,
        periodDays: days,
        authToken: authToken,
      );

      if (result.success) {
        return {
          'total_feedbacks': result.totalFeedbacks,
          'avg_rating': result.avgRating,
          'helpful_rate': result.helpfulRate,
          'accuracy_rate': result.accuracyRate,
          'regeneration_requests': result.regenerationRequests,
          'successful_regenerations': result.successfulRegenerations,
          'period_days': result.periodDays,
        };
      }
      return null;
    } catch (e) {
      debugPrint('[ChatProvider] Failed to get feedback statistics: $e');
      return null;
    }
  }
}

// 3. Provider
final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ChatRepository(apiClient.dio);
});

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>(
    (ref) => ChatNotifier(ref.watch(chatRepositoryProvider), ref),);

class _Debouncer {
  _Debouncer(this.delay);
  final Duration delay;
  Timer? _timer;

  void run(void Function() action) {
    _timer?.cancel();
    _timer = Timer(delay, action);
  }

  void flush(void Function() action) {
    _timer?.cancel();
    action();
  }

  void cancel() {
    _timer?.cancel();
    _timer = null;
  }
}
