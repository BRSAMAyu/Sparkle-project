import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart'
    hide ButtonVariant;
import 'package:sparkle/core/design/widgets/success_animation.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_context_summary.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/blocking_interceptor_dialog.dart';
import 'package:sparkle/features/task/presentation/widgets/quick_tools_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/task_chat_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/task_feedback_dialog.dart';
import 'package:sparkle/features/task/presentation/widgets/timer_widget.dart';
import 'package:sparkle/features/task/task_routes.dart';
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

class TaskExecutionScreen extends ConsumerStatefulWidget {
  const TaskExecutionScreen({super.key});

  @override
  ConsumerState<TaskExecutionScreen> createState() =>
      _TaskExecutionScreenState();
}

class _TaskExecutionScreenState extends ConsumerState<TaskExecutionScreen> {
  int _elapsedSeconds = 0;
  bool _showCelebration = false;
  TaskCompletionResult? _completionResult;
  bool _completionFlowFinished = false;
  Timer? _celebrationDismissTimer;

  // Timer Enhancement State
  TimerMode _timerMode = TimerMode.countUp;
  int _currentTimerDuration = 0; // In seconds
  bool _isPomodoroMode = false;
  int _pomodoroCycle = 0; // 0: work, 1: break, 2: long break

  // Focus Protection State
  DateTime? _pageEnterTime;

  @override
  void initState() {
    super.initState();
    _pageEnterTime = DateTime.now(); // Record page entry time
    final task = ref.read(activeTaskProvider);
    _currentTimerDuration =
        task?.actualMinutes != null ? task!.actualMinutes! * 60 : 0;

    // 🔧 Fix: Call startTask if the task is PENDING
    // This ensures backend state transitions to IN_PROGRESS when user enters execution screen
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final activeTask = ref.read(activeTaskProvider);
      if (activeTask != null && activeTask.status == TaskStatus.pending) {
        ref.read(taskListProvider.notifier).startTask(activeTask.id).catchError(
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
                      ),),
                  backgroundColor: DS.error,
                ),
              );
            }
          },
        );
      }
    });
  }

  @override
  void dispose() {
    _celebrationDismissTimer?.cancel();
    super.dispose();
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

    final shouldPop = await showDialog<bool>(
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

    // 1. Stop Timer
    setState(() {
      _showCelebration = true;
      _completionFlowFinished = false;
    });

    // 2. Haptic Feedback
    HapticFeedback.mediumImpact();

    // 3. API Call
    final task = ref.read(activeTaskProvider);
    if (task != null) {
      // Run completion in background while animation plays
      final result = await ref
          .read(taskListProvider.notifier)
          .completeTask(task.id, minutes, note);
      if (mounted) {
        setState(() {
          _completionResult = result;
        });
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
          _celebrationDismissTimer?.cancel();
          _celebrationDismissTimer = Timer(
            const Duration(milliseconds: 1100),
            _finishCompletionFlow,
          );
        }
      }
    }
  }

  void _onCelebrationComplete() {
    _finishCompletionFlow();
  }

  void _finishCompletionFlow({bool showFeedbackDialog = true}) {
    if (!mounted || _completionFlowFinished) return;
    _completionFlowFinished = true;
    _celebrationDismissTimer?.cancel();

    final result = _completionResult;
    setState(() {
      _showCelebration = false;
    });

    if (!showFeedbackDialog || result == null) {
      return;
    }

    final task = ref.read(activeTaskProvider);
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => TaskFeedbackDialog(
        result: result,
        taskId: task?.id ?? '',
        onClose: () {
          Navigator.of(context).pop();
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
                                    _currentTimerDuration,
                                  ), // Force rebuild on duration change
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
                              ),
                              const SizedBox(height: DS.spacing24),

                              // Plan Context Summary (if task has a plan)
                              if (activeTask.planId != null)
                                PlanContextSummary(planId: activeTask.planId),
                              if (activeTask.planId != null)
                                const SizedBox(height: DS.spacing16),

                              // 2. Task Guide Area
                              GraphiteCardSurface(
                                padding: EdgeInsets.zero,
                                child: ExpansionTile(
                                  shape:
                                      const Border(), // Remove default borders
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
                                      Text(
                                        l10n.taskExecutionGuideTitle,
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
                                    Container(
                                      width: double.infinity,
                                      padding:
                                          const EdgeInsets.all(DS.spacing16),
                                      decoration: BoxDecoration(
                                        color: DS.neutral50,
                                        borderRadius: const BorderRadius.only(
                                          bottomLeft: Radius.circular(16),
                                          bottomRight: Radius.circular(16),
                                        ),
                                      ),
                                      child: MarkdownBody(
                                        data:
                                            activeTask.guideContent ??
                                                l10n.taskExecutionGuideEmpty,
                                        styleSheet: MarkdownStyleSheet(
                                          p: Theme.of(context)
                                              .textTheme
                                              .bodyMedium
                                              ?.copyWith(
                                                color: DS.neutral700,
                                                height: 1.6,
                                              ),
                                          h1: Theme.of(context)
                                              .textTheme
                                              .titleLarge
                                              ?.copyWith(
                                                fontWeight: DS.fontWeightBold,
                                              ),
                                          h2: Theme.of(context)
                                              .textTheme
                                              .titleMedium
                                              ?.copyWith(
                                                fontWeight: DS.fontWeightBold,
                                              ),
                                          code: TextStyle(
                                            backgroundColor: DS.neutral100,
                                            color: DS.textPrimary,
                                            fontFamily: 'monospace',
                                            fontSize: DS.fontSizeSm,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: DS.spacing16),

                              // 3. Quick Tools Panel
                              QuickToolsPanel(taskId: activeTask.id),
                              const SizedBox(height: DS.spacing16),

                              // 4. Task Chat Panel
                              TaskChatPanel(taskId: activeTask.id),
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
              child: GestureDetector(
                onTap: _skipCelebration,
                behavior: HitTestBehavior.opaque,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: DS.overlay50.withValues(alpha: 0.84),
                  ),
                  child: SuccessAnimation(
                    playAnimation: true,
                    onAnimationComplete: _onCelebrationComplete,
                    child: Center(
                      child: GraphiteCardSurface(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(DS.xl),
                              decoration: BoxDecoration(
                                color: DS.surfaceSecondary,
                                shape: BoxShape.circle,
                                border: Border.all(color: DS.borderSubtle),
                              ),
                              child: Icon(
                                Icons.check_circle,
                                color: DS.success,
                                size: 72,
                              ),
                            ),
                            const SizedBox(height: DS.spacing24),
                            Text(
                              l10n.taskExecutionCompletedTitle,
                              style: Theme.of(context)
                                  .textTheme
                                  .headlineSmall
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                            const SizedBox(height: DS.spacing12),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.spacing18,
                                vertical: DS.spacing8,
                              ),
                              decoration: BoxDecoration(
                                color: DS.surfaceSecondary,
                                borderRadius: DS.borderRadius20,
                                border: Border.all(color: DS.borderSubtle),
                              ),
                              child: Text(
                                l10n.taskExecutionExpGained(
                                  activeTask.difficulty * 10,
                                ),
                                style: Theme.of(context)
                                    .textTheme
                                    .titleMedium
                                    ?.copyWith(
                                      color: DS.textPrimary,
                                      fontWeight: DS.fontWeightBold,
                                    ),
                              ),
                            ),
                            const SizedBox(height: DS.spacing16),
                            Text(
                              l10n.taskExecutionTapToContinue,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(color: DS.textSecondary),
                            ),
                            const SizedBox(height: DS.spacing16),
                            SparkleButton.ghost(
                              label: l10n.taskExecutionSkipAnimation,
                              onPressed: _skipCelebration,
                            ),
                          ],
                        ),
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

class _TimerControls extends StatelessWidget {
  const _TimerControls({
    required this.isPomodoroMode,
    required this.onTogglePomodoro,
    required this.onSetPreset,
  });
  final bool isPomodoroMode;
  final VoidCallback onTogglePomodoro;
  final void Function(int minutes) onSetPreset;

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

class _BottomControls extends ConsumerWidget {
  const _BottomControls({
    required this.task,
    required this.elapsedSeconds,
    required this.onComplete,
  });
  final TaskModel task;
  final int elapsedSeconds;
  final void Function(int minutes, String? note) onComplete;

  void _showCompleteDialog(BuildContext context, WidgetRef ref) {
    final noteController = TextEditingController();
    final minutes = Duration(seconds: elapsedSeconds).inMinutes;

    showDialog<void>(
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
                        HapticFeedback.heavyImpact();
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
    );
  }

  void _abandonTask(BuildContext context, WidgetRef ref) {
    showDialog<void>(
      context: context,
      builder: (ctx) => BlockingInterceptorDialog(
        taskId: task.id,
        onAbandonConfirmed: () {
          ref.read(taskListProvider.notifier).abandonTask(task.id);
          context.go(TaskRoutes.home);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => GraphiteCardSurface(
        padding: const EdgeInsets.all(DS.spacing16),
        borderColor: DS.borderSubtle,
        child: Row(
          children: [
            Expanded(
              child: CustomButton.text(
                text: context.l10n.taskExecutionAbandon,
                onPressed: () => _abandonTask(context, ref),
                // Use error color for text if possible, or leave as primary/custom
              ),
            ),
            const SizedBox(width: DS.spacing16),
            Expanded(
              flex: 2,
              child: CustomButton.primary(
                text: context.l10n.taskExecutionCompleteTitle,
                customGradient: _taskWarmActionGradient(context),
                onPressed: () => _showCompleteDialog(context, ref),
              ),
            ),
          ],
        ),
      );
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
    HapticFeedback.lightImpact();
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
    HapticFeedback.lightImpact();
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
