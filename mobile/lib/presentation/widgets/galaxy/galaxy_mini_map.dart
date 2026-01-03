import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

class GalaxyMiniMap extends StatelessWidget {

  const GalaxyMiniMap({
    required this.transformationController,
    required this.canvasSize,
    required this.screenSize,
    super.key,
    this.minimapSize = 120.0,
  });
  final TransformationController transformationController;
  final double canvasSize;
  final Size screenSize;
  final double minimapSize;

  @override
  Widget build(BuildContext context) => Container(
      width: minimapSize,
      height: minimapSize,
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.brandPrimary24),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: CustomPaint(
          painter: _MiniMapPainter(
            listenable: transformationController,
            canvasSize: canvasSize,
            screenSize: screenSize,
          ),
        ),
      ),
    );
}

class _MiniMapPainter extends CustomPainter {

  _MiniMapPainter({
    required this.listenable,
    required this.canvasSize,
    required this.screenSize,
  }) : super(repaint: listenable);
  final double canvasSize;
  final Size screenSize;
  final TransformationController listenable;

  @override
  void paint(Canvas canvas, Size size) {
    final scale = size.width / canvasSize;
    final center = Offset(size.width / 2, size.height / 2);

    // 1. Draw Sectors (Simplified)
    _drawSectors(canvas, center, size.width / 2);

    // 2. Draw Viewport Rect
    _drawViewport(canvas, size, scale);
  }

  void _drawSectors(Canvas canvas, Offset center, double radius) {
    final paint = Paint()..style = PaintingStyle.fill;
    
    for (final entry in SectorConfig.styles.entries) {
      final style = entry.value;
      paint.color = style.primaryColor.withValues(alpha: 0.3);
      
      final startAngle = (style.baseAngle - 90) * 3.14159 / 180;
      final sweepAngle = style.sweepAngle * 3.14159 / 180;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweepAngle,
        true,
        paint,
      );
    }
  }

  void _drawViewport(Canvas canvas, Size size, double scale) {
    final matrix = listenable.value;
    final minimapScale = size.width / canvasSize; // e.g. 120 / 4000 = 0.03

    // Use the actual screen size passed from parent
    final screenWidth = screenSize.width;
    final screenHeight = screenSize.height;

    // Handle edge case: if screen size is zero or invalid, use fallback
    if (screenWidth <= 0 || screenHeight <= 0) {
      // Fallback to minimap-based estimation (original logic)
      final fallbackWidth = size.width * 2;
      final fallbackHeight = size.height * 2;
      _drawViewportWithSize(canvas, size, minimapScale, matrix, fallbackWidth, fallbackHeight);
      return;
    }

    _drawViewportWithSize(canvas, size, minimapScale, matrix, screenWidth, screenHeight);
  }

  void _drawViewportWithSize(
    Canvas canvas,
    Size size,
    double minimapScale,
    Matrix4 matrix,
    double screenWidth,
    double screenHeight,
  ) {
    final inverseMatrix = matrix.clone()..invert();
    
    final topLeft = MatrixUtils.transformPoint(inverseMatrix, Offset.zero);
    final topRight = MatrixUtils.transformPoint(inverseMatrix, Offset(screenWidth, 0));
    final bottomLeft = MatrixUtils.transformPoint(inverseMatrix, Offset(0, screenHeight));
    final bottomRight = MatrixUtils.transformPoint(inverseMatrix, Offset(screenWidth, screenHeight));
    
    // Compute bounding box
    final minX = math.min(math.min(topLeft.dx, topRight.dx), math.min(bottomLeft.dx, bottomRight.dx));
    final maxX = math.max(math.max(topLeft.dx, topRight.dx), math.max(bottomLeft.dx, bottomRight.dx));
    final minY = math.min(math.min(topLeft.dy, topRight.dy), math.min(bottomLeft.dy, bottomRight.dy));
    final maxY = math.max(math.max(topLeft.dy, topRight.dy), math.max(bottomLeft.dy, bottomRight.dy));
    
    // Create rectangle in canvas coordinates
    final rect = Rect.fromLTRB(minX, minY, maxX, maxY);
    
    // Scale to minimap coordinates
    final miniRect = Rect.fromLTRB(
      rect.left * minimapScale,
      rect.top * minimapScale,
      rect.right * minimapScale,
      rect.bottom * minimapScale,
    );

    // Draw viewport rectangle
    final viewportPaint = Paint()
      ..color = DS.brandPrimary.withValues(alpha: 0.8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    canvas.drawRect(miniRect, viewportPaint);
  }

  @override
  bool shouldRepaint(covariant _MiniMapPainter oldDelegate) =>
      oldDelegate.listenable != listenable ||
      oldDelegate.canvasSize != canvasSize ||
      oldDelegate.screenSize != screenSize;
}
