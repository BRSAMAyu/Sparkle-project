import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/models/chat_stream_events.dart';
import 'package:sparkle/data/repositories/chat_repository.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';

// 1. ChatState Class
class ChatState {
  final bool isLoading;
  final bool isSending;
  final String? conversationId;
  final List<ChatMessageModel> messages;
  final String? error;
  final String streamingContent;
  final String? aiStatus; // THINKING, GENERATING, etc.
  final String? aiStatusDetails;

  ChatState({
    this.isLoading = false,
    this.isSending = false,
    this.conversationId,
    this.messages = const [],
    this.error,
    this.streamingContent = '',
    this.aiStatus,
    this.aiStatusDetails,
  });

  ChatState copyWith({
    bool? isLoading,
    bool? isSending,
    String? conversationId,
    bool clearConversation = false,
    List<ChatMessageModel>? messages,
    String? error,
    bool clearError = false,
    String? streamingContent,
    String? aiStatus,
    bool clearAiStatus = false,
    String? aiStatusDetails,
  }) {
    return ChatState(
      isLoading: isLoading ?? this.isLoading,
      isSending: isSending ?? this.isSending,
      conversationId: clearConversation ? null : conversationId ?? this.conversationId,
      messages: messages ?? this.messages,
      error: clearError ? null : error ?? this.error,
      streamingContent: streamingContent ?? this.streamingContent,
      aiStatus: clearAiStatus ? null : aiStatus ?? this.aiStatus,
      aiStatusDetails: clearAiStatus ? null : aiStatusDetails ?? this.aiStatusDetails,
    );
  }
}

// 2. ChatNotifier Class
class ChatNotifier extends StateNotifier<ChatState> {
  final ChatRepository _chatRepository;
  final Ref _ref;

  ChatNotifier(this._chatRepository, this._ref) : super(ChatState()) {
    if (DemoDataService.isDemoMode) {
      // Load demo history
      state = state.copyWith(messages: DemoDataService().demoChatHistory, conversationId: 'demo_conv_1');
    }
  }

  /// 发送消息 (使用 SSE/WebSocket 流式响应)
  Future<void> sendMessage(String content, {String? taskId}) async {
    // 获取当前用户信息
    final authState = _ref.read(authProvider);
    final user = authState.user;
    final userId = user?.id ?? 'guest_${DateTime.now().millisecondsSinceEpoch}';
    final nickname = user?.nickname ?? user?.username ?? 'Guest';

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

    String accumulatedContent = '';
    final List<WidgetPayload> accumulatedWidgets = [];

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
            clearAiStatus: true, // 开始输出文本时清除状态
          );
        } else if (event is StatusUpdateEvent) {
          // AI 状态更新（THINKING, GENERATING 等）
          state = state.copyWith(
            aiStatus: event.state,
            aiStatusDetails: event.details,
          );
        } else if (event is FullTextEvent) {
          // 完整文本（通常在流结束时）
          accumulatedContent = event.content;
          state = state.copyWith(streamingContent: accumulatedContent);
        } else if (event is ErrorEvent) {
          // 错误事件
          state = state.copyWith(
            error: '${event.code}: ${event.message}',
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
          state = state.copyWith(
            aiStatus: 'EXECUTING_TOOL',
            aiStatusDetails: '正在使用 ${event.toolName}...',
          );
        } else if (event is ToolResultEvent) {
          // 工具结果
          // 暂时不处理或者添加到 debug log
        } else if (event is UsageEvent) {
          // Token 使用统计（可选显示）
          // print('Usage: ${event.totalTokens} tokens');
        } else if (event is DoneEvent) {
          // 流结束
          // finishReason: event.finishReason
        }
      }

      // 流结束后，将累积的内容转为正式消息
      if (accumulatedContent.isNotEmpty || accumulatedWidgets.isNotEmpty) {
        final aiMessage = ChatMessageModel(
          id: 'ai_${DateTime.now().millisecondsSinceEpoch}',
          userId: 'ai_assistant',
          conversationId: state.conversationId ?? 'temp_conversation',
          role: MessageRole.assistant,
          content: accumulatedContent,
          createdAt: DateTime.now(),
          widgets: accumulatedWidgets.isNotEmpty ? accumulatedWidgets : null,
        );

        state = state.copyWith(
          isSending: false,
          messages: [...state.messages, aiMessage],
          streamingContent: '',
          clearAiStatus: true,
        );
      } else {
        state = state.copyWith(
          isSending: false,
          streamingContent: '',
          clearAiStatus: true,
        );
      }

    } catch (e) {
      state = state.copyWith(
        isSending: false,
        streamingContent: '',
        error: '发送失败: $e',
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

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>((ref) {
  return ChatNotifier(ref.watch(chatRepositoryProvider), ref);
});

