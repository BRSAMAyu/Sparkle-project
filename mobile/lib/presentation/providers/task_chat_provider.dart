import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/repositories/chat_repository.dart';
import 'package:sparkle/presentation/providers/chat_provider.dart';

class TaskChatState {
  final bool isLoading;
  final List<ChatMessageModel> messages;
  final String? error;

  TaskChatState({
    this.isLoading = false,
    this.messages = const [],
    this.error,
  });

  TaskChatState copyWith({
    bool? isLoading,
    List<ChatMessageModel>? messages,
    String? error,
  }) {
    return TaskChatState(
      isLoading: isLoading ?? this.isLoading,
      messages: messages ?? this.messages,
      error: error ?? this.error,
    );
  }
}

class TaskChatNotifier extends StateNotifier<TaskChatState> {
  final ChatRepository _repository;
  final String taskId;
  String? _conversationId;

  TaskChatNotifier(this._repository, this.taskId) : super(TaskChatState());

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    // 1. Add user message
    final userMsg = ChatMessageModel(
      id: DateTime.now().toString(),
      userId: 'current_user',
      role: MessageRole.user,
      content: text,
      createdAt: DateTime.now(),
      taskId: taskId,
      conversationId: _conversationId ?? 'new',
    );

    state = state.copyWith(
      messages: [...state.messages, userMsg],
      isLoading: true,
      error: null,
    );

    try {
      // 2. Call API
      final response = await _repository.sendMessageToTask(taskId, text, _conversationId);
      
      _conversationId = response.conversationId;

      // 3. Add assistant message
      final aiMsg = ChatMessageModel(
        id: DateTime.now().toString(), // Should come from backend ideally
        userId: 'ai',
        role: MessageRole.assistant,
        content: response.message,
        createdAt: DateTime.now(),
        taskId: taskId,
        conversationId: _conversationId!,
      );

      state = state.copyWith(
        messages: [...state.messages, aiMsg],
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }
}

final taskChatProvider = StateNotifierProvider.family<TaskChatNotifier, TaskChatState, String>((ref, taskId) {
  final repository = ref.watch(chatRepositoryProvider);
  return TaskChatNotifier(repository, taskId);
});
