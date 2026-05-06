import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Obsidian-style knowledge node creation animation.
///
/// Phases:
/// 1. Node materializes with spring scale-in + glow pulse (0.0 – 0.20)
/// 2. Connection lines draw outward to neighbor nodes (0.15 – 0.55)
/// 3. Energy particles travel along connections (0.25 – 0.65)
/// 4. Neighbor nodes pulse/glow on arrival (0.45 – 0.75)
/// 5. Gentle fade-out of all effects (0.70 – 1.0)
class StarSuccessAnimation extends StatefulWidget {
  const StarSuccessAnimation({
    required this.position,
    required this.color,
    required this.onComplete,
    super.key,
    this.neighborPositions = const [],
    this.emphasizeNeighbors = false,
    this.duration = const Duration(milliseconds: 2800),
  });

  final Offset position;
  final Color color;
  final VoidCallback onComplete;
  final List<Offset> neighborPositions;
  final bool emphasizeNeighbors;
  final Duration duration;

  @override
  State<StarSuccessAnimation> createState() => _StarSuccessAnimationState();
}

class _StarSuccessAnimationState extends State<StarSuccessAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late List<_ConnectionParticle> _connectionParticles;
  late List<_BurstParticle> _burstParticles;
  final Random _random = Random();
  bool _completed = false;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: widget.duration,
      vsync: this,
    );

    // Generate burst particles around the central node
    _burstParticles = List.generate(16, (i) {
      final angle = (i / 16) * 2 * pi + _random.nextDouble() * 0.4;
      return _BurstParticle(
        angle: angle,
        velocity: 30 + _random.nextDouble() * 50,
        size: 1.5 + _random.nextDouble() * 2.5,
        delay: _random.nextDouble() * 0.08,
      );
    });

    // Generate traveling particles for each connection
    _connectionParticles = [];
    for (var ci = 0; ci < widget.neighborPositions.length; ci++) {
      final particleCount = 2 + _random.nextInt(2);
      for (var j = 0; j < particleCount; j++) {
        _connectionParticles.add(
          _ConnectionParticle(
            connectionIndex: ci,
            delay: 0.25 + ci * 0.04 + j * 0.06 + _random.nextDouble() * 0.03,
            speed: 0.8 + _random.nextDouble() * 0.4,
            size: 2.0 + _random.nextDouble() * 1.5,
          ),
        );
      }
    }

    unawaited(
      SensoryFeedbackService.emit(
        SensoryFeedbackEvent.starUnlock,
      ),
    );
    unawaited(
      _controller.forward().then((_) {
        if (!_completed) {
          _completed = true;
          widget.onComplete();
        }
      }),
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (context.reduceMotion && !_completed) {
      _completed = true;
      _controller.stop();
      widget.onComplete();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _controller,
        builder: (context, child) => RepaintBoundary(
          child: CustomPaint(
            size: Size.infinite,
            painter: _ObsidianNodePainter(
              center: widget.position,
              color: widget.color,
              progress: _controller.value,
              neighborPositions: widget.neighborPositions,
              emphasizeNeighbors: widget.emphasizeNeighbors,
              burstParticles: _burstParticles,
              connectionParticles: _connectionParticles,
            ),
          ),
        ),
      );
}

class _BurstParticle {
  _BurstParticle({
    required this.angle,
    required this.velocity,
    required this.size,
    required this.delay,
  });
  final double angle;
  final double velocity;
  final double size;
  final double delay;
}

class _ConnectionParticle {
  _ConnectionParticle({
    required this.connectionIndex,
    required this.delay,
    required this.speed,
    required this.size,
  });
  final int connectionIndex;
  final double delay;
  final double speed;
  final double size;
}

class _ObsidianNodePainter extends CustomPainter {
  _ObsidianNodePainter({
    required this.center,
    required this.color,
    required this.progress,
    required this.neighborPositions,
    required this.emphasizeNeighbors,
    required this.burstParticles,
    required this.connectionParticles,
  });

  final Offset center;
  final Color color;
  final double progress;
  final List<Offset> neighborPositions;
  final bool emphasizeNeighbors;
  final List<_BurstParticle> burstParticles;
  final List<_ConnectionParticle> connectionParticles;

  @override
  void paint(Canvas canvas, Size size) {
    _paintConnectionLines(canvas);
    _paintConnectionParticles(canvas);
    _paintNeighborPulses(canvas);
    _paintCentralNode(canvas);
    _paintBurstParticles(canvas);
  }

  /// Phase 2: Connection lines draw from center to neighbors
  void _paintConnectionLines(Canvas canvas) {
    if (neighborPositions.isEmpty) return;

    for (var i = 0; i < neighborPositions.length; i++) {
      final neighbor = neighborPositions[i];
      // Stagger line drawing: each connection starts slightly later
      final lineStart = 0.12 + i * 0.03;
      final lineEnd = lineStart + 0.30;
      final drawProgress =
          ((progress - lineStart) / (lineEnd - lineStart)).clamp(0.0, 1.0);

      if (drawProgress <= 0) continue;

      // Fade out in the final phase
      final fadeOut =
          progress > 0.70 ? ((1.0 - progress) / 0.30).clamp(0.0, 1.0) : 1.0;

      final eased = Curves.easeOutCubic.transform(drawProgress);
      final lineEnd2 = Offset.lerp(center, neighbor, eased)!;

      // Glow line
      final glowPaint = Paint()
        ..color = color.withValues(alpha: 0.15 * fadeOut)
        ..strokeWidth = 4.0
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
      canvas.drawLine(center, lineEnd2, glowPaint);

      // Core line
      final linePaint = Paint()
        ..color = color.withValues(alpha: 0.5 * fadeOut)
        ..strokeWidth = 1.5
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(center, lineEnd2, linePaint);

      // Leading dot at the tip of the growing line
      if (drawProgress < 1.0 && drawProgress > 0.05) {
        final dotPaint = Paint()
          ..color = color.withValues(alpha: 0.9 * fadeOut);
        canvas.drawCircle(lineEnd2, 3.0, dotPaint);

        final dotGlow = Paint()
          ..color = color.withValues(alpha: 0.3 * fadeOut)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5);
        canvas.drawCircle(lineEnd2, 5.0, dotGlow);
      }
    }
  }

  /// Phase 3: Energy particles traveling along connections
  void _paintConnectionParticles(Canvas canvas) {
    if (neighborPositions.isEmpty) return;

    final fadeOut =
        progress > 0.70 ? ((1.0 - progress) / 0.30).clamp(0.0, 1.0) : 1.0;

    for (final particle in connectionParticles) {
      if (particle.connectionIndex >= neighborPositions.length) continue;

      final neighbor = neighborPositions[particle.connectionIndex];
      final travelDuration = 0.25 / particle.speed;
      final t = ((progress - particle.delay) / travelDuration).clamp(0.0, 1.0);

      if (t <= 0 || t >= 1) continue;

      final eased = Curves.easeInOutCubic.transform(t);
      final pos = Offset.lerp(center, neighbor, eased)!;
      final particleOpacity = sin(t * pi) * fadeOut; // fade in and out

      final paint = Paint()
        ..color = DS.brandPrimary.withValues(alpha: 0.8 * particleOpacity);
      canvas.drawCircle(pos, particle.size, paint);

      final glow = Paint()
        ..color = color.withValues(alpha: 0.3 * particleOpacity)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
      canvas.drawCircle(pos, particle.size * 2, glow);
    }
  }

  /// Phase 4: Neighbor nodes pulse/glow when connection arrives
  void _paintNeighborPulses(Canvas canvas) {
    if (neighborPositions.isEmpty) return;

    for (var i = 0; i < neighborPositions.length; i++) {
      final neighbor = neighborPositions[i];
      // Pulse starts when the line reaches the neighbor
      final pulseStart = 0.12 + i * 0.03 + 0.30; // lineStart + lineDuration
      final pulseDuration = emphasizeNeighbors ? 0.25 : 0.18;
      final pulseProgress =
          ((progress - pulseStart) / pulseDuration).clamp(0.0, 1.0);

      if (pulseProgress <= 0) continue;

      final fadeOut =
          progress > 0.75 ? ((1.0 - progress) / 0.25).clamp(0.0, 1.0) : 1.0;

      // Expanding ring
      final ringRadius = 8 + 20 * Curves.easeOutCubic.transform(pulseProgress);
      final ringOpacity = (1.0 - pulseProgress) * 0.6 * fadeOut;

      final ringPaint = Paint()
        ..color = color.withValues(alpha: ringOpacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0 * (1 - pulseProgress * 0.5);
      canvas.drawCircle(neighbor, ringRadius, ringPaint);

      // Glow at neighbor
      final glowOpacity = (1.0 - pulseProgress * 0.7) * 0.35 * fadeOut;
      final glowPaint = Paint()
        ..color = color.withValues(alpha: glowOpacity)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12);
      canvas.drawCircle(neighbor, 10, glowPaint);

      // Small bright core flash
      if (pulseProgress < 0.4) {
        final flashOpacity = (1 - pulseProgress / 0.4) * 0.7 * fadeOut;
        final flashPaint = Paint()
          ..color = DS.brandPrimary.withValues(alpha: flashOpacity);
        canvas.drawCircle(neighbor, 4, flashPaint);
      }
    }
  }

  /// Phase 1 & 5: Central node materializes and fades
  void _paintCentralNode(Canvas canvas) {
    // Scale-in with overshoot (spring feel)
    final scaleProgress = (progress / 0.20).clamp(0.0, 1.0);
    final scale = Curves.easeOutBack.transform(scaleProgress);

    // Fade out
    final fadeOut =
        progress > 0.72 ? ((1.0 - progress) / 0.28).clamp(0.0, 1.0) : 1.0;

    // Outer glow pulse
    final glowPhase = progress * 3 * pi;
    final glowPulse = 0.5 + 0.5 * sin(glowPhase);
    final glowRadius = (18 + 8 * glowPulse) * scale;
    final glowOpacity = (0.2 + 0.1 * glowPulse) * fadeOut;

    final glowPaint = Paint()
      ..color = color.withValues(alpha: glowOpacity)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 16);
    canvas.drawCircle(center, glowRadius, glowPaint);

    // Mid-ring pulse
    if (progress < 0.55) {
      final ringProgress = (progress / 0.55).clamp(0.0, 1.0);
      final ringRadius = 30 * Curves.easeOutQuart.transform(ringProgress);
      final ringOpacity = (1 - ringProgress) * 0.5 * fadeOut;

      final ringPaint = Paint()
        ..color = color.withValues(alpha: ringOpacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5 * (1 - ringProgress * 0.6);
      canvas.drawCircle(center, ringRadius * scale, ringPaint);
    }

    // Secondary ring (delayed)
    if (progress > 0.08 && progress < 0.45) {
      const ring2Start = 0.08;
      final ring2Progress = ((progress - ring2Start) / 0.32).clamp(0.0, 1.0);
      final ring2Radius = 20 * Curves.easeOutQuart.transform(ring2Progress);
      final ring2Opacity = (1 - ring2Progress) * 0.35 * fadeOut;

      final ring2Paint = Paint()
        ..color = DS.brandPrimary.withValues(alpha: ring2Opacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.8 * (1 - ring2Progress * 0.6);
      canvas.drawCircle(center, ring2Radius * scale, ring2Paint);
    }

    // Bright core
    final coreRadius = 6.0 * scale;
    final coreOpacity = fadeOut * 0.9;
    final corePaint = Paint()..color = color.withValues(alpha: coreOpacity);
    canvas.drawCircle(center, coreRadius, corePaint);

    // Inner white flash on initial appear
    if (progress < 0.15) {
      final flashProgress = (progress / 0.15).clamp(0.0, 1.0);
      final flashRadius = 12 * scale;
      final flashOpacity = (1 - flashProgress) * 0.8;

      final flashPaint = Paint()
        ..color = DS.neutral0.withValues(alpha: flashOpacity)
        ..maskFilter =
            MaskFilter.blur(BlurStyle.normal, 8 * (1 - flashProgress));
      canvas.drawCircle(center, flashRadius, flashPaint);
    }
  }

  /// Subtle burst particles around the central node
  void _paintBurstParticles(Canvas canvas) {
    final fadeOut =
        progress > 0.70 ? ((1.0 - progress) / 0.30).clamp(0.0, 1.0) : 1.0;

    for (final particle in burstParticles) {
      final adjustedProgress =
          ((progress - particle.delay) / (0.6 - particle.delay))
              .clamp(0.0, 1.0);
      if (adjustedProgress <= 0) continue;

      final easedProgress = Curves.easeOutQuart.transform(adjustedProgress);
      final distance = particle.velocity * easedProgress;
      final pos = center +
          Offset(
            cos(particle.angle) * distance,
            sin(particle.angle) * distance,
          );
      final particleOpacity = (1 - adjustedProgress).clamp(0.0, 1.0) * fadeOut;

      if (particleOpacity <= 0) continue;

      // Glow
      final glowPaint = Paint()
        ..color = color.withValues(alpha: particleOpacity * 0.3)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
      canvas.drawCircle(pos, particle.size * 1.5, glowPaint);

      // Core
      final corePaint = Paint()
        ..color = Color.lerp(DS.brandPrimary, color, progress)!
            .withValues(alpha: particleOpacity * 0.8);
      canvas.drawCircle(pos, particle.size, corePaint);
    }
  }

  @override
  bool shouldRepaint(covariant _ObsidianNodePainter oldDelegate) =>
      oldDelegate.progress != progress;
}
