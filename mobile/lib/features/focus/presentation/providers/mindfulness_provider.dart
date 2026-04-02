import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/focus/data/models/candidate_action_model.dart';
import 'package:sparkle/features/focus/data/services/context_service.dart';
import 'package:sparkle/features/focus/data/services/prediction_service.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/utils/task_identity.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// 分心事件类型
enum InterruptionType {
  appSwitch, // 切换应用
  notification, // 通知
  screenOff, // 熄屏
  unknown,
}

/// 分心事件记录
class InterruptionEvent {
  const InterruptionEvent({
    required this.timestamp,
    required this.type,
    this.duration,
  });
  final DateTime timestamp;
  final InterruptionType type;
  final Duration? duration;
}

/// 正念模式状态
class MindfulnessState {
  const MindfulnessState({
    this.isActive = false,
    this.startTime,
    this.elapsedSeconds = 0,
    this.interruptionCount = 0,
    this.interruptions = const [],
    this.isDNDEnabled = false,
    this.currentTask,
    this.exitConfirmationStep = 0,
    this.isPaused = false,
    this.translationRequestCount = 0,
    this.lastTranslationGranularity = 'word',
    this.candidateActions = const [],
    this.isLoggingSession = false,
    this.loggingError,
  });
  final bool isActive;
  final DateTime? startTime;
  final int elapsedSeconds;
  final int interruptionCount;
  final List<InterruptionEvent> interruptions;
  final bool isDNDEnabled;
  final TaskModel? currentTask;
  final int exitConfirmationStep; // 0: 未开始, 1-3: 三重确认步骤
  final bool isPaused;
  final int translationRequestCount; // Translation requests in this session
  final String lastTranslationGranularity; // 'word', 'sentence', 'page'
  final List<CandidateActionModel>
      candidateActions; // Predicted actions from signals pipeline
  final bool isLoggingSession;
  final String? loggingError;

  MindfulnessState copyWith({
    bool? isActive,
    DateTime? startTime,
    int? elapsedSeconds,
    int? interruptionCount,
    List<InterruptionEvent>? interruptions,
    bool? isDNDEnabled,
    TaskModel? currentTask,
    int? exitConfirmationStep,
    bool? isPaused,
    int? translationRequestCount,
    String? lastTranslationGranularity,
    List<CandidateActionModel>? candidateActions,
    bool? isLoggingSession,
    String? loggingError,
    bool clearTask = false,
    bool clearStartTime = false,
  }) =>
      MindfulnessState(
        isActive: isActive ?? this.isActive,
        startTime: clearStartTime ? null : (startTime ?? this.startTime),
        elapsedSeconds: elapsedSeconds ?? this.elapsedSeconds,
        interruptionCount: interruptionCount ?? this.interruptionCount,
        interruptions: interruptions ?? this.interruptions,
        isDNDEnabled: isDNDEnabled ?? this.isDNDEnabled,
        currentTask: clearTask ? null : (currentTask ?? this.currentTask),
        exitConfirmationStep: exitConfirmationStep ?? this.exitConfirmationStep,
        isPaused: isPaused ?? this.isPaused,
        translationRequestCount:
            translationRequestCount ?? this.translationRequestCount,
        lastTranslationGranularity:
            lastTranslationGranularity ?? this.lastTranslationGranularity,
        candidateActions: candidateActions ?? this.candidateActions,
        isLoggingSession: isLoggingSession ?? this.isLoggingSession,
        loggingError: loggingError ?? this.loggingError,
      );
}

class MindfulnessStopResult {
  const MindfulnessStopResult({
    required this.savedLocally,
    required this.syncedRemotely,
    this.message,
  });

  final bool savedLocally;
  final bool syncedRemotely;
  final String? message;
}

/// 正念模式状态管理器
class MindfulnessNotifier extends StateNotifier<MindfulnessState> {
  MindfulnessNotifier(
    this._ref,
    this._predictionService,
    this._taskRepository,
    this._eventStream,
    this._predictionAttribution,
    this._visualElementRepository,
  ) : super(const MindfulnessState()) {
    unawaited(_restoreSession());
  }

  static const String _sessionStorageKey = 'mindfulness.active_session';
  final Ref _ref;
  final PredictionService _predictionService;
  final TaskRepository _taskRepository;
  final AppEventStreamService _eventStream;
  final PredictionAttributionService _predictionAttribution;
  final VisualElementRepository _visualElementRepository;
  Timer? _timer;
  DateTime? _lastPauseTime;
  Duration _accumulatedPaused = Duration.zero;

  /// 开始正念模式
  void start(TaskModel task, {bool enableDND = false}) {
    _timer?.cancel();
    _accumulatedPaused = Duration.zero;
    _lastPauseTime = null;

    // Call backend to start task if it's pending
    if (task.status == TaskStatus.pending && isServerTaskId(task.id)) {
      unawaited(
        _taskRepository.startTask(task.id).then((_) {
          debugPrint('✅ Task started in backend: ${task.id}');
        }).catchError((Object error) {
          debugPrint('❌ Failed to start task in backend: $error');
          // We don't block the UI here, assuming optimistic success or retries
        }),
      );
    }

    state = MindfulnessState(
      isActive: true,
      startTime: DateTime.now(),
      currentTask: task,
      isDNDEnabled: enableDND,
    );

    _startTimer();
    unawaited(_persistSession());
  }

  /// 开始计时器
  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      _refreshElapsedSeconds();
    });
  }

  void _refreshElapsedSeconds() {
    if (!state.isActive || state.startTime == null) {
      return;
    }

    final sessionEnd =
        state.isPaused ? (_lastPauseTime ?? DateTime.now()) : DateTime.now();
    final totalSeconds = sessionEnd.difference(state.startTime!).inSeconds -
        _accumulatedPaused.inSeconds;
    final nextElapsed = totalSeconds < 0 ? 0 : totalSeconds;
    if (nextElapsed != state.elapsedSeconds) {
      state = state.copyWith(elapsedSeconds: nextElapsed);
    }
  }

  /// 暂停
  void pause() {
    if (!state.isActive || state.isPaused) {
      return;
    }
    _refreshElapsedSeconds();
    _lastPauseTime = DateTime.now();
    state = state.copyWith(isPaused: true);
    unawaited(_persistSession());
  }

  /// 恢复
  void resume() {
    if (!state.isActive || !state.isPaused) {
      return;
    }
    if (_lastPauseTime != null) {
      _accumulatedPaused += DateTime.now().difference(_lastPauseTime!);
    }
    _lastPauseTime = null;
    state = state.copyWith(isPaused: false);
    _refreshElapsedSeconds();
    unawaited(_persistSession());
  }

  /// 记录分心事件
  void recordInterruption(InterruptionType type) {
    final event = InterruptionEvent(
      timestamp: DateTime.now(),
      type: type,
    );

    state = state.copyWith(
      interruptionCount: state.interruptionCount + 1,
      interruptions: [...state.interruptions, event],
    );
    unawaited(_persistSession());
  }

  /// 开始退出确认流程
  void startExitConfirmation() {
    state = state.copyWith(exitConfirmationStep: 1);
  }

  /// 继续退出确认
  void continueExitConfirmation() {
    if (state.exitConfirmationStep < 3) {
      state =
          state.copyWith(exitConfirmationStep: state.exitConfirmationStep + 1);
    }
  }

  /// 取消退出确认
  void cancelExitConfirmation() {
    state = state.copyWith(exitConfirmationStep: 0);
  }

  /// 确认退出（完成三重确认后）
  void confirmExit() {
    unawaited(stop());
  }

  /// 停止正念模式
  Future<MindfulnessStopResult> stop() async {
    if (!state.isActive || state.startTime == null) {
      _timer?.cancel();
      _timer = null;
      await _clearPersistedSession();
      state = const MindfulnessState();
      return const MindfulnessStopResult(
        savedLocally: false,
        syncedRemotely: false,
      );
    }

    _refreshElapsedSeconds();
    final snapshot = state;
    final endTime = DateTime.now();
    final durationMinutes = (snapshot.elapsedSeconds / 60).floor();
    final status = snapshot.interruptionCount > 3 ? 'interrupted' : 'completed';
    var savedLocally = false;
    var syncedRemotely = false;
    String? resultMessage;

    state = snapshot.copyWith(isLoggingSession: true);
    await _persistSession();

    if (durationMinutes > 0) {
      try {
        final response =
            await _ref.read(focusStatisticsProvider.notifier).saveSession(
                  startTime: snapshot.startTime!,
                  endTime: endTime,
                  durationMinutes: durationMinutes,
                  focusType: 'mindfulness',
                  status: status,
                  taskId: snapshot.currentTask?.id,
                  taskTitle: snapshot.currentTask?.title,
                  interruptionCount: snapshot.interruptionCount,
                );

        savedLocally = true;
        syncedRemotely = response != null;

        if (response != null) {
          final linkedPrediction =
              await _predictionAttribution.consumeForExecution(
            executionType: 'focus',
            entityType: 'focus_session',
            entityId: response.response.id,
          );
          await _eventStream.recordEntityExecution(
            entityType: 'focus_session',
            entityId: response.response.id,
            actionType: 'complete_focus_session',
            source: 'mindfulness',
            payload: {
              'duration_minutes': durationMinutes,
              'status': status,
              if (snapshot.currentTask?.id != null)
                'task_id': snapshot.currentTask!.id,
              if (linkedPrediction != null) ...{
                'prediction_id': linkedPrediction['prediction_id'],
                'candidate_id': linkedPrediction['candidate_id'],
                'prediction_action_type': linkedPrediction['action_type'],
                'prediction_surface': linkedPrediction['surface'],
                'prediction_horizon': linkedPrediction['horizon'],
                'prediction_source': linkedPrediction['source'],
              },
            },
          );

          for (final achievement in response.unlockedAchievements) {
            final achievementId =
                (achievement['id'] ?? achievement['achievement_id'])
                    ?.toString();
            if (achievementId != null && achievementId.isNotEmpty) {
              try {
                await _visualElementRepository.unlockByAchievement(
                  achievementId,
                );
              } catch (e) {
                debugPrint(
                  'Visual element unlock failed for $achievementId: $e',
                );
              }
            }
          }
        } else {
          resultMessage = '专注记录已离线保存，稍后会自动重试同步。';
        }
      } catch (e) {
        state = state.copyWith(loggingError: e.toString());
        resultMessage = '专注记录保存失败：$e';
      }

      try {
        final envelope = await contextService.generateContextEnvelope(
          focusState: snapshot,
          translationRequests: snapshot.translationRequestCount,
          translationGranularity: snapshot.lastTranslationGranularity,
        );
        final resolvedUserId = _resolvePredictionUserId(snapshot);
        if (resolvedUserId != null && resolvedUserId.isNotEmpty) {
          final candidates = await _predictionService.requestPredictions(
            userId: resolvedUserId,
            contextEnvelope: envelope,
          );
          if (candidates.isNotEmpty) {
            state = state.copyWith(candidateActions: candidates);
          }
        }
      } catch (e) {
        debugPrint('❌ Failed to generate prediction: $e');
      }
    }

    _timer?.cancel();
    _timer = null;
    _accumulatedPaused = Duration.zero;
    _lastPauseTime = null;
    await _clearPersistedSession();
    state = const MindfulnessState();
    return MindfulnessStopResult(
      savedLocally: savedLocally,
      syncedRemotely: syncedRemotely,
      message: resultMessage,
    );
  }

  /// Record translation request (called by translation widgets)
  void recordTranslationRequest(String granularity) {
    state = state.copyWith(
      translationRequestCount: state.translationRequestCount + 1,
      lastTranslationGranularity: granularity,
    );
    debugPrint('📝 Translation request recorded: granularity=$granularity, '
        'total=${state.translationRequestCount}');
  }

  /// 切换勿扰模式
  void toggleDND(bool enabled) {
    state = state.copyWith(isDNDEnabled: enabled);
    unawaited(_persistSession());
  }

  /// 格式化时间显示
  String get formattedTime {
    final duration = Duration(seconds: state.elapsedSeconds);
    final hours = duration.inHours.toString().padLeft(2, '0');
    final minutes = (duration.inMinutes % 60).toString().padLeft(2, '0');
    final seconds = (duration.inSeconds % 60).toString().padLeft(2, '0');

    if (duration.inHours > 0) {
      return '$hours:$minutes:$seconds';
    }
    return '$minutes:$seconds';
  }

  /// 获取分钟数
  int get elapsedMinutes => (state.elapsedSeconds / 60).floor();

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  String? _resolvePredictionUserId(MindfulnessState snapshot) {
    final taskUserId = snapshot.currentTask?.userId;
    if (taskUserId != null && taskUserId.isNotEmpty) {
      return taskUserId;
    }
    final currentUser = _ref.read(currentUserProvider);
    return currentUser?.id;
  }

  Future<void> _restoreSession() async {
    final prefs = await SharedPreferences.getInstance();
    final rawSession = prefs.getString(_sessionStorageKey);
    if (rawSession == null || rawSession.isEmpty) {
      return;
    }

    try {
      final json = jsonDecode(rawSession);
      if (json is! Map<String, dynamic>) {
        await prefs.remove(_sessionStorageKey);
        return;
      }

      final rawTask = json['currentTask'];
      final restoredTask =
          rawTask is Map<String, dynamic> ? TaskModel.fromJson(rawTask) : null;
      final restoredStartTime = DateTime.tryParse(
        json['startTime'] as String? ?? '',
      );
      if (restoredStartTime == null) {
        await prefs.remove(_sessionStorageKey);
        return;
      }

      _accumulatedPaused = Duration(
        seconds: (json['accumulatedPausedSeconds'] as num?)?.toInt() ?? 0,
      );
      _lastPauseTime =
          DateTime.tryParse(json['lastPauseTime'] as String? ?? '');

      final interruptions =
          (json['interruptions'] as List<dynamic>? ?? const <dynamic>[])
              .whereType<Map<String, dynamic>>()
              .map(
                (item) => InterruptionEvent(
                  timestamp:
                      DateTime.tryParse(item['timestamp'] as String? ?? '') ??
                          restoredStartTime,
                  type: InterruptionType.values.firstWhere(
                    (value) => value.name == item['type'],
                    orElse: () => InterruptionType.unknown,
                  ),
                ),
              )
              .toList();

      state = MindfulnessState(
        isActive: json['isActive'] as bool? ?? false,
        startTime: restoredStartTime,
        elapsedSeconds: (json['elapsedSeconds'] as num?)?.toInt() ?? 0,
        interruptionCount: (json['interruptionCount'] as num?)?.toInt() ?? 0,
        interruptions: interruptions,
        isDNDEnabled: json['isDNDEnabled'] as bool? ?? false,
        currentTask: restoredTask,
        isPaused: json['isPaused'] as bool? ?? false,
        translationRequestCount:
            (json['translationRequestCount'] as num?)?.toInt() ?? 0,
        lastTranslationGranularity:
            json['lastTranslationGranularity'] as String? ?? 'word',
      );

      if (state.isActive) {
        _refreshElapsedSeconds();
        _startTimer();
      }
    } catch (e) {
      debugPrint('Failed to restore mindfulness session: $e');
      await prefs.remove(_sessionStorageKey);
    }
  }

  Future<void> _persistSession() async {
    if (!state.isActive || state.startTime == null) {
      await _clearPersistedSession();
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final payload = <String, dynamic>{
      'isActive': state.isActive,
      'startTime': state.startTime?.toIso8601String(),
      'elapsedSeconds': state.elapsedSeconds,
      'interruptionCount': state.interruptionCount,
      'interruptions': state.interruptions
          .map(
            (event) => <String, dynamic>{
              'timestamp': event.timestamp.toIso8601String(),
              'type': event.type.name,
            },
          )
          .toList(),
      'isDNDEnabled': state.isDNDEnabled,
      'currentTask': state.currentTask?.toJson(),
      'isPaused': state.isPaused,
      'accumulatedPausedSeconds': _accumulatedPaused.inSeconds,
      'lastPauseTime': _lastPauseTime?.toIso8601String(),
      'translationRequestCount': state.translationRequestCount,
      'lastTranslationGranularity': state.lastTranslationGranularity,
    };
    await prefs.setString(_sessionStorageKey, jsonEncode(payload));
  }

  Future<void> _clearPersistedSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionStorageKey);
  }
}

/// Prediction Service Provider
final predictionServiceProvider = Provider<PredictionService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return PredictionService(apiClient.dio);
});

/// 正念模式 Provider
final mindfulnessProvider =
    StateNotifierProvider<MindfulnessNotifier, MindfulnessState>((ref) {
  final predictionService = ref.watch(predictionServiceProvider);
  final taskRepository = ref.watch(taskRepositoryProvider);
  final eventStream = ref.watch(appEventStreamServiceProvider);
  final predictionAttribution = ref.watch(predictionAttributionServiceProvider);
  final visualElementRepository = ref.watch(visualElementRepositoryProvider);
  return MindfulnessNotifier(
    ref,
    predictionService,
    taskRepository,
    eventStream,
    predictionAttribution,
    visualElementRepository,
  );
});
