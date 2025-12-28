import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/presentation/widgets/focus/exit_confirmation_dialog.dart';
import 'package:sparkle/presentation/widgets/focus/flip_clock.dart';
import 'package:sparkle/presentation/widgets/focus/star_background.dart';

/// 正念模式屏幕
class MindfulnessModeScreen extends ConsumerStatefulWidget {

  const MindfulnessModeScreen({
    required this.task, super.key,
  });
  final TaskModel task;

  @override
  ConsumerState<MindfulnessModeScreen> createState() => _MindfulnessModeScreenState();
}

class _MindfulnessModeScreenState extends ConsumerState<MindfulnessModeScreen>
    with WidgetsBindingObserver, TickerProviderStateMixin {
  late AnimationController _entryController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<double> _clockFadeAnimation;

  bool _isExiting = false;

  @override
  void initState() {
    super.initState();

    // 注册生命周期观察者
    WidgetsBinding.instance.addObserver(this);

    // 设置全屏模式
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersive);

    // 入场动画控制器
    _entryController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    _fadeAnimation = CurvedAnimation(
      parent: _entryController,
      curve: const Interval(0, 0.4, curve: Curves.easeOut),
    );

    _scaleAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(
        parent: _entryController,
        curve: const Interval(0.2, 0.7, curve: Curves.elasticOut),
      ),
    );

    _clockFadeAnimation = CurvedAnimation(
      parent: _entryController,
      curve: const Interval(0.5, 1.0, curve: Curves.easeIn),
    );

    // 启动正念模式
    ref.read(mindfulnessProvider.notifier).start(widget.task);

    // 开始入场动画
    _entryController.forward();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _entryController.dispose();

    // 恢复系统UI
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);

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
            SizedBox(width: DS.md),
            Expanded(
              child: Text(
                '检测到分心行为 (第 ${state.interruptionCount} 次)',
                style: TextStyle(color: DS.brandPrimary),
              ),
            ),
          ],
        ),
        backgroundColor: AppDesignTokens.warning,
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
      ref.read(mindfulnessProvider.notifier).stop();
      context.pop();
    }
  }

  Future<bool> _onWillPop() async {
    await _handleExit();
    return false; // 阻止默认返回行为
  }

  @override
  Widget build(BuildContext context) {
    final mindfulness = ref.watch(mindfulnessProvider);

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
      child: Scaffold(
        backgroundColor: AppDesignTokens.deepSpaceStart,
        body: Stack(
          children: [
            // 1. 星空背景
            Positioned.fill(
              child: AnimatedStarBackground(starCount: 120),
            ),

            // 2. 主内容
            SafeArea(
              child: Column(
                children: [
                  // 顶部状态栏
                  _buildStatusBar(mindfulness),

                  // 中间内容
                  Expanded(
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          // 任务卡片
                          ScaleTransition(
                            scale: _scaleAnimation,
                            child: FadeTransition(
                              opacity: _fadeAnimation,
                              child: _buildTaskCard(),
                            ),
                          ),

                          SizedBox(height: DS.xxxl),

                          // 翻页时钟
                          FadeTransition(
                            opacity: _clockFadeAnimation,
                            child: SimpleFlipClock(
                              seconds: mindfulness.elapsedSeconds,
                              fontSize: 72,
                            ),
                          ),

                          SizedBox(height: DS.xxl),

                          // 火焰动画
                          FadeTransition(
                            opacity: _clockFadeAnimation,
                            child: _buildFlameAnimation(),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // 底部退出按钮
                  _buildExitButton(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBar(MindfulnessState state) => Padding(
      padding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // 分心计数
          if (state.interruptionCount > 0)
            Container(
              padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: AppDesignTokens.warning.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.visibility_off_rounded,
                    color: AppDesignTokens.warning,
                    size: 16,
                  ),
                  SizedBox(width: 6),
                  Text(
                    '分心 ${state.interruptionCount} 次',
                    style: TextStyle(
                      color: AppDesignTokens.warning,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            )
          else
            SizedBox(width: 80),

          // 正念模式标题
          Row(
            children: [
              Icon(
                Icons.self_improvement_rounded,
                color: DS.brandPrimary.withValues(alpha: 0.7),
                size: 20,
              ),
              SizedBox(width: DS.sm),
              Text(
                '正念模式',
                style: TextStyle(
                  color: DS.brandPrimary.withValues(alpha: 0.7),
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),

          // 暂停按钮
          IconButton(
            icon: Icon(
              state.isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded,
              color: DS.brandPrimary.withValues(alpha: 0.7),
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

  Widget _buildTaskCard() => Container(
      margin: EdgeInsets.symmetric(horizontal: 40),
      padding: EdgeInsets.all(DS.xl),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: DS.brandPrimary.withValues(alpha: 0.15),
        ),
        boxShadow: [
          BoxShadow(
            color: DS.brandPrimary.withValues(alpha: 0.3),
            blurRadius: 20,
            spreadRadius: 5,
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 任务标题
          Text(
            widget.task.title,
            style: TextStyle(
              color: DS.brandPrimaryConst,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),

          SizedBox(height: DS.md),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              gradient: AppDesignTokens.primaryGradient,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              widget.task.type.name.toUpperCase(),
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );

  Widget _buildFlameAnimation() => TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.9, end: 1.1),
      duration: const Duration(milliseconds: 1500),
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
          gradient: AppDesignTokens.flameGradient,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: AppDesignTokens.flameCore.withValues(alpha: 0.6),
              blurRadius: 20,
              spreadRadius: 5,
            ),
          ],
        ),
        child: Icon(
          Icons.local_fire_department_rounded,
          color: DS.brandPrimaryConst,
          size: 32,
        ),
      ),
    );

  Widget _buildExitButton() => Padding(
      padding: EdgeInsets.all(DS.xl),
      child: TextButton(
        onPressed: _handleExit,
        style: TextButton.styleFrom(
          foregroundColor: DS.brandPrimary.withValues(alpha: 0.5),
          padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.exit_to_app_rounded, size: 18),
            SizedBox(width: DS.sm),
            Text('退出正念模式'),
          ],
        ),
      ),
    );
}
