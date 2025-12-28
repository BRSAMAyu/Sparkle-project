import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';

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

class _CentralFlameState extends State<CentralFlame> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
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
          ),
        ),
    );
}

class _SmallFlamePainter extends CustomPainter {

  _SmallFlamePainter({
    required this.progress,
    required this.intensity,
  });
  final double progress;
  final double intensity;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    // Intensity affects color and size
    final safeIntensity = intensity.clamp(0.0, 1.0);
    
    // Breathing effect
    final breath = 1.0 + 0.1 * progress * (0.5 + safeIntensity * 0.5);
    
    // Core color (White -> Yellow)
    final corePaint = Paint()
      ..shader = RadialGradient(
        colors: [
          DS.brandPrimary,
          Color.lerp(AppDesignTokens.warningAccent, DS.warningAccent, safeIntensity)!,
          Colors.transparent,
        ],
        stops: const [0.2, 0.6, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: radius * breath));

    // Outer Glow (Orange -> Red)
    final glowPaint = Paint()
      ..color = Color.lerp(DS.brandPrimary.withValues(alpha: 0.3), DS.errorAccent.withValues(alpha: 0.5), safeIntensity)!
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, radius * 0.5);

    // Draw Glow
    canvas.drawCircle(center, radius * breath * 1.5, glowPaint);

    // Draw Flame Core (Simple tear shape or circle)
    // Using a circle for stability and "source" feel
    canvas.drawCircle(center, radius * breath * 0.6, corePaint);
    
    // Draw a small "spark" or halo ring
    if (safeIntensity > 0.3) {
      final ringPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5
        ..color = DS.brandPrimary.withValues(alpha: 0.3 * (1.0 - progress))
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);
        
      canvas.drawCircle(center, radius * (0.8 + 0.4 * progress), ringPaint);
    }
  }

  @override
  bool shouldRepaint(_SmallFlamePainter oldDelegate) => oldDelegate.progress != progress || oldDelegate.intensity != intensity;
}