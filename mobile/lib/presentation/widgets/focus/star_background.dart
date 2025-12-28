import 'dart:math';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// 星星数据
class _Star {
  final double x;
  final double y;
  final double size;
  final double twinkleSpeed; // 闪烁速度因子
  final double twinkleOffset; // 闪烁相位偏移

  const _Star({
    required this.x,
    required this.y,
    required this.size,
    required this.twinkleSpeed,
    required this.twinkleOffset,
  });
}

/// 星空背景组件
class StarBackground extends StatefulWidget {
  final int starCount;
  final bool enableTwinkle;

  const StarBackground({
    super.key,
    this.starCount = 100,
    this.enableTwinkle = true,
  });

  @override
  State<StarBackground> createState() => _StarBackgroundState();
}

class _StarBackgroundState extends State<StarBackground>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late List<_Star> _stars;
  final Random _random = Random();

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    );

    if (widget.enableTwinkle) {
      _controller.repeat();
    }

    _generateStars();
  }

  void _generateStars() {
    _stars = List.generate(widget.starCount, (_) {
      return _Star(
        x: _random.nextDouble(),
        y: _random.nextDouble(),
        size: _random.nextDouble() * 2 + 0.5, // 0.5 - 2.5
        twinkleSpeed: _random.nextDouble() * 2 + 0.5, // 0.5 - 2.5
        twinkleOffset: _random.nextDouble() * 2 * pi,
      );
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return CustomPaint(
          painter: _StarPainter(
            stars: _stars,
            animationValue: _controller.value,
            enableTwinkle: widget.enableTwinkle,
          ),
          size: Size.infinite,
        );
      },
    );
  }
}

/// 星空绘制器
class _StarPainter extends CustomPainter {
  final List<_Star> stars;
  final double animationValue;
  final bool enableTwinkle;

  _StarPainter({
    required this.stars,
    required this.animationValue,
    required this.enableTwinkle,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 绘制深空背景渐变
    final bgRect = Rect.fromLTWH(0, 0, size.width, size.height);
    final bgPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          AppDesignTokens.deepSpaceStart,
          AppDesignTokens.deepSpaceEnd,
        ],
      ).createShader(bgRect);

    canvas.drawRect(bgRect, bgPaint);

    // 绘制星星
    for (final star in stars) {
      double opacity;
      if (enableTwinkle) {
        // 使用正弦函数实现闪烁效果
        final twinkle = sin(
          animationValue * 2 * pi * star.twinkleSpeed + star.twinkleOffset,
        );
        opacity = 0.3 + (twinkle + 1) / 2 * 0.7; // 0.3 - 1.0
      } else {
        opacity = 0.8;
      }

      final starPaint = Paint()
        ..color = DS.brandPrimary.withValues(alpha: opacity);

      // 绘制星星光晕
      if (star.size > 1.5) {
        final glowPaint = Paint()
          ..color = DS.brandPrimary.withValues(alpha: opacity * 0.3)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);

        canvas.drawCircle(
          Offset(star.x * size.width, star.y * size.height),
          star.size * 2,
          glowPaint,
        );
      }

      // 绘制星星本体
      canvas.drawCircle(
        Offset(star.x * size.width, star.y * size.height),
        star.size,
        starPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _StarPainter oldDelegate) {
    return oldDelegate.animationValue != animationValue;
  }
}

/// 带渐入动画的星空背景
class AnimatedStarBackground extends StatefulWidget {
  final Duration fadeInDuration;
  final int starCount;

  const AnimatedStarBackground({
    super.key,
    this.fadeInDuration = const Duration(milliseconds: 500),
    this.starCount = 100,
  });

  @override
  State<AnimatedStarBackground> createState() => _AnimatedStarBackgroundState();
}

class _AnimatedStarBackgroundState extends State<AnimatedStarBackground>
    with SingleTickerProviderStateMixin {
  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      vsync: this,
      duration: widget.fadeInDuration,
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeIn,
    );
    _fadeController.forward();
  }

  @override
  void dispose() {
    _fadeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: StarBackground(starCount: widget.starCount),
    );
  }
}
