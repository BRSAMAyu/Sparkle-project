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

  ChatState({
    this.isLoading = false,
    this.isSending = false,
    this.currentSessionId,
    this.messages = const [],
    this.sessions = const [],
    this.error,
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
  }) {
    return ChatState(
      isLoading: isLoading ?? this.isLoading,
      isSending: isSending ?? this.isSending,
      currentSessionId: clearCurrentSession ? null : currentSessionId ?? this.currentSessionId,
      messages: messages ?? this.messages,
      sessions: sessions ?? this.sessions,
      error: clearError ? null : error ?? this.error,
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

  Future<void> sendMessage(String content, {String? taskId}) async {
    final request = ChatRequest(
      content: content,
      sessionId: state.currentSessionId,
      taskId: taskId,
    );

    // Add user message to UI immediately for responsiveness
    final userMessage = ChatMessageModel(
        id: 'temp_user_${DateTime.now().millisecondsSinceEpoch}',
        userId: '', // This should be filled from a user provider
        sessionId: state.currentSessionId ?? 'temp_session',
        role: MessageRole.user,
        content: content,
        createdAt: DateTime.now(),);
    state = state.copyWith(messages: [...state.messages, userMessage]);

    await _runWithErrorHandling(() async {
      final response = await _chatRepository.sendMessage(request);
      // Replace user's temp message and add AI's message
      final newMessages = state.messages.where((m) => !m.id.startsWith('temp_user')).toList();
      newMessages.add(response.message); // This assumes the backend returns the user's persisted message as well, or we can construct it. Let's assume we just add the AI one.
       
       // A better way would be for backend to return both persisted user message and new AI message
       // For now, let's just add the AI message.
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
