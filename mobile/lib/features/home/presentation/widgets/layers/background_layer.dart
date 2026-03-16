import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// 背景层 - 渲染用户选择的背景
class BackgroundLayer extends StatelessWidget {
  const BackgroundLayer({
    super.key,
    this.element,
    required this.mainAnimation,
  });

  final VisualElementModel? element;
  final Animation<double> mainAnimation;

  @override
  Widget build(BuildContext context) {
    // 如果没有装备背景，使用默认深色渐变
    if (element == null) {
      return _buildDefaultBackground();
    }

    final config = element!.config;
    return _buildBackgroundFromConfig(config);
  }

  Widget _buildDefaultBackground() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFF0a0a1a),
            Color(0xFF1a1a2e),
            Color(0xFF16213e),
          ],
        ),
      ),
    );
  }

  Widget _buildBackgroundFromConfig(Map<String, dynamic> config) {
    // 解析渐变配置
    final gradientConfig = config['gradient'] as Map<String, dynamic>?;
    final texture = config['texture'] as String?;
    final auroraColors = config['aurora_colors'] as List<dynamic>?;
    final nebulaColors = config['nebula_colors'] as List<dynamic>?;
    final neonColors = config['neon_colors'] as List<dynamic>?;

    return Stack(
      children: [
        // 基础渐变背景
        if (gradientConfig != null)
          Container(
            decoration: BoxDecoration(
              gradient: _buildGradient(gradientConfig),
            ),
          ),

        // 极光效果
        if (auroraColors != null && auroraColors.isNotEmpty)
          _buildAuroraEffect(auroraColors),

        // 星云效果
        if (nebulaColors != null && nebulaColors.isNotEmpty)
          _buildNebulaEffect(nebulaColors),

        // 霓虹效果
        if (neonColors != null && neonColors.isNotEmpty)
          _buildNeonEffect(neonColors),

        // 纹理叠加
        if (texture != null) _buildTextureOverlay(texture),
      ],
    );
  }

  LinearGradient _buildGradient(Map<String, dynamic> config) {
    final colors = (config['colors'] as List<dynamic>)
        .map((c) => _parseColor(c as String))
        .toList();

    final begin = _parseAlignment(config['begin'] as String? ?? 'topCenter');
    final end = _parseAlignment(config['end'] as String? ?? 'bottomCenter');

    return LinearGradient(
      begin: begin,
      end: end,
      colors: colors,
    );
  }

  Widget _buildAuroraEffect(List<dynamic> colors) {
    return AnimatedBuilder(
      animation: mainAnimation,
      builder: (context, child) {
        return CustomPaint(
          size: Size.infinite,
          painter: _AuroraPainter(
            colors: colors.map((c) => _parseColor(c as String)).toList(),
            animationValue: mainAnimation.value,
          ),
        );
      },
    );
  }

  Widget _buildNebulaEffect(List<dynamic> colors) {
    return AnimatedBuilder(
      animation: mainAnimation,
      builder: (context, child) {
        return CustomPaint(
          size: Size.infinite,
          painter: _NebulaPainter(
            colors: colors.map((c) => _parseColor(c as String)).toList(),
            animationValue: mainAnimation.value,
          ),
        );
      },
    );
  }

  Widget _buildNeonEffect(List<dynamic> colors) {
    return AnimatedBuilder(
      animation: mainAnimation,
      builder: (context, child) {
        return CustomPaint(
          size: Size.infinite,
          painter: _NeonPainter(
            colors: colors.map((c) => _parseColor(c as String)).toList(),
            animationValue: mainAnimation.value,
          ),
        );
      },
    );
  }

  Widget _buildTextureOverlay(String texture) {
    // TODO: 实现纹理叠加
    return const SizedBox.shrink();
  }

  Color _parseColor(String hexColor) {
    final buffer = StringBuffer();
    if (hexColor.length == 6 || hexColor.length == 7) {
      buffer.write('ff');
    }
    buffer.write(hexColor.replaceFirst('#', ''));
    return Color(int.parse(buffer.toString(), radix: 16));
  }

  Alignment _parseAlignment(String value) {
    return switch (value) {
      'topLeft' => Alignment.topLeft,
      'topCenter' => Alignment.topCenter,
      'topRight' => Alignment.topRight,
      'centerLeft' => Alignment.centerLeft,
      'center' => Alignment.center,
      'centerRight' => Alignment.centerRight,
      'bottomLeft' => Alignment.bottomLeft,
      'bottomCenter' => Alignment.bottomCenter,
      'bottomRight' => Alignment.bottomRight,
      _ => Alignment.topCenter,
    };
  }
}

// ========== Custom Painters ==========

class _AuroraPainter extends CustomPainter {
  _AuroraPainter({
    required this.colors,
    required this.animationValue,
  });

  final List<Color> colors;
  final double animationValue;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..blendMode = BlendMode.plus;

    for (var i = 0; i < colors.length; i++) {
      final offset = (animationValue + i * 0.33) % 1.0;
      final x = size.width * (0.2 + offset * 0.6);
      final y = size.height * (0.1 + (i % 2) * 0.1);

      paint.shader = RadialGradient(
        colors: [
          colors[i].withValues(alpha: 0.15),
          colors[i].withValues(alpha: 0.05),
          colors[i].withValues(alpha: 0.0),
        ],
        stops: const [0.0, 0.5, 1.0],
      ).createShader(Rect.fromCircle(
        center: Offset(x, y),
        radius: size.width * 0.4,
      ));

      canvas.drawRect(
        Rect.fromLTWH(0, 0, size.width, size.height),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _AuroraPainter oldDelegate) {
    return animationValue != oldDelegate.animationValue;
  }
}

class _NebulaPainter extends CustomPainter {
  _NebulaPainter({
    required this.colors,
    required this.animationValue,
  });

  final List<Color> colors;
  final double animationValue;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..blendMode = BlendMode.plus;

    for (var i = 0; i < colors.length; i++) {
      final offset = (animationValue * 0.5 + i * 0.25) % 1.0;
      final x = size.width * (0.3 + offset * 0.4);
      final y = size.height * (0.3 + (i % 2) * 0.2);

      paint.shader = RadialGradient(
        colors: [
          colors[i].withValues(alpha: 0.1),
          colors[i].withValues(alpha: 0.05),
          colors[i].withValues(alpha: 0.0),
        ],
        stops: const [0.0, 0.6, 1.0],
      ).createShader(Rect.fromCircle(
        center: Offset(x, y),
        radius: size.width * 0.5,
      ));

      canvas.drawRect(
        Rect.fromLTWH(0, 0, size.width, size.height),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _NebulaPainter oldDelegate) {
    return animationValue != oldDelegate.animationValue;
  }
}

class _NeonPainter extends CustomPainter {
  _NeonPainter({
    required this.colors,
    required this.animationValue,
  });

  final List<Color> colors;
  final double animationValue;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..blendMode = BlendMode.plus
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    for (var i = 0; i < colors.length; i++) {
      final offset = (animationValue + i * 0.33) % 1.0;
      final alpha = 0.1 + offset * 0.1;

      paint.color = colors[i].withValues(alpha: alpha);

      // 绘制霓虹线条
      final path = Path();
      final startX = size.width * 0.1;
      final endX = size.width * 0.9;
      final baseY = size.height * (0.1 + i * 0.2);

      path.moveTo(startX, baseY);

      for (var x = startX; x < endX; x += 20) {
        final y = baseY + (x - startX) * 0.05 * ((i % 2) * 2 - 1);
        path.lineTo(x, y);
      }

      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _NeonPainter oldDelegate) {
    return animationValue != oldDelegate.animationValue;
  }
}
