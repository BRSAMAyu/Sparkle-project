import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/design/widgets/success_animation.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/blocking_interceptor_dialog.dart';
import 'package:sparkle/features/task/presentation/widgets/quick_tools_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/task_chat_panel.dart';
import 'package:sparkle/features/task/presentation/widgets/task_feedback_dialog.dart';
import 'package:sparkle/features/task/presentation/widgets/timer_widget.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class TaskExecutionScreen extends ConsumerStatefulWidget {
  const TaskExecutionScreen({super.key});

  @override
  ConsumerState<TaskExecutionScreen> createState() =>
      _TaskExecutionScreenState();
}

class _TaskExecutionScreenState extends ConsumerState<TaskExecutionScreen> {
  int _elapsedSeconds = 0;
  bool _isTimerRunning = false;
  bool _showCelebration = false;
  TaskCompletionResult? _completionResult;

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
    // 1. Stop Timer
    setState(() {
      _isTimerRunning = false;
      _showCelebration = true;
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
      }
    }
  }

  void _onCelebrationComplete() {
    if (!mounted) return;

    if (_completionResult != null) {
      final task = ref.read(activeTaskProvider);
      // Show feedback dialog
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (context) => TaskFeedbackDialog(
          result: _completionResult!,
          taskId: task?.id ?? '',
          onClose: () {
            Navigator.of(context).pop(); // Close dialog
            context.go(GalaxyRoutes.home); // Navigate away
          },
        ),
      );
    } else {
      // Fallback if result isn't ready or failed (though optimistic update usually handles it)
      // For now, just go to galaxy
      context.go(GalaxyRoutes.home);
    }
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
        const SnackBar(content: Text('番茄工作时间结束！休息一下。')),
      );
    } else if (_pomodoroCycle == 1) {
      // Short break completed
      _pomodoroCycle = 0;
      _currentTimerDuration = 25 * 60; // Next work phase
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('休息时间结束！开始新的工作。')),
      );
    }
    // Extend for long breaks if desired
    setState(() {}); // Trigger rebuild for TimerWidget to update
  }

  @override
  Widget build(BuildContext context) {
    final activeTask = ref.watch(activeTaskProvider);

    if (activeTask == null) {
      return Scaffold(
        appBar: AppBar(
          flexibleSpace: Container(
            decoration: BoxDecoration(
              gradient: DS.primaryGradient,
            ),
          ),
        ),
        body: Center(
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
                '未选择任务',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: DS.neutral700,
                    ),
              ),
              const SizedBox(height: DS.spacing24),
              CustomButton.primary(
                text: '返回',
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
          Scaffold(
            extendBodyBehindAppBar: true,
            appBar: AppBar(
              backgroundColor: Colors.transparent,
              elevation: 0,
              iconTheme: IconThemeData(color: DS.neutral900),
              title: Text(
                activeTask.title,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: DS.neutral900),
              ),
            ),
            body: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    DS.primaryBase.withValues(alpha: 0.05),
                    DS.secondaryBase.withValues(alpha: 0.05),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: SafeArea(
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
                                  horizontal: DS.spacing8, vertical: DS.spacing16),
                              child: Divider(
                                height: 1,
                                thickness: 1,
                                color: DS.neutral200,
                              ),
                            ),

                            // 2. Timer Area (Auxiliary)
                            Text(
                              '页面内计时器',
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
                                    _currentTimerDuration,), // Force rebuild on duration change
                                mode: _timerMode,
                                initialSeconds: _currentTimerDuration,
                                maxSeconds: _isPomodoroMode
                                    ? (_pomodoroCycle == 0 ? 25 * 60 : 5 * 60)
                                    : null,
                                onTick: (seconds) => _elapsedSeconds = seconds,
                                onStateChange: (isRunning) =>
                                    _isTimerRunning = isRunning,
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
                            const SizedBox(height: DS.spacing40),

                            // 2. Task Guide Area
                            DecoratedBox(
                              decoration: BoxDecoration(
                                color: DS.brandPrimary,
                                borderRadius: DS.borderRadius16,
                                boxShadow: DS.shadowMd,
                                border: Border.all(
                                  color: DS.neutral200,
                                ),
                              ),
                              child: ExpansionTile(
                                shape: const Border(), // Remove default borders
                                tilePadding: const EdgeInsets.symmetric(
                                  horizontal: DS.spacing16,
                                  vertical: DS.spacing12,
                                ),
                                title: Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(10),
                                      decoration: BoxDecoration(
                                        gradient: DS.infoGradient,
                                        shape: BoxShape.circle,
                                        boxShadow: [
                                          BoxShadow(
                                            color:
                                                DS.info.withValues(alpha: 0.3),
                                            blurRadius: 8,
                                            offset: const Offset(0, 2),
                                          ),
                                        ],
                                      ),
                                      child: Icon(Icons.description_outlined,
                                          color: DS.brandPrimary, size: 22,),
                                    ),
                                    const SizedBox(width: DS.spacing12),
                                    Text(
                                      '执行指南',
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
                                    padding: const EdgeInsets.all(DS.spacing16),
                                    decoration: BoxDecoration(
                                      color: DS.neutral50,
                                      borderRadius: const BorderRadius.only(
                                        bottomLeft: Radius.circular(16),
                                        bottomRight: Radius.circular(16),
                                      ),
                                    ),
                                    child: MarkdownBody(
                                      data: activeTask.guideContent ?? '暂无执行指南',
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
                                          color: DS.primaryDark,
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

          // Celebration Overlay
          if (_showCelebration)
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      DS.brandPrimary.withValues(alpha: 0.7),
                      DS.primaryBase.withValues(alpha: 0.3),
                    ],
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                  ),
                ),
                child: SuccessAnimation(
                  playAnimation: true,
                  onAnimationComplete: _onCelebrationComplete,
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(DS.xl),
                          decoration: BoxDecoration(
                            gradient: DS.successGradient,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: DS.success.withValues(alpha: 0.5),
                                blurRadius: 30,
                                spreadRadius: 10,
                              ),
                            ],
                          ),
                          child: Icon(
                            Icons.check_circle,
                            color: DS.brandPrimary,
                            size: 80,
                          ),
                        ),
                        const SizedBox(height: DS.spacing24),
                        Text(
                          '任务完成！',
                          style: Theme.of(context)
                              .textTheme
                              .headlineMedium
                              ?.copyWith(
                                color: DS.brandPrimary,
                                fontWeight: DS.fontWeightBold,
                              ),
                        ),
                        const SizedBox(height: DS.spacing12),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: DS.spacing20,
                            vertical: DS.spacing8,
                          ),
                          decoration: BoxDecoration(
                            gradient: DS.warningGradient,
                            borderRadius: DS.borderRadius20,
                            boxShadow: DS.shadowLg,
                          ),
                          child: Text(
                            '+${activeTask.difficulty * 10} 经验值',
                            style: Theme.of(context)
                                .textTheme
                                .titleLarge
                                ?.copyWith(
                                  color: DS.brandPrimary,
                                  fontWeight: DS.fontWeightBold,
                                ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildFocusEntryCard(BuildContext context, TaskModel task) => Container(
        margin: const EdgeInsets.symmetric(horizontal: DS.spacing4),
        padding: const EdgeInsets.all(DS.xl),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              DS.primaryBase.withValues(alpha: 0.08),
              DS.secondaryBase.withValues(alpha: 0.08),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: DS.borderRadius20,
          border: Border.all(
            color: DS.primaryBase.withValues(alpha: 0.2),
          ),
          boxShadow: [
            BoxShadow(
              color: DS.primaryBase.withValues(alpha: 0.15),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    gradient: DS.flameGradient,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.local_fire_department_rounded,
                      color: DS.brandPrimaryConst, size: 28),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: Text(
                    '进入沉浸专注模式',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: DS.fontWeightBold,
                      color: DS.neutral900,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.md),
            Wrap(
              spacing: DS.md,
              runSpacing: DS.xs,
              children: const [
                _FeatureChip(icon: Icons.fullscreen, label: '全屏专注'),
                _FeatureChip(icon: Icons.access_time_rounded, label: '翻页时钟'),
                _FeatureChip(icon: Icons.star_rounded, label: '星空背景'),
                _FeatureChip(icon: Icons.visibility_off_rounded, label: '分心检测'),
                _FeatureChip(icon: Icons.psychology_rounded, label: 'AI教练'),
                _FeatureChip(icon: Icons.emoji_events_rounded, label: '火苗奖励'),
              ],
            ),
            const SizedBox(height: DS.lg),
            CustomButton.primary(
              text: '立即开始',
              icon: Icons.arrow_forward_rounded,
              customGradient: DS.primaryGradient,
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
                text: '番茄钟',
                icon: Icons.timer,
                onPressed: onTogglePomodoro,
                size: CustomButtonSize.small,
              ),
              ...[15, 25, 45, 60].map(
                (minutes) => CustomButton.secondary(
                  text: '$minutes 分钟',
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
          color: DS.brandPrimaryConst.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.primaryBase),
            const SizedBox(width: 4),
            Text(label,
                style: const TextStyle(fontSize: 12, color: DS.neutral700)),
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
      builder: (ctx) => AlertDialog(
        shape: const RoundedRectangleBorder(
          borderRadius: DS.borderRadius20,
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                gradient: DS.successGradient,
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.check_circle_outline,
                  color: DS.brandPrimary, size: 24,),
            ),
            const SizedBox(width: DS.spacing12),
            const Text(
              '完成任务',
              style: TextStyle(
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.neutral50,
                borderRadius: DS.borderRadius12,
              ),
              child: Row(
                children: [
                  Icon(Icons.timer_outlined, color: DS.primaryBase),
                  const SizedBox(width: DS.spacing8),
                  Text(
                    '用时：$minutes 分钟',
                    style: TextStyle(
                      fontWeight: DS.fontWeightMedium,
                      color: DS.neutral700,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing16),
            TextField(
              controller: noteController,
              decoration: InputDecoration(
                labelText: '笔记（选填）',
                hintText: '记录一些学习心得...',
                border: const OutlineInputBorder(
                  borderRadius: DS.borderRadius12,
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: DS.borderRadius12,
                  borderSide: BorderSide(
                    color: DS.primaryBase,
                    width: 2,
                  ),
                ),
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          CustomButton.text(
            text: '取消',
            onPressed: () => Navigator.of(ctx).pop(),
          ),
          CustomButton.primary(
            text: '确认完成',
            icon: Icons.check_rounded,
            onPressed: () {
              HapticFeedback.heavyImpact();
              Navigator.of(ctx).pop();
              onComplete(
                  minutes,
                  noteController.text.trim().isEmpty
                      ? null
                      : noteController.text.trim(),);
            },
            customGradient: DS.successGradient,
            size: CustomButtonSize.small,
          ),
        ],
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
          // Navigate away completely to Galaxy to exit execution flow safely
          context.go(GalaxyRoutes.home);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.brandPrimary,
          boxShadow: [
            BoxShadow(
              color: DS.brandPrimary.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        child: Row(
          children: [
            Expanded(
              child: CustomButton.text(
                text: '放弃',
                onPressed: () => _abandonTask(context, ref),
                // Use error color for text if possible, or leave as primary/custom
              ),
            ),
            const SizedBox(width: DS.spacing16),
            Expanded(
              flex: 2,
              child: CustomButton.primary(
                text: '完成任务',
                onPressed: () => _showCompleteDialog(context, ref),
                customGradient: DS.successGradient,
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

class _TaskExitConfirmationDialogState extends State<_TaskExitConfirmationDialog>
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
          backgroundColor: Colors.transparent,
          insetPadding: const EdgeInsets.all(DS.xl),
          child: Container(
            padding: const EdgeInsets.all(DS.xl),
            decoration: BoxDecoration(
              color: DS.surfaceBase,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: DS.neutral200,
              ),
              boxShadow: [
                BoxShadow(
                  color: DS.neutral900.withValues(alpha: 0.2),
                  blurRadius: 20,
                  spreadRadius: 5,
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
                      child: CustomButton.primary(
                        text: _getConfirmText(),
                        onPressed: _nextStep,
                        customGradient: _currentStep == _TaskExitStep.third
                            ? DS.warningGradient
                            : null,
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
              color: isActive
                  ? DS.primaryBase
                  : DS.neutral300,
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
    switch (_currentStep) {
      case _TaskExitStep.first:
        return '确定要离开任务吗？';
      case _TaskExitStep.second:
        return '专注统计';
      case _TaskExitStep.third:
        return '最后确认';
    }
  }

  String _getMessage() {
    switch (_currentStep) {
      case _TaskExitStep.first:
        return '你正在执行任务，离开可能会影响专注效果。';
      case _TaskExitStep.second:
        return '你已经专注了 ${widget.elapsedMinutes} 分钟 ${widget.elapsedSeconds % 60} 秒。';
      case _TaskExitStep.third:
        return '再坚持一下！现在离开会中断你的专注记录。';
    }
  }

  String _getCancelText() {
    switch (_currentStep) {
      case _TaskExitStep.first:
        return '继续执行';
      case _TaskExitStep.second:
        return '返回';
      case _TaskExitStep.third:
        return '取消';
    }
  }

  String _getConfirmText() {
    switch (_currentStep) {
      case _TaskExitStep.first:
        return '确认离开';
      case _TaskExitStep.second:
        return '继续';
      case _TaskExitStep.third:
        return '确定离开';
    }
  }
}
