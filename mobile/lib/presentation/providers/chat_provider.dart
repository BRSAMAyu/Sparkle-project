import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/repositories/chat_repository.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

// 1. ChatState Class
class ChatState {
  final bool isLoading;
  final bool isSending;
  final String? conversationId;
  final List<ChatMessageModel> messages;
  final String? error;
  final String streamingContent;

  ChatState({
    this.isLoading = false,
    this.isSending = false,
    this.conversationId,
    this.messages = const [],
    this.error,
    this.streamingContent = '',
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
  }) {
    return ChatState(
      isLoading: isLoading ?? this.isLoading,
      isSending: isSending ?? this.isSending,
      conversationId: clearConversation ? null : conversationId ?? this.conversationId,
      messages: messages ?? this.messages,
      error: clearError ? null : error ?? this.error,
      streamingContent: streamingContent ?? this.streamingContent,
    );
  }
}

// 2. ChatNotifier Class
class ChatNotifier extends StateNotifier<ChatState> {
  final ChatRepository _chatRepository;

  ChatNotifier(this._chatRepository) : super(ChatState()) {
    if (DemoDataService.isDemoMode) {
      // Load demo history
      state = state.copyWith(messages: DemoDataService().demoChatHistory, conversationId: 'demo_conv_1');
    }
  }

  /// 发送消息 (使用 SSE 流式响应)
  Future<void> sendMessage(String content, {String? taskId}) async {
    // 1. 立即添加用户消息到 UI
    final userMessage = ChatMessageModel(
      id: 'temp_user_${DateTime.now().millisecondsSinceEpoch}',
      userId: '', // TODO: Get actual user ID
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
      await for (final event in _chatRepository.chatStream(content, state.conversationId)) {
        if (event is TextEvent) {
          accumulatedContent += event.content;
          state = state.copyWith(streamingContent: accumulatedContent);
        } else if (event is WidgetEvent) {
          accumulatedWidgets.add(WidgetPayload(
            type: event.widgetType,
            data: event.widgetData,
          ),);
        } else if (event is ToolStartEvent) {
          // 可以选择显示"正在使用工具: xxx"
        } else if (event is ToolResultEvent) {
          // 工具结果，暂时不处理或者添加到 debug log
        } else if (event is DoneEvent) {
          // 流结束
        } else if (event is UnknownEvent) {
          // 忽略
        }
      }

      // 流结束后，将累积的内容转为正式消息
      if (accumulatedContent.isNotEmpty || accumulatedWidgets.isNotEmpty) {
        final aiMessage = ChatMessageModel(
          id: 'ai_${DateTime.now().millisecondsSinceEpoch}',
          userId: '',
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
        );
      } else {
         state = state.copyWith(
          isSending: false,
          streamingContent: '',
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
  return ChatNotifier(ref.watch(chatRepositoryProvider));
});
