import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

class GalaxyMiniMap extends StatelessWidget {

  const GalaxyMiniMap({
    required this.transformationController, required this.canvasSize, super.key,
    this.minimapSize = 120.0,
  });
  final TransformationController transformationController;
  final double canvasSize;
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
          ),
        ),
      ),
    );
}

class _MiniMapPainter extends CustomPainter {

  _MiniMapPainter({
    required this.listenable,
    required this.canvasSize,
  }) : super(repaint: listenable);
  final double canvasSize;
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
    // Matrix:
    // [s, 0, 0, tx]
    // [0, s, 0, ty]
    
    // The canvas is 4000x4000.
    // Viewport rectangle in MiniMap space (0..120):
    
    final minimapScale = size.width / canvasSize; // e.g. 120 / 4000 = 0.03

    // We need to invert the matrix to find where the screen corners land on the canvas
    final inverseMatrix = matrix.clone()..invert();
    
    // We assume a standard mobile screen size for the viewport rect size if we don't have it
    // Let's use a fixed "Screen Size" constant or try to deduce it.
    // Using a fixed reference size (e.g. 390x844) is better than nothing.
    const mockScreenWidth = 390.0;
    const mockScreenHeight = 844.0;
    
    final topLeft = MatrixUtils.transformPoint(inverseMatrix, Offset.zero);
    final bottomRight = MatrixUtils.transformPoint(inverseMatrix, const Offset(mockScreenWidth, mockScreenHeight));
    
    final rect = Rect.fromPoints(topLeft, bottomRight);
    
    // Draw the rect scaled down to minimap
    final miniRect = Rect.fromLTRB(
      rect.left * minimapScale,
      rect.top * minimapScale,
      rect.right * minimapScale,
      rect.bottom * minimapScale,
    );
    
    final paint = Paint()
      ..color = DS.brandPrimary
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
      
    canvas.drawRect(miniRect, paint);
    
    // Fill with very light white
    paint
      ..color = DS.brandPrimary.withValues(alpha: 0.1)
      ..style = PaintingStyle.fill;
    canvas.drawRect(miniRect, paint);
  }

  @override
  bool shouldRepaint(covariant _MiniMapPainter oldDelegate) => oldDelegate.listenable != listenable;
}
