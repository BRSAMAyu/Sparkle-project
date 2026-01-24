import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/agent_session_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';

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
    this.pendingPlanReview,
    this.pendingReviewActionId,
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

  // Plan Review state
  final PlanReviewResult? pendingPlanReview;
  final String? pendingReviewActionId;

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

  // Plan review service (lazy initialized)
  PlanReviewGrpcService? _planReviewService;

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
          lastActionMessage: result.message ?? _getSuccessMessage(decision),
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
          lastActionMessage: result.message ?? '提交失败',
        );
        debugPrint('❌ Plan review failed: ${result.message}');
        return false;
      }
    } catch (e) {
      debugPrint('❌ Plan review error: $e');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '网络错误，请重试',
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

  /// Get user-friendly success message
  String _getSuccessMessage(ReviewDecision decision) {
    switch (decision) {
      case ReviewDecision.approved:
        return '✅ 已批准';
      case ReviewDecision.rejected:
        return '❌ 已取消';
      case ReviewDecision.needsModification:
        return '📝 已请求修改';
      case ReviewDecision.requiresConfirmation:
        return '✅ 已确认';
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
          flushPending();
        } else if (event is ToolResultEvent) {
          final widgetType = event.result.widgetType;
          final widgetData = event.result.widgetData;
          if (widgetType != null && widgetData != null) {
            accumulatedWidgets.add(
              WidgetPayload(
                type: widgetType,
                data: widgetData,
              ),
            );
          }
        } else if (event is UsageEvent) {
          // Token 使用统计（可选显示）
          // print('Usage: ${event.totalTokens} tokens');
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
        } else if (event is DoneEvent) {
          // 流结束
          // finishReason: event.finishReason
          flushPending(immediate: true);
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
