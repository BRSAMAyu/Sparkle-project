import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';

/// Describes the current dormant-mode injection state for a task assistant session.
class DormantInjectionState {
  DormantInjectionState({
    this.hasInjection = false,
    this.injectionItems = const [],
    this.uxIntent = 'routine',
    this.auroraPresence = 'ambient',
  });
  final bool hasInjection;
  final List<DormantInjectionItem> injectionItems;
  final String uxIntent;
  final String auroraPresence;

  DormantInjectionState copyWith({
    bool? hasInjection,
    List<DormantInjectionItem>? injectionItems,
    String? uxIntent,
    String? auroraPresence,
  }) =>
      DormantInjectionState(
        hasInjection: hasInjection ?? this.hasInjection,
        injectionItems: injectionItems ?? this.injectionItems,
        uxIntent: uxIntent ?? this.uxIntent,
        auroraPresence: auroraPresence ?? this.auroraPresence,
      );
}

/// A single dormant injection item received from the backend.
class DormantInjectionItem {
  DormantInjectionItem({
    required this.kind,
    required this.available,
    this.payload,
  });
  final String kind;
  final bool available;
  final Map<String, dynamic>? payload;
}

class TaskChatState {
  TaskChatState({
    this.isLoading = false,
    this.messages = const [],
    this.error,
    this.dormantInjection,
    this.turnCount = 0,
  });
  final bool isLoading;
  final List<ChatMessageModel> messages;
  final String? error;
  final DormantInjectionState? dormantInjection;
  final int turnCount;

  TaskChatState copyWith({
    bool? isLoading,
    List<ChatMessageModel>? messages,
    String? error,
    bool clearError = false,
    DormantInjectionState? dormantInjection,
    int? turnCount,
  }) =>
      TaskChatState(
        isLoading: isLoading ?? this.isLoading,
        messages: messages ?? this.messages,
        error: clearError ? null : error ?? this.error,
        dormantInjection: dormantInjection ?? this.dormantInjection,
        turnCount: turnCount ?? this.turnCount,
      );
}

class TaskChatNotifier extends StateNotifier<TaskChatState> {
  TaskChatNotifier(this._repository, this.taskId) : super(TaskChatState());
  final ChatRepository _repository;
  final String taskId;
  String? _conversationId;

  /// Parse dormant injection metadata from backend response.
  DormantInjectionState? parseDormantMeta(Map<String, dynamic>? meta) {
    if (meta == null) return null;
    final items = <DormantInjectionItem>[];
    final rawItems = meta['items'];
    if (rawItems is List) {
      for (final item in rawItems) {
        if (item is Map<String, dynamic>) {
          items.add(
            DormantInjectionItem(
              kind: item['kind'] as String? ?? '',
              available: item['available'] as bool? ?? false,
              payload: item['payload'] as Map<String, dynamic>?,
            ),
          );
        }
      }
    }
    if (items.isEmpty && meta['ux_intent'] == null) return null;
    return DormantInjectionState(
      hasInjection: true,
      injectionItems: items,
      uxIntent: meta['ux_intent'] as String? ?? 'routine',
      auroraPresence: meta['aurora_presence'] as String? ?? 'ambient',
    );
  }

  Future<void> sendMessage(
    String text, {
    Map<String, dynamic>? extraContext,
  }) async {
    if (text.trim().isEmpty) return;

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
      clearError: true,
    );

    try {
      final result = await _repository.sendMessageToTask(
        taskId,
        text,
        _conversationId,
        extraContext,
      );

      _conversationId = result.response.conversationId;

      final aiMsg = ChatMessageModel(
        id: DateTime.now().toString(),
        userId: 'ai',
        role: MessageRole.assistant,
        content: result.response.message,
        createdAt: DateTime.now(),
        taskId: taskId,
        conversationId: _conversationId!,
      );

      // Parse dormant injection metadata from backend response
      final dormantState = parseDormantMeta(result.dormantInjection);

      state = state.copyWith(
        messages: [...state.messages, aiMsg],
        isLoading: false,
        clearError: true,
        turnCount: state.turnCount + 1,
        dormantInjection: dormantState,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }
}

final taskChatProvider =
    StateNotifierProvider.family<TaskChatNotifier, TaskChatState, String>(
        (ref, taskId) {
  final repository = ref.watch(chatRepositoryProvider);
  return TaskChatNotifier(repository, taskId);
});
