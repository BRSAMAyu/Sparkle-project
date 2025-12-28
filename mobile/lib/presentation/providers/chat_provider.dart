import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/websocket_chat_service_v2.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/models/chat_stream_events.dart';
import 'package:sparkle/data/models/reasoning_step_model.dart';
import 'package:sparkle/data/repositories/chat_repository.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/guest_provider.dart';
import 'package:sparkle/presentation/widgets/galaxy/graphrag_visualizer.dart';

// 1. ChatState Class
class ChatState { // Timestamp for duration calculation

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
  }) => ChatState(
      isLoading: isLoading ?? this.isLoading,
      isSending: isSending ?? this.isSending,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      hasMoreMessages: hasMoreMessages ?? this.hasMoreMessages,
      conversationId: clearConversation ? null : conversationId ?? this.conversationId,
      messages: messages ?? this.messages,
      error: clearError ? null : error ?? this.error,
      errorCode: clearError ? null : errorCode ?? this.errorCode,
      isErrorRetryable: clearError ? false : isErrorRetryable ?? this.isErrorRetryable,
      streamingContent: streamingContent ?? this.streamingContent,
      aiStatus: clearAiStatus ? null : aiStatus ?? this.aiStatus,
      aiStatusDetails: clearAiStatus ? null : aiStatusDetails ?? this.aiStatusDetails,
      wsConnectionState: wsConnectionState ?? this.wsConnectionState,
      graphragTrace: clearGraphragTrace ? null : graphragTrace ?? this.graphragTrace,
      reasoningSteps: clearReasoning ? [] : reasoningSteps ?? this.reasoningSteps,
      isReasoningActive: clearReasoning ? false : isReasoningActive ?? this.isReasoningActive,
      reasoningStartTime: clearReasoning ? null : reasoningStartTime ?? this.reasoningStartTime,
    );
}

// 2. ChatNotifier Class
class ChatNotifier extends StateNotifier<ChatState> {

  ChatNotifier(this._chatRepository, this._ref) : super(ChatState()) {
    if (DemoDataService.isDemoMode) {
      // Load demo history
      state = state.copyWith(messages: DemoDataService().demoChatHistory, conversationId: 'demo_conv_1');
    }

    // 监听 WebSocket 连接状态
    _chatRepository.connectionStateStream.listen((connectionState) {
      state = state.copyWith(wsConnectionState: connectionState);
    });
  }
  final ChatRepository _chatRepository;
  final Ref _ref;

  /// 手动触发重连
  Future<void> reconnect() async {
    await _chatRepository.reconnect();
  }

  @override
  void dispose() {
    _chatRepository.dispose();
    super.dispose();
  }

  /// 加载历史对话
  Future<void> loadConversationHistory(String conversationId) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final history = await _chatRepository.getConversationHistory(conversationId);
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

  /// 获取最近对话列表
  Future<List<Map<String, dynamic>>> getRecentConversations() async => _chatRepository.getRecentConversations();

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
          : (user.username ?? 'User');
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
    String? lastAiStatus;
    final accumulatedWidgets = <WidgetPayload>[];
    final accumulatedReasoningSteps = <ReasoningStep>[];
    int? reasoningStartTime;

    try {
      await for (final event in _chatRepository.chatStream(
        content,
        state.conversationId,
        userId: userId,
        nickname: nickname,
      )) {
        if (event is TextEvent) {
          // 流式文本片段（delta）
          accumulatedContent += event.content;
          state = state.copyWith(
            streamingContent: accumulatedContent,
          );
        } else if (event is StatusUpdateEvent) {
          // AI 状态更新（THINKING, GENERATING 等）
          lastAiStatus = event.state;
          state = state.copyWith(
            aiStatus: event.state,
            aiStatusDetails: event.details,
          );
        } else if (event is FullTextEvent) {
          // 完整文本（通常在流结束时）
          accumulatedContent = event.content;
          state = state.copyWith(streamingContent: accumulatedContent);
        } else if (event is ErrorEvent) {
          // 错误事件 - 使用用户友好的错误消息
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
          state = state.copyWith(
            aiStatus: 'EXECUTING_TOOL',
            aiStatusDetails: '正在使用 ${event.toolName}...',
          );
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

          // Update state with new reasoning steps
          state = state.copyWith(
            reasoningSteps: List.from(accumulatedReasoningSteps),
            isReasoningActive: true,
            reasoningStartTime: reasoningStartTime,
          );
        } else if (event is DoneEvent) {
          // 流结束
          // finishReason: event.finishReason
        }
      }

      // 流结束后，将累积的内容转为正式消息
      if (accumulatedContent.isNotEmpty || accumulatedWidgets.isNotEmpty) {
        // Calculate total duration if reasoning steps exist
        String? reasoningSummary;
        if (accumulatedReasoningSteps.isNotEmpty && reasoningStartTime != null) {
          final durationMs = DateTime.now().millisecondsSinceEpoch - reasoningStartTime;
          reasoningSummary = '完成于 ${(durationMs / 1000).toStringAsFixed(1)}s，${accumulatedReasoningSteps.length}个步骤';
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
          reasoningSteps: accumulatedReasoningSteps.isNotEmpty ? accumulatedReasoningSteps : null,
          reasoningSummary: reasoningSummary,
          isReasoningComplete: accumulatedReasoningSteps.isNotEmpty,
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
}

// 3. Provider
final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ChatRepository(apiClient.dio);
});

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>((ref) => ChatNotifier(ref.watch(chatRepositoryProvider), ref));
