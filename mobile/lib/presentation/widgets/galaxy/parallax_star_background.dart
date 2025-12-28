import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class ParallaxStarBackground extends StatelessWidget {

  const ParallaxStarBackground({
    required this.transformationController, super.key,
  });
  final TransformationController transformationController;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
      animation: transformationController,
      builder: (context, child) {
        // Invert the translation to simulate background moving slower than foreground
        // When we pan RIGHT (content moves right), we want background to move RIGHT but slower?
        // Actually, InteractiveViewer moves the viewport. 
        // If we pan right, we are looking left? No.
        // InteractiveViewer uses a matrix. The translation (tx, ty) is the offset of the content.
        // If tx = -100, the content is shifted left by 100.
        // We want the background to shift left by 10 (0.1 factor).
        
        final matrix = transformationController.value;
        final tx = matrix.getTranslation().x;
        final ty = matrix.getTranslation().y;
        final scale = matrix.getMaxScaleOnAxis();

        return CustomPaint(
          painter: _ParallaxLayersPainter(
            offsetX: tx,
            offsetY: ty,
            scale: scale,
          ),
          size: Size.infinite,
        );
      },
    );
}

class _ParallaxLayersPainter extends CustomPainter {

  _ParallaxLayersPainter({
    required this.offsetX,
    required this.offsetY,
    required this.scale,
  });
  final double offsetX;
  final double offsetY;
  final double scale;

  @override
  void paint(Canvas canvas, Size size) {
    // Fill with deep space void - Radial Gradient
    final center = Offset(size.width / 2, size.height / 2);
    final gradient = ui.Gradient.radial(
      center,
      math.max(size.width, size.height) * 0.8,
      [
        const Color(0xFF0D1B2A), // Dark blue-gray at center
        const Color(0xFF0A1628), // Darker at edges
        const Color(0xFF050A10), // Almost black at far edges
      ],
      [0.0, 0.5, 1.0],
    );

    final bgPaint = Paint()..shader = gradient;
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), bgPaint);

    // Layer 1: Distant Stars (Slowest, 0.05 factor)
    _drawLayer(canvas, size, 0.05, 150, 0.8, 1.0);

    // Layer 2: Mid Stars (0.15 factor)
    _drawLayer(canvas, size, 0.15, 100, 1.5, 0.6);

    // Layer 3: Near Stars (Fastest, 0.3 factor)
    _drawLayer(canvas, size, 0.3, 50, 2.5, 0.4);
  }

  void _drawLayer(
    Canvas canvas,
    Size size,
    double parallaxFactor,
    int starCount,
    double baseSize,
    double opacityBase,
  ) {
    // We use a fixed seed based on layer index/factor so stars don't jump
    final random = math.Random((parallaxFactor * 1000).toInt());
    final paint = Paint();

    // Calculate the effective offset for this layer
    // We wrap around the screen size to create infinite scrolling illusion
    // using modulo operator.
    
    // Virtual width/height of the star field (larger than screen to allow panning)
    final fieldWidth = size.width; 
    final fieldHeight = size.height;

    final dx = offsetX * parallaxFactor;
    final dy = offsetY * parallaxFactor;

    for (var i = 0; i < starCount; i++) {
      // Original position
      var x = random.nextDouble() * fieldWidth;
      var y = random.nextDouble() * fieldHeight;

      // Apply parallax shift
      x = (x + dx) % fieldWidth;
      y = (y + dy) % fieldHeight;
      
      // Handle negative modulo result in Dart
      if (x < 0) x += fieldWidth;
      if (y < 0) y += fieldHeight;

      // Draw star
      final r = baseSize * (0.8 + random.nextDouble() * 0.4);
      // Scale star size slightly with zoom to give depth feeling (optional)
      // r = r * (0.5 + scale * 0.5); 
      
      paint.color = DS.brandPrimary.withValues(alpha: opacityBase * (0.5 + random.nextDouble() * 0.5));
      canvas.drawCircle(Offset(x, y), r, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _ParallaxLayersPainter oldDelegate) => oldDelegate.offsetX != offsetX ||
        oldDelegate.offsetY != offsetY ||
        oldDelegate.scale != scale;
}
