import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/repositories/chat_repository.dart';

// 1. ChatState Class
class ChatState {
  final bool isLoading;
  final bool isSending;
  final String? currentSessionId;
  final List<ChatMessageModel> messages;
  final List<ChatSession> sessions;
  final String? error;
  final String streamingContent;  // 🆕 正在流式输出的内容

  ChatState({
    this.isLoading = false,
    this.isSending = false,
    this.currentSessionId,
    this.messages = const [],
    this.sessions = const [],
    this.error,
    this.streamingContent = '',
  });

  ChatState copyWith({
    bool? isLoading,
    bool? isSending,
    String? currentSessionId,
    bool clearCurrentSession = false,
    List<ChatMessageModel>? messages,
    List<ChatSession>? sessions,
    String? error,
    bool clearError = false,
    String? streamingContent,
  }) {
    return ChatState(
      isLoading: isLoading ?? this.isLoading,
      isSending: isSending ?? this.isSending,
      currentSessionId: clearCurrentSession ? null : currentSessionId ?? this.currentSessionId,
      messages: messages ?? this.messages,
      sessions: sessions ?? this.sessions,
      error: clearError ? null : error ?? this.error,
      streamingContent: streamingContent ?? this.streamingContent,
    );
  }
}

// 2. ChatNotifier Class
class ChatNotifier extends StateNotifier<ChatState> {
  final ChatRepository _chatRepository;

  ChatNotifier(this._chatRepository) : super(ChatState()) {
    loadSessions();
  }

  Future<void> _runWithErrorHandling(Future<void> Function() action, {bool sending = false}) async {
    state = state.copyWith(isLoading: !sending, isSending: sending, clearError: true);
    try {
      await action();
    } catch (e) {
      state = state.copyWith(isLoading: false, isSending: false, error: e.toString());
    }
  }

  Future<void> loadSessions() async {
    await _runWithErrorHandling(() async {
      final sessions = await _chatRepository.getSessions();
      state = state.copyWith(isLoading: false, sessions: sessions);
    });
  }

  Future<void> loadMessages(String sessionId) async {
    await _runWithErrorHandling(() async {
      final messages = await _chatRepository.getSessionMessages(sessionId);
      state = state.copyWith(isLoading: false, messages: messages, currentSessionId: sessionId);
    });
  }

  /// 发送消息 (使用 SSE 流式响应)
  Future<void> sendMessage(String content, {String? taskId}) async {
    final request = ChatRequest(
      content: content,
      sessionId: state.currentSessionId,
      taskId: taskId,
    );

    // 1. 立即添加用户消息到 UI
    final userMessage = ChatMessageModel(
      id: 'temp_user_${DateTime.now().millisecondsSinceEpoch}',
      userId: '',
      sessionId: state.currentSessionId ?? 'temp_session',
      role: MessageRole.user,
      content: content,
      createdAt: DateTime.now(),
    );
    state = state.copyWith(
      messages: [...state.messages, userMessage],
      isSending: true,
      streamingContent: '',  // 清空流式内容
      clearError: true,
    );

    // 2. 使用流式 API 发送消息
    String accumulatedContent = '';
    String? finalSessionId;
    String? finalMessageId;

    try {
      await for (final event in _chatRepository.sendMessageStream(request)) {
        switch (event.type) {
          case StreamEventType.token:
            // 实时更新流式内容
            accumulatedContent += event.content ?? '';
            state = state.copyWith(streamingContent: accumulatedContent);
            break;

          case StreamEventType.actions:
            // 处理 actions (如创建任务)
            if (event.actions != null) {
              for (final action in event.actions!) {
                if (action is Map<String, dynamic>) {
                  handleAction(ChatAction(
                    type: action['type'] as String? ?? '',
                    params: action['data'] as Map<String, dynamic>? ?? {},
                  ),);
                }
              }
            }
            break;

          case StreamEventType.parseStatus:
            // 可以在这里处理解析状态，如显示警告
            if (event.degraded == true) {
              print('⚠️ LLM 响应解析降级');
            }
            break;

          case StreamEventType.done:
            finalSessionId = event.sessionId;
            finalMessageId = event.messageId;
            break;

          case StreamEventType.error:
            // 🚨 错误处理：如果有已累积的内容，保留它
            if (event.content != null && event.content!.isNotEmpty) {
              accumulatedContent = event.content!;
            }
            // 设置错误状态但不清空已累积的内容
            state = state.copyWith(error: event.errorMessage);
            break;
        }
      }

      // 3. 流结束后，将累积的内容转为正式消息
      if (accumulatedContent.isNotEmpty) {
        final aiMessage = ChatMessageModel(
          id: finalMessageId ?? 'ai_${DateTime.now().millisecondsSinceEpoch}',
          userId: '',
          sessionId: finalSessionId ?? state.currentSessionId ?? 'temp_session',
          role: MessageRole.assistant,
          content: accumulatedContent,
          createdAt: DateTime.now(),
        );

        // 保留用户消息，添加 AI 消息
        final finalMessages = [...state.messages, aiMessage];

        state = state.copyWith(
          isSending: false,
          messages: finalMessages,
          currentSessionId: finalSessionId ?? state.currentSessionId,
          streamingContent: '',  // 清空流式内容
        );
      } else {
        // 没有收到任何内容
        state = state.copyWith(
          isSending: false,
          streamingContent: '',
        );
      }

    } catch (e) {
      // 兜底错误处理
      state = state.copyWith(
        isSending: false,
        streamingContent: '',
        error: '发送失败: $e',
      );
    }
  }

  /// 发送消息 (非流式，兼容旧代码)
  Future<void> sendMessageNonStream(String content, {String? taskId}) async {
    final request = ChatRequest(
      content: content,
      sessionId: state.currentSessionId,
      taskId: taskId,
    );

    final userMessage = ChatMessageModel(
        id: 'temp_user_${DateTime.now().millisecondsSinceEpoch}',
        userId: '',
        sessionId: state.currentSessionId ?? 'temp_session',
        role: MessageRole.user,
        content: content,
        createdAt: DateTime.now(),);
    state = state.copyWith(messages: [...state.messages, userMessage]);

    await _runWithErrorHandling(() async {
      final response = await _chatRepository.sendMessage(request);
      final finalMessages = [...state.messages.where((m) => !m.id.startsWith('temp_user')), response.message];

      state = state.copyWith(
        isSending: false,
        messages: finalMessages,
        currentSessionId: response.sessionId,
      );
    }, sending: true,);
  }

  void startNewSession() {
    state = state.copyWith(clearCurrentSession: true, messages: []);
  }

  Future<void> deleteSession(String sessionId) async {
    await _runWithErrorHandling(() async {
      await _chatRepository.deleteSession(sessionId);
      if (state.currentSessionId == sessionId) {
        startNewSession();
      }
      await loadSessions();
    });
  }
  
  void clearCurrentSession() {
      state = state.copyWith(clearCurrentSession: true, messages: []);
  }
  
  // Placeholder
  void handleAction(ChatAction action) {
    // Logic to handle actions like 'create_task'
    print('Handling action: ${action.type}');
  }
}

// 3. Provider
final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>((ref) {
  return ChatNotifier(ref.watch(chatRepositoryProvider));
});
