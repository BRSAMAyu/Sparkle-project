import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// 连胜指示器样式
enum StreakIndicatorStyle {
  /// 紧凑型 - 用于导航栏或小空间
  compact,
  /// 标准型 - 用于卡片或列表
  standard,
  /// 完整型 - 用于详情页或个人资料
  full,
  /// 圆形 - 用于仪表盘焦点区域
  circular,
}

/// 连胜指示器组件
///
/// 显示当前连胜天数，带有火焰动画效果
class StreakIndicator extends ConsumerWidget {
  const StreakIndicator({
    super.key,
    this.style = StreakIndicatorStyle.standard,
    this.onTap,
    this.showFreezeCharges = true,
  });

  final StreakIndicatorStyle style;
  final VoidCallback? onTap;
  final bool showFreezeCharges;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final streakStats = ref.watch(streakStatsProvider);

    switch (style) {
      case StreakIndicatorStyle.compact:
        return _StreakIndicatorCompact(
          streakStats: streakStats,
          onTap: onTap,
        );
      case StreakIndicatorStyle.standard:
        return _StreakIndicatorStandard(
          streakStats: streakStats,
          onTap: onTap,
        );
      case StreakIndicatorStyle.full:
        return _StreakIndicatorFull(
          streakStats: streakStats,
          onTap: onTap,
          showFreezeCharges: showFreezeCharges,
        );
      case StreakIndicatorStyle.circular:
        return _StreakIndicatorCircular(
          streakStats: streakStats,
          onTap: onTap,
        );
    }
  }
}

/// 紧凑型连胜指示器
class _StreakIndicatorCompact extends StatelessWidget {
  const _StreakIndicatorCompact({
    required this.streakStats,
    this.onTap,
  });

  final StreakStats streakStats;
  final VoidCallback? onTap;

  Color get _flameColor => _getFlameColor(streakStats.currentStreak);

  @override
  Widget build(BuildContext context) => GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: _flameColor.withValues(alpha: 0.1),
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: _flameColor.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.local_fire_department_rounded,
              size: DS.iconSizeSm,
              color: _flameColor,
            ),
            const SizedBox(width: DS.spacing4),
            Text(
              '${streakStats.currentStreak}',
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                fontWeight: DS.fontWeightBold,
                color: DS.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );

  Color _getFlameColor(int streak) {
    if (streak >= 30) return const Color(0xFFFFD700); // 金色 - 大师级
    if (streak >= 14) return const Color(0xFFFF6B00); // 橙红色 - 专家级
    if (streak >= 7) return const Color(0xFFFF9500); // 橙色 - 进阶级
    return DS.warning; // 黄色 - 入门级
  }
}

/// 标准型连胜指示器
class _StreakIndicatorStandard extends StatelessWidget {
  const _StreakIndicatorStandard({
    required this.streakStats,
    this.onTap,
  });

  final StreakStats streakStats;
  final VoidCallback? onTap;

  Color get _flameColor => _getFlameColor(streakStats.currentStreak);

  @override
  Widget build(BuildContext context) => GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              _flameColor.withValues(alpha: 0.15),
              _flameColor.withValues(alpha: 0.05),
            ],
          ),
          borderRadius: DS.borderRadius16,
          border: Border.all(
            color: _flameColor.withValues(alpha: 0.3),
            width: 1.5,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildFlameIcon(),
            const SizedBox(width: DS.spacing12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '连续学习',
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.textSecondary,
                  ),
                ),
                Text(
                  '${streakStats.currentStreak} 天',
                  style: TextStyle(
                    fontSize: DS.fontSizeLg,
                    fontWeight: DS.fontWeightBold,
                    color: _flameColor,
                  ),
                ),
              ],
            ),
            if (streakStats.maxStreak > streakStats.currentStreak) ...[
              const SizedBox(width: DS.spacing12),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: DS.neutral200,
                  borderRadius: DS.borderRadius8,
                ),
                child: Text(
                  '最高 ${streakStats.maxStreak}',
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.textSecondary,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );

  Widget _buildFlameIcon() => Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            _flameColor,
            _flameColor.withValues(alpha: 0.6),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: _flameColor.withValues(alpha: 0.3),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: const Icon(
        Icons.whatshot_rounded,
        color: Colors.white,
        size: DS.iconSizeLg,
      ),
    );

  Color _getFlameColor(int streak) {
    if (streak >= 30) return const Color(0xFFFFD700);
    if (streak >= 14) return const Color(0xFFFF6B00);
    if (streak >= 7) return const Color(0xFFFF9500);
    return DS.warning;
  }
}

/// 完整型连胜指示器
class _StreakIndicatorFull extends StatefulWidget {
  const _StreakIndicatorFull({
    required this.streakStats,
    this.onTap,
    this.showFreezeCharges = true,
  });

  final StreakStats streakStats;
  final VoidCallback? onTap;
  final bool showFreezeCharges;

  @override
  State<_StreakIndicatorFull> createState() => _StreakIndicatorFullState();
}

class _StreakIndicatorFullState extends State<_StreakIndicatorFull>
    with SingleTickerProviderStateMixin {
  late AnimationController _flameController;
  late Animation<double> _flameAnimation;

  @override
  void initState() {
    super.initState();
    _flameController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _flameAnimation = Tween<double>(begin: 0.95, end: 1.05).animate(
      CurvedAnimation(
        parent: _flameController,
        curve: Curves.easeInOut,
      ),
    );
    _flameController.repeat(reverse: true);
  }

  @override
  void dispose() {
    _flameController.dispose();
    super.dispose();
  }

  Color get _flameColor => _getFlameColor(widget.streakStats.currentStreak);

  @override
  Widget build(BuildContext context) => GestureDetector(
      onTap: widget.onTap,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              _flameColor.withValues(alpha: 0.2),
              _flameColor.withValues(alpha: 0.05),
            ],
          ),
          borderRadius: DS.borderRadius20,
          border: Border.all(
            color: _flameColor.withValues(alpha: 0.4),
            width: 2,
          ),
          boxShadow: [
            BoxShadow(
              color: _flameColor.withValues(alpha: 0.2),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          children: [
            // 顶部火焰和天数
            Row(
              children: [
                AnimatedBuilder(
                  animation: _flameAnimation,
                  builder: (context, child) => Transform.scale(
                    scale: _flameAnimation.value,
                    child: _buildLargeFlameIcon(),
                  ),
                ),
                const SizedBox(width: DS.spacing16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '连续学习',
                        style: TextStyle(
                          fontSize: DS.fontSizeSm,
                          color: DS.textSecondary,
                        ),
                      ),
                      Text(
                        '${widget.streakStats.currentStreak} 天',
                        style: TextStyle(
                          fontSize: DS.fontSize3xl,
                          fontWeight: DS.fontWeightBold,
                          color: _flameColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            // 统计信息
            Row(
              children: [
                _buildStatItem(
                  '最高',
                  '${widget.streakStats.maxStreak}天',
                  Icons.emoji_events,
                ),
                const SizedBox(width: DS.spacing12),
                _buildStatItem(
                  '累计',
                  '${widget.streakStats.totalCheckinDays}天',
                  Icons.calendar_today,
                ),
                const Spacer(),
                if (widget.showFreezeCharges)
                  _buildFreezeCharges(),
              ],
            ),
          ],
        ),
      ),
    );

  Widget _buildLargeFlameIcon() => Container(
      width: 64,
      height: 64,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            _flameColor,
            _flameColor.withValues(alpha: 0.5),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: _flameColor.withValues(alpha: 0.4),
            blurRadius: 20,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: const Icon(
        Icons.whatshot_rounded,
        color: Colors.white,
        size: DS.iconSize3xl,
      ),
    );

  Widget _buildStatItem(String label, String value, IconData icon) => Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: DS.surfacePrimary.withValues(alpha: 0.6),
        borderRadius: DS.borderRadius12,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: DS.iconSizeSm,
            color: DS.textSecondary,
          ),
          const SizedBox(width: DS.spacing6),
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.textSecondary,
                ),
              ),
              Text(
                value,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
        ],
      ),
    );

  Widget _buildFreezeCharges() {
    final charges = widget.streakStats.freezeCharges;
    final maxCharges = widget.streakStats.maxFreezeCharges;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        ...List.generate(maxCharges, (index) {
          final isActive = index < charges;
          return Container(
            width: 12,
            height: 20,
            margin: const EdgeInsets.only(left: 2),
            decoration: BoxDecoration(
              color: isActive
                  ? Colors.cyan.withValues(alpha: 0.8)
                  : DS.neutral300,
              borderRadius: DS.borderRadius4,
              border: Border.all(
                color: isActive ? Colors.cyan : DS.neutral400,
              ),
            ),
          );
        }),
        const SizedBox(width: DS.spacing8),
        Icon(
          Icons.ac_unit,
          size: DS.iconSizeSm,
          color: Colors.cyan.withValues(alpha: 0.8),
        ),
      ],
    );
  }

  Color _getFlameColor(int streak) {
    if (streak >= 30) return const Color(0xFFFFD700);
    if (streak >= 14) return const Color(0xFFFF6B00);
    if (streak >= 7) return const Color(0xFFFF9500);
    return DS.warning;
  }
}

/// 圆形连胜指示器
class _StreakIndicatorCircular extends StatefulWidget {
  const _StreakIndicatorCircular({
    required this.streakStats,
    this.onTap,
  });

  final StreakStats streakStats;
  final VoidCallback? onTap;

  @override
  State<_StreakIndicatorCircular> createState() =>
      _StreakIndicatorCircularState();
}

class _StreakIndicatorCircularState extends State<_StreakIndicatorCircular>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _progressAnimation;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );
    _progressAnimation = Tween<double>(begin: 0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOutCubic,
      ),
    );
    _controller.forward();

    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(
        parent: _pulseController,
        curve: Curves.easeInOut,
      ),
    );
    _pulseController.repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  Color get _flameColor => _getFlameColor(widget.streakStats.currentStreak);

  @override
  Widget build(BuildContext context) {
    final progress = widget.streakStats.currentStreak / 30; // 目标30天
    final isZeroStreak = widget.streakStats.currentStreak == 0;
    final displayColor = isZeroStreak ? DS.neutral400 : _flameColor;

    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        widget.onTap?.call();
      },
      child: SizedBox(
        width: double.infinity,
        height: double.infinity,
        child: FittedBox(
          fit: BoxFit.contain,
          child: SizedBox(
            width: 100,
            height: 100,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // 背景光晕
                if (!isZeroStreak)
                  AnimatedBuilder(
                    animation: _pulseAnimation,
                    builder: (context, child) => Container(
                      width: 100,
                      height: 100,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: displayColor.withValues(alpha: 0.3),
                            blurRadius: 20 * _pulseAnimation.value,
                            spreadRadius: 4 * _pulseAnimation.value,
                          ),
                        ],
                      ),
                    ),
                  ),
                // 进度圆环
                AnimatedBuilder(
                  animation: _progressAnimation,
                  builder: (context, child) => CustomPaint(
                    size: const Size(100, 100),
                    painter: _CircularProgressPainter(
                      progress: isZeroStreak ? 1.0 : progress * _progressAnimation.value,
                      color: displayColor,
                      isBackground: isZeroStreak,
                    ),
                  ),
                ),
                // 中心内容
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.whatshot_rounded,
                      color: displayColor,
                      size: 20,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      isZeroStreak ? '开始' : '${widget.streakStats.currentStreak}',
                      style: TextStyle(
                        fontSize: isZeroStreak ? DS.fontSizeSm : DS.fontSizeLg,
                        fontWeight: DS.fontWeightBold,
                        color: displayColor,
                      ),
                    ),
                    Text(
                      isZeroStreak ? '挑战' : '天',
                      style: TextStyle(
                        fontSize: 10,
                        color: DS.textSecondary,
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

  Color _getFlameColor(int streak) {
    if (streak >= 30) return const Color(0xFFFFD700);
    if (streak >= 14) return const Color(0xFFFF6B00);
    if (streak >= 7) return const Color(0xFFFF9500);
    return DS.warning;
  }
}

/// 圆环进度条绘制器
class _CircularProgressPainter extends CustomPainter {
  _CircularProgressPainter({
    required this.progress,
    required this.color,
    this.isBackground = false,
  });

  final double progress;
  final Color color;
  final bool isBackground;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - 12) / 2;
    const strokeWidth = 8.0;

    // 绘制底色圆环
    final backgroundPaint = Paint()
      ..color = DS.neutral200
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, backgroundPaint);

    if (isBackground) {
      // 空状态：绘制虚线圆环
      final dashPaint = Paint()
        ..color = color.withValues(alpha: 0.5)
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round;
      
      _drawDashedCircle(canvas, center, radius, dashPaint);
    } else if (progress > 0) {
      // 正常进度
      final rect = Rect.fromCircle(center: center, radius: radius);
      final progressPaint = Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round;

      const startAngle = -math.pi / 2;
      final sweepAngle = 2 * math.pi * progress.clamp(0.0, 1.0);

      canvas.drawArc(
        rect,
        startAngle,
        sweepAngle,
        false,
        progressPaint,
      );
    }
  }

  void _drawDashedCircle(Canvas canvas, Offset center, double radius, Paint paint) {
    const dashWidth = 5.0;
    const dashSpace = 5.0;
    final circumference = 2 * math.pi * radius;
    
    const startAngle = -math.pi / 2;
    var currentAngle = startAngle;
    
    while (currentAngle < startAngle + 2 * math.pi) {
      final arcAngle = (dashWidth / circumference) * 2 * math.pi;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        currentAngle,
        arcAngle,
        false,
        paint,
      );
      currentAngle += ((dashWidth + dashSpace) / circumference) * 2 * math.pi;
    }
  }

  @override
  bool shouldRepaint(_CircularProgressPainter oldDelegate) =>
      oldDelegate.progress != progress || 
      oldDelegate.color != color ||
      oldDelegate.isBackground != isBackground;
}

/// 便捷组件：导航栏连胜指示器
class NavStreakIndicator extends ConsumerWidget {
  const NavStreakIndicator({
    super.key,
    this.onTap,
  });

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) => StreakIndicator(
      style: StreakIndicatorStyle.compact,
      onTap: onTap,
    );
}

/// 便捷组件：卡片连胜指示器
class CardStreakIndicator extends ConsumerWidget {
  const CardStreakIndicator({
    super.key,
    this.onTap,
  });

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) => StreakIndicator(
      onTap: onTap,
    );
}

/// 便捷组件：仪表盘圆形指示器
class DashboardStreakIndicator extends ConsumerWidget {
  const DashboardStreakIndicator({
    super.key,
    this.onTap,
  });

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) => StreakIndicator(
      style: StreakIndicatorStyle.circular,
      onTap: onTap,
    );
}
