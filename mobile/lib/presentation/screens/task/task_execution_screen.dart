import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/data/models/task_completion_result.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/widgets/task/timer_widget.dart';
import 'package:sparkle/presentation/widgets/success_animation.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';
import 'package:sparkle/presentation/widgets/task/quick_tools_panel.dart';
import 'package:sparkle/presentation/widgets/task/task_chat_panel.dart';
import 'package:sparkle/presentation/widgets/task/task_feedback_dialog.dart';

import 'package:sparkle/presentation/widgets/task/blocking_interceptor_dialog.dart';

class TaskExecutionScreen extends ConsumerStatefulWidget {
  const TaskExecutionScreen({super.key});

  @override
  ConsumerState<TaskExecutionScreen> createState() => _TaskExecutionScreenState();
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

  @override
  void initState() {
    super.initState();
    final task = ref.read(activeTaskProvider);
    _currentTimerDuration = task?.actualMinutes != null ? task!.actualMinutes! * 60 : 0;
  }

  Future<bool> _onWillPop() async {
    if (_showCelebration) return false; // Don't pop during celebration
    if (!_isTimerRunning) return true;

    final shouldPop = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: AppDesignTokens.borderRadius20,
        ),
        title: const Text(
          '离开任务？',
          style: TextStyle(
            fontWeight: AppDesignTokens.fontWeightBold,
          ),
        ),
        content: const Text('计时器仍在运行，确定要离开吗？您的进度将被保存。'),
        actions: [
          CustomButton.text(
            text: '继续执行',
            onPressed: () => Navigator.of(context).pop(false),
          ),
          CustomButton.primary(
            text: '离开',
            icon: Icons.exit_to_app,
            onPressed: () {
              HapticFeedback.mediumImpact();
              Navigator.of(context).pop(true);
            },
            customGradient: AppDesignTokens.warningGradient,
            size: ButtonSize.small,
          ),
        ],
      ),
    );
    return shouldPop ?? false;
  }

  void _handleCompletion(int minutes, String? note) async {
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
      final result = await ref.read(taskListProvider.notifier).completeTask(task.id, minutes, note);
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
      // Show feedback dialog
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => TaskFeedbackDialog(
          result: _completionResult!,
          onClose: () {
            Navigator.of(context).pop(); // Close dialog
            context.go('/galaxy'); // Navigate away
          },
        ),
      );
    } else {
      // Fallback if result isn't ready or failed (though optimistic update usually handles it)
      // For now, just go to galaxy
       context.go('/galaxy');
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

    if (_pomodoroCycle == 0) { // Work phase completed
      _pomodoroCycle = 1;
      _currentTimerDuration = 5 * 60; // Short break
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('番茄工作时间结束！休息一下。')),
      );
    } else if (_pomodoroCycle == 1) { // Short break completed
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
            decoration: const BoxDecoration(
              gradient: AppDesignTokens.primaryGradient,
            ),
          ),
        ),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.error_outline_rounded,
                size: 80,
                color: AppDesignTokens.neutral400,
              ),
              const SizedBox(height: AppDesignTokens.spacing16),
              Text(
                '未选择任务',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: AppDesignTokens.fontWeightBold,
                  color: AppDesignTokens.neutral700,
                ),
              ),
              const SizedBox(height: AppDesignTokens.spacing24),
              CustomButton.primary(
                text: '返回',
                icon: Icons.arrow_back,
                onPressed: () => context.pop(),
                size: ButtonSize.medium,
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
              iconTheme: const IconThemeData(color: AppDesignTokens.neutral900),
              title: Text(
                activeTask.title, 
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: AppDesignTokens.neutral900),
              ),
            ),
            body: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    AppDesignTokens.primaryBase.withValues(alpha: 0.05),
                    AppDesignTokens.secondaryBase.withValues(alpha: 0.05),
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
                        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            const SizedBox(height: AppDesignTokens.spacing16),
                            // 1. Timer Area
                            Center(
                              child: TimerWidget(
                                key: ValueKey(_currentTimerDuration), // Force rebuild on duration change
                                mode: _timerMode,
                                initialSeconds: _currentTimerDuration,
                                maxSeconds: _isPomodoroMode ? (_pomodoroCycle == 0 ? 25 * 60 : 5 * 60) : null,
                                onTick: (seconds) => _elapsedSeconds = seconds,
                                onStateChange: (isRunning) => _isTimerRunning = isRunning,
                                onComplete: _onPomodoroComplete, // Call only for Pomodoro
                              ),
                            ),
                            const SizedBox(height: AppDesignTokens.spacing24),

                            // Timer Controls
                            _TimerControls(
                              isPomodoroMode: _isPomodoroMode,
                              onTogglePomodoro: _togglePomodoro,
                              onSetPreset: _setPresetDuration,
                            ),
                            const SizedBox(height: AppDesignTokens.spacing40),

                            // 2. Task Guide Area
                            Container(
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: AppDesignTokens.borderRadius16,
                                boxShadow: AppDesignTokens.shadowMd,
                                border: Border.all(
                                  color: AppDesignTokens.neutral200,
                                  width: 1,
                                ),
                              ),
                              child: ExpansionTile(
                                shape: const Border(), // Remove default borders
                                tilePadding: const EdgeInsets.symmetric(
                                  horizontal: AppDesignTokens.spacing16,
                                  vertical: AppDesignTokens.spacing12,
                                ),
                                title: Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(10),
                                      decoration: BoxDecoration(
                                        gradient: AppDesignTokens.infoGradient,
                                        shape: BoxShape.circle,
                                        boxShadow: [
                                          BoxShadow(
                                            color: AppDesignTokens.info.withValues(alpha: 0.3),
                                            blurRadius: 8,
                                            offset: const Offset(0, 2),
                                          ),
                                        ],
                                      ),
                                      child: const Icon(Icons.description_outlined, color: Colors.white, size: 22),
                                    ),
                                    const SizedBox(width: AppDesignTokens.spacing12),
                                    Text(
                                      '执行指南',
                                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                        fontWeight: AppDesignTokens.fontWeightBold,
                                        color: AppDesignTokens.neutral900,
                                      ),
                                    ),
                                  ],
                                ),
                                children: [
                                  Container(
                                    width: double.infinity,
                                    padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                                    decoration: const BoxDecoration(
                                      color: AppDesignTokens.neutral50,
                                      borderRadius: BorderRadius.only(
                                        bottomLeft: Radius.circular(16),
                                        bottomRight: Radius.circular(16),
                                      ),
                                    ),
                                    child: MarkdownBody(
                                      data: activeTask.guideContent ?? '暂无执行指南',
                                      styleSheet: MarkdownStyleSheet(
                                        p: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                          color: AppDesignTokens.neutral700,
                                          height: 1.6,
                                        ),
                                        h1: Theme.of(context).textTheme.titleLarge?.copyWith(
                                          fontWeight: AppDesignTokens.fontWeightBold,
                                        ),
                                        h2: Theme.of(context).textTheme.titleMedium?.copyWith(
                                          fontWeight: AppDesignTokens.fontWeightBold,
                                        ),
                                        code: const TextStyle(
                                          backgroundColor: AppDesignTokens.neutral100,
                                          color: AppDesignTokens.primaryDark,
                                          fontFamily: 'monospace',
                                          fontSize: AppDesignTokens.fontSizeSm,
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: AppDesignTokens.spacing16),

                            // 3. Quick Tools Panel
                            QuickToolsPanel(taskId: activeTask.id),
                            const SizedBox(height: AppDesignTokens.spacing16),

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
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.black.withValues(alpha: 0.7),
                      AppDesignTokens.primaryBase.withValues(alpha: 0.3),
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
                          padding: const EdgeInsets.all(24),
                          decoration: BoxDecoration(
                            gradient: AppDesignTokens.successGradient,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: AppDesignTokens.success.withValues(alpha: 0.5),
                                blurRadius: 30,
                                spreadRadius: 10,
                              ),
                            ],
                          ),
                          child: const Icon(
                            Icons.check_circle,
                            color: Colors.white,
                            size: 80,
                          ),
                        ),
                        const SizedBox(height: AppDesignTokens.spacing24),
                        Text(
                          '任务完成！',
                          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                            color: Colors.white,
                            fontWeight: AppDesignTokens.fontWeightBold,
                          ),
                        ),
                        const SizedBox(height: AppDesignTokens.spacing12),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppDesignTokens.spacing20,
                            vertical: AppDesignTokens.spacing8,
                          ),
                          decoration: BoxDecoration(
                            gradient: AppDesignTokens.warningGradient,
                            borderRadius: AppDesignTokens.borderRadius20,
                            boxShadow: AppDesignTokens.shadowLg,
                          ),
                          child: Text(
                            '+${activeTask.difficulty * 10} 经验值',
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              color: Colors.white,
                              fontWeight: AppDesignTokens.fontWeightBold,
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
}

class _TimerControls extends StatelessWidget {
  final bool isPomodoroMode;
  final VoidCallback onTogglePomodoro;
  final Function(int minutes) onSetPreset;

  const _TimerControls({
    required this.isPomodoroMode,
    required this.onTogglePomodoro,
    required this.onSetPreset,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Wrap(
          alignment: WrapAlignment.center,
          spacing: AppDesignTokens.spacing8,
          runSpacing: AppDesignTokens.spacing8,
          children: [
            CustomButton.secondary(
              text: '番茄钟',
              icon: Icons.timer,
              onPressed: onTogglePomodoro,
              size: ButtonSize.small,
            ),
            ...[15, 25, 45, 60].map((minutes) => CustomButton.secondary(
              text: '$minutes 分钟',
              onPressed: () => onSetPreset(minutes),
              size: ButtonSize.small,
            ),),
          ],
        ),
        const SizedBox(height: 16),
        CustomButton.primary(
          text: '进入正念模式',
          icon: Icons.self_improvement,
          onPressed: () {
            final activeTask = ProviderScope.containerOf(context).read(activeTaskProvider);
            if (activeTask != null) {
              context.push('/focus/mindfulness', extra: activeTask);
            }
          },
          customGradient: AppDesignTokens.primaryGradient,
        ),
      ],
    );
  }
}

class _BottomControls extends ConsumerWidget {
  final TaskModel task;
  final int elapsedSeconds;
  final Function(int minutes, String? note) onComplete;

  const _BottomControls({
    required this.task, 
    required this.elapsedSeconds,
    required this.onComplete,
  });

  void _showCompleteDialog(BuildContext context, WidgetRef ref) {
    final noteController = TextEditingController();
    final minutes = Duration(seconds: elapsedSeconds).inMinutes;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: AppDesignTokens.borderRadius20,
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: const BoxDecoration(
                gradient: AppDesignTokens.successGradient,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.check_circle_outline, color: Colors.white, size: 24),
            ),
            const SizedBox(width: AppDesignTokens.spacing12),
            const Text(
              '完成任务',
              style: TextStyle(
                fontWeight: AppDesignTokens.fontWeightBold,
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(AppDesignTokens.spacing12),
              decoration: BoxDecoration(
                color: AppDesignTokens.neutral50,
                borderRadius: AppDesignTokens.borderRadius12,
              ),
              child: Row(
                children: [
                  const Icon(Icons.timer_outlined, color: AppDesignTokens.primaryBase),
                  const SizedBox(width: AppDesignTokens.spacing8),
                  Text(
                    '用时：$minutes 分钟',
                    style: const TextStyle(
                      fontWeight: AppDesignTokens.fontWeightMedium,
                      color: AppDesignTokens.neutral700,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            TextField(
              controller: noteController,
              decoration: InputDecoration(
                labelText: '笔记（选填）',
                hintText: '记录一些学习心得...',
                border: OutlineInputBorder(
                  borderRadius: AppDesignTokens.borderRadius12,
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: AppDesignTokens.borderRadius12,
                  borderSide: const BorderSide(
                    color: AppDesignTokens.primaryBase,
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
              onComplete(minutes, noteController.text.trim().isEmpty ? null : noteController.text.trim());
            },
            customGradient: AppDesignTokens.successGradient,
            size: ButtonSize.small,
          ),
        ],
      ),
    );
  }

  void _abandonTask(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (ctx) => BlockingInterceptorDialog(
        taskId: task.id,
        onAbandonConfirmed: () {
           ref.read(taskListProvider.notifier).abandonTask(task.id);
           // Navigate away completely to Galaxy to exit execution flow safely
           context.go('/galaxy');
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      padding: const EdgeInsets.all(AppDesignTokens.spacing16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, -5),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            flex: 1,
            child: CustomButton.text(
              text: '放弃',
              onPressed: () => _abandonTask(context, ref),
              // Use error color for text if possible, or leave as primary/custom
            ),
          ),
          const SizedBox(width: AppDesignTokens.spacing16),
          Expanded(
            flex: 2,
            child: CustomButton.primary(
              text: '完成任务',
              onPressed: () => _showCompleteDialog(context, ref),
              customGradient: AppDesignTokens.successGradient,
            ),
          ),
        ],
      ),
    );
  }
}
