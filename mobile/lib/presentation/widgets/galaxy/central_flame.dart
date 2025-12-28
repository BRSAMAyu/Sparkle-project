import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/device_performance_service.dart';

/// P2: Central flame widget with performance-aware rendering
/// Automatically degrades visual effects on low-end devices
class CentralFlame extends StatefulWidget {
  const CentralFlame({
    required this.intensity,
    super.key,
    this.size = 40.0,
  });

  final double intensity; // 0.0 to 1.0 (or higher for super states)
  final double size;

  @override
  State<CentralFlame> createState() => _CentralFlameState();
}

class _CentralFlameState extends State<CentralFlame>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late RenderConfig _renderConfig;

  @override
  void initState() {
    super.initState();
    _renderConfig = DevicePerformanceService.instance.renderConfig;

    // Adjust animation duration based on performance tier
    final duration = _renderConfig.tier == PerformanceTier.low
        ? const Duration(milliseconds: 2000) // Slower animation for low-end
        : const Duration(milliseconds: 1500);

    _controller = AnimationController(
      vsync: this,
      duration: duration,
    )..repeat(reverse: true);
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
          size: Size(widget.size, widget.size),
          painter: _SmallFlamePainter(
            progress: _controller.value,
            intensity: widget.intensity,
            renderConfig: _renderConfig,
          ),
        ),
      );
}

class _SmallFlamePainter extends CustomPainter {
  _SmallFlamePainter({
    required this.progress,
    required this.intensity,
    required this.renderConfig,
  });

  final double progress;
  final double intensity;
  final RenderConfig renderConfig;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    // Intensity affects color and size
    final safeIntensity = intensity.clamp(0.0, 1.0);

    // Breathing effect
    final breath = 1.0 + 0.1 * progress * (0.5 + safeIntensity * 0.5);

    // P2: Performance-aware rendering
    if (renderConfig.tier == PerformanceTier.low) {
      // LOW-END: Simple solid circle with minimal effects
      _paintSimplified(canvas, center, radius, safeIntensity, breath);
    } else {
      // MEDIUM/HIGH: Full effects
      _paintFull(canvas, center, radius, safeIntensity, breath);
    }
  }

  /// Simplified rendering for low-end devices
  void _paintSimplified(
    Canvas canvas,
    Offset center,
    double radius,
    double safeIntensity,
    double breath,
  ) {
    // Simple solid core without gradients
    final corePaint = Paint()
      ..color = Color.lerp(
        DS.brandPrimary,
        DS.warningAccent,
        safeIntensity,
      )!;

    canvas.drawCircle(center, radius * breath * 0.6, corePaint);

    // Simple outer ring instead of glow (no blur filter)
    if (safeIntensity > 0.3) {
      final ringPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0
        ..color = DS.brandPrimary.withValues(alpha: 0.4);

      canvas.drawCircle(center, radius * breath, ringPaint);
    }
  }

  /// Full rendering for medium/high-end devices
  void _paintFull(
    Canvas canvas,
    Offset center,
    double radius,
    double safeIntensity,
    double breath,
  ) {
    // Core color (White -> Yellow) with gradient
    final corePaint = Paint()
      ..shader = RadialGradient(
        colors: [
          DS.brandPrimary,
          Color.lerp(
            DS.warningAccent,
            DS.warningAccent,
            safeIntensity,
          )!,
          Colors.transparent,
        ],
        stops: const [0.2, 0.6, 1.0],
      ).createShader(
        Rect.fromCircle(center: center, radius: radius * breath),
      );

    // Outer Glow (Orange -> Red) - only if blur enabled
    if (renderConfig.enableBlur) {
      final glowPaint = Paint()
        ..color = Color.lerp(
          DS.brandPrimary.withValues(alpha: 0.3),
          DS.errorAccent.withValues(alpha: 0.5),
          safeIntensity,
        )!
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, radius * 0.5);

      canvas.drawCircle(center, radius * breath * 1.5, glowPaint);
    } else if (renderConfig.enableGlow) {
      // Medium tier: simple glow without blur
      final glowPaint = Paint()
        ..color = Color.lerp(
          DS.brandPrimary.withValues(alpha: 0.2),
          DS.errorAccent.withValues(alpha: 0.3),
          safeIntensity,
        )!;

      canvas.drawCircle(center, radius * breath * 1.3, glowPaint);
    }

    // Draw Flame Core
    canvas.drawCircle(center, radius * breath * 0.6, corePaint);

    // Draw a small "spark" or halo ring
    if (safeIntensity > 0.3) {
      final ringPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5
        ..color = DS.brandPrimary.withValues(alpha: 0.3 * (1.0 - progress));

      if (renderConfig.enableBlur) {
        ringPaint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);
      }

      canvas.drawCircle(center, radius * (0.8 + 0.4 * progress), ringPaint);
    }
  }

  @override
  bool shouldRepaint(_SmallFlamePainter oldDelegate) =>
      oldDelegate.progress != progress ||
      oldDelegate.intensity != intensity ||
      oldDelegate.renderConfig.tier != renderConfig.tier;
}