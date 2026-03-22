import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/focus/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/features/focus/presentation/widgets/exit_confirmation_dialog.dart';
import 'package:sparkle/features/focus/presentation/widgets/flip_clock.dart';
import 'package:sparkle/features/focus/presentation/widgets/reflection_dialog.dart';
import 'package:sparkle/features/focus/presentation/widgets/star_background.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// 正念模式屏幕
class MindfulnessModeScreen extends ConsumerStatefulWidget {
  const MindfulnessModeScreen({
    required this.taskId,
    super.key,
  });
  final String taskId;

  @override
  ConsumerState<MindfulnessModeScreen> createState() =>
      _MindfulnessModeScreenState();
}

class _MindfulnessModeScreenState extends ConsumerState<MindfulnessModeScreen>
    with WidgetsBindingObserver, TickerProviderStateMixin {
  late AnimationController _entryController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<double> _clockFadeAnimation;
  late Animation<Offset> _statusSlideAnimation;
  late Animation<Offset> _contentSlideAnimation;
  late Animation<Offset> _bottomSlideAnimation;

  bool _isExiting = false;
  bool _isInitialized = false;

  @override
  void initState() {
    super.initState();

    // 注册生命周期观察者
    WidgetsBinding.instance.addObserver(this);

    // 设置全屏模式
    unawaited(SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersive));

    // 入场动画控制器
    _entryController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 560),
    );

    _fadeAnimation = CurvedAnimation(
      parent: _entryController,
      curve: const Interval(0, 0.4, curve: Curves.easeOut),
    );

    _scaleAnimation = Tween<double>(begin: 0.96, end: 1.0).animate(
      CurvedAnimation(
        parent: _entryController,
        curve: const Interval(0.12, 1.0, curve: Curves.easeOutCubic),
      ),
    );

    _clockFadeAnimation = CurvedAnimation(
      parent: _entryController,
      curve: const Interval(0.5, 1.0, curve: Curves.easeIn),
    );

    _statusSlideAnimation = Tween<Offset>(
      begin: const Offset(0, -0.16),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _entryController,
        curve: const Interval(0.0, 0.42, curve: Curves.easeOutCubic),
      ),
    );

    _contentSlideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.06),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _entryController,
        curve: const Interval(0.14, 0.82, curve: Curves.easeOutCubic),
      ),
    );

    _bottomSlideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.18),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _entryController,
        curve: const Interval(0.52, 1.0, curve: Curves.easeOutCubic),
      ),
    );

    // 开始入场动画
    unawaited(_entryController.forward());
  }

  void _initializeWithTask(TaskModel task) {
    if (_isInitialized) return;
    _isInitialized = true;

    // 启动正念模式
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(mindfulnessProvider.notifier).start(task);
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _entryController.dispose();

    // 恢复系统UI
    unawaited(SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge));

    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      // 用户切换离开应用
      ref.read(mindfulnessProvider.notifier).recordInterruption(
            InterruptionType.appSwitch,
          );
    } else if (state == AppLifecycleState.resumed) {
      // 用户返回应用，显示提醒
      _showInterruptionWarning();
    }
  }

  void _showInterruptionWarning() {
    final state = ref.read(mindfulnessProvider);
    if (!state.isActive) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: DS.brandPrimary),
            const SizedBox(width: DS.md),
            Expanded(
              child: Text(
                context.l10n.focusInterruptionDetected(state.interruptionCount),
                style: TextStyle(color: DS.brandPrimary),
              ),
            ),
          ],
        ),
        backgroundColor: DS.warning,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  Future<void> _handleExit() async {
    if (_isExiting) return;

    final confirmed = await showExitConfirmation(
      context,
      elapsedMinutes: ref.read(mindfulnessProvider.notifier).elapsedMinutes,
    );

    if (confirmed && mounted) {
      _isExiting = true;
      await ref.read(mindfulnessProvider.notifier).stop();

      if (mounted) {
        // Show Reflection Dialog
        await showDialog<void>(
          context: context,
          barrierDismissible: false,
          builder: (context) => const ReflectionDialog(),
        );

        if (mounted) {
          context.pop();
        }
      }
    }
  }

  Future<bool> _onWillPop() async {
    await _handleExit();
    return false; // 阻止默认返回行为
  }

  @override
  Widget build(BuildContext context) {
    final taskAsync = ref.watch(taskDetailProvider(widget.taskId));

    return taskAsync.when(
      data: (task) {
        _initializeWithTask(task);
        final mindfulness = ref.watch(mindfulnessProvider);
        final ambienceIntensity =
            (0.52 +
                    (mindfulness.elapsedSeconds / 900).clamp(0, 1) * 0.4 -
                    (mindfulness.interruptionCount * 0.04))
                .clamp(0.35, 1.0);

        return PopScope(
          canPop: false,
          onPopInvokedWithResult: (didPop, result) async {
            if (didPop) return;
            final shouldPop = await _onWillPop();
            if (!mounted) return;
            if (shouldPop) {
              Navigator.of(this.context).pop();
            }
          },
          child: SparklePageScaffold(
            role: SparklePageRole.immersive,
            safeArea: false,
            child: Stack(
              children: [
                const Positioned.fill(
                  child: SizedBox.shrink(),
                ),
                Positioned.fill(
                  child: AnimatedStarBackground(
                    fadeInDuration: const Duration(milliseconds: 420),
                    starCount: 88,
                    intensity: ambienceIntensity,
                  ),
                ),
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          DS.deepSpaceStart.withValues(alpha: 0.18),
                          Colors.transparent,
                          DS.deepSpaceEnd.withValues(alpha: 0.32),
                        ],
                      ),
                    ),
                  ),
                ),

                // 2. 主内容
                SafeArea(
                  child: Column(
                    children: [
                      FadeTransition(
                        opacity: _fadeAnimation,
                        child: SlideTransition(
                          position: _statusSlideAnimation,
                          child: _buildStatusBar(mindfulness),
                        ),
                      ),
                      Expanded(
                        child: Center(
                          child: FadeTransition(
                            opacity: _clockFadeAnimation,
                            child: SlideTransition(
                              position: _contentSlideAnimation,
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  ScaleTransition(
                                    scale: _scaleAnimation,
                                    child: FadeTransition(
                                      opacity: _fadeAnimation,
                                      child: _buildTaskCard(task),
                                    ),
                                  ),
                                  const SizedBox(height: DS.xxxl),
                                  FadeTransition(
                                    opacity: _clockFadeAnimation,
                                    child: SimpleFlipClock(
                                      seconds: mindfulness.elapsedSeconds,
                                      fontSize: 72,
                                    ),
                                  ),
                                  const SizedBox(height: DS.xxl),
                                  FadeTransition(
                                    opacity: _clockFadeAnimation,
                                    child: ScaleTransition(
                                      scale: _scaleAnimation,
                                      child: _buildFlameAnimation(),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                      FadeTransition(
                        opacity: _clockFadeAnimation,
                        child: SlideTransition(
                          position: _bottomSlideAnimation,
                          child: _buildExitButton(),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
      loading: () => const SparklePageScaffold(
        role: SparklePageRole.immersive,
        safeArea: false,
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (err, stack) => SparklePageScaffold(
        role: SparklePageRole.immersive,
        safeArea: false,
        child: Center(
          child: Text(
            context.l10n.focusLoadFailed(err.toString()),
            style: TextStyle(color: DS.textPrimary),
          ),
        ),
      ),
    );
  }

  Widget _buildStatusBar(MindfulnessState state) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // 返回任务按钮
            _buildBackToTaskButton(),

            // 正念模式标题
            Row(
              children: [
                Icon(
                  Icons.self_improvement_rounded,
                  color: DS.textSecondary,
                  size: 20,
                ),
                const SizedBox(width: DS.sm),
                Text(
                  context.l10n.focusMindfulnessTitle,
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),

            // 暂停按钮
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              size: 40,
              icon: Icon(
                state.isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded,
                color: DS.textSecondary,
              ),
              onPressed: () {
                if (state.isPaused) {
                  ref.read(mindfulnessProvider.notifier).resume();
                } else {
                  ref.read(mindfulnessProvider.notifier).pause();
                }
              },
            ),
          ],
        ),
      );

  Widget _buildBackToTaskButton() => SparkleButton(
        label: context.l10n.focusReturnToTask,
        variant: ButtonVariant.ghost,
        icon: const Icon(Icons.arrow_back_rounded, size: 18),
        onPressed: () {
          unawaited(_returnToTaskExecution());
        },
      );

  Future<void> _returnToTaskExecution() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        child: GraphiteModalSurface(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.focusReturnToTaskTitle,
                style: DS.titleLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.focusReturnToTaskMessage,
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              ),
              const SizedBox(height: DS.spacing20),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton(
                      label: context.l10n.cancel,
                      variant: ButtonVariant.ghost,
                      onPressed: () => Navigator.of(context).pop(false),
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: SparkleButton(
                      label: context.l10n.focusReturnToTaskConfirm,
                      onPressed: () => Navigator.of(context).pop(true),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );

    if ((confirmed ?? false) && mounted) {
      await ref.read(mindfulnessProvider.notifier).stop();
      if (mounted) {
        // 🔧 修复：从mindfulnessProvider获取完整任务并设置activeTaskProvider
        final currentTask = ref.read(mindfulnessProvider).currentTask;
        if (currentTask != null) {
          ref.read(activeTaskProvider.notifier).state = currentTask;
        }
        unawaited(context.push('/tasks/${widget.taskId}/execute'));
      }
    }
  }

  Widget _buildTaskCard(TaskModel task) => GraphiteCardSurface(
        margin: const EdgeInsets.symmetric(horizontal: 40),
        padding: const EdgeInsets.all(DS.xl),
        borderColor: DS.brandPrimary.withValues(alpha: 0.14),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: DS.surfaceOverlay.withValues(alpha: 0.78),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing8),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  task.title,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: DS.md),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: DS.brandPrimary.withValues(alpha: 0.18),
                    ),
                  ),
                  child: Text(
                    task.type.name.toUpperCase(),
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );

  Widget _buildFlameAnimation() => TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.985, end: 1.025),
        duration: const Duration(milliseconds: 1400),
        curve: Curves.easeInOut,
        builder: (context, scale, child) => Transform.scale(
          scale: scale,
          child: child,
        ),
        onEnd: () {
          // 循环动画
          if (mounted) {
            setState(() {});
          }
        },
        child: Container(
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                DS.brandPrimary.withValues(alpha: 0.22),
                DS.brandSecondary.withValues(alpha: 0.16),
              ],
            ),
            shape: BoxShape.circle,
            border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.18)),
            boxShadow: [
              BoxShadow(
                color: DS.brandPrimary.withValues(alpha: 0.12),
                blurRadius: 18,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Icon(
            Icons.local_fire_department_rounded,
            color: DS.primaryBase,
            size: 32,
          ),
        ),
      );

  Widget _buildExitButton() => Padding(
        padding: const EdgeInsets.all(DS.xl),
        child: SparkleButton(
          label: context.l10n.focusExitMindfulness,
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.exit_to_app_rounded, size: 18),
          onPressed: _handleExit,
        ),
      );
}
