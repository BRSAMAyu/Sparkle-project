import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart'
    hide ButtonVariant;
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/intervention_action_service.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_core_session_sheet.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart'
    as focus_stats;
import 'package:sparkle/features/focus/presentation/widgets/focus_agent_sheet.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_context_summary.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/data/models/execution_record_model.dart';
import 'package:sparkle/features/task/data/models/execution_template_model.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/presentation/execution_copy.dart';
import 'package:sparkle/features/task/presentation/providers/subtask_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_chat_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/blocking_interceptor_dialog.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_approval_card.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_status_indicator.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_template_card.dart';
import 'package:sparkle/features/task/presentation/widgets/paused_task_status_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/quick_tools_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/source_lifecycle_badge.dart';
import 'package:sparkle/features/task/presentation/widgets/stuck_help_sheet.dart';
import 'package:sparkle/features/task/presentation/widgets/subtask_list_widget.dart';
import 'package:sparkle/features/task/presentation/widgets/task_chat_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/task_completion_celebration.dart';
import 'package:sparkle/features/task/presentation/widgets/task_feedback_dialog.dart';
import 'package:sparkle/features/task/presentation/widgets/task_guide_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/task_offline_indicator.dart';
import 'package:sparkle/features/task/presentation/widgets/task_protocol_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/timer_widget.dart';
import 'package:sparkle/features/task/presentation/widgets/why_this_today_panel.dart';
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
  const TaskExecutionScreen({super.key, this.origin, this.interventionId});

  final String? origin;
  final String? interventionId;

  @override
  ConsumerState<TaskExecutionScreen> createState() =>
      _TaskExecutionScreenState();
}

class _TaskExecutionScreenState extends ConsumerState<TaskExecutionScreen> {
  int _elapsedSeconds = 0;
  bool _showCelebration = false;
  bool _playCompletionConfetti = false;
  TaskCompletionResult? _completionResult;
  bool _completionFlowFinished = false;
  bool _finishCompletionWhenReady = false;
  Timer? _executionRefreshTimer;

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
        if (widget.interventionId != null &&
            widget.interventionId!.isNotEmpty) {
          unawaited(
            ref.read(interventionActionServiceProvider).reportAction(
              recordId: widget.interventionId!,
              action: 'accepted',
              actionPayload: {
                'surface': 'task_execution',
                'source': 'task_execution_entry',
                'task_id': activeTask.id,
              },
            ),
          );
        }
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
                    SparkleSnackBar.error(
                      context.l10n.taskExecutionStartFailed(
                        error is DioException
                            ? (error.message ?? error.toString())
                            : error.toString(),
                      ),
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
    if (shouldPop ?? false) {
      await _autoPauseIfLongExit(elapsedSeconds);
    }
    return shouldPop ?? false;
  }

  Future<void> _autoPauseIfLongExit(int elapsedSeconds) async {
    final task = ref.read(activeTaskProvider);
    if (task == null || isLocalOnlyTaskId(task.id)) return;
    if (task.status != TaskStatus.inProgress &&
        task.status != TaskStatus.stuck) {
      return;
    }
    final expectedSeconds = (task.estimatedMinutes * 60).clamp(60, 86400);
    if (elapsedSeconds < (expectedSeconds / 2).ceil()) return;

    await ref.read(taskListProvider.notifier).pauseTask(
          task.id,
          reason: 'auto_paused_after_long_exit',
        );
  }

  Future<void> _handleCompletion(int minutes, String? note) async {
    if (_completionFlowFinished) return;

    setState(() {
      _showCelebration = true;
      _playCompletionConfetti = true;
      _completionFlowFinished = false;
      _finishCompletionWhenReady = false;
      _completionResult = null;
    });

    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.focusComplete));
    unawaited(BgmService.duckTemporarily());

    final task = ref.read(activeTaskProvider);
    if (task != null) {
      if (isLocalOnlyTaskId(task.id)) {
        if (mounted) {
          setState(() {
            _completionResult = TaskCompletionResult(
              task: task.toJson(),
              feedback: context.l10n.taskExecutionFreeFocusCompleted,
            );
          });
          _refreshFocusStats();
          if (_finishCompletionWhenReady) {
            _finishCompletionFlow();
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
        _refreshFocusStats();
        if (result != null) {
          if (widget.interventionId != null &&
              widget.interventionId!.isNotEmpty) {
            unawaited(
              ref.read(interventionActionServiceProvider).reportAction(
                recordId: widget.interventionId!,
                action: 'acted',
                actionPayload: {
                  'surface': 'task_execution',
                  'source': 'task_execution_complete',
                  'task_id': task.id,
                  'duration_minutes': minutes,
                },
              ),
            );
          }
          unawaited(_processAchievementUnlocks(result));
        }
        if (result == null) {
          _finishCompletionFlow(showFeedbackDialog: false);
          AppFeedback.error(context, context.l10n.taskExecutionSyncFailed);
          return;
        }
        if (_finishCompletionWhenReady) {
          _finishCompletionFlow();
        }
      }
    }
  }

  void _refreshFocusStats() {
    unawaited(
      Future<void>.sync(
        () => ref
            .read(focus_stats.focusStatisticsProvider.notifier)
            .loadTodayStats(),
      ).catchError((Object error, StackTrace stackTrace) {
        debugPrint('Focus stats refresh skipped after task completion: $error');
      }),
    );
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
    final result = _completionResult;
    if (showFeedbackDialog && result == null) {
      _finishCompletionWhenReady = true;
      return;
    }
    _completionFlowFinished = true;

    setState(() {
      _showCelebration = false;
      _playCompletionConfetti = false;
      _finishCompletionWhenReady = false;
    });

    if (!showFeedbackDialog || result == null) {
      return;
    }

    final task = ref.read(activeTaskProvider);
    unawaited(
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
        SparkleSnackBar.info(context.l10n.pomodoroWorkFinished,
            duration: const Duration(seconds: 3)),
      );
    } else if (_pomodoroCycle == 1) {
      // Short break completed
      _pomodoroCycle = 0;
      _currentTimerDuration = 25 * 60; // Next work phase
      ScaffoldMessenger.of(context).showSnackBar(
        SparkleSnackBar.info(context.l10n.pomodoroBreakFinished,
            duration: const Duration(seconds: 3)),
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

  Future<void> _showStuckHelp(TaskModel task) async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    var sheetTask = task;
    if (isServerTaskId(task.id)) {
      try {
        final result = await ref.read(taskListProvider.notifier).markTaskStuck(
              task.id,
              recentSteps:
                  _guideStepNames(task.guideJson ?? const {}).take(5).toList(),
              elapsedSeconds: _elapsedSeconds,
              trigger: 'stuck_help_fab',
            );
        sheetTask = result.task;
      } catch (error) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SparkleSnackBar.error(
            context.l10n.taskExecutionAuroraDiagnosticUnavailable('$error'),
          ),
        );
      }
    }
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (sheetContext) => StuckHelpSheet(
        task: sheetTask,
        onChatPressed: () {
          Navigator.of(sheetContext).pop();
          _openStuckChat(sheetTask);
        },
        onCoreSessionPressed: () {
          Navigator.of(sheetContext).pop();
          _openStuckCoreSession(sheetTask);
        },
      ),
    );
  }

  void _openStuckCoreSession(TaskModel task) {
    final guide = task.guideJson ?? const <String, dynamic>{};
    final fallbackLines = _guideFallbackLines(guide['fallback_if_stuck']);
    final observed = <String>[
      task.title,
      ..._guideStepNames(guide).take(2),
      ...fallbackLines.take(2),
    ].where((item) => item.trim().isNotEmpty).toList();
    unawaited(
      showAuroraCoreSession(
        context: context,
        bandStatus: 'risk_found',
        wakeReasons: const ['task_stuck'],
        entryReason: AuroraCoreSessionEntryReason(
          triggerSource: 'task_stuck_prompt',
          observedSignals: observed.isEmpty ? [task.title] : observed,
          suggestedAgendaPreview: [
            I18nService.instance.isChinese
                ? '确认卡点发生在哪里'
                : 'Confirm where the block happened',
            I18nService.instance.isChinese
                ? '判断是任务太大还是知识点没接上'
                : 'Determine if the task is too big or a knowledge gap',
            I18nService.instance.isChinese
                ? '给出下一步可执行调整'
                : 'Suggest an actionable next step',
          ],
          whyNow: context.l10n.auroraTaskStuckWhyNow,
          estimatedMinutes: 4,
        ),
        scope: task.title,
        sessionType: 'strategy_recalibration',
      ),
    );
  }

  void _openStuckChat(TaskModel task) {
    final prompt = _buildStuckChatPrompt(task);
    unawaited(
      showModalBottomSheet<void>(
        context: context,
        backgroundColor: Colors.transparent,
        isScrollControlled: true,
        builder: (context) => DraggableScrollableSheet(
          initialChildSize: 0.82,
          minChildSize: 0.48,
          maxChildSize: 0.94,
          builder: (context, scrollController) => GraphiteModalSurface(
            title: context.l10n.taskExecutionChatAboutStuckPoint,
            expandChild: true,
            child: SingleChildScrollView(
              controller: scrollController,
              child: TaskChatPanel(
                taskId: task.id,
                isAvailable: isServerTaskId(task.id),
                initialExpanded: true,
                initialPrompt: prompt,
                initialExtraContext: _buildStuckChatContext(task),
              ),
            ),
          ),
        ),
      ),
    );
  }

  void _sendAuroraTrigger(TaskModel task, String trigger) {
    final message = trigger.trim();
    if (message.isEmpty) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));

    if (isServerTaskId(task.id)) {
      unawaited(
        ref.read(taskChatProvider(task.id).notifier).sendMessage(
              message,
              extraContext: _buildTaskHelpChatContext(task, trigger),
            ),
      );
      ScaffoldMessenger.of(context).showSnackBar(
        SparkleSnackBar.success(context.l10n.taskExecutionSentToAurora),
      );
      return;
    }

    final route = Uri(
      path: '/chat',
      queryParameters: {
        'chat_mode': 'study_plan',
        'prompt': message,
      },
    ).toString();
    unawaited(
      context.push(
        route,
        extra: {
          'initial_context': _buildTaskHelpChatContext(task, trigger),
        },
      ),
    );
  }

  Map<String, dynamic> _buildStuckChatContext(TaskModel task) => {
        'task_state': {
          'stage': 'stuck',
          'status': 'STUCK',
          'task_id': task.id,
          'current_task_id': task.id,
          'task_title': task.title,
          'stuck_topic': task.title,
          'estimated_minutes': task.estimatedMinutes,
          if (task.successCriteria?.trim().isNotEmpty ?? false)
            'success_criteria': task.successCriteria,
        },
        'task_stage': 'stuck',
        'stuck_event': {
          'task_id': task.id,
          'task_title': task.title,
          'source': 'task_execution_overlay',
        },
      };

  Map<String, dynamic> _buildTaskHelpChatContext(
    TaskModel task,
    String trigger,
  ) {
    final isStuck = task.status == TaskStatus.stuck ||
        trigger.toLowerCase().contains('stuck') ||
        trigger.contains('卡住');
    if (isStuck) return _buildStuckChatContext(task);
    return {
      'task_state': {
        'stage': 'task_help',
        'task_id': task.id,
        'current_task_id': task.id,
        'task_title': task.title,
        'trigger': trigger,
        'estimated_minutes': task.estimatedMinutes,
      },
    };
  }

  String _buildStuckChatPrompt(TaskModel task) {
    final guide = task.guideJson ?? const <String, dynamic>{};
    final focusCue = (guide['focus_cue']?.toString() ?? '').trim();
    final steps = _guideStepNames(guide).take(5).join('；');
    final criteria = taskSuccessCriteriaLines(task).take(3).join('；').trim();
    final structuredFallback = _guideFallbackLines(guide['fallback_if_stuck']);
    final ifStuck = (structuredFallback.isNotEmpty
            ? structuredFallback
            : _guideList(guide['if_stuck']))
        .take(5)
        .join('；')
        .trim();
    final fallback = StuckHelpSheet.genericSuggestions(context).join('；');
    final parts = <String>[
      context.l10n.taskExecutionStuckPromptIntro,
      context.l10n.taskExecutionStuckTaskLabel(task.title),
      if (task.estimatedMinutes > 0)
        context.l10n.taskExecutionStuckEstimatedTime(task.estimatedMinutes),
      if (focusCue.isNotEmpty)
        context.l10n.taskExecutionStuckFocusCue(focusCue),
      if (steps.isNotEmpty) context.l10n.taskExecutionStuckSteps(steps),
      if (criteria.isNotEmpty)
        context.l10n.taskExecutionStuckCriteria(criteria),
      context.l10n.taskExecutionStuckSuggestion(
          ifStuck.isNotEmpty ? ifStuck : fallback),
      context.l10n.taskExecutionStuckClarifyPrompt,
    ];
    return parts.join('\n');
  }

  List<String> _guideList(Object? value) {
    if (value == null) return const [];
    if (value is Iterable) {
      return value
          .map((item) => item?.toString().trim() ?? '')
          .where((item) => item.isNotEmpty)
          .toList(growable: false);
    }
    final text = value.toString().trim();
    if (text.isEmpty) return const [];
    return text
        .split(RegExp(r'[\n；;]+'))
        .map((item) => item.trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }

  List<String> _guideStepNames(Map<String, dynamic> guide) {
    final structured = guide['steps'];
    if (structured is Iterable) {
      final names = structured
          .map((item) {
            if (item is Map) {
              return (item['name'] ?? '').toString().trim();
            }
            return item?.toString().trim() ?? '';
          })
          .where((item) => item.isNotEmpty)
          .toList(growable: false);
      if (names.isNotEmpty) return names;
    }
    return _guideList(guide['method_steps']);
  }

  List<String> _guideFallbackLines(Object? value) {
    if (value is! Iterable) return const [];
    final lines = <String>[];
    for (final item in value) {
      if (item is! Map) continue;
      lines.addAll(_guideList(item['guidance'] ?? item['content']));
    }
    return lines;
  }

  Future<void> _openFocusCoach(TaskModel task) {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (sheetContext) => DraggableScrollableSheet(
        initialChildSize: 0.85,
        minChildSize: 0.55,
        maxChildSize: 0.95,
        expand: false,
        builder: (context, scrollController) => FocusAgentSheet(task: task),
      ),
    );
  }

  /// AI Coach is the *primary* creative companion on this screen — wears
  /// a brand-tinted gradient surface, sparkle glyph, and brand-coloured
  /// label so it reads as "tap me to think with AI" at a glance. The
  /// Stuck Help pill (left side) intentionally uses a quieter
  /// warning-amber treatment so the two never get mistaken.
  Widget _buildCoachFab(TaskModel task) => Positioned(
        right: DS.spacing16,
        bottom: DS.spacing64 + DS.spacing24,
        child: SafeArea(
          top: false,
          child: Tooltip(
            message: context.l10n.taskExecutionCoachTooltip,
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    DS.brandPrimary.withValues(alpha: 0.95),
                    DS.brandPrimary.withValues(alpha: 0.78),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(999),
                boxShadow: [
                  BoxShadow(
                    color: DS.brandPrimary.withValues(alpha: 0.32),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Material(
                color: Colors.transparent,
                borderRadius: BorderRadius.circular(999),
                child: InkWell(
                  key: const Key('focus-coach-fab'),
                  borderRadius: BorderRadius.circular(999),
                  onTap: () => unawaited(_openFocusCoach(task)),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing12,
                      vertical: DS.spacing10,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.auto_awesome_rounded,
                          color: DS.surfaceCanvas,
                          size: 18,
                        ),
                        const SizedBox(width: DS.spacing6),
                        Text(
                          context.l10n.taskExecutionCoachLabel,
                          style: DS.bodySmall.copyWith(
                            color: DS.surfaceCanvas,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );

  /// Stuck Help is the *escape-hatch* support action — wears a quieter
  /// warning-amber outline pill so it reads as "I'm in trouble" rather
  /// than competing with the brand-tinted AI Coach. Visually distinct
  /// in colour, weight, and surface so the two pills are never mistaken
  /// for variants of the same control.
  Widget _buildStuckHelpFab(TaskModel task) => Positioned(
        left: DS.spacing16,
        bottom: DS.spacing64 + DS.spacing24,
        child: SafeArea(
          top: false,
          child: Tooltip(
            message: context.l10n.taskExecutionStuckTooltip,
            child: Material(
              color: DS.surfaceOverlay.withValues(alpha: 0.92),
              borderRadius: BorderRadius.circular(999),
              child: InkWell(
                key: const Key('stuck-help-fab'),
                borderRadius: BorderRadius.circular(999),
                onTap: () => unawaited(_showStuckHelp(task)),
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                      color: DS.warning.withValues(alpha: 0.45),
                    ),
                  ),
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing10,
                    vertical: DS.spacing8,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.lightbulb_outline_rounded,
                        color: DS.warning,
                        size: 17,
                      ),
                      const SizedBox(width: DS.spacing4),
                      Text(
                        context.l10n.taskExecutionStuckLabel,
                        style: DS.bodySmall.copyWith(
                          color: DS.warning,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      );

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
                              // TASK-013: offline / pending sync banner
                              const TaskOfflineIndicator(),
                              if (activeTask.status == TaskStatus.paused) ...[
                                const SizedBox(height: DS.spacing12),
                                PausedTaskBanner(
                                  task: activeTask,
                                  onResume: () async {
                                    try {
                                      await ref
                                          .read(taskListProvider.notifier)
                                          .resumeTask(activeTask.id);
                                      return true;
                                    } catch (_) {
                                      return false;
                                    }
                                  },
                                ),
                              ],
                              if (activeTask.boundSources.isNotEmpty) ...[
                                const SizedBox(height: DS.spacing12),
                                SourceLifecycleBadgeGroup(
                                  sources: activeTask.boundSources,
                                  maxVisible: 2,
                                ),
                              ],
                              // 1. Focus Mode Entry Card (Prominent)
                              const SizedBox(height: DS.spacing16),
                              _buildFocusEntryCard(context, activeTask),
                              const SizedBox(height: DS.spacing16),
                              // TASK-001: structured TaskCardProtocol panel
                              // (why_this_task / materials / fallback)
                              TaskProtocolPanel(taskId: activeTask.id),
                              WhyThisTodayPanel(taskId: activeTask.id),
                              const SizedBox(height: DS.spacing16),
                              TaskGuidePanel(
                                task: activeTask,
                                onAuroraTriggerPressed: (trigger) =>
                                    _sendAuroraTrigger(activeTask, trigger),
                              ),
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
                                  fontWeight: DS.fontWeightMedium,
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

          _buildStuckHelpFab(activeTask),
          _buildCoachFab(activeTask),

          // Celebration Overlay
          if (_showCelebration)
            Positioned.fill(
              child: TaskCompletionCelebration(
                task: activeTask,
                play: _playCompletionConfetti,
                onContinue: _skipCelebration,
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
                unawaited(context.push('/focus/mindfulness/${task.id}'));
              },
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
                text: context.l10n.taskExecutionResetTimer,
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

  bool _hasExecutionPermissionIssue(OpenClawConnectionService connection) {
    return connection.hasExecutionPermissionIssue;
  }

  Future<void> _handoffTask(BuildContext context, WidgetRef ref) async {
    ref.read(openClawTaskNudgeDismissedProvider.notifier).state = false;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.messageSend));
    final intent =
        await ref.read(taskListProvider.notifier).handoffTaskToAi(task.id);
    if (!context.mounted) return;

    if (intent == null) {
      final message = ref.read(taskListProvider).error ??
          context.l10n.taskExecutionAiHandoffFailed;
      AppFeedback.error(
        context,
        message.replaceFirst('Exception: ', ''),
      );
      return;
    }

    final feedbackMessage = switch (intent.status) {
      ExecutionIntentStatus.succeeded => context.l10n.taskExecutionAiCompleted,
      ExecutionIntentStatus.partial => context.l10n.taskExecutionAiPartial,
      ExecutionIntentStatus.failed =>
        intent.errorMessage ?? context.l10n.taskExecutionAiFailed,
      ExecutionIntentStatus.waitingApproval =>
        context.l10n.taskExecutionAiWaitingApproval,
      _ => context.l10n.taskExecutionAiHandedOff(intent.statusLabel),
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
    AppFeedback.info(
      context,
      _hasExecutionPermissionIssue(connection)
          ? context.l10n.taskExecutionPermissionInsufficientQueued
          : ExecutionCopy.engineOfflineQueuedMessage(),
    );
  }

  Future<void> _confirmAiResult(BuildContext context, WidgetRef ref) async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    final record = await ref
        .read(taskListProvider.notifier)
        .confirmTaskExecutionResult(task.id);
    if (!context.mounted) return;

    if (record == null) {
      final message = ref.read(taskListProvider).error ??
          context.l10n.taskExecutionAiConfirmFailed;
      AppFeedback.error(context, message.replaceFirst('Exception: ', ''));
      return;
    }

    AppFeedback.success(context, context.l10n.taskExecutionAiResultConfirmed);
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
      final message = ref.read(taskListProvider).error ??
          context.l10n.taskExecutionRejectFailed;
      AppFeedback.error(context, message.replaceFirst('Exception: ', ''));
      return;
    }
    AppFeedback.info(context, context.l10n.taskExecutionTaskReturned);
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
      case ExecutionIntentStatus.queued:
      case ExecutionIntentStatus.dispatched:
      case ExecutionIntentStatus.running:
      case ExecutionIntentStatus.unknown:
      case null:
        return DS.primaryBase;
    }
  }

  String _executionStatusTitle(
      BuildContext context, ExecutionIntentModel? intent, bool isLoading) {
    if (isLoading) return context.l10n.taskExecutionAiTakingOver;
    return intent == null
        ? context.l10n.taskExecutionAiNotStarted
        : context.l10n.taskExecutionAiStatusLabel(intent.statusLabel);
  }

  String _executionStatusSubtitle(
    BuildContext context,
    ExecutionIntentModel? intent,
    ExecutionRecordModel? record,
    bool isLoading,
  ) {
    if (isLoading) {
      return context.l10n.taskExecutionSendingToOpenclaw;
    }
    if (intent == null) {
      return context.l10n.taskExecutionDigitalTaskHint;
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
              ? context.l10n.taskExecutionValidationLabel(
                  record.validationPassed!, record.validationTotal!)
              : record.trustLabel;
      return '${context.l10n.taskExecutionResultLabel(validationText)}'
          '${record.approvalRequested != null ? context.l10n.taskExecutionApprovalRequestLabel(record.approvalRequested!) : ''}';
    }
    if (intent.goal.trim().isNotEmpty) {
      return context.l10n
          .taskExecutionGoalWithTrust(intent.goal, intent.trustLabel);
    }
    return context.l10n.taskExecutionResultTrust(intent.trustLabel);
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

  String? _executionMetaPreview(
      BuildContext context, ExecutionIntentModel? intent) {
    if (intent == null) return null;
    final parts = <String>[
      if (intent.templateName != null && intent.templateName!.isNotEmpty)
        context.l10n.taskExecutionTemplateLabel(intent.templateName!),
      if (intent.strategyVariant != null && intent.strategyVariant!.isNotEmpty)
        context.l10n.taskExecutionStrategyLabel(intent.strategyVariant!),
      if (intent.targetNodeLabel != null && intent.targetNodeLabel!.isNotEmpty)
        context.l10n.taskExecutionNodeLabel(intent.targetNodeLabel!),
    ];
    if (parts.isEmpty) return null;
    return parts.join(' · ');
  }

  String _handoffButtonText(
      BuildContext context, ExecutionIntentModel? intent, bool isLoading) {
    if (isLoading) return context.l10n.taskExecutionAiTakingOverLoading;
    switch (intent?.status) {
      case ExecutionIntentStatus.failed:
      case ExecutionIntentStatus.timedOut:
      case ExecutionIntentStatus.canceled:
      case ExecutionIntentStatus.handedBack:
        return context.l10n.taskExecutionRehandoffToAi;
      case ExecutionIntentStatus.succeeded:
      case ExecutionIntentStatus.partial:
        return context.l10n.taskExecutionHandoffToAiAgain;
      case ExecutionIntentStatus.waitingApproval:
        return context.l10n.taskExecutionWaitingConfirm;
      case ExecutionIntentStatus.draft:
      case ExecutionIntentStatus.ready:
      case ExecutionIntentStatus.queued:
      case ExecutionIntentStatus.dispatched:
      case ExecutionIntentStatus.running:
        return context.l10n.taskExecutionAiRunning;
      case ExecutionIntentStatus.unknown:
      case null:
        return context.l10n.taskExecutionHandoffToAi;
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
    final hasExecutionPermissionIssue =
        _hasExecutionPermissionIssue(connection);
    final nudgeDismissed = ref.watch(openClawTaskNudgeDismissedProvider);
    final nudgeExpanded = ref.watch(openClawTaskNudgeExpandedProvider);
    final supportsAiHandoff = isServerTaskId(task.id);
    final canHandoff = supportsAiHandoff &&
        isClawConnected &&
        task.status != TaskStatus.completed &&
        task.status != TaskStatus.abandoned &&
        task.status != TaskStatus.paused &&
        (executionIntent == null || executionIntent.isTerminal) &&
        !isHandoffLoading;
    final canQueueHandoff = supportsAiHandoff &&
        !isClawConnected &&
        isClawConfigured &&
        task.status != TaskStatus.completed &&
        task.status != TaskStatus.abandoned &&
        task.status != TaskStatus.paused &&
        (executionIntent == null || executionIntent.isTerminal) &&
        !isHandoffLoading;
    final showExecutionStatus =
        supportsAiHandoff && (executionIntent != null || isHandoffLoading);
    final statusColor =
        _executionStatusColor(executionIntent, isHandoffLoading);
    final outputPreview = _executionOutputPreview(executionRecord);
    final metaPreview = _executionMetaPreview(context, executionIntent);

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
                context.l10n.taskExecutionRecommendedTemplates,
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
              title: hasExecutionPermissionIssue
                  ? context.l10n.taskExecutionOpenclawConnectedNoPermission
                  : isClawConfigured
                      ? context.l10n.taskExecutionOpenclawOfflineQueued
                      : context.l10n.taskExecutionOpenclawNotConnected,
              subtitle: hasExecutionPermissionIssue
                  ? context.l10n.taskExecutionOpenclawPermissionHint
                  : isClawConfigured
                      ? context.l10n.taskExecutionOpenclawOfflineHint
                      : context.l10n.taskExecutionOpenclawNotConnectedHint,
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
                    child: Text(isClawConfigured
                        ? context.l10n.taskExecutionViewAction
                        : context.l10n.taskExecutionConnectAction),
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
                    tooltip: context.l10n.taskExecutionDismissHint,
                  ),
                ],
              ),
              metrics: [
                OpenClawMetricPill(
                  icon: hasExecutionPermissionIssue
                      ? Icons.key_off_rounded
                      : Icons.sensors_rounded,
                  label: hasExecutionPermissionIssue
                      ? context.l10n.taskExecutionMetricConnectedNoPermission
                      : isClawConfigured
                          ? context.l10n.taskExecutionMetricConfiguredOffline
                          : context.l10n.taskExecutionMetricNotConfigured,
                  tone: OpenClawVisualTone.offline,
                  emphasized: true,
                ),
                if (queuedRequestCount > 0)
                  OpenClawMetricPill(
                    icon: Icons.schedule_rounded,
                    label: context.l10n
                        .taskExecutionMetricQueuedTasks(queuedRequestCount),
                    tone: OpenClawVisualTone.attention,
                    emphasized: true,
                  ),
                OpenClawMetricPill(
                  icon: Icons.arrow_circle_right_rounded,
                  label: hasExecutionPermissionIssue
                      ? context.l10n.taskExecutionSuggestionFixPermission
                      : isClawConfigured
                          ? context.l10n.taskExecutionSuggestionQueueFirst
                          : context.l10n.taskExecutionSuggestionConnectFirst,
                  tone: OpenClawVisualTone.active,
                ),
              ],
              expandedContent: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildNudgeDetailBlock(
                    label: context.l10n.taskExecutionNudgeCurrentStatus,
                    value: hasExecutionPermissionIssue
                        ? context.l10n.taskExecutionNudgeStatusPermissionIssue
                        : isClawConfigured
                            ? context.l10n.taskExecutionNudgeStatusOffline
                            : context.l10n.taskExecutionNudgeStatusNotConnected,
                  ),
                  const SizedBox(height: DS.spacing8),
                  _buildNudgeDetailBlock(
                    label: context.l10n.taskExecutionNudgeWhyThisPrompt,
                    value: context.l10n.taskExecutionNudgeWhyThisPromptValue,
                  ),
                  const SizedBox(height: DS.spacing8),
                  _buildNudgeDetailBlock(
                    label: context.l10n.taskExecutionNudgeNextAction,
                    value: hasExecutionPermissionIssue
                        ? context
                            .l10n.taskExecutionNudgeNextActionPermissionIssue
                        : isClawConfigured
                            ? context.l10n.taskExecutionNudgeNextActionOffline
                            : context
                                .l10n.taskExecutionNudgeNextActionNotConnected,
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
                              context,
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
                              context,
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
                        ? _handoffButtonText(
                            context, executionIntent, isHandoffLoading)
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
    final criteria = taskSuccessCriteriaLines(task);

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
                      context.l10n.taskExecutionCompletedToday,
                      style: DS.titleLarge.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  context.l10n.taskExecutionCompletionCheckHint,
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
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
                const SizedBox(height: DS.spacing12),
                if (criteria.isNotEmpty)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(DS.spacing12),
                    decoration: BoxDecoration(
                      color: DS.surfaceSecondary,
                      borderRadius: DS.borderRadius12,
                      border: Border.all(color: DS.borderSubtle),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.l10n.taskExecutionCompletionCriteria,
                          style: DS.bodyMedium.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        const SizedBox(height: DS.spacing8),
                        for (final item in criteria.take(4))
                          Padding(
                            padding: const EdgeInsets.only(
                              bottom: DS.spacing8,
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(
                                  Icons.check_circle_outline_rounded,
                                  size: 18,
                                  color: DS.success,
                                ),
                                const SizedBox(width: DS.spacing8),
                                Expanded(
                                  child: Text(
                                    item,
                                    style: DS.bodySmall.copyWith(
                                      color: DS.textSecondary,
                                      height: 1.45,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  )
                else
                  Text(
                    context.l10n.taskExecutionNoCriteriaHint,
                    style: DS.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
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
                Text(
                  context.l10n.taskExecutionCriteriaMatchQuestion,
                  style: DS.bodyMedium.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: DS.spacing12),
                Row(
                  children: [
                    Expanded(
                      child: CustomButton.secondary(
                        text: context.l10n.taskExecutionCriteriaNotMet,
                        onPressed: () {
                          Navigator.of(ctx).pop();
                          AppFeedback.info(
                            context,
                            context.l10n.taskExecutionContinueOrRetryTomorrow,
                          );
                        },
                        size: CustomButtonSize.small,
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: CustomButton.primary(
                        text: context.l10n.taskExecutionCriteriaMetComplete,
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
      ).whenComplete(noteController.dispose),
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
    final isPaused = task.status == TaskStatus.paused;
    final canPause =
        task.status == TaskStatus.inProgress || task.status == TaskStatus.stuck;
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
          if (canPause) ...[
            Expanded(
              child: CustomButton.secondary(
                text: context.l10n.taskActionPause,
                onPressed: () {
                  unawaited(
                    ref.read(taskListProvider.notifier).pauseTask(
                          task.id,
                          reason: 'user_paused_from_execution_controls',
                        ),
                  );
                },
              ),
            ),
            const SizedBox(width: DS.spacing16),
          ],
          Expanded(
            flex: 2,
            child: CustomButton.primary(
              text: isPaused
                  ? context.l10n.taskActionResume
                  : context.l10n.taskExecutionCompleteTitle,
              customGradient: _taskWarmActionGradient(context),
              onPressed: isPaused
                  ? () {
                      unawaited(
                        ref.read(taskListProvider.notifier).resumeTask(task.id),
                      );
                    }
                  : () => _showCompleteDialog(context),
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
  String? _selectedReason;
  final TextEditingController _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final presetReasons = [
      context.l10n.taskExecutionRejectReasonInaccurate,
      context.l10n.taskExecutionRejectReasonIncomplete,
      context.l10n.taskExecutionRejectReasonSafety,
      context.l10n.taskExecutionRejectReasonSelfDo,
    ];

    return GraphiteModalSurface(
      title: context.l10n.taskExecutionRejectReasonTitle,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.taskExecutionRejectDescription,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: presetReasons.map((reason) {
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
            decoration: InputDecoration(
              labelText: context.l10n.taskExecutionRejectAdditionalNote,
              hintText: context.l10n.taskExecutionRejectNoteHint,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Row(
            children: [
              Expanded(
                child: CustomButton.text(
                  text: context.l10n.cancel,
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: CustomButton.primary(
                  text: context.l10n.taskExecutionRejectConfirm,
                  onPressed: () {
                    final extra = _controller.text.trim();
                    final reason = [
                      _selectedReason,
                      if (extra.isNotEmpty) extra,
                    ].whereType<String>().join('；');
                    Navigator.of(context).pop(
                      reason.isEmpty
                          ? context.l10n.taskExecutionUserRetrievedTask
                          : reason,
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
    unawaited(_slideController.forward());
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
        child: SafeArea(
          minimum: const EdgeInsets.all(DS.xl),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Material(
                color: Colors.transparent,
                child: Container(
                  padding: const EdgeInsets.all(DS.xl),
                  decoration: BoxDecoration(
                    color: DS.surfacePrimary,
                    borderRadius: BorderRadius.circular(28),
                    border: Border.all(
                      color: DS.neutral200.withValues(alpha: 0.8),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: DS.neutral900.withValues(alpha: 0.18),
                        blurRadius: 36,
                        offset: const Offset(0, 18),
                      ),
                    ],
                  ),
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
                          fontWeight: DS.fontWeightBold,
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
