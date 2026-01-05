import 'dart:math';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Model representing a single energy particle in the transfer animation
class EnergyParticle {
  // For trail effect

  const EnergyParticle({
    required this.position,
    required this.size,
    required this.opacity,
    required this.color,
    this.angle = 0,
  });
  final Offset position;
  final double size;
  final double opacity;
  final Color color;
  final double angle;

  EnergyParticle copyWith({
    Offset? position,
    double? size,
    double? opacity,
    Color? color,
    double? angle,
  }) =>
      EnergyParticle(
        position: position ?? this.position,
        size: size ?? this.size,
        opacity: opacity ?? this.opacity,
        color: color ?? this.color,
        angle: angle ?? this.angle,
      );
}

/// Callback when the energy transfer animation completes (particle hits target)
typedef OnEnergyTransferComplete = void Function();

/// Widget that displays an animated energy particle traveling from center to target
class EnergyTransferAnimation extends StatefulWidget {
  const EnergyTransferAnimation({
    required this.sourcePosition,
    required this.targetPosition,
    required this.targetColor,
    required this.onComplete,
    super.key,
    this.duration = const Duration(milliseconds: 800),
  });

  /// Screen coordinates of the flame core (source)
  final Offset sourcePosition;

  /// Screen coordinates of the target star
  final Offset targetPosition;

  /// Color of the target star (for particle coloring)
  final Color targetColor;

  /// Called when the particle reaches the target
  final OnEnergyTransferComplete onComplete;

  /// Duration of the flight animation
  final Duration duration;

  @override
  State<EnergyTransferAnimation> createState() =>
      _EnergyTransferAnimationState();
}

class _EnergyTransferAnimationState extends State<EnergyTransferAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _progressAnimation;
  late Animation<double> _glowAnimation;

  // Trail particles for comet effect
  final List<_TrailParticle> _trailParticles = [];
  final Random _random = Random();

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: widget.duration,
      vsync: this,
    );

    // Main progress: ease out for natural deceleration as particle approaches target
    _progressAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutQuart,
    );

    // Glow pulsation during flight
    _glowAnimation = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 1.3), weight: 1),
      TweenSequenceItem(tween: Tween(begin: 1.3, end: 1.0), weight: 1),
    ]).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeInOut,
      ),
    );

    _controller.addListener(_updateTrail);

    _controller.forward().then((_) {
      widget.onComplete();
    });
  }

  void _updateTrail() {
    // Add new trail particles periodically
    if (_controller.value > 0.05 && _controller.value < 0.95) {
      final currentPos = _getCurrentPosition();
      _trailParticles.add(
        _TrailParticle(
          position: currentPos +
              Offset(
                (_random.nextDouble() - 0.5) * 6,
                (_random.nextDouble() - 0.5) * 6,
              ),
          opacity: 0.8,
          size: 3.0 + _random.nextDouble() * 2,
          createdAt: _controller.value,
        ),
      );
    }

    // Remove old trail particles
    _trailParticles.removeWhere((p) => _controller.value - p.createdAt > 0.15);

    // Limit max particles to prevent memory issues
    if (_trailParticles.length > 50) {
      _trailParticles.removeAt(0);
    }
  }

  Offset _getCurrentPosition() {
    final t = _progressAnimation.value;

    // Bezier curve for a slight arc effect
    final controlPoint = Offset(
      (widget.sourcePosition.dx + widget.targetPosition.dx) / 2,
      min(widget.sourcePosition.dy, widget.targetPosition.dy) - 50,
    );

    // Quadratic bezier interpolation
    final x = (1 - t) * (1 - t) * widget.sourcePosition.dx +
        2 * (1 - t) * t * controlPoint.dx +
        t * t * widget.targetPosition.dx;
    final y = (1 - t) * (1 - t) * widget.sourcePosition.dy +
        2 * (1 - t) * t * controlPoint.dy +
        t * t * widget.targetPosition.dy;

    return Offset(x, y);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _controller,
        builder: (context, child) => CustomPaint(
          size: Size.infinite,
          painter: _EnergyParticlePainter(
            currentPosition: _getCurrentPosition(),
            progress: _progressAnimation.value,
            glowScale: _glowAnimation.value,
            targetColor: widget.targetColor,
            trailParticles: List.from(_trailParticles),
            currentTime: _controller.value,
          ),
        ),
      );
}

class _TrailParticle {
  _TrailParticle({
    required this.position,
    required this.opacity,
    required this.size,
    required this.createdAt,
  });
  final Offset position;
  final double opacity;
  final double size;
  final double createdAt;
}

class _EnergyParticlePainter extends CustomPainter {
  _EnergyParticlePainter({
    required this.currentPosition,
    required this.progress,
    required this.glowScale,
    required this.targetColor,
    required this.trailParticles,
    required this.currentTime,
  });
  final Offset currentPosition;
  final double progress;
  final double glowScale;
  final Color targetColor;
  final List<_TrailParticle> trailParticles;
  final double currentTime;

  @override
  void paint(Canvas canvas, Size size) {
    // Draw trail particles first (behind main particle)
    for (final particle in trailParticles) {
      final age = currentTime - particle.createdAt;
      final fadeOut = (1 - age / 0.15).clamp(0.0, 1.0);

      final trailPaint = Paint()
        ..color = _blendColor(
          DS.brandPrimary,
          targetColor,
          progress,
        ).withValues(alpha: 0.4 * fadeOut)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);

      canvas.drawCircle(particle.position, particle.size * fadeOut, trailPaint);
    }

    // Main particle color transitions from fire orange to target color
    final particleColor = _blendColor(
      DS.brandPrimary,
      targetColor,
      progress,
    );

    // Outer glow (large, soft)
    final outerGlowPaint = Paint()
      ..color = particleColor.withValues(alpha: 0.3)
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, 20 * glowScale);
    canvas.drawCircle(currentPosition, 15 * glowScale, outerGlowPaint);

    // Middle glow
    final middleGlowPaint = Paint()
      ..color = particleColor.withValues(alpha: 0.5)
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, 10 * glowScale);
    canvas.drawCircle(currentPosition, 10 * glowScale, middleGlowPaint);

    // Inner glow (bright core)
    final innerGlowPaint = Paint()
      ..color = DS.brandPrimary.withValues(alpha: 0.8)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
    canvas.drawCircle(currentPosition, 5 * glowScale, innerGlowPaint);

    // Core particle (solid)
    final corePaint = Paint()
      ..color = particleColor
      ..style = PaintingStyle.fill;
    canvas.drawCircle(currentPosition, 4, corePaint);

    // White hot center
    final whitePaint = Paint()
      ..color = DS.brandPrimary
      ..style = PaintingStyle.fill;
    canvas.drawCircle(currentPosition, 2, whitePaint);

    // Impact flash at the end
    if (progress > 0.9) {
      final impactProgress = (progress - 0.9) / 0.1;
      final impactRadius = 30 * impactProgress;
      final impactOpacity = (1 - impactProgress) * 0.6;

      final impactPaint = Paint()
        ..color = targetColor.withValues(alpha: impactOpacity)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, 15 * impactProgress);
      canvas.drawCircle(currentPosition, impactRadius, impactPaint);
    }
  }

  Color _blendColor(Color from, Color to, double t) =>
      Color.lerp(from, to, t) ?? from;

  @override
  bool shouldRepaint(covariant _EnergyParticlePainter oldDelegate) =>
      oldDelegate.currentPosition != currentPosition ||
      oldDelegate.progress != progress ||
      oldDelegate.glowScale != glowScale;
}

/// Controller for managing energy transfer animations
class EnergyTransferController {
  final List<_ActiveTransfer> _activeTransfers = [];

  /// Get the current active transfers for rendering
  List<EnergyTransferData> get activeTransfers =>
      _activeTransfers.map((t) => t.data).toList();

  /// Start a new energy transfer animation
  void startTransfer({
    required Offset sourcePosition,
    required Offset targetPosition,
    required Color targetColor,
    required String targetNodeId,
    required VoidCallback onComplete,
  }) {
    final data = EnergyTransferData(
      sourcePosition: sourcePosition,
      targetPosition: targetPosition,
      targetColor: targetColor,
      targetNodeId: targetNodeId,
      onComplete: onComplete,
    );
    _activeTransfers.add(_ActiveTransfer(data: data));
  }

  /// Remove a completed transfer
  void removeTransfer(String targetNodeId) {
    _activeTransfers.removeWhere((t) => t.data.targetNodeId == targetNodeId);
  }

  void dispose() {
    _activeTransfers.clear();
  }
}

class _ActiveTransfer {
  _ActiveTransfer({required this.data});
  final EnergyTransferData data;
}

/// Data for a single energy transfer
class EnergyTransferData {
  EnergyTransferData({
    required this.sourcePosition,
    required this.targetPosition,
    required this.targetColor,
    required this.targetNodeId,
    required this.onComplete,
  });
  final Offset sourcePosition;
  final Offset targetPosition;
  final Color targetColor;
  final String targetNodeId;
  final VoidCallback onComplete;
}
