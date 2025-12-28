import 'dart:math';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter/material.dart';

/// Animation that plays when a star is successfully "sparked"
/// Shows a burst of particles emanating from the star position
class StarSuccessAnimation extends StatefulWidget {
  /// Screen position of the star
  final Offset position;

  /// Color of the star
  final Color color;

  /// Called when the animation completes
  final VoidCallback onComplete;

  /// Duration of the animation
  final Duration duration;

  const StarSuccessAnimation({
    required this.position, required this.color, required this.onComplete, super.key,
    this.duration = const Duration(milliseconds: 600),
  });

  @override
  State<StarSuccessAnimation> createState() => _StarSuccessAnimationState();
}

class _StarSuccessAnimationState extends State<StarSuccessAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;
  late Animation<double> _opacityAnimation;

  final List<_BurstParticle> _particles = [];
  final Random _random = Random();

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: widget.duration,
      vsync: this,
    );

    _scaleAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.0, 0.4, curve: Curves.easeOutBack),
      ),
    );

    _opacityAnimation = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.5, 1.0, curve: Curves.easeOut),
      ),
    );

    // Generate burst particles
    for (int i = 0; i < 12; i++) {
      final angle = (i / 12) * 2 * pi + _random.nextDouble() * 0.3;
      final velocity = 80 + _random.nextDouble() * 60;
      _particles.add(
        _BurstParticle(
          angle: angle,
          velocity: velocity,
          size: 3 + _random.nextDouble() * 3,
          delay: _random.nextDouble() * 0.1,
        ),
      );
    }

    _controller.forward().then((_) {
      widget.onComplete();
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
      builder: (context, child) {
        return CustomPaint(
          size: Size.infinite,
          painter: _SuccessAnimationPainter(
            center: widget.position,
            color: widget.color,
            progress: _controller.value,
            scale: _scaleAnimation.value,
            opacity: _opacityAnimation.value,
            particles: _particles,
          ),
        );
      },
    );
  }
}

class _BurstParticle {
  final double angle;
  final double velocity;
  final double size;
  final double delay;

  _BurstParticle({
    required this.angle,
    required this.velocity,
    required this.size,
    required this.delay,
  });

  Offset getPosition(double progress, Offset center) {
    final adjustedProgress = ((progress - delay) / (1 - delay)).clamp(0.0, 1.0);
    // Ease out for natural deceleration
    final easedProgress = Curves.easeOutQuart.transform(adjustedProgress);
    final distance = velocity * easedProgress;
    return center + Offset(
      cos(angle) * distance,
      sin(angle) * distance,
    );
  }

  double getOpacity(double progress) {
    final adjustedProgress = ((progress - delay) / (1 - delay)).clamp(0.0, 1.0);
    return (1 - adjustedProgress).clamp(0.0, 1.0);
  }
}

class _SuccessAnimationPainter extends CustomPainter {
  final Offset center;
  final Color color;
  final double progress;
  final double scale;
  final double opacity;
  final List<_BurstParticle> particles;

  _SuccessAnimationPainter({
    required this.center,
    required this.color,
    required this.progress,
    required this.scale,
    required this.opacity,
    required this.particles,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Central ring expansion
    if (progress < 0.6) {
      final ringProgress = (progress / 0.6).clamp(0.0, 1.0);
      final ringRadius = 30 * Curves.easeOutQuart.transform(ringProgress);
      final ringOpacity = (1 - ringProgress) * 0.8;

      final ringPaint = Paint()
        ..color = color.withValues(alpha: ringOpacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3 * (1 - ringProgress);
      canvas.drawCircle(center, ringRadius, ringPaint);

      // Secondary ring (delayed)
      if (progress > 0.1) {
        final ring2Progress = ((progress - 0.1) / 0.5).clamp(0.0, 1.0);
        final ring2Radius = 20 * Curves.easeOutQuart.transform(ring2Progress);
        final ring2Opacity = (1 - ring2Progress) * 0.5;

        final ring2Paint = Paint()
          ..color = DS.brandPrimary.withValues(alpha: ring2Opacity)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2 * (1 - ring2Progress);
        canvas.drawCircle(center, ring2Radius, ring2Paint);
      }
    }

    // Burst particles
    for (final particle in particles) {
      final pos = particle.getPosition(progress, center);
      final particleOpacity = particle.getOpacity(progress);

      if (particleOpacity > 0) {
        // Glow
        final glowPaint = Paint()
          ..color = color.withValues(alpha: particleOpacity * 0.4)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
        canvas.drawCircle(pos, particle.size * 1.5, glowPaint);

        // Core
        final corePaint = Paint()
          ..color = Color.lerp(DS.brandPrimary, color, progress)!
              .withValues(alpha: particleOpacity);
        canvas.drawCircle(pos, particle.size, corePaint);
      }
    }

    // Central flash
    if (progress < 0.3) {
      final flashProgress = (progress / 0.3).clamp(0.0, 1.0);
      final flashRadius = 15 * scale;
      final flashOpacity = (1 - flashProgress) * 0.9;

      final flashPaint = Paint()
        ..color = DS.brandPrimary.withValues(alpha: flashOpacity)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, 10 * (1 - flashProgress));
      canvas.drawCircle(center, flashRadius, flashPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _SuccessAnimationPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
