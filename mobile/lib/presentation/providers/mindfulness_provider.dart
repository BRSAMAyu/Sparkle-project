import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/repositories/focus_repository.dart';
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
      );
}

/// 正念模式状态管理器
class MindfulnessNotifier extends StateNotifier<MindfulnessState> {
  MindfulnessNotifier(this._focusRepository) : super(const MindfulnessState());

  final FocusRepository _focusRepository;
  Timer? _timer;
  // ignore: unused_field - used for pause tracking
  DateTime? _lastPauseTime;

  /// 开始正念模式
  void start(TaskModel task, {bool enableDND = false}) {
    _timer?.cancel();

    state = MindfulnessState(
      isActive: true,
      startTime: DateTime.now(),
      currentTask: task,
      isDNDEnabled: enableDND,
    );

    _startTimer();
  }

  /// 开始计时器
  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!state.isPaused) {
        state = state.copyWith(elapsedSeconds: state.elapsedSeconds + 1);
      }
    });
  }

  /// 暂停
  void pause() {
    _lastPauseTime = DateTime.now();
    state = state.copyWith(isPaused: true);
  }

  /// 恢复
  void resume() {
    _lastPauseTime = null;
    state = state.copyWith(isPaused: false);
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
    stop();
  }

  /// 停止正念模式
  Future<void> stop() async {
    // P0.3: Log focus session to backend before stopping
    if (state.startTime != null && state.isActive) {
      try {
        final endTime = DateTime.now();
        final durationMinutes = (state.elapsedSeconds / 60).floor();
        final status =
            state.interruptionCount > 3 ? 'interrupted' : 'completed';

        debugPrint(
            '📤 Logging focus session: ${durationMinutes}min, status=$status',);

        final response = await _focusRepository.logFocusSession(
          startTime: state.startTime!,
          endTime: endTime,
          durationMinutes: durationMinutes,
          taskId: state.currentTask?.id,
          status: status,
        );

        debugPrint(
            '✅ Focus session logged: ${response.rewards.flameEarned} flames earned',);

        // TODO: Show reward feedback to user
        // Can emit an event or update state to trigger UI update
      } catch (e) {
        // Log error but don't block exit
        debugPrint('❌ Failed to log focus session: $e');
      }
    }

    _timer?.cancel();
    _timer = null;
    state = const MindfulnessState();
  }

  /// 切换勿扰模式
  void toggleDND(bool enabled) {
    state = state.copyWith(isDNDEnabled: enabled);
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
}

/// 正念模式 Provider
final mindfulnessProvider =
    StateNotifierProvider<MindfulnessNotifier, MindfulnessState>((ref) {
  final focusRepository = ref.watch(focusRepositoryProvider);
  return MindfulnessNotifier(focusRepository);
});
