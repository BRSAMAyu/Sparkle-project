import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

/// Widget that renders the background in tiles to avoid texture size limits
class TiledSectorBackground extends StatelessWidget {
  const TiledSectorBackground({
    required this.width,
    required this.height,
    super.key,
  });

  final double width;
  final double height;
  
  static const double _maxTileSize = 2048.0;

  @override
  Widget build(BuildContext context) {
    if (width <= _maxTileSize && height <= _maxTileSize) {
      return RepaintBoundary(
        child: CustomPaint(
          painter: SectorBackgroundPainter(
            totalSize: Size(width, height),
          ),
          size: Size(width, height),
        ),
      );
    }
    
    final cols = (width / _maxTileSize).ceil();
    final rows = (height / _maxTileSize).ceil();
    
    final tileWidth = width / cols;
    final tileHeight = height / rows;

    return Column(
      children: List.generate(rows, (r) => Row(
          children: List.generate(cols, (c) {
             final x = c * tileWidth;
             final y = r * tileHeight;
             return _buildTile(x, y, tileWidth, tileHeight);
          }),
        ),),
    );
  }

  Widget _buildTile(double x, double y, double w, double h) => RepaintBoundary(
      child: CustomPaint(
        size: Size(w, h),
        painter: SectorBackgroundPainter(
          totalSize: Size(width, height),
          offset: Offset(x, y),
        ),
      ),
    );
}

/// Painter for the sector nebula backgrounds
class SectorBackgroundPainter extends CustomPainter {
  SectorBackgroundPainter({
    required this.totalSize,
    this.offset = Offset.zero,
    // Legacy support
    double? canvasSize,
  }) : actualTotalSize = canvasSize != null ? Size(canvasSize, canvasSize) : totalSize;

  final Size totalSize;
  final Size actualTotalSize;
  final Offset offset;

  @override
  void paint(Canvas canvas, Size size) {
    // Save canvas state
    canvas.save();
    // Translate canvas to simulate drawing on the full surface
    // If we are tile (x,y), we shift back by (x,y) so that (0,0) of this canvas
    // corresponds to (x,y) of the virtual full canvas.
    canvas.translate(-offset.dx, -offset.dy);

    final center = Offset(actualTotalSize.width / 2, actualTotalSize.height / 2);

    // Draw each sector's nebula
    for (final entry in SectorConfig.styles.entries) {
      _drawSectorNebula(canvas, center, entry.key, entry.value);
    }

    // Draw sector labels
    for (final entry in SectorConfig.styles.entries) {
      _drawSectorLabel(canvas, center, entry.value);
    }
    
    canvas.restore();
  }

  void _drawSectorNebula(
    Canvas canvas,
    Offset center,
    SectorEnum sector,
    SectorStyle style,
  ) {
    // Convert angles to radians
    final startAngleRad =
        (style.baseAngle - 90) * pi / 180; // -90 to start from top
    final sweepAngleRad = style.sweepAngle * pi / 180;

    // Calculate sector path
    final path = Path();

    // Create a pie slice shape
    const innerRadius = 100.0; // Start from center area (leave room for flame)
    final outerRadius = actualTotalSize.width / 2 - 200; // Leave margin at edges

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
    final centerAngle =
        (style.baseAngle + style.sweepAngle / 2 - 90) * pi / 180;
    const labelRadius =
        220.0; // Fixed radius for labels, comfortably outside the flame

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
              color: DS.brandPrimary.withValues(alpha: 0.8),
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
      Offset(labelPos.dx - textPainter.width / 2,
          labelPos.dy - textPainter.height / 2,),
    );
  }

  @override
  bool shouldRepaint(covariant SectorBackgroundPainter oldDelegate) =>
      oldDelegate.totalSize != totalSize || oldDelegate.offset != offset;
}
