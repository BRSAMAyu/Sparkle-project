import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/intervention_action_service.dart';
import 'package:sparkle/features/focus/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/features/focus/presentation/widgets/exit_confirmation_dialog.dart';
import 'package:sparkle/features/focus/presentation/widgets/flip_clock.dart';
import 'package:sparkle/features/focus/presentation/widgets/focus_session_summary_dialog.dart';
import 'package:sparkle/features/focus/presentation/widgets/star_background.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// 正念模式屏幕
class MindfulnessModeScreen extends ConsumerStatefulWidget {
  const MindfulnessModeScreen({
    required this.taskId,
    this.interventionId,
    super.key,
  });
  final String taskId;
  final String? interventionId;

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
  bool _isExitDialogOpen = false;
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
    final mindfulness = ref.read(mindfulnessProvider);
    if (mindfulness.isActive && mindfulness.currentTask?.id == task.id) {
      _isInitialized = true;
      return;
    }
    _isInitialized = true;

    // 启动正念模式
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(mindfulnessProvider.notifier).start(task);
      if (widget.interventionId != null && widget.interventionId!.isNotEmpty) {
        unawaited(
          ref.read(interventionActionServiceProvider).reportAction(
            recordId: widget.interventionId!,
            action: 'accepted',
            actionPayload: {
              'surface': 'focus_mode',
              'source': 'mindfulness_start',
              'task_id': task.id,
            },
          ),
        );
      }
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
    if (_isExiting || _isExitDialogOpen) return;

    _isExitDialogOpen = true;
    final confirmed = await showExitConfirmation(
      context,
      elapsedMinutes: ref.read(mindfulnessProvider.notifier).elapsedMinutes,
    );
    _isExitDialogOpen = false;

    if (confirmed && mounted) {
      _isExiting = true;
      final elapsedMinutes =
          ref.read(mindfulnessProvider.notifier).elapsedMinutes;
      final result = await ref.read(mindfulnessProvider.notifier).stop();

      if (mounted) {
        if (widget.interventionId != null &&
            widget.interventionId!.isNotEmpty &&
            elapsedMinutes > 0) {
          unawaited(
            ref.read(interventionActionServiceProvider).reportAction(
              recordId: widget.interventionId!,
              action: 'acted',
              actionPayload: {
                'surface': 'focus_mode',
                'source': 'mindfulness_complete',
                'task_id': widget.taskId,
                'duration_minutes': elapsedMinutes,
              },
            ),
          );
        }
        if (result.masteryUpdates.isNotEmpty) {
          await showFocusSessionSummaryDialog(
            context,
            durationMinutes: elapsedMinutes,
            flameEarned: result.flameEarned,
            masteryUpdates: result.masteryUpdates,
          );
          if (!mounted) return;
        } else if (result.message != null) {
          AppFeedback.info(context, result.message!);
        }
        context.pop();
      }
      _isExiting = false;
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
        final ambienceIntensity = (0.52 +
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
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: DS.spacing20,
                          ),
                          child: Center(
                            child: FadeTransition(
                              opacity: _clockFadeAnimation,
                              child: SlideTransition(
                                position: _contentSlideAnimation,
                                child: ConstrainedBox(
                                  constraints: const BoxConstraints(
                                    maxWidth: 520,
                                  ),
                                  child: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      ScaleTransition(
                                        scale: _scaleAnimation,
                                        child: FadeTransition(
                                          opacity: _fadeAnimation,
                                          child: _buildTaskCard(task),
                                        ),
                                      ),
                                      const SizedBox(height: DS.spacing24),
                                      FadeTransition(
                                        opacity: _clockFadeAnimation,
                                        child: FittedBox(
                                          fit: BoxFit.scaleDown,
                                          child: SimpleFlipClock(
                                            seconds: mindfulness.elapsedSeconds,
                                            fontSize: 72,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(height: DS.spacing24),
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
        padding: const EdgeInsets.fromLTRB(
          DS.spacing12,
          DS.spacing12,
          DS.spacing12,
          DS.spacing8,
        ),
        child: Row(
          children: [
            _buildBackToTaskButton(),
            Expanded(
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing12,
                    vertical: DS.spacing8,
                  ),
                  decoration: BoxDecoration(
                    color: DS.surfaceOverlay.withValues(alpha: 0.52),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: DS.borderSubtle),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.self_improvement_rounded,
                        color: DS.textSecondary,
                        size: 18,
                      ),
                      const SizedBox(width: DS.spacing6),
                      Text(
                        context.l10n.focusMindfulnessTitle,
                        style: TextStyle(
                          color: DS.textSecondary,
                          fontSize: DS.fontSizeSm,
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
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

  Widget _buildBackToTaskButton() => SparkleIconButton(
        variant: ButtonVariant.ghost,
        size: 40,
        icon: const Icon(Icons.arrow_back_rounded, size: 20),
        onPressed: () {
          unawaited(_handleExit());
        },
      );

  Widget _buildTaskCard(TaskModel task) => GraphiteCardSurface(
        margin: const EdgeInsets.symmetric(horizontal: DS.spacing8),
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
                    fontSize: 20,
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
        padding: const EdgeInsets.fromLTRB(
          DS.spacing20,
          DS.spacing8,
          DS.spacing20,
          DS.spacing20,
        ),
        child: SparkleButton(
          expand: true,
          label: ref.watch(mindfulnessProvider).isLoggingSession
              ? context.l10n.commonSaving
              : context.l10n.focusExitMindfulness,
          variant: ButtonVariant.secondary,
          icon: const Icon(Icons.exit_to_app_rounded, size: 18),
          onPressed: ref.watch(mindfulnessProvider).isLoggingSession
              ? null
              : _handleExit,
        ),
      );
}
