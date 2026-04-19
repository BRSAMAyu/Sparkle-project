import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class TaskAssistantDormantState {
  const TaskAssistantDormantState({
    required this.mode,
    required this.focusSummary,
    required this.guidanceSource,
    required this.latestUxIntent,
    required this.latestAuroraPresence,
    this.lastRefreshReason,
    this.refreshCount = 0,
    this.usedColdStartFallback = false,
  });

  final String mode;
  final String focusSummary;
  final String guidanceSource;
  final String latestUxIntent;
  final String latestAuroraPresence;
  final String? lastRefreshReason;
  final int refreshCount;
  final bool usedColdStartFallback;

  TaskAssistantDormantState copyWith({
    String? mode,
    String? focusSummary,
    String? guidanceSource,
    String? latestUxIntent,
    String? latestAuroraPresence,
    String? lastRefreshReason,
    int? refreshCount,
    bool? usedColdStartFallback,
  }) =>
      TaskAssistantDormantState(
        mode: mode ?? this.mode,
        focusSummary: focusSummary ?? this.focusSummary,
        guidanceSource: guidanceSource ?? this.guidanceSource,
        latestUxIntent: latestUxIntent ?? this.latestUxIntent,
        latestAuroraPresence: latestAuroraPresence ?? this.latestAuroraPresence,
        lastRefreshReason: lastRefreshReason ?? this.lastRefreshReason,
        refreshCount: refreshCount ?? this.refreshCount,
        usedColdStartFallback:
            usedColdStartFallback ?? this.usedColdStartFallback,
      );
}

class TaskChatState {
  TaskChatState({
    this.isLoading = false,
    this.messages = const [],
    this.error,
    this.dormant,
  });
  final bool isLoading;
  final List<ChatMessageModel> messages;
  final String? error;
  final TaskAssistantDormantState? dormant;

  TaskChatState copyWith({
    bool? isLoading,
    List<ChatMessageModel>? messages,
    String? error,
    bool clearError = false,
    TaskAssistantDormantState? dormant,
    bool clearDormant = false,
  }) =>
      TaskChatState(
        isLoading: isLoading ?? this.isLoading,
        messages: messages ?? this.messages,
        error: clearError ? null : error ?? this.error,
        dormant: clearDormant ? null : dormant ?? this.dormant,
      );
}

class TaskChatNotifier extends StateNotifier<TaskChatState> {
  TaskChatNotifier(this._ref, this._repository, this.taskId)
      : super(TaskChatState());

  static const _planningMarkers = <String>[
    '规划',
    '计划',
    '拆解',
    '拆成',
    '路线',
    'workflow',
    'plan',
    'checkpoint',
  ];
  static const _taskAssistantMarkers = <String>[
    '当前任务',
    '当前这张任务卡',
    '带我做',
    '陪我做',
    '开始做',
    '进入任务',
    '不要再讲大道理',
  ];
  static const _frustrationMarkers = <String>[
    '做不下去',
    '卡住了',
    '不会',
    '太难了',
    '不想做',
    '崩了',
    '完全不会',
    'stuck',
    'frustrated',
  ];

  final Ref _ref;
  final ChatRepository _repository;
  final String taskId;
  String? _conversationId;

  bool get _dormantEnabled =>
      AppFeatureFlags.enableTaskAssistantDormantMode && taskId.trim().isNotEmpty;

  Future<void> primeDormantSession() async {
    if (!_dormantEnabled || state.dormant != null) return;
    final dormant = await _prepareDormantState(
      refreshReason: 'session_start',
      strongSignal: null,
      coldStart: true,
    );
    state = state.copyWith(dormant: dormant, clearError: true);
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    final strongSignal = _detectStrongSignal(text);
    final shouldInject = _dormantEnabled &&
        (_conversationId == null || state.messages.isEmpty || strongSignal != null);
    final refreshReason = strongSignal ?? (_conversationId == null ? 'session_start' : null);
    final dormant = shouldInject
        ? await _prepareDormantState(
            refreshReason: refreshReason,
            strongSignal: strongSignal,
            coldStart: _conversationId == null,
          )
        : state.dormant;
    final context = shouldInject && dormant != null
        ? await _buildDormantContextPayload(
            text: text,
            dormant: dormant,
            refreshReason: refreshReason ?? 'session_start',
            strongSignal: strongSignal,
            coldStart: _conversationId == null,
          )
        : null;

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
      dormant: dormant,
    );

    try {
      final response = await _repository.sendMessageToTask(
        taskId,
        text,
        _conversationId,
        context: context,
      );

      _conversationId = response.conversationId;

      final aiMsg = ChatMessageModel(
        id: DateTime.now().toString(),
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
        clearError: true,
        dormant: dormant?.copyWith(
          lastRefreshReason: refreshReason ?? dormant.lastRefreshReason,
          refreshCount: refreshReason == null
              ? dormant.refreshCount
              : dormant.refreshCount + 1,
        ),
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
        dormant: dormant,
      );
    }
  }

  String? _detectStrongSignal(String text) {
    final normalized = text.trim().toLowerCase();
    if (normalized.isEmpty) return null;
    if (_planningMarkers.any((marker) => normalized.contains(marker.toLowerCase()))) {
      return 'explicit_planning';
    }
    if (_frustrationMarkers.any((marker) => normalized.contains(marker.toLowerCase()))) {
      return 'frustration';
    }
    if (_taskAssistantMarkers.any((marker) => normalized.contains(marker.toLowerCase()))) {
      return 'task_reentry';
    }

    final structuralTurns = state.messages
        .where((message) => message.role == MessageRole.user)
        .toList()
        .reversed
        .take(2)
        .where((message) => _isStructuralTopic(message.content))
        .length;
    if (structuralTurns >= 2 && _isStructuralTopic(text)) {
      return 'structural_topic_turns';
    }
    return null;
  }

  bool _isStructuralTopic(String content) {
    final normalized = content.trim().toLowerCase();
    if (normalized.isEmpty) return false;
    return _planningMarkers.any((marker) => normalized.contains(marker.toLowerCase())) ||
        normalized.contains('怎么做') ||
        normalized.contains('下一步') ||
        normalized.contains('顺序');
  }

  TaskModel? _resolveTask() {
    final activeTask = _ref.read(activeTaskProvider);
    if (activeTask != null && activeTask.id == taskId) {
      return activeTask;
    }
    final taskState = _ref.read(taskListProvider);
    for (final task in taskState.tasks) {
      if (task.id == taskId) return task;
    }
    return null;
  }

  String _buildFocusSummary(TaskModel? task) {
    if (task == null) {
      return '当前任务执行会话，优先帮助用户推进眼前这张任务卡。';
    }
    final status = task.status.name;
    final estimate = task.estimatedMinutes == null || task.estimatedMinutes == 0
        ? '未设置时长'
        : '${task.estimatedMinutes} 分钟';
    return '当前聚焦任务：${task.title}；状态：$status；预计时长：$estimate。'
        '默认先帮助用户推进当前任务，而不是重新展开全量规划。';
  }

  Future<TaskGuidanceModel?> _resolveGuidance(TaskGuidanceAudience audience) async {
    final stateSnapshot = _ref.read(taskListProvider);
    final cacheKey = '${taskId}_${audience.wireValue}';
    final cached = stateSnapshot.taskGuidance[cacheKey];
    if (cached != null) return cached;

    final notifier = _ref.read(taskListProvider.notifier);
    final loaded = await notifier.loadTaskGuidance(taskId, audience: audience);
    if (loaded != null) return loaded;
    return notifier.createOrRefreshTaskGuidance(taskId, audience: audience);
  }

  Future<TaskAssistantDormantState> _prepareDormantState({
    required String? refreshReason,
    required String? strongSignal,
    required bool coldStart,
  }) async {
    final task = _resolveTask();
    TaskGuidanceModel? aiGuide;
    TaskGuidanceModel? humanGuide;
    try {
      aiGuide = await _resolveGuidance(TaskGuidanceAudience.ai);
    } catch (_) {
      aiGuide = null;
    }
    if (aiGuide == null) {
      try {
        humanGuide = await _resolveGuidance(TaskGuidanceAudience.human);
      } catch (_) {
        humanGuide = null;
      }
    }

    final guidanceSource = aiGuide != null
        ? 'task_guidance_ai'
        : (humanGuide != null ? 'human_guidance_fallback' : 'task_focus_only');
    return TaskAssistantDormantState(
      mode: 'dormant_candidate_v1',
      focusSummary: _buildFocusSummary(task),
      guidanceSource: guidanceSource,
      latestUxIntent: state.dormant?.latestUxIntent ?? 'routine',
      latestAuroraPresence: state.dormant?.latestAuroraPresence ?? 'ambient',
      lastRefreshReason: refreshReason ?? strongSignal,
      refreshCount: state.dormant?.refreshCount ?? 0,
      usedColdStartFallback: coldStart && state.dormant == null,
    );
  }

  Future<Map<String, dynamic>> _buildDormantContextPayload({
    required String text,
    required TaskAssistantDormantState dormant,
    required String refreshReason,
    required String? strongSignal,
    required bool coldStart,
  }) async {
    TaskGuidanceModel? aiGuide;
    TaskGuidanceModel? humanGuide;
    try {
      aiGuide = await _resolveGuidance(TaskGuidanceAudience.ai);
    } catch (_) {
      aiGuide = null;
    }
    if (aiGuide == null) {
      try {
        humanGuide = await _resolveGuidance(TaskGuidanceAudience.human);
      } catch (_) {
        humanGuide = null;
      }
    }
    final guidance = aiGuide ?? humanGuide;
    final guideSource = aiGuide != null
        ? 'task_guidance_ai'
        : (humanGuide != null ? 'human_guidance_fallback' : dormant.guidanceSource);
    final lastAssistant = state.messages.lastWhere(
      (message) => message.role == MessageRole.assistant,
      orElse: () => ChatMessageModel(
        id: 'task-assistant-initial',
        userId: 'ai',
        role: MessageRole.assistant,
        content: '',
        createdAt: DateTime.now(),
        taskId: taskId,
        conversationId: _conversationId ?? 'new',
      ),
    );
    return {
      'task_assistant': {
        'session_mode': dormant.mode,
        'cold_start': coldStart,
        'refresh_reason': refreshReason,
        'strong_signal': strongSignal,
        'injection': {
          'focus_summary': dormant.focusSummary,
          'guidance_content': guidance?.content,
          'guidance_source': guideSource,
          'latest_ux_intent': dormant.latestUxIntent,
          'latest_aurora_presence': dormant.latestAuroraPresence,
          'active_claims': const <String>[],
          'recent_probe_outcomes': const <String>[],
        },
        'outcome': {
          'turn_index': state.messages.where((message) => message.role == MessageRole.assistant).length,
          'latest_user_message': text,
          'latest_assistant_message': lastAssistant.content,
          'strong_signal': strongSignal,
          'refresh_reason': refreshReason,
          'used_cold_start_fallback': dormant.usedColdStartFallback,
          'metadata': {
            'conversation_id': _conversationId,
            'guidance_source': guideSource,
          },
        },
      },
    };
  }
}

final taskChatProvider =
    StateNotifierProvider.family<TaskChatNotifier, TaskChatState, String>(
        (ref, taskId) {
  final repository = ref.watch(chatRepositoryProvider);
  return TaskChatNotifier(ref, repository, taskId);
});
