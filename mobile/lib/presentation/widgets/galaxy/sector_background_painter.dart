import 'dart:math';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

/// Painter for the sector nebula backgrounds
class SectorBackgroundPainter extends CustomPainter {
  final double canvasSize;

  SectorBackgroundPainter({
    required this.canvasSize,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);

    // Draw deep space background gradient
    _drawSpaceBackground(canvas, size, center);

    // Draw stars
    _drawStars(canvas, size);

    // Draw each sector's nebula
    for (final entry in SectorConfig.styles.entries) {
      _drawSectorNebula(canvas, center, entry.key, entry.value);
    }

    // Draw sector labels
    for (final entry in SectorConfig.styles.entries) {
      _drawSectorLabel(canvas, center, entry.value);
    }
  }

  void _drawSpaceBackground(Canvas canvas, Size size, Offset center) {
    // Radial gradient from slightly lighter center to dark edges
    final gradient = ui.Gradient.radial(
      center,
      size.width / 2,
      [
        const Color(0xFF0D1B2A), // Dark blue-gray at center
        const Color(0xFF0A1628), // Darker at edges
        const Color(0xFF050A10), // Almost black at far edges
      ],
      [0.0, 0.5, 1.0],
    );

    final paint = Paint()..shader = gradient;
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), paint);
  }

  void _drawStars(Canvas canvas, Size size) {
    final random = Random(42); // Consistent seed
    final paint = Paint()..color = Colors.white;
    
    // Draw 200 random stars
    for (int i = 0; i < 200; i++) {
      final x = random.nextDouble() * size.width;
      final y = random.nextDouble() * size.height;
      final radius = random.nextDouble() * 1.5;
      final alpha = random.nextDouble() * 0.5 + 0.1;
      
      paint.color = Colors.white.withValues(alpha: alpha);
      canvas.drawCircle(Offset(x, y), radius, paint);
    }
  }

  void _drawSectorNebula(
    Canvas canvas,
    Offset center,
    SectorEnum sector,
    SectorStyle style,
  ) {
    // Convert angles to radians
    final startAngleRad = (style.baseAngle - 90) * pi / 180; // -90 to start from top
    final sweepAngleRad = style.sweepAngle * pi / 180;

    // Calculate sector path
    final path = Path();

    // Create a pie slice shape
    const innerRadius = 100.0; // Start from center area (leave room for flame)
    final outerRadius = canvasSize / 2 - 200; // Leave margin at edges

    // Move to inner arc start point
    final innerStart = Offset(
      center.dx + innerRadius * cos(startAngleRad),
      center.dy + innerRadius * sin(startAngleRad),
    );
    path.moveTo(innerStart.dx, innerStart.dy);

    // Arc to inner end
    path.arcTo(
      Rect.fromCircle(center: center, radius: innerRadius),
      startAngleRad,
      sweepAngleRad,
      false,
    );

    // Line to outer arc
    final outerEnd = Offset(
      center.dx + outerRadius * cos(startAngleRad + sweepAngleRad),
      center.dy + outerRadius * sin(startAngleRad + sweepAngleRad),
    );
    path.lineTo(outerEnd.dx, outerEnd.dy);

    // Arc back on outer edge (reversed)
    path.arcTo(
      Rect.fromCircle(center: center, radius: outerRadius),
      startAngleRad + sweepAngleRad,
      -sweepAngleRad,
      false,
    );

    // Close the path
    path.close();

    // Create gradient for the sector
    final centerAngle = startAngleRad + sweepAngleRad / 2;
    final gradientCenter = Offset(
      center.dx + (innerRadius + outerRadius) / 3 * cos(centerAngle),
      center.dy + (innerRadius + outerRadius) / 3 * sin(centerAngle),
    );

    final gradient = ui.Gradient.radial(
      gradientCenter,
      outerRadius * 0.8,
      [
        style.primaryColor.withValues(alpha: 0.08),
        style.primaryColor.withValues(alpha: 0.04),
        style.primaryColor.withValues(alpha: 0.01),
        Colors.transparent,
      ],
      [0.0, 0.3, 0.6, 1.0],
    );

    final paint = Paint()
      ..shader = gradient
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 30);

    canvas.drawPath(path, paint);

    // Draw a subtle glow effect at the sector center
    final glowPaint = Paint()
      ..color = style.glowColor.withValues(alpha: 0.03)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 50);

    canvas.drawCircle(gradientCenter, outerRadius * 0.3, glowPaint);
  }

  void _drawSectorLabel(Canvas canvas, Offset center, SectorStyle style) {
    // Calculate label position nearer to center for readability
    final centerAngle = (style.baseAngle + style.sweepAngle / 2 - 90) * pi / 180;
    const labelRadius = 220.0; // Fixed radius for labels, comfortably outside the flame

    final labelPos = Offset(
      center.dx + labelRadius * cos(centerAngle),
      center.dy + labelRadius * sin(centerAngle),
    );

    // Create text painter
    final textPainter = TextPainter(
      text: TextSpan(
        text: style.name,
        style: TextStyle(
          color: style.glowColor.withValues(alpha: 0.9), // Higher opacity
          fontSize: 16, // Smaller but clearer
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
          shadows: [
            Shadow(
              color: Colors.black.withValues(alpha: 0.8),
              blurRadius: 4,
            ),
            Shadow(
              color: style.primaryColor,
              blurRadius: 8,
            ),
          ],
        ),
      ),
      textDirection: TextDirection.ltr,
    );

    textPainter.layout();

    // Draw text horizontally (no rotation)
    textPainter.paint(
      canvas,
      Offset(labelPos.dx - textPainter.width / 2, labelPos.dy - textPainter.height / 2),
    );
  }

  @override
  bool shouldRepaint(covariant SectorBackgroundPainter oldDelegate) {
    return oldDelegate.canvasSize != canvasSize;
  }
}
