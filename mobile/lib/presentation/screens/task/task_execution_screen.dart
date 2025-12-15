import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/widgets/task/timer_widget.dart';
import 'package:sparkle/presentation/widgets/success_animation.dart';
import 'package:sparkle/presentation/widgets/custom_button.dart';

class TaskExecutionScreen extends ConsumerStatefulWidget {
  const TaskExecutionScreen({super.key});

  @override
  ConsumerState<TaskExecutionScreen> createState() => _TaskExecutionScreenState();
}

class _TaskExecutionScreenState extends ConsumerState<TaskExecutionScreen> {
  int _elapsedSeconds = 0;
  bool _isTimerRunning = false;
  bool _showCelebration = false;

  Future<bool> _onWillPop() async {
    if (_showCelebration) return false; // Don't pop during celebration
    if (!_isTimerRunning) return true;

    final shouldPop = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Leave Session?'),
        content: const Text('Your timer is still running. Are you sure you want to leave? Your progress will be saved.'),
        shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius16),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Stay'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Leave', style: TextStyle(color: AppDesignTokens.error)),
          ),
        ],
      ),
    );
    return shouldPop ?? false;
  }

  void _handleCompletion(int minutes, String? note) async {
    // 1. Stop Timer (handled by widget state generally, but good to be sure)
    setState(() {
      _isTimerRunning = false;
      _showCelebration = true;
    });

    // 2. Haptic Feedback
    HapticFeedback.mediumImpact();

    // 3. API Call
    final task = ref.read(activeTaskProvider);
    if (task != null) {
      await ref.read(taskListProvider.notifier).completeTask(task.id, minutes, note);
    }
  }

  void _onCelebrationComplete() {
    if (mounted) {
      context.pop(); // Go back to task list/detail
    }
  }

  @override
  Widget build(BuildContext context) {
    final activeTask = ref.watch(activeTaskProvider);

    if (activeTask == null) {
      return Scaffold(
        appBar: AppBar(),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text('No active task selected.'),
              const SizedBox(height: 16),
              CustomButton(
                text: 'Go Back',
                onPressed: () => context.pop(),
                variant: CustomButtonVariant.secondary,
              ),
            ],
          ),
        ),
      );
    }

    return WillPopScope(
      onWillPop: _onWillPop,
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
                    AppDesignTokens.primaryBase.withOpacity(0.05),
                    AppDesignTokens.secondaryBase.withOpacity(0.05),
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
                                mode: TimerMode.countUp,
                                initialSeconds: activeTask.actualMinutes != null ? activeTask.actualMinutes! * 60 : 0,
                                maxSeconds: activeTask.estimatedMinutes * 60,
                                onTick: (seconds) => _elapsedSeconds = seconds,
                                onStateChange: (isRunning) => _isTimerRunning = isRunning,
                              ),
                            ),
                            const SizedBox(height: AppDesignTokens.spacing40),

                            // 2. Task Guide Area
                            Container(
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: AppDesignTokens.borderRadius12,
                                boxShadow: AppDesignTokens.shadowMd,
                              ),
                              child: ExpansionTile(
                                shape: const Border(), // Remove default borders
                                tilePadding: const EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing16, vertical: 8),
                                title: Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(8),
                                      decoration: const BoxDecoration(
                                        gradient: AppDesignTokens.infoGradient,
                                        shape: BoxShape.circle,
                                      ),
                                      child: const Icon(Icons.description_outlined, color: Colors.white, size: 20),
                                    ),
                                    const SizedBox(width: AppDesignTokens.spacing12),
                                    Text('Task Guide', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                                  ],
                                ),
                                children: [
                                   Padding(
                                     padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                                     child: MarkdownBody(
                                       data: activeTask.guideContent ?? 'No guide available.',
                                       styleSheet: MarkdownStyleSheet(
                                         p: Theme.of(context).textTheme.bodyMedium,
                                       ),
                                     ),
                                   ),
                                ],
                              ),
                            ),
                            const SizedBox(height: AppDesignTokens.spacing16),

                            // 3. Chat Area (Placeholder)
                            Container(
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: AppDesignTokens.borderRadius12,
                                boxShadow: AppDesignTokens.shadowMd,
                              ),
                              child: ExpansionTile(
                                shape: const Border(),
                                tilePadding: const EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing16, vertical: 8),
                                title: Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(8),
                                      decoration: const BoxDecoration(
                                        gradient: AppDesignTokens.primaryGradient,
                                        shape: BoxShape.circle,
                                      ),
                                      child: const Icon(Icons.auto_awesome, color: Colors.white, size: 20),
                                    ),
                                    const SizedBox(width: AppDesignTokens.spacing12),
                                    Text('AI Mentor', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                                  ],
                                ),
                                children: const [
                                   Padding(
                                     padding: EdgeInsets.all(AppDesignTokens.spacing16),
                                     child: Center(child: Text('Chat UI coming soon...')),
                                   ),
                                ],
                              ),
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
          
          // Celebration Overlay
          if (_showCelebration)
            Positioned.fill(
              child: Container(
                color: Colors.black54,
                child: SuccessAnimation(
                  playAnimation: true,
                  onAnimationComplete: _onCelebrationComplete,
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.check_circle, color: AppDesignTokens.success, size: 80),
                        const SizedBox(height: 16),
                        Text(
                          'Task Completed!', 
                          style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: Colors.white, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '+${activeTask.difficulty * 10} XP',
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(color: AppDesignTokens.accent),
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
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Complete Task'),
        shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius16),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Time spent: ${Duration(seconds: elapsedSeconds).inMinutes} minutes.'),
            const SizedBox(height: 16),
            TextField(
              controller: noteController,
              decoration: const InputDecoration(
                labelText: 'Notes (optional)',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              onComplete(Duration(seconds: elapsedSeconds).inMinutes, noteController.text);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppDesignTokens.success,
              foregroundColor: Colors.white,
            ),
            child: const Text('Complete'),
          ),
        ],
      ),
    );
  }

  void _abandonTask(BuildContext context, WidgetRef ref) {
     showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Abandon Task?'),
        shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius16),
        content: const Text('Are you sure? This will mark the task as abandoned.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              ref.read(taskListProvider.notifier).abandonTask(task.id);
              Navigator.of(ctx).pop();
              context.pop(); 
            },
            child: const Text('Abandon', style: TextStyle(color: AppDesignTokens.error)),
          ),
        ],
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
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, -5),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            flex: 1,
            child: CustomButton(
              text: 'Abandon',
              variant: CustomButtonVariant.text,
              onPressed: () => _abandonTask(context, ref),
              // Use error color for text if possible, or leave as primary/custom
            ),
          ),
          const SizedBox(width: AppDesignTokens.spacing16),
          Expanded(
            flex: 2,
            child: CustomButton(
              text: 'Complete Task',
              variant: CustomButtonVariant.success,
              onPressed: () => _showCompleteDialog(context, ref),
            ),
          ),
        ],
      ),
    );
  }
}