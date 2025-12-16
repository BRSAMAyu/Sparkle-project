import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// 火焰等级指示器组件
///
/// 用于可视化用户的火焰等级和亮度
/// 包含圆环进度条、火焰图标和脉冲动画
class FlameIndicator extends StatefulWidget {
  /// 火焰等级 (0-100)
  final int level;

  /// 火焰亮度 (0-100)
  final int brightness;

  /// 组件尺寸
  final double size;

  /// 是否显示标签
  final bool showLabel;

  /// 是否显示动画
  final bool animate;

  /// 自定义渐变
  final LinearGradient? customGradient;

  /// 点击回调
  final VoidCallback? onTap;

  const FlameIndicator({
    required this.level, required this.brightness, super.key,
    this.size = 120.0,
    this.showLabel = true,
    this.animate = true,
    this.customGradient,
    this.onTap,
  });

  @override
  State<FlameIndicator> createState() => _FlameIndicatorState();
}

class _FlameIndicatorState extends State<FlameIndicator>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _rotationController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();

    // 脉冲动画控制器
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.1).animate(
      CurvedAnimation(
        parent: _pulseController,
        curve: Curves.easeInOut,
      ),
    );

    // 旋转动画控制器（用于火焰图标）
    _rotationController = AnimationController(
      duration: const Duration(milliseconds: 3000),
      vsync: this,
    );

    if (widget.animate) {
      _pulseController.repeat(reverse: true);
      _rotationController.repeat();
    }
  }

  @override
  void didUpdateWidget(FlameIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.animate != oldWidget.animate) {
      if (widget.animate) {
        _pulseController.repeat(reverse: true);
        _rotationController.repeat();
      } else {
        _pulseController.stop();
        _rotationController.stop();
      }
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _rotationController.dispose();
    super.dispose();
  }

  Color _getFlameColor() {
    if (widget.brightness >= 80) {
      return const Color(0xFFFFD700); // 金色
    } else if (widget.brightness >= 60) {
      return AppDesignTokens.accent; // 黄色
    } else if (widget.brightness >= 40) {
      return AppDesignTokens.primaryBase; // 橙色
    } else {
      return AppDesignTokens.warning; // 浅橙色
    }
  }

  LinearGradient _getProgressGradient() {
    if (widget.customGradient != null) {
      return widget.customGradient!;
    }

    if (widget.brightness >= 80) {
      return const LinearGradient(
        colors: [Color(0xFFFFD700), Color(0xFFFFA500)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
    } else if (widget.brightness >= 60) {
      return AppDesignTokens.accentGradient;
    } else {
      return AppDesignTokens.primaryGradient;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 火焰指示器主体
          AnimatedBuilder(
            animation: _pulseAnimation,
            builder: (context, child) {
              return Transform.scale(
                scale: widget.animate ? _pulseAnimation.value : 1.0,
                child: SizedBox(
                  width: widget.size,
                  height: widget.size,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      // 外层发光效果
                      Container(
                        width: widget.size,
                        height: widget.size,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: _getFlameColor().withOpacity(0.3),
                              blurRadius: 20,
                              spreadRadius: 5,
                            ),
                          ],
                        ),
                      ),
                      // 圆环进度条
                      CustomPaint(
                        size: Size(widget.size, widget.size),
                        painter: _CircularProgressPainter(
                          progress: widget.brightness / 100.0,
                          gradient: _getProgressGradient(),
                          backgroundColor: AppDesignTokens.neutral200,
                          strokeWidth: 8.0,
                        ),
                      ),
                      // 火焰图标
                      _buildFlameIcon(),
                    ],
                  ),
                ),
              );
            },
          ),
          // 标签
          if (widget.showLabel) ...[
            const SizedBox(height: AppDesignTokens.spacing12),
            _buildLabel(),
          ],
        ],
      ),
    );
  }

  Widget _buildFlameIcon() {
    return AnimatedBuilder(
      animation: _rotationController,
      builder: (context, child) {
        return Transform.rotate(
          angle: widget.animate
              ? _rotationController.value * 2 * math.pi * 0.1
              : 0.0,
          child: Container(
            width: widget.size * 0.5,
            height: widget.size * 0.5,
            decoration: BoxDecoration(
              gradient: _getProgressGradient(),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: _getFlameColor().withOpacity(0.4),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Icon(
              Icons.local_fire_department_rounded,
              size: widget.size * 0.3,
              color: Colors.white,
            ),
          ),
        );
      },
    );
  }

  Widget _buildLabel() {
    return Column(
      children: [
        // 等级
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.whatshot_rounded,
              size: AppDesignTokens.iconSizeSm,
              color: _getFlameColor(),
            ),
            const SizedBox(width: AppDesignTokens.spacing4),
            Text(
              'Lv.${widget.level}',
              style: const TextStyle(
                fontSize: AppDesignTokens.fontSizeLg,
                fontWeight: AppDesignTokens.fontWeightBold,
                color: AppDesignTokens.neutral900,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppDesignTokens.spacing4),
        // 亮度
        Text(
          '亮度 ${widget.brightness}%',
          style: const TextStyle(
            fontSize: AppDesignTokens.fontSizeSm,
            color: AppDesignTokens.neutral600,
          ),
        ),
      ],
    );
  }
}

/// 圆环进度条绘制器
class _CircularProgressPainter extends CustomPainter {
  final double progress;
  final LinearGradient gradient;
  final Color backgroundColor;
  final double strokeWidth;

  _CircularProgressPainter({
    required this.progress,
    required this.gradient,
    required this.backgroundColor,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;

    // 绘制背景圆环
    final backgroundPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, backgroundPaint);

    // 绘制进度圆环
    if (progress > 0) {
      final rect = Rect.fromCircle(center: center, radius: radius);

      final progressPaint = Paint()
        ..shader = gradient.createShader(rect)
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round;

      const startAngle = -math.pi / 2; // 从顶部开始
      final sweepAngle = 2 * math.pi * progress;

      canvas.drawArc(
        rect,
        startAngle,
        sweepAngle,
        false,
        progressPaint,
      );

      // 绘制进度端点的发光效果
      if (progress < 1.0) {
        final endAngle = startAngle + sweepAngle;
        final endX = center.dx + radius * math.cos(endAngle);
        final endY = center.dy + radius * math.sin(endAngle);
        final endPoint = Offset(endX, endY);

        final glowPaint = Paint()
          ..color = Colors.white.withOpacity(0.8)
          ..style = PaintingStyle.fill;

        canvas.drawCircle(endPoint, strokeWidth / 2, glowPaint);
      }
    }
  }

  @override
  bool shouldRepaint(_CircularProgressPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.gradient != gradient ||
        oldDelegate.backgroundColor != backgroundColor ||
        oldDelegate.strokeWidth != strokeWidth;
  }
}

/// 紧凑型火焰指示器
///
/// 用于在小空间中显示火焰状态
class CompactFlameIndicator extends StatelessWidget {
  final int level;
  final int brightness;
  final VoidCallback? onTap;

  const CompactFlameIndicator({
    required this.level, required this.brightness, super.key,
    this.onTap,
  });

  Color _getFlameColor() {
    if (brightness >= 80) {
      return const Color(0xFFFFD700);
    } else if (brightness >= 60) {
      return AppDesignTokens.accent;
    } else if (brightness >= 40) {
      return AppDesignTokens.primaryBase;
    } else {
      return AppDesignTokens.warning;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing12,
          vertical: AppDesignTokens.spacing8,
        ),
        decoration: BoxDecoration(
          color: _getFlameColor().withOpacity(0.1),
          borderRadius: AppDesignTokens.borderRadius12,
          border: Border.all(
            color: _getFlameColor().withOpacity(0.3),
            width: 1.0,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.local_fire_department_rounded,
              size: AppDesignTokens.iconSizeSm,
              color: _getFlameColor(),
            ),
            const SizedBox(width: AppDesignTokens.spacing8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Lv.$level',
                  style: const TextStyle(
                    fontSize: AppDesignTokens.fontSizeSm,
                    fontWeight: AppDesignTokens.fontWeightBold,
                    color: AppDesignTokens.neutral900,
                  ),
                ),
                Text(
                  '$brightness%',
                  style: const TextStyle(
                    fontSize: AppDesignTokens.fontSizeXs,
                    color: AppDesignTokens.neutral600,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
