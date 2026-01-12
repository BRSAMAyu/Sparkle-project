import 'package:flutter/material.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_render_engine.dart';

class GalaxyShaderBackground extends StatelessWidget {
  const GalaxyShaderBackground({
    required this.engine,
    super.key,
  });

  final GalaxyRenderEngine engine;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: Listenable.merge([
          engine.isReady,
          engine.frameTick,
          engine.settings,
        ]),
        builder: (context, child) {
          if (!engine.hasShader) {
            engine.logFallbackOnce();
            return const SizedBox.shrink();
          }

          return LayoutBuilder(
            builder: (context, constraints) {
              final size = Size(constraints.maxWidth, constraints.maxHeight);
              if (size.width <= 0 || size.height <= 0) {
                return const SizedBox.shrink();
              }

              final renderScale = engine.settings.value.renderScale;
              final scaledSize = Size(
                size.width * renderScale,
                size.height * renderScale,
              );

              final paint = CustomPaint(
                size: scaledSize,
                painter: _GalaxyShaderPainter(engine: engine),
              );

              if (renderScale >= 0.99) {
                return paint;
              }

              return Transform.scale(
                scale: 1 / renderScale,
                alignment: Alignment.topLeft,
                transformHitTests: false,
                child: RepaintBoundary(
                  child: SizedBox(
                    width: scaledSize.width,
                    height: scaledSize.height,
                    child: paint,
                  ),
                ),
              );
            },
          );
        },
      );
}

class _GalaxyShaderPainter extends CustomPainter {
  _GalaxyShaderPainter({required this.engine})
      : super(repaint: engine.frameTick);

  final GalaxyRenderEngine engine;

  @override
  void paint(Canvas canvas, Size size) {
    final fieldShader = engine.fieldShader;
    final burstShader = engine.burstShader;
    if (fieldShader == null || burstShader == null) return;

    engine.applyUniforms(
      fieldShader: fieldShader,
      burstShader: burstShader,
      size: size,
    );

    final fieldPaint = Paint()..shader = fieldShader;
    canvas.drawRect(Offset.zero & size, fieldPaint);

    final burstPaint = Paint()
      ..shader = burstShader
      ..blendMode = BlendMode.plus;
    canvas.drawRect(Offset.zero & size, burstPaint);
  }

  @override
  bool shouldRepaint(covariant _GalaxyShaderPainter oldDelegate) =>
      oldDelegate.engine != engine;
}
