import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart'
    hide ButtonVariant;
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/bgm_scope.dart';
import 'package:sparkle/core/widgets/scene_atmosphere_layer.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/focus/data/repositories/focus_repository.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart'
    as focus_stats;
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_context_summary.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/data/models/execution_record_model.dart';
import 'package:sparkle/features/task/data/models/execution_template_model.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/presentation/execution_copy.dart';
import 'package:sparkle/features/task/presentation/providers/subtask_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/blocking_interceptor_dialog.dart';
import 'package:sparkle/features/task/presentation/widgets/quick_tools_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/subtask_list_widget.dart';
import 'package:sparkle/features/task/presentation/widgets/task_chat_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_approval_card.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_status_indicator.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_template_card.dart';
import 'package:sparkle/features/task/presentation/widgets/task_feedback_dialog.dart';
import 'package:sparkle/features/task/presentation/widgets/timer_widget.dart';
import 'package:sparkle/features/task/task_routes.dart';
import 'package:sparkle/features/task/utils/task_identity.dart';
import 'package:sparkle/features/visual_elements/presentation/providers/visual_elements_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

LinearGradient _taskWarmActionGradient(BuildContext context) {
  final isDark = Theme.of(context).brightness == Brightness.dark;
  return LinearGradient(
    colors: [
      DS.primaryBase,
      Color.lerp(
            DS.primaryBase,
            isDark ? DS.surfaceTertiary : DS.surfaceSecondary,
            isDark ? 0.24 : 0.16,
          ) ??
          DS.primaryBase,
    ],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}

final openClawTaskNudgeDismissedProvider = StateProvider<bool>((ref) => false);
final openClawTaskNudgeExpandedProvider = StateProvider<bool>((ref) => false);

class TaskExecutionScreen extends ConsumerStatefulWidget {
  const TaskExecutionScreen({super.key, this.origin});

  final String? origin;

  @override
  ConsumerState<TaskExecutionScreen> createState() =>
      _TaskExecutionScreenState();
}

class _TaskExecutionScreenState extends ConsumerState<TaskExecutionScreen> {
  int _elapsedSeconds = 0;
  bool _showCelebration = false;
  bool _showCompletionPanel = false;
  bool _showCompletionStats = false;
  bool _playCompletionConfetti = false;
  TaskCompletionResult? _completionResult;
  bool _completionFlowFinished = false;
  Timer? _celebrationDismissTimer;
  Timer? _completionPanelTimer;
  Timer? _completionStatsTimer;
  Timer? _completionAudioTimer;
  Timer? _executionRefreshTimer;
  int _completionMinutesSnapshot = 0;
  int? _todayFocusMinutesSnapshot;

  // Timer Enhancement State
  TimerMode _timerMode = TimerMode.countUp;
  int _currentTimerDuration = 0; // In seconds
  bool _isPomodoroMode = false;
  int _pomodoroCycle = 0; // 0: work, 1: break, 2: long break
  int _timerResetVersion = 0;

  // Focus Protection State
  DateTime? _pageEnterTime;

  @override
  void initState() {
    super.initState();
    _pageEnterTime = DateTime.now(); // Record page entry time
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    unawaited(BgmService.setFocusSession(true));
    final task = ref.read(activeTaskProvider);
    final estimated = task?.estimatedMinutes ?? 0;
    _currentTimerDuration = estimated > 0 ? estimated * 60 : 0;
    if (estimated > 0) _timerMode = TimerMode.countDown;

    // 🔧 Fix: Call startTask if the task is PENDING
    // This ensures backend state transitions to IN_PROGRESS when user enters execution screen
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final activeTask = ref.read(activeTaskProvider);
      ref.listenManual<String>(
        openClawConnectionProvider.select(
          (service) => [
            service.config.normalizedGatewayUrl,
            service.config.transport,
            service.config.authToken ?? '',
            service.config.deviceToken ?? '',
            service.info.status.name,
            '${service.queuedRequestCount}',
          ].join('|'),
        ),
        (previous, next) {
          if (previous == null || previous == next) return;
          ref.read(openClawTaskNudgeDismissedProvider.notifier).state = false;
          ref.read(openClawTaskNudgeExpandedProvider.notifier).state = false;
        },
      );
      if (activeTask != null && isServerTaskId(activeTask.id)) {
        ref.listenManual<ExecutionIntentStatus?>(
          taskListProvider.select(
            (state) => state.taskExecutions[activeTask.id]?.status,
          ),
          (previous, next) {
            if (previous == null || previous == next) return;
            ref.read(openClawTaskNudgeDismissedProvider.notifier).state = false;
            ref.read(openClawTaskNudgeExpandedProvider.notifier).state = false;
          },
        );
        unawaited(
          ref
              .read(taskListProvider.notifier)
              .loadTaskExecutionState(activeTask.id),
        );
        unawaited(
          ref
              .read(taskListProvider.notifier)
              .loadTaskExecutionTemplates(activeTask.id),
        );
        _startExecutionPolling(activeTask.id);

        if (activeTask.status == TaskStatus.pending) {
          unawaited(
            ref
                .read(taskListProvider.notifier)
                .startTask(activeTask.id)
                .catchError(
              (Object error, StackTrace stackTrace) {
                debugPrint('Error starting task: $error');
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        context.l10n.taskExecutionStartFailed(
                          error is DioException
                              ? (error.message ?? error.toString())
                              : error.toString(),
                        ),
                      ),
                      backgroundColor: DS.error,
                    ),
                  );
                }
              },
            ),
          );
        }
      }
    });
  }

  @override
  void dispose() {
    unawaited(BgmService.setFocusSession(false));
    _celebrationDismissTimer?.cancel();
    _completionPanelTimer?.cancel();
    _completionStatsTimer?.cancel();
    _completionAudioTimer?.cancel();
    _executionRefreshTimer?.cancel();
    super.dispose();
  }

  void _startExecutionPolling(String taskId) {
    _executionRefreshTimer?.cancel();
    _executionRefreshTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      unawaited(() async {
        final latest = await ref
            .read(taskListProvider.notifier)
            .loadTaskExecutionState(taskId);
        if (!mounted) return;
        if (latest == null || latest.isTerminal) {
          _executionRefreshTimer?.cancel();
        }
      }());
    });
  }

  bool _shouldShowFullExitConfirmation() {
    if (_pageEnterTime == null) return true;
    final elapsed = DateTime.now().difference(_pageEnterTime!);
    return elapsed.inSeconds >= 15; // Require confirmation after 15 seconds
  }

  Future<bool> _onWillPop() async {
    if (_showCelebration) return false; // Don't pop during celebration

    // Quick exit within 15 seconds (mis-click protection)
    if (!_shouldShowFullExitConfirmation()) {
      return true;
    }

    // Show focus protection confirmation after 15 seconds
    final elapsedSeconds = DateTime.now().difference(_pageEnterTime!).inSeconds;
    final elapsedMinutes = (elapsedSeconds / 60).floor();

    final shouldPop = await showSensoryDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => _TaskExitConfirmationDialog(
        elapsedSeconds: elapsedSeconds,
        elapsedMinutes: elapsedMinutes,
      ),
    );
    return shouldPop ?? false;
  }

  Future<void> _handleCompletion(int minutes, String? note) async {
    if (_completionFlowFinished) return;

    setState(() {
      _showCelebration = true;
      _showCompletionPanel = false;
      _showCompletionStats = false;
      _playCompletionConfetti = true;
      _completionFlowFinished = false;
      _completionMinutesSnapshot = minutes;
      _todayFocusMinutesSnapshot = null;
    });

    _scheduleFocusCompletionSequence();

    final task = ref.read(activeTaskProvider);
    if (task != null) {
      if (isLocalOnlyTaskId(task.id)) {
        if (mounted) {
          setState(() {
            _completionResult = TaskCompletionResult(
              task: task.toJson(),
              feedback: '本次自由专注已完成。',
            );
          });
          unawaited(_loadFocusCompletionSummary(minutes));
          final reduceMotion = MediaQuery.maybeOf(context)?.disableAnimations ??
              MediaQuery.maybeOf(context)?.accessibleNavigation ??
              false;
          if (reduceMotion) {
            _finishCompletionFlow();
          } else {
            _scheduleCelebrationAutoDismiss();
          }
        }
        return;
      }

      // Run completion in background while animation plays
      final result = await ref
          .read(taskListProvider.notifier)
          .completeTask(task.id, minutes, note);
      if (mounted) {
        setState(() {
          _completionResult = result;
        });
        unawaited(_loadFocusCompletionSummary(minutes));
        if (result != null) {
          unawaited(_processAchievementUnlocks(result));
        }
        if (result == null) {
          _finishCompletionFlow(showFeedbackDialog: false);
          AppFeedback.error(context, context.l10n.taskExecutionSyncFailed);
          return;
        }
        final reduceMotion = MediaQuery.maybeOf(context)?.disableAnimations ??
            MediaQuery.maybeOf(context)?.accessibleNavigation ??
            false;
        if (reduceMotion) {
          _finishCompletionFlow();
        } else {
          _scheduleCelebrationAutoDismiss();
        }
      }
    }
  }

  void _scheduleFocusCompletionSequence() {
    _completionPanelTimer?.cancel();
    _completionStatsTimer?.cancel();
    _completionAudioTimer?.cancel();

    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.focusComplete),
    );

    final reduceMotion = MediaQuery.maybeOf(context)?.disableAnimations ??
        MediaQuery.maybeOf(context)?.accessibleNavigation ??
        false;

    if (reduceMotion) {
      setState(() {
        _showCompletionPanel = true;
        _showCompletionStats = true;
      });
      unawaited(BgmService.duckTemporarily(factor: 0.3));
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
      return;
    }

    _completionPanelTimer = Timer(const Duration(milliseconds: 120), () {
      if (!mounted) return;
      setState(() {
        _showCompletionPanel = true;
      });
    });

    _completionStatsTimer = Timer(const Duration(milliseconds: 300), () {
      if (!mounted) return;
      setState(() {
        _showCompletionStats = true;
      });
    });

    _completionAudioTimer = Timer(const Duration(milliseconds: 400), () {
      unawaited(BgmService.duckTemporarily(factor: 0.3));
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
    });
  }

  void _scheduleCelebrationAutoDismiss() {
    _celebrationDismissTimer?.cancel();
    _celebrationDismissTimer = Timer(
      const Duration(milliseconds: 1650),
      _finishCompletionFlow,
    );
  }

  Future<void> _loadFocusCompletionSummary(int minutes) async {
    final focusStatsState = ref.read(focus_stats.focusStatisticsProvider);
    final fallbackToday =
        (focusStatsState.todayMinutes > 0 ? focusStatsState.todayMinutes : 0) +
            minutes;
    if (mounted) {
      setState(() {
        _todayFocusMinutesSnapshot = fallbackToday;
      });
    }

    try {
      final stats = await ref.read(focusRepositoryProvider).getFocusStats();
      if (!mounted) return;
      setState(() {
        _todayFocusMinutesSnapshot = stats.totalMinutes;
      });
      unawaited(
        ref.read(focus_stats.focusStatisticsProvider.notifier).loadTodayStats(),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _todayFocusMinutesSnapshot ??= fallbackToday;
      });
    }
  }

  Future<void> _processAchievementUnlocks(TaskCompletionResult result) async {
    if (result.unlockedAchievements.isEmpty) return;
    final notifier = ref.read(visualElementsNotifierProvider.notifier);
    for (final achievement in result.unlockedAchievements) {
      final id = (achievement is Map<String, dynamic>)
          ? (achievement['id'] ?? achievement['achievement_id'])?.toString()
          : null;
      if (id != null && id.isNotEmpty) {
        try {
          await notifier.unlockByAchievement(id);
        } catch (e) {
          debugPrint('Visual element unlock failed for $id: $e');
        }
      }
    }
  }

  void _finishCompletionFlow({bool showFeedbackDialog = true}) {
    if (!mounted || _completionFlowFinished) return;
    _completionFlowFinished = true;
    _celebrationDismissTimer?.cancel();
    _completionPanelTimer?.cancel();
    _completionStatsTimer?.cancel();
    _completionAudioTimer?.cancel();

    final result = _completionResult;
    setState(() {
      _showCelebration = false;
      _showCompletionPanel = false;
      _showCompletionStats = false;
      _playCompletionConfetti = false;
    });

    if (!showFeedbackDialog || result == null) {
      return;
    }

    final task = ref.read(activeTaskProvider);
    showSensoryDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => TaskFeedbackDialog(
        result: result,
        taskId: task?.id ?? '',
        onClose: () {
          Navigator.of(context).pop();
          if (widget.origin == 'focus') {
            context.go('/focus');
            return;
          }
          if (context.canPop()) {
            context.pop();
            return;
          }
          context.go(TaskRoutes.home);
        },
      ),
    );
  }

  void _skipCelebration() {
    if (!_showCelebration) return;
    _finishCompletionFlow();
  }

  void _setPresetDuration(int minutes) {
    setState(() {
      _timerMode = TimerMode.countDown;
      _currentTimerDuration = minutes * 60;
      _isPomodoroMode = false; // Disable Pomodoro if a preset is selected
    });
  }

  void _togglePomodoro() {
    setState(() {
      _isPomodoroMode = !_isPomodoroMode;
      if (_isPomodoroMode) {
        _timerMode = TimerMode.countDown; // Pomodoro is always countdown
        _currentTimerDuration = 25 * 60; // Start with work phase
        _pomodoroCycle = 0;
      } else {
        // Reset to default or previous state if exiting Pomodoro
        _timerMode = TimerMode.countUp;
        _currentTimerDuration = 0;
      }
    });
  }

  void _onPomodoroComplete() {
    if (!_isPomodoroMode) return;

    if (_pomodoroCycle == 0) {
      // Work phase completed
      _pomodoroCycle = 1;
      _currentTimerDuration = 5 * 60; // Short break
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.l10n.pomodoroWorkFinished)),
      );
    } else if (_pomodoroCycle == 1) {
      // Short break completed
      _pomodoroCycle = 0;
      _currentTimerDuration = 25 * 60; // Next work phase
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.l10n.pomodoroBreakFinished)),
      );
    }
    // Extend for long breaks if desired
    setState(() {}); // Trigger rebuild for TimerWidget to update
  }

  void _resetTimer() {
    setState(() {
      _elapsedSeconds = 0;
      if (_isPomodoroMode) {
        _currentTimerDuration = _pomodoroCycle == 0 ? 25 * 60 : 5 * 60;
      } else if (_timerMode == TimerMode.countUp) {
        _currentTimerDuration = 0;
      }
      _timerResetVersion += 1;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final activeTask = ref.watch(activeTaskProvider);

    if (activeTask == null) {
      return GraphiteScaffold(
        appBar: AppBar(
          flexibleSpace: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [DS.surfaceCanvas, DS.surfacePanel],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
          ),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.error_outline_rounded,
                size: 80,
                color: DS.neutral400,
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                l10n.taskExecutionNoTask,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: DS.neutral700,
                    ),
              ),
              const SizedBox(height: DS.spacing24),
              CustomButton.primary(
                text: l10n.back,
                icon: Icons.arrow_back,
                onPressed: () => context.pop(),
              ),
            ],
          ),
        ),
      );
    }

    final hasPersistentTask = isServerTaskId(activeTask.id);

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        final shouldPop = await _onWillPop();
        if (!mounted) return;
        if (shouldPop) {
          Navigator.of(context).pop();
        }
      },
      child: Stack(
        children: [
          GraphiteScaffold(
            extendBodyBehindAppBar: true,
            appBar: AppBar(
              leading: SparkleIconButton(
                variant: ButtonVariant.ghost,
                icon: const Icon(Icons.arrow_back),
                onPressed: () async {
                  final shouldPop = await _onWillPop();
                  if (mounted && shouldPop) {
                    context.pop();
                  }
                },
              ),
              backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
              elevation: 0,
              iconTheme: IconThemeData(color: DS.textPrimary),
              title: Text(
                activeTask.title,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: DS.textPrimary),
              ),
            ),
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    DS.surfaceCanvas,
                    DS.surfacePanel,
                    DS.surfacePrimary,
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: SafeArea(
                child: ContentConstraint(
                  child: Column(
                    children: [
                      Expanded(
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.all(DS.spacing16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              const SizedBox(height: DS.spacing16),
                              // 1. Focus Mode Entry Card (Prominent)
                              _buildFocusEntryCard(context, activeTask),
                              const SizedBox(height: DS.spacing24),

                              // Divider
                              Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: DS.spacing8,
                                  vertical: DS.spacing16,
                                ),
                                child: Divider(
                                  height: 1,
                                  thickness: 1,
                                  color: DS.neutral200,
                                ),
                              ),

                              // 2. Timer Area (Auxiliary)
                              Text(
                                l10n.taskExecutionTimerLabel,
                                style: TextStyle(
                                  fontSize: DS.fontSizeSm,
                                  color: DS.neutral500,
                                  fontWeight: FontWeight.w500,
                                ),
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: DS.spacing12),
                              Center(
                                child: TimerWidget(
                                  key: ValueKey(
                                    '$_currentTimerDuration-$_timerResetVersion',
                                  ),
                                  mode: _timerMode,
                                  initialSeconds: _currentTimerDuration,
                                  maxSeconds: _isPomodoroMode
                                      ? (_pomodoroCycle == 0 ? 25 * 60 : 5 * 60)
                                      : null,
                                  onTick: (seconds) =>
                                      _elapsedSeconds = seconds,
                                  onStateChange: (_) {},
                                  onComplete:
                                      _onPomodoroComplete, // Call only for Pomodoro
                                ),
                              ),
                              const SizedBox(height: DS.spacing24),

                              // Timer Controls (without mindfulness button)
                              _TimerControls(
                                isPomodoroMode: _isPomodoroMode,
                                onTogglePomodoro: _togglePomodoro,
                                onSetPreset: _setPresetDuration,
                                onReset: _resetTimer,
                              ),
                              const SizedBox(height: DS.spacing24),

                              // Plan Context Summary (if task has a plan)
                              if (activeTask.planId != null)
                                PlanContextSummary(planId: activeTask.planId),
                              if (activeTask.planId != null)
                                const SizedBox(height: DS.spacing16),

                              // 2. Task Guide Area
                              _TaskGuidePanel(task: activeTask),
                              const SizedBox(height: DS.spacing16),

                              // Subtasks Section (if task has subtasks)
                              Consumer(
                                builder: (context, ref, child) {
                                  if (!hasPersistentTask) {
                                    return const SizedBox.shrink();
                                  }
                                  final subtaskState = ref.watch(
                                    subtaskNotifierProvider(activeTask.id),
                                  );
                                  if (subtaskState.total == 0) {
                                    return const SizedBox.shrink();
                                  }

                                  return GraphiteCardSurface(
                                    padding: EdgeInsets.zero,
                                    child: ExpansionTile(
                                      shape: const Border(),
                                      tilePadding: const EdgeInsets.symmetric(
                                        horizontal: DS.spacing16,
                                        vertical: DS.spacing12,
                                      ),
                                      title: Row(
                                        children: [
                                          Container(
                                            padding: const EdgeInsets.all(10),
                                            decoration: BoxDecoration(
                                              color: DS.surfaceSecondary,
                                              shape: BoxShape.circle,
                                              border: Border.all(
                                                color: DS.borderSubtle,
                                              ),
                                            ),
                                            child: Icon(
                                              Icons.checklist,
                                              color: DS.primaryBase,
                                              size: 22,
                                            ),
                                          ),
                                          const SizedBox(width: DS.spacing12),
                                          Text(
                                            '${l10n.subtaskTitle} (${subtaskState.completed}/${subtaskState.total})',
                                            style: Theme.of(context)
                                                .textTheme
                                                .titleMedium
                                                ?.copyWith(
                                                  fontWeight: DS.fontWeightBold,
                                                  color: DS.neutral900,
                                                ),
                                          ),
                                        ],
                                      ),
                                      children: [
                                        Padding(
                                          padding: const EdgeInsets.all(
                                            DS.spacing16,
                                          ),
                                          child: SubtaskListWidget(
                                            parentTaskId: activeTask.id,
                                            onSubtaskToggle: (_) {},
                                            onSubtaskDelete: (_) {},
                                            readOnly: true,
                                          ),
                                        ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                              const SizedBox(height: DS.spacing16),

                              _ExecutionAssistPanel(task: activeTask),
                              const SizedBox(height: DS.spacing16),

                              // 3. Quick Tools Panel
                              QuickToolsPanel(
                                taskId:
                                    hasPersistentTask ? activeTask.id : null,
                              ),
                              const SizedBox(height: DS.spacing16),

                              // 4. Task Chat Panel
                              TaskChatPanel(
                                taskId: hasPersistentTask ? activeTask.id : '',
                                isAvailable: hasPersistentTask,
                              ),
                            ],
                          ),
                        ),
                      ),
                      _BottomControls(
                        task: activeTask,
                        elapsedSeconds: _elapsedSeconds,
                        onComplete: _handleCompletion,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Celebration Overlay
          if (_showCelebration)
            Positioned.fill(
              child: BgmScope(
                track: BgmTrack.achievement,
                priority: BgmPriority.stage,
                child: GestureDetector(
                  onTap: _skipCelebration,
                  behavior: HitTestBehavior.opaque,
                  child: TweenAnimationBuilder<double>(
                    tween: Tween<double>(begin: 0, end: 1),
                    duration: const Duration(milliseconds: 620),
                    curve: Curves.easeOutCubic,
                    builder: (context, warmth, child) => DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Color.lerp(
                                  const Color(0xFF0D1B2A),
                                  const Color(0xFF53321F),
                                  warmth,
                                ) ??
                                const Color(0xFF0D1B2A),
                            Color.lerp(
                                  DS.overlay50.withValues(alpha: 0.90),
                                  const Color(0xFFF0B77A)
                                      .withValues(alpha: 0.78),
                                  warmth,
                                ) ??
                                DS.overlay50.withValues(alpha: 0.84),
                          ],
                        ),
                      ),
                      child: Stack(
                        fit: StackFit.expand,
                        children: [
                          Opacity(
                            opacity: 0.9,
                            child: SceneAtmosphereLayer(
                              atmosphere: ExperienceAtmosphere.focusBreath,
                            ),
                          ),
                          SparkleConfetti(
                            play: _playCompletionConfetti,
                            intensity: SparkleCelebrationIntensity.large,
                            alignment: Alignment.topCenter,
                            enableSensory: false,
                          ),
                          child!,
                        ],
                      ),
                    ),
                    child: Center(
                      child: _FocusCompletionPanel(
                        visible: _showCompletionPanel,
                        animateStats: _showCompletionStats,
                        sessionMinutes: _completionMinutesSnapshot,
                        todayMinutes: _todayFocusMinutesSnapshot ??
                            _completionMinutesSnapshot,
                        expGained: activeTask.difficulty * 10,
                        unlockedAchievements:
                            _completionResult?.unlockedAchievements ?? const [],
                        onSkip: _skipCelebration,
                        continueLabel: l10n.taskExecutionTapToContinue,
                        skipLabel: l10n.taskExecutionSkipAnimation,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildFocusEntryCard(BuildContext context, TaskModel task) =>
      GraphiteCardSurface(
        margin: const EdgeInsets.symmetric(horizontal: DS.spacing4),
        padding: const EdgeInsets.all(DS.xl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.md),
                  decoration: BoxDecoration(
                    color: DS.surfaceSecondary,
                    shape: BoxShape.circle,
                    border: Border.all(color: DS.borderSubtle),
                  ),
                  child: Icon(
                    Icons.local_fire_department_rounded,
                    color: DS.primaryBase,
                    size: 28,
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: Text(
                    context.l10n.taskExecutionEnterFocus,
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.md),
            Wrap(
              spacing: DS.md,
              runSpacing: DS.xs,
              children: [
                _FeatureChip(
                  icon: Icons.fullscreen,
                  label: context.l10n.taskExecutionFeatureFullscreen,
                ),
                _FeatureChip(
                  icon: Icons.access_time_rounded,
                  label: context.l10n.taskExecutionFeatureFlipClock,
                ),
                _FeatureChip(
                  icon: Icons.star_rounded,
                  label: context.l10n.taskExecutionFeatureStarfield,
                ),
                _FeatureChip(
                  icon: Icons.visibility_off_rounded,
                  label: context.l10n.taskExecutionFeatureDistraction,
                ),
                _FeatureChip(
                  icon: Icons.psychology_rounded,
                  label: context.l10n.taskExecutionFeatureCoach,
                ),
                _FeatureChip(
                  icon: Icons.emoji_events_rounded,
                  label: context.l10n.taskExecutionFeatureReward,
                ),
              ],
            ),
            const SizedBox(height: DS.lg),
            CustomButton.primary(
              text: context.l10n.taskExecutionStartNow,
              icon: Icons.arrow_forward_rounded,
              customGradient: _taskWarmActionGradient(context),
              onPressed: () {
                context.push('/focus/mindfulness/${task.id}');
              },
            ),
          ],
        ),
      );
}

class _FocusCompletionPanel extends StatelessWidget {
  const _FocusCompletionPanel({
    required this.visible,
    required this.animateStats,
    required this.sessionMinutes,
    required this.todayMinutes,
    required this.expGained,
    required this.onSkip,
    required this.continueLabel,
    required this.skipLabel,
    this.unlockedAchievements = const [],
  });

  final bool visible;
  final bool animateStats;
  final int sessionMinutes;
  final int todayMinutes;
  final int expGained;
  final List<dynamic> unlockedAchievements;
  final VoidCallback onSkip;
  final String continueLabel;
  final String skipLabel;

  String _labelForLocale(BuildContext context, String zh, String en) {
    return Localizations.localeOf(context).languageCode == 'zh' ? zh : en;
  }

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<Offset>(
        tween: Tween<Offset>(
          begin: const Offset(0, 0.08),
          end: visible ? Offset.zero : const Offset(0, 0.08),
        ),
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
        builder: (context, slideOffset, child) => Transform.translate(
          offset: Offset(0, slideOffset.dy * 120),
          child: AnimatedOpacity(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeOutCubic,
            opacity: visible ? 1 : 0,
            child: child,
          ),
        ),
        child: TweenAnimationBuilder<double>(
          tween: Tween<double>(begin: 0.96, end: 1),
          duration: const Duration(milliseconds: 600),
          curve: Curves.elasticOut,
          builder: (context, scale, child) =>
              Transform.scale(scale: scale, child: child),
          child: GraphiteCardSurface(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    padding: const EdgeInsets.all(DS.xl),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          const Color(0xFFFFD79A).withValues(alpha: 0.92),
                          const Color(0xFFFFB86B).withValues(alpha: 0.88),
                        ],
                      ),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color:
                              const Color(0xFFFFC06B).withValues(alpha: 0.38),
                          blurRadius: 36,
                          spreadRadius: 6,
                        ),
                      ],
                      border: Border.all(
                        color: const Color(0xFFFFF1D7).withValues(alpha: 0.7),
                      ),
                    ),
                    child: Icon(
                      Icons.self_improvement_rounded,
                      color: const Color(0xFF7E4A12),
                      size: 72,
                    ),
                  ),
                  const SizedBox(height: DS.spacing20),
                  Text(
                    _labelForLocale(context, '专注完成', 'Focus Complete'),
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    _labelForLocale(
                      context,
                      '状态已回暖，来看看这次沉浸带来的积累。',
                      'You are back from deep focus. Here is what you gained.',
                    ),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                  ),
                  const SizedBox(height: DS.spacing18),
                  Row(
                    children: [
                      Expanded(
                        child: _FocusMetricCard(
                          icon: Icons.timer_outlined,
                          label:
                              _labelForLocale(context, '本次专注', 'This Session'),
                          value: sessionMinutes,
                          suffix: _labelForLocale(context, '分钟', ' min'),
                          animate: animateStats,
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      Expanded(
                        child: _FocusMetricCard(
                          icon: Icons.today_rounded,
                          label: _labelForLocale(
                            context,
                            '今日累计',
                            'Today Total',
                          ),
                          value: todayMinutes,
                          suffix: _labelForLocale(context, '分钟', ' min'),
                          animate: animateStats,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing12),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing18,
                      vertical: DS.spacing10,
                    ),
                    decoration: BoxDecoration(
                      color: DS.surfaceSecondary,
                      borderRadius: DS.borderRadius20,
                      border: Border.all(color: DS.borderSubtle),
                    ),
                    child: SparkleCountUp(
                      end: expGained,
                      animate: animateStats,
                      prefix: _labelForLocale(context, '专注经验 +', 'Focus XP +'),
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                  ),
                  if (unlockedAchievements.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing12),
                    ...unlockedAchievements.map((a) {
                      final data = a is Map<String, dynamic>
                          ? a
                          : const <String, dynamic>{};
                      final name =
                          (data['name'] ?? data['title'] ?? '').toString();
                      return Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing16,
                          vertical: DS.spacing8,
                        ),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [
                              const Color(0xFFFFD700).withValues(alpha: 0.18),
                              const Color(0xFFFFA500).withValues(alpha: 0.10),
                            ],
                          ),
                          borderRadius: DS.borderRadius12,
                          border: Border.all(
                            color:
                                const Color(0xFFFFD700).withValues(alpha: 0.4),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.emoji_events_rounded,
                              color: const Color(0xFFFFB300),
                              size: 20,
                            ),
                            const SizedBox(width: DS.spacing8),
                            Flexible(
                              child: Text(
                                name,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyMedium
                                    ?.copyWith(
                                      color: DS.textPrimary,
                                      fontWeight: DS.fontWeightSemiBold,
                                    ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      );
                    }),
                  ],
                  const SizedBox(height: DS.spacing12),
                  Text(
                    continueLabel,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  SparkleButton.ghost(
                    label: skipLabel,
                    onPressed: onSkip,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}

class _FocusMetricCard extends StatelessWidget {
  const _FocusMetricCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.suffix,
    required this.animate,
  });

  final IconData icon;
  final String label;
  final int value;
  final String suffix;
  final bool animate;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary.withValues(alpha: 0.92),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: DS.primaryBase, size: 18),
                const SizedBox(width: DS.spacing6),
                Expanded(
                  child: Text(
                    label,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          fontWeight: DS.fontWeightMedium,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            RichText(
              text: TextSpan(
                children: [
                  WidgetSpan(
                    alignment: PlaceholderAlignment.middle,
                    child: SparkleCountUp(
                      end: value,
                      animate: animate,
                      duration: const Duration(milliseconds: 600),
                      style:
                          Theme.of(context).textTheme.headlineSmall?.copyWith(
                                color: DS.textPrimary,
                                fontWeight: DS.fontWeightBold,
                              ),
                    ),
                  ),
                  TextSpan(
                    text: suffix,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textSecondary,
                          fontWeight: DS.fontWeightMedium,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _TimerControls extends StatelessWidget {
  const _TimerControls({
    required this.isPomodoroMode,
    required this.onTogglePomodoro,
    required this.onSetPreset,
    required this.onReset,
  });
  final bool isPomodoroMode;
  final VoidCallback onTogglePomodoro;
  final void Function(int minutes) onSetPreset;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Wrap(
            alignment: WrapAlignment.center,
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              CustomButton.secondary(
                text: context.l10n.taskTimerPomodoro,
                icon: Icons.timer,
                onPressed: onTogglePomodoro,
                size: CustomButtonSize.small,
              ),
              ...[15, 25, 45, 60].map(
                (minutes) => CustomButton.secondary(
                  text: context.l10n.taskTimerMinutes(minutes),
                  onPressed: () => onSetPreset(minutes),
                  size: CustomButtonSize.small,
                ),
              ),
              CustomButton.secondary(
                text: '重置',
                icon: Icons.restart_alt_rounded,
                onPressed: onReset,
                size: CustomButtonSize.small,
              ),
            ],
          ),
        ],
      );
}

class _FeatureChip extends StatelessWidget {
  const _FeatureChip({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.primaryBase),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(fontSize: 12, color: DS.textSecondary),
            ),
          ],
        ),
      );
}

class _ExecutionAssistPanel extends ConsumerWidget {
  const _ExecutionAssistPanel({
    required this.task,
  });
  final TaskModel task;

  Future<void> _handoffTask(BuildContext context, WidgetRef ref) async {
    ref.read(openClawTaskNudgeDismissedProvider.notifier).state = false;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.messageSend));
    final intent =
        await ref.read(taskListProvider.notifier).handoffTaskToAi(task.id);
    if (!context.mounted) return;

    if (intent == null) {
      final message = ref.read(taskListProvider).error ?? 'AI 执行发起失败';
      AppFeedback.error(
        context,
        message.replaceFirst('Exception: ', ''),
      );
      return;
    }

    final feedbackMessage = switch (intent.status) {
      ExecutionIntentStatus.succeeded => 'AI 已完成本次执行',
      ExecutionIntentStatus.partial => 'AI 已完成部分内容，请继续查看',
      ExecutionIntentStatus.failed => intent.errorMessage ?? 'AI 执行失败',
      ExecutionIntentStatus.waitingApproval => 'AI 正在等待你的确认',
      _ => '任务已交给 AI，当前状态：${intent.statusLabel}',
    };

    if (intent.status == ExecutionIntentStatus.failed) {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.error));
      AppFeedback.error(context, feedbackMessage);
    } else {
      unawaited(
        SensoryFeedbackService.emit(
          intent.status == ExecutionIntentStatus.waitingApproval
              ? SensoryFeedbackEvent.warning
              : SensoryFeedbackEvent.success,
        ),
      );
      AppFeedback.success(context, feedbackMessage);
    }
  }

  Future<void> _queueHandoffTask(
    BuildContext context,
    WidgetRef ref, {
    String? templateId,
  }) async {
    final connection = ref.read(openClawConnectionProvider);
    await connection.queueExecutionRequest(
      taskId: task.id,
      templateId: templateId,
      goal: task.title,
      source: 'task_execution_screen',
      priority: 1,
    );
    if (!context.mounted) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    AppFeedback.info(context, ExecutionCopy.engineOfflineQueuedMessage);
  }

  Future<void> _confirmAiResult(BuildContext context, WidgetRef ref) async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    final record = await ref
        .read(taskListProvider.notifier)
        .confirmTaskExecutionResult(task.id);
    if (!context.mounted) return;

    if (record == null) {
      final message = ref.read(taskListProvider).error ?? 'AI 结果确认失败';
      AppFeedback.error(context, message.replaceFirst('Exception: ', ''));
      return;
    }

    AppFeedback.success(context, 'AI 结果已确认，任务状态已同步');
  }

  Future<void> _showRejectReasonSheet(
      BuildContext context, WidgetRef ref) async {
    final selectedReason = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => const _RejectReasonSheet(),
    );
    if (!context.mounted || selectedReason == null) return;
    final record = await ref
        .read(taskListProvider.notifier)
        .rejectTaskExecutionResult(task.id, reason: selectedReason);
    if (!context.mounted) return;
    if (record == null) {
      final message = ref.read(taskListProvider).error ?? '取回任务失败';
      AppFeedback.error(context, message.replaceFirst('Exception: ', ''));
      return;
    }
    AppFeedback.info(context, '任务已交还给你继续处理');
  }

  Color _executionStatusColor(ExecutionIntentModel? intent, bool isLoading) {
    if (isLoading) return DS.primaryBase;
    switch (intent?.status) {
      case ExecutionIntentStatus.succeeded:
        return DS.success;
      case ExecutionIntentStatus.partial:
        return DS.warning;
      case ExecutionIntentStatus.failed:
      case ExecutionIntentStatus.timedOut:
      case ExecutionIntentStatus.canceled:
        return DS.error;
      case ExecutionIntentStatus.waitingApproval:
        return DS.warning;
      case ExecutionIntentStatus.handedBack:
        return DS.neutral500;
      case ExecutionIntentStatus.draft:
      case ExecutionIntentStatus.ready:
      case ExecutionIntentStatus.dispatched:
      case ExecutionIntentStatus.running:
      case ExecutionIntentStatus.unknown:
      case null:
        return DS.primaryBase;
    }
  }

  String _executionStatusTitle(ExecutionIntentModel? intent, bool isLoading) {
    if (isLoading) return 'AI 正在接管这个任务';
    return intent == null ? 'AI 执行尚未开始' : 'AI 状态：${intent.statusLabel}';
  }

  String _executionStatusSubtitle(
    ExecutionIntentModel? intent,
    ExecutionRecordModel? record,
    bool isLoading,
  ) {
    if (isLoading) {
      return 'Sparkle 正在把任务发送给 OpenClaw。';
    }
    if (intent == null) {
      return '适合数字执行的任务可以在这里一键转交。';
    }
    if (intent.errorMessage != null && intent.errorMessage!.trim().isNotEmpty) {
      return intent.errorMessage!;
    }
    if (record?.errorMessage != null &&
        record!.errorMessage!.trim().isNotEmpty) {
      return record.errorMessage!;
    }
    if (record != null) {
      final validationText =
          record.validationPassed != null && record.validationTotal != null
              ? '校验 ${record.validationPassed}/${record.validationTotal}'
              : record.trustLabel;
      return '结果：$validationText'
          '${record.approvalRequested != null ? ' · 审批请求 ${record.approvalRequested}' : ''}';
    }
    if (intent.goal.trim().isNotEmpty) {
      return '目标：${intent.goal} · ${intent.trustLabel}';
    }
    return '结果信任：${intent.trustLabel}';
  }

  String? _executionOutputPreview(ExecutionRecordModel? record) {
    final parsedOutput = record?.parsedOutput;
    if (parsedOutput == null || parsedOutput.isEmpty) return null;
    final preview = parsedOutput.entries.take(2).map((entry) {
      final rawValue = entry.value;
      final value = rawValue is List
          ? rawValue.join(', ')
          : rawValue is Map
              ? rawValue.toString()
              : rawValue.toString();
      return '${entry.key}: $value';
    }).join('  |  ');
    return preview.isEmpty ? null : preview;
  }

  String? _executionMetaPreview(ExecutionIntentModel? intent) {
    if (intent == null) return null;
    final parts = <String>[
      if (intent.templateName != null && intent.templateName!.isNotEmpty)
        '模板 ${intent.templateName}',
      if (intent.strategyVariant != null && intent.strategyVariant!.isNotEmpty)
        '策略 ${intent.strategyVariant}',
      if (intent.targetNodeLabel != null && intent.targetNodeLabel!.isNotEmpty)
        '节点 ${intent.targetNodeLabel}',
    ];
    if (parts.isEmpty) return null;
    return parts.join(' · ');
  }

  String _handoffButtonText(ExecutionIntentModel? intent, bool isLoading) {
    if (isLoading) return 'AI 接管中...';
    switch (intent?.status) {
      case ExecutionIntentStatus.failed:
      case ExecutionIntentStatus.timedOut:
      case ExecutionIntentStatus.canceled:
      case ExecutionIntentStatus.handedBack:
        return '重新交给 AI';
      case ExecutionIntentStatus.succeeded:
      case ExecutionIntentStatus.partial:
        return '再次交给 AI';
      case ExecutionIntentStatus.waitingApproval:
        return '等待确认';
      case ExecutionIntentStatus.draft:
      case ExecutionIntentStatus.ready:
      case ExecutionIntentStatus.dispatched:
      case ExecutionIntentStatus.running:
        return 'AI 执行中';
      case ExecutionIntentStatus.unknown:
      case null:
        return '交给 AI 执行';
    }
  }

  Widget _buildNudgeDetailBlock({
    required String label,
    required String value,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: DS.bodySmall.copyWith(
            color: DS.warning,
            fontWeight: DS.fontWeightBold,
          ),
        ),
        const SizedBox(height: DS.spacing4),
        Text(
          value,
          style: DS.bodySmall.copyWith(
            color: DS.neutral700,
            height: 1.45,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final copy = ExecutionCopy.of(context);
    final executionIntent = ref.watch(
      taskListProvider.select((state) => state.taskExecutions[task.id]),
    );
    final executionRecord = ref.watch(
      taskListProvider.select((state) => state.taskExecutionRecords[task.id]),
    );
    final executionTemplates = ref.watch(
      taskListProvider.select(
        (state) =>
            state.taskExecutionTemplates[task.id] ??
            const <ExecutionTemplateModel>[],
      ),
    );
    final selectedTemplateId = ref.watch(
      taskListProvider.select(
        (state) => state.selectedExecutionTemplateIds[task.id],
      ),
    );
    final isHandoffLoading = ref.watch(
      taskListProvider
          .select((state) => state.handoffInFlight.contains(task.id)),
    );
    final isExecutionDecisionLoading = ref.watch(
      taskListProvider.select(
        (state) => state.executionDecisionInFlight.contains(task.id),
      ),
    );
    final connection = ref.watch(openClawConnectionProvider);
    final isClawConnected = connection.isConnected;
    final isClawConfigured = connection.config.isConfigured;
    final queuedRequestCount = connection.queuedRequestCount;
    final nudgeDismissed = ref.watch(openClawTaskNudgeDismissedProvider);
    final nudgeExpanded = ref.watch(openClawTaskNudgeExpandedProvider);
    final supportsAiHandoff = isServerTaskId(task.id);
    final canHandoff = supportsAiHandoff &&
        isClawConnected &&
        task.status != TaskStatus.completed &&
        task.status != TaskStatus.abandoned &&
        (executionIntent == null || executionIntent.isTerminal) &&
        !isHandoffLoading;
    final canQueueHandoff = supportsAiHandoff &&
        !isClawConnected &&
        isClawConfigured &&
        task.status != TaskStatus.completed &&
        task.status != TaskStatus.abandoned &&
        (executionIntent == null || executionIntent.isTerminal) &&
        !isHandoffLoading;
    final showExecutionStatus =
        supportsAiHandoff && (executionIntent != null || isHandoffLoading);
    final statusColor =
        _executionStatusColor(executionIntent, isHandoffLoading);
    final outputPreview = _executionOutputPreview(executionRecord);
    final metaPreview = _executionMetaPreview(executionIntent);

    return GraphiteCardSurface(
      padding: const EdgeInsets.all(DS.spacing16),
      borderColor: DS.borderSubtle,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (supportsAiHandoff &&
              executionTemplates.isNotEmpty &&
              (executionIntent == null || executionIntent.isTerminal)) ...[
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                '推荐执行模板',
                style: DS.bodySmall.copyWith(
                  color: DS.neutral700,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ),
            const SizedBox(height: DS.spacing8),
            ...executionTemplates.toList().asMap().entries.map(
                  (entry) => Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing8),
                    child: SparkleStaggerItem(
                      index: entry.key,
                      child: ExecutionTemplateCard(
                        template: entry.value,
                        isSelected:
                            selectedTemplateId == entry.value.templateId,
                        onTap: () {
                          ref
                              .read(taskListProvider.notifier)
                              .selectExecutionTemplate(
                                  task.id, entry.value.templateId);
                        },
                      ),
                    ),
                  ),
                ),
            const SizedBox(height: DS.spacing8),
          ],
          if (supportsAiHandoff &&
              (executionIntent == null || executionIntent.isTerminal) &&
              !isClawConnected &&
              !nudgeDismissed) ...[
            OpenClawStatusCapsule(
              title:
                  isClawConfigured ? 'OpenClaw 当前离线，可先加入等待队列' : 'OpenClaw 尚未连接',
              subtitle: isClawConfigured
                  ? '你可以先继续委派，等引擎恢复后再统一重试，不需要在这个任务页停住。'
                  : '先完成一次连接，之后任务页和聊天页都会把它当成同一个执行入口来使用。',
              icon: isClawConfigured
                  ? Icons.cloud_queue_rounded
                  : Icons.link_off_rounded,
              tone: OpenClawVisualTone.offline,
              expanded: nudgeExpanded,
              onToggleExpanded: () {
                ref.read(openClawTaskNudgeExpandedProvider.notifier).state =
                    !nudgeExpanded;
              },
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextButton(
                    onPressed: () => context.push(
                      '${HomeRoutes.openClawHub}?section=connection',
                    ),
                    child: Text(isClawConfigured ? '查看' : '连接'),
                  ),
                  IconButton(
                    onPressed: () {
                      ref
                          .read(openClawTaskNudgeDismissedProvider.notifier)
                          .state = true;
                      ref
                          .read(openClawTaskNudgeExpandedProvider.notifier)
                          .state = false;
                    },
                    icon: const Icon(Icons.close_rounded, size: 18),
                    visualDensity: VisualDensity.compact,
                    color: DS.textSecondary,
                    tooltip: '关闭提示',
                  ),
                ],
              ),
              metrics: [
                OpenClawMetricPill(
                  icon: Icons.sensors_rounded,
                  label: isClawConfigured ? '已配置但离线' : '尚未配置',
                  tone: OpenClawVisualTone.offline,
                  emphasized: true,
                ),
                if (queuedRequestCount > 0)
                  OpenClawMetricPill(
                    icon: Icons.schedule_rounded,
                    label: '$queuedRequestCount 个任务已排队',
                    tone: OpenClawVisualTone.attention,
                    emphasized: true,
                  ),
                OpenClawMetricPill(
                  icon: Icons.arrow_circle_right_rounded,
                  label: isClawConfigured ? '建议先排队再统一重试' : '建议先连接再委派',
                  tone: OpenClawVisualTone.active,
                ),
              ],
              expandedContent: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildNudgeDetailBlock(
                    label: '当前状态',
                    value: isClawConfigured
                        ? '连接信息还在，但引擎暂时不在线。'
                        : '这台设备还没有接入 OpenClaw。',
                  ),
                  const SizedBox(height: DS.spacing8),
                  _buildNudgeDetailBlock(
                    label: '为什么现在看到这个提示',
                    value: '你正在一个支持 AI 委派的任务里，而且当前执行入口还没有准备好。',
                  ),
                  const SizedBox(height: DS.spacing8),
                  _buildNudgeDetailBlock(
                    label: '下一步动作',
                    value: isClawConfigured
                        ? '继续把任务加入等待队列，或去 OpenClaw Hub 恢复连接后统一重试。'
                        : '打开 OpenClaw Hub 完成连接，之后再回到这里发起委派。',
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing12),
          ],
          if (showExecutionStatus) ...[
            SparkleStaggerItem(
              index: 0,
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(DS.borderRadiusMD),
                  border: Border.all(
                    color: statusColor.withValues(alpha: 0.22),
                  ),
                ),
                child: Row(
                  children: [
                    ExecutionStatusIndicator(
                      status: executionIntent?.status ??
                          ExecutionIntentStatus.dispatched,
                      dispatchedAt: executionIntent?.dispatchedAt,
                      size: 52,
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _executionStatusTitle(
                              executionIntent,
                              isHandoffLoading,
                            ),
                            style: DS.bodyMedium.copyWith(
                              fontWeight: DS.fontWeightBold,
                            ),
                          ),
                          const SizedBox(height: DS.spacing4),
                          Text(
                            _executionStatusSubtitle(
                              executionIntent,
                              executionRecord,
                              isHandoffLoading,
                            ),
                            style: DS.bodySmall.copyWith(
                              color: DS.neutral600,
                            ),
                          ),
                          if (outputPreview != null) ...[
                            const SizedBox(height: DS.spacing8),
                            Text(
                              outputPreview,
                              style: DS.bodySmall.copyWith(
                                color: DS.neutral700,
                                fontWeight: DS.fontWeightMedium,
                              ),
                            ),
                          ],
                          if (metaPreview != null) ...[
                            const SizedBox(height: DS.spacing6),
                            Text(
                              metaPreview,
                              style: DS.bodySmall.copyWith(
                                color: DS.neutral600,
                                fontWeight: DS.fontWeightMedium,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (isHandoffLoading)
                      SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(statusColor),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.spacing12),
          ],
          if ((executionIntent?.isWaitingApproval ?? false) &&
              executionRecord != null) ...[
            ExecutionApprovalCard(
              record: executionRecord,
              intent: executionIntent!,
              isLoading: isExecutionDecisionLoading,
              onConfirm: () => _confirmAiResult(context, ref),
              onReject: () => _showRejectReasonSheet(context, ref),
            ),
            const SizedBox(height: DS.spacing12),
          ],
          if (supportsAiHandoff) ...[
            SizedBox(
              width: double.infinity,
              child: CustomButton.secondary(
                text: canQueueHandoff
                    ? copy.queueAction
                    : isClawConfigured
                        ? _handoffButtonText(executionIntent, isHandoffLoading)
                        : copy.connectEngineAction,
                icon: canQueueHandoff
                    ? Icons.cloud_queue_rounded
                    : Icons.smart_toy_outlined,
                onPressed: canHandoff
                    ? () => _handoffTask(context, ref)
                    : canQueueHandoff
                        ? () => _queueHandoffTask(
                              context,
                              ref,
                              templateId: selectedTemplateId,
                            )
                        : () {
                            ref
                                .read(
                                    openClawTaskNudgeDismissedProvider.notifier)
                                .state = false;
                            ref
                                .read(
                                  openClawTaskNudgeExpandedProvider.notifier,
                                )
                                .state = true;
                          },
                isLoading: isHandoffLoading,
              ),
            ),
            const SizedBox(height: DS.spacing12),
          ],
        ],
      ),
    );
  }
}

class _BottomControls extends ConsumerWidget {
  const _BottomControls({
    required this.task,
    required this.elapsedSeconds,
    required this.onComplete,
  });

  final TaskModel task;
  final int elapsedSeconds;
  final void Function(int minutes, String? note) onComplete;

  void _showCompleteDialog(BuildContext context) {
    final noteController = TextEditingController();
    final minutes = Duration(seconds: elapsedSeconds).inMinutes;

    unawaited(
      showSensoryDialog<void>(
        context: context,
        builder: (ctx) => Dialog(
          backgroundColor: Colors.transparent,
          child: GraphiteModalSurface(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(DS.sm),
                      decoration: BoxDecoration(
                        color: DS.surfaceOverlay,
                        shape: BoxShape.circle,
                        border: Border.all(color: DS.borderSubtle),
                      ),
                      child: Icon(
                        Icons.check_circle_outline,
                        color: DS.success,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Text(
                      context.l10n.taskExecutionCompleteTitle,
                      style: DS.titleLarge.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing16),
                GraphiteCardSurface(
                  padding: const EdgeInsets.all(DS.spacing12),
                  borderColor: DS.borderSubtle,
                  child: Row(
                    children: [
                      Icon(Icons.timer_outlined, color: DS.primaryBase),
                      const SizedBox(width: DS.spacing8),
                      Text(
                        context.l10n.taskExecutionElapsedMinutes(minutes),
                        style: DS.bodyMedium.copyWith(
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                TextField(
                  controller: noteController,
                  decoration: InputDecoration(
                    labelText: context.l10n.taskExecutionNoteLabel,
                    hintText: context.l10n.taskExecutionNoteHint,
                  ),
                  maxLines: 3,
                ),
                const SizedBox(height: DS.spacing20),
                Row(
                  children: [
                    Expanded(
                      child: CustomButton.text(
                        text: context.l10n.cancel,
                        onPressed: () => Navigator.of(ctx).pop(),
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: CustomButton.primary(
                        text: context.l10n.taskExecutionConfirmComplete,
                        icon: Icons.check_rounded,
                        customGradient: _taskWarmActionGradient(context),
                        onPressed: () {
                          Navigator.of(ctx).pop();
                          onComplete(
                            minutes,
                            noteController.text.trim().isEmpty
                                ? null
                                : noteController.text.trim(),
                          );
                        },
                        size: CustomButtonSize.small,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _abandonTask(BuildContext context, WidgetRef ref) {
    unawaited(
      showSensoryDialog<void>(
        context: context,
        builder: (ctx) => BlockingInterceptorDialog(
          taskId: task.id,
          onAbandonConfirmed: () {
            unawaited(ref.read(taskListProvider.notifier).abandonTask(task.id));
            context.go(TaskRoutes.home);
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GraphiteCardSurface(
      borderColor: DS.borderSubtle,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Row(
        children: [
          Expanded(
            child: CustomButton.text(
              text: context.l10n.taskExecutionAbandon,
              onPressed: () => _abandonTask(context, ref),
            ),
          ),
          const SizedBox(width: DS.spacing16),
          Expanded(
            flex: 2,
            child: CustomButton.primary(
              text: context.l10n.taskExecutionCompleteTitle,
              customGradient: _taskWarmActionGradient(context),
              onPressed: () => _showCompleteDialog(context),
            ),
          ),
        ],
      ),
    );
  }
}

class _TaskGuidePanel extends ConsumerStatefulWidget {
  const _TaskGuidePanel({required this.task});

  final TaskModel task;

  @override
  ConsumerState<_TaskGuidePanel> createState() => _TaskGuidePanelState();
}

class _TaskGuidePanelState extends ConsumerState<_TaskGuidePanel> {
  bool _isGeneratingGuide = false;

  Future<void> _generateTaskGuide() async {
    if (_isGeneratingGuide || !isServerTaskId(widget.task.id)) return;
    setState(() => _isGeneratingGuide = true);
    try {
      final updated = await ref
          .read(taskListProvider.notifier)
          .generateGuide(widget.task.id);
      if (!mounted) return;
      ref.read(activeTaskProvider.notifier).state = updated;
      AppFeedback.success(context, '任务指南已生成');
    } catch (error) {
      if (!mounted) return;
      AppFeedback.error(
        context,
        '任务指南生成失败：${error.toString().replaceFirst('Exception: ', '')}',
      );
    } finally {
      if (mounted) {
        setState(() => _isGeneratingGuide = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final task = ref.watch(activeTaskProvider) ?? widget.task;
    final hasGuide = task.guideContent != null && task.guideContent!.isNotEmpty;
    final canGenerateGuide = isServerTaskId(task.id);

    return GraphiteCardSurface(
      padding: EdgeInsets.zero,
      child: ExpansionTile(
        shape: const Border(),
        tilePadding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                shape: BoxShape.circle,
                border: Border.all(
                  color: DS.borderSubtle,
                ),
              ),
              child: Icon(
                Icons.description_outlined,
                color: DS.primaryBase,
                size: 22,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Text(
                l10n.taskExecutionGuideTitle,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: DS.neutral900,
                    ),
              ),
            ),
          ],
        ),
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.spacing16),
            decoration: BoxDecoration(
              color: DS.neutral50,
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(16),
                bottomRight: Radius.circular(16),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    OpenClawMetricPill(
                      icon: hasGuide
                          ? Icons.auto_awesome_rounded
                          : Icons.tips_and_updates_outlined,
                      label: hasGuide ? '已生成任务指南' : '还没有任务指南',
                      tone: hasGuide
                          ? OpenClawVisualTone.connected
                          : OpenClawVisualTone.attention,
                      emphasized: hasGuide,
                    ),
                    if (canGenerateGuide)
                      const OpenClawMetricPill(
                        icon: Icons.psychology_alt_rounded,
                        label: '支持 AI 生成',
                        tone: OpenClawVisualTone.active,
                      ),
                  ],
                ),
                const SizedBox(height: DS.spacing12),
                if (hasGuide)
                  SparkleMarkdown(
                    content: task.guideContent!,
                    textColor: DS.textPrimary,
                    codeBackgroundColor: DS.neutral100,
                    linkColor: DS.primaryBase,
                    contentRole: SparkleMarkdownRole.taskGuide,
                  )
                else
                  Text(
                    canGenerateGuide
                        ? '还没有任务指南。你可以让 AI 根据当前任务目标即时生成一版执行建议和步骤。'
                        : l10n.taskExecutionGuideEmpty,
                    style: DS.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.5,
                    ),
                  ),
                if (canGenerateGuide) ...[
                  const SizedBox(height: DS.spacing16),
                  SizedBox(
                    width: double.infinity,
                    child: CustomButton.secondary(
                      text: hasGuide ? '重新生成任务指南' : '生成任务指南',
                      icon: _isGeneratingGuide
                          ? Icons.sync_rounded
                          : Icons.auto_awesome_rounded,
                      onPressed: _isGeneratingGuide ? null : _generateTaskGuide,
                      isLoading: _isGeneratingGuide,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RejectReasonSheet extends StatefulWidget {
  const _RejectReasonSheet();

  @override
  State<_RejectReasonSheet> createState() => _RejectReasonSheetState();
}

class _RejectReasonSheetState extends State<_RejectReasonSheet> {
  static const List<String> _presetReasons = [
    '结果不准确',
    '结果不完整',
    '安全顾虑',
    '我想自己做',
  ];

  String? _selectedReason;
  final TextEditingController _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GraphiteModalSurface(
      title: '退回原因',
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '告诉 Sparkle 为什么这次结果不适合直接采纳，后续会据此调整执行方式。',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: _presetReasons.map((reason) {
              final selected = _selectedReason == reason;
              return ChoiceChip(
                label: Text(reason),
                selected: selected,
                onSelected: (_) => setState(() => _selectedReason = reason),
              );
            }).toList(),
          ),
          const SizedBox(height: DS.spacing12),
          TextField(
            controller: _controller,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: '补充说明',
              hintText: '例如：缺少来源、结论太武断、我想保留自己的表达方式',
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Row(
            children: [
              Expanded(
                child: CustomButton.text(
                  text: '取消',
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: CustomButton.primary(
                  text: '确认退回',
                  onPressed: () {
                    final extra = _controller.text.trim();
                    final reason = [
                      _selectedReason,
                      if (extra.isNotEmpty) extra,
                    ].whereType<String>().join('；');
                    Navigator.of(context).pop(
                      reason.isEmpty ? '用户取回任务' : reason,
                    );
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Task Exit Confirmation Dialog - Triple confirmation for focus protection
enum _TaskExitStep { first, second, third }

class _TaskExitConfirmationDialog extends StatefulWidget {
  const _TaskExitConfirmationDialog({
    required this.elapsedSeconds,
    required this.elapsedMinutes,
  });
  final int elapsedSeconds;
  final int elapsedMinutes;

  @override
  State<_TaskExitConfirmationDialog> createState() =>
      _TaskExitConfirmationDialogState();
}

class _TaskExitConfirmationDialogState
    extends State<_TaskExitConfirmationDialog>
    with SingleTickerProviderStateMixin {
  _TaskExitStep _currentStep = _TaskExitStep.first;
  late AnimationController _slideController;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _slideController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _slideController,
        curve: Curves.easeOut,
      ),
    );
    _slideController.forward();
  }

  @override
  void dispose() {
    _slideController.dispose();
    super.dispose();
  }

  void _nextStep() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    if (_currentStep == _TaskExitStep.third) {
      // Show reflection dialog after triple confirmation
      Navigator.of(context).pop(true);
    } else {
      setState(() {
        _currentStep = _TaskExitStep.values[_currentStep.index + 1];
      });
    }
  }

  void _cancel() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    Navigator.of(context).pop(false);
  }

  @override
  Widget build(BuildContext context) => SlideTransition(
        position: _slideAnimation,
        child: Dialog(
          backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
          insetPadding: const EdgeInsets.all(DS.xl),
          child: GraphiteModalSurface(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Progress Indicator
                _buildProgressIndicator(),
                const SizedBox(height: DS.xl),

                // Icon
                _buildIcon(),
                const SizedBox(height: DS.lg),

                // Title
                Text(
                  _getTitle(),
                  style: TextStyle(
                    color: DS.neutral900,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: DS.md),

                // Message
                Text(
                  _getMessage(),
                  style: TextStyle(
                    color: DS.neutral600,
                    fontSize: 14,
                    height: 1.5,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: DS.xl),

                // Buttons
                Row(
                  children: [
                    Expanded(
                      child: CustomButton.secondary(
                        text: _getCancelText(),
                        onPressed: _cancel,
                      ),
                    ),
                    const SizedBox(width: DS.lg),
                    Expanded(
                      child: _currentStep == _TaskExitStep.third
                          ? CustomButton.primary(
                              text: _getConfirmText(),
                              onPressed: _nextStep,
                              customGradient: DS.warningGradient,
                            )
                          : CustomButton.secondary(
                              text: _getConfirmText(),
                              onPressed: _nextStep,
                            ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );

  Widget _buildProgressIndicator() => Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(3, (index) {
          final isActive = index <= _currentStep.index;
          return Container(
            width: 24,
            height: 4,
            margin: const EdgeInsets.symmetric(horizontal: 4),
            decoration: BoxDecoration(
              color: isActive ? DS.primaryBase : DS.neutral300,
              borderRadius: BorderRadius.circular(2),
            ),
          );
        }),
      );

  Widget _buildIcon() {
    IconData icon;
    Color color;

    switch (_currentStep) {
      case _TaskExitStep.first:
        icon = Icons.pause_circle_outline_rounded;
        color = DS.warning;
      case _TaskExitStep.second:
        icon = Icons.timer_outlined;
        color = DS.info;
      case _TaskExitStep.third:
        icon = Icons.exit_to_app_rounded;
        color = DS.error;
    }

    return Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        shape: BoxShape.circle,
      ),
      child: Icon(icon, color: color, size: 40),
    );
  }

  String _getTitle() {
    final l10n = context.l10n;
    switch (_currentStep) {
      case _TaskExitStep.first:
        return l10n.taskExitTitleStep1;
      case _TaskExitStep.second:
        return l10n.taskExitTitleStep2;
      case _TaskExitStep.third:
        return l10n.taskExitTitleStep3;
    }
  }

  String _getMessage() {
    final l10n = context.l10n;
    switch (_currentStep) {
      case _TaskExitStep.first:
        return l10n.taskExitMessageStep1;
      case _TaskExitStep.second:
        return l10n.taskExitMessageStep2(
          widget.elapsedMinutes,
          widget.elapsedSeconds % 60,
        );
      case _TaskExitStep.third:
        return l10n.taskExitMessageStep3;
    }
  }

  String _getCancelText() {
    final l10n = context.l10n;
    switch (_currentStep) {
      case _TaskExitStep.first:
        return l10n.taskExitCancelStep1;
      case _TaskExitStep.second:
        return l10n.taskExitCancelStep2;
      case _TaskExitStep.third:
        return l10n.taskExitCancelStep3;
    }
  }

  String _getConfirmText() {
    final l10n = context.l10n;
    switch (_currentStep) {
      case _TaskExitStep.first:
        return l10n.taskExitConfirmStep1;
      case _TaskExitStep.second:
        return l10n.taskExitConfirmStep2;
      case _TaskExitStep.third:
        return l10n.taskExitConfirmStep3;
    }
  }
}
