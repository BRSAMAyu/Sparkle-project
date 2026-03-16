import 'dart:math';
import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// 特效层 - 渲染用户选择的特效
class EffectLayer extends StatelessWidget {
  const EffectLayer({
    super.key,
    this.element,
    required this.mainAnimation,
  });

  final VisualElementModel? element;
  final Animation<double> mainAnimation;

  @override
  Widget build(BuildContext context) {
    // 如果没有装备特效，使用默认柔光
    if (element == null) {
      return _buildDefaultEffect();
    }

    final config = element!.config;
    final effectType = config['effect_type'] as String? ?? 'pulse_glow';

    return AnimatedBuilder(
      animation: mainAnimation,
      builder: (context, child) {
        return CustomPaint(
          size: Size.infinite,
          painter: _getEffectPainter(effectType, config),
        );
      },
    );
  }

  Widget _buildDefaultEffect() {
    return AnimatedBuilder(
      animation: mainAnimation,
      builder: (context, child) {
        return CustomPaint(
          size: Size.infinite,
          painter: _PulseGlowPainter(
            intensity: 0.3,
            color: const Color(0xFFFFFFFF),
            position: 'center',
            radius: 200,
            animationValue: mainAnimation.value,
          ),
        );
      },
    );
  }

  CustomPainter _getEffectPainter(String effectType, Map<String, dynamic> config) {
    final intensity = (config['intensity'] as num?)?.toDouble() ?? 0.5;
    final speed = (config['speed'] as num?)?.toDouble() ?? 1.0;
    final color = _parseColor(config['color'] as String? ?? '#FFFFFF');
    final position = config['position'] as String? ?? 'center';
    final radius = (config['radius'] as num?)?.toDouble() ?? 150.0;

    final animatedValue = (mainAnimation.value * speed) % 1.0;

    switch (effectType) {
      case 'pulse_ring':
        return _PulseRingPainter(
          intensity: intensity,
          color: color,
          position: position,
          radius: radius,
          ringCount: config['ring_count'] as int? ?? 3,
          animationValue: animatedValue,
        );

      case 'gravity_wave':
        return _GravityWavePainter(
          intensity: intensity,
          color: color,
          position: position,
          waveCount: config['wave_count'] as int? ?? 5,
          waveInterval: (config['wave_interval'] as num?)?.toDouble() ?? 2.0,
          animationValue: animatedValue,
        );

      case 'supernova':
        return _SupernovaPainter(
          intensity: intensity,
          color: color,
          position: position,
          animationValue: animatedValue,
        );

      case 'pulse_glow':
      default:
        return _PulseGlowPainter(
          intensity: intensity,
          color: color,
          position: position,
          radius: radius,
          animationValue: animatedValue,
        );
    }
  }

  Color _parseColor(String hexColor) {
    final buffer = StringBuffer();
    if (hexColor.length == 6 || hexColor.length == 7) {
      buffer.write('ff');
    }
    buffer.write(hexColor.replaceFirst('#', ''));
    return Color(int.parse(buffer.toString(), radix: 16));
  }
}

// ========== Effect Painters ==========

class _PulseGlowPainter extends CustomPainter {
  _PulseGlowPainter({
    required this.intensity,
    required this.color,
    required this.position,
    required this.radius,
    required this.animationValue,
  });

  final double intensity;
  final Color color;
  final String position;
  final double radius;
  final double animationValue;

  @override
  void paint(Canvas canvas, Size size) {
    final center = _getPosition(size);
    final pulseRadius = radius * (0.8 + animationValue * 0.4);

    final paint = Paint()
      ..shader = RadialGradient(
        colors: [
          color.withValues(alpha: intensity * 0.2),
          color.withValues(alpha: intensity * 0.1),
          color.withValues(alpha: 0.0),
        ],
        stops: const [0.0, 0.5, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: pulseRadius));

    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height),
      paint,
    );
  }

  Offset _getPosition(Size size) {
    return switch (position) {
      'top-right' => Offset(size.width * 0.8, size.height * 0.2),
      'top-left' => Offset(size.width * 0.2, size.height * 0.2),
      'bottom-right' => Offset(size.width * 0.8, size.height * 0.8),
      'bottom-left' => Offset(size.width * 0.2, size.height * 0.8),
      'center' => Offset(size.width / 2, size.height / 2),
      _ => Offset(size.width / 2, size.height / 2),
    };
  }

  @override
  bool shouldRepaint(covariant _PulseGlowPainter oldDelegate) {
    return animationValue != oldDelegate.animationValue;
  }
}

class _PulseRingPainter extends CustomPainter {
  _PulseRingPainter({
    required this.intensity,
    required this.color,
    required this.position,
    required this.radius,
    required this.ringCount,
    required this.animationValue,
  });

  final double intensity;
  final Color color;
  final String position;
  final double radius;
  final int ringCount;
  final double animationValue;

  @override
  void paint(Canvas canvas, Size size) {
    final center = _getPosition(size);

    for (var i = 0; i < ringCount; i++) {
      final ringProgress = (animationValue + i / ringCount) % 1.0;
      final ringRadius = radius * (0.5 + ringProgress * 0.5);
      final alpha = intensity * (1.0 - ringProgress) * 0.3;

      final paint = Paint()
        ..color = color.withValues(alpha: alpha)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0;

      canvas.drawCircle(center, ringRadius, paint);
    }
  }

  Offset _getPosition(Size size) {
    return switch (position) {
      'top-right' => Offset(size.width * 0.8, size.height * 0.2),
      'center' => Offset(size.width / 2, size.height / 2),
      _ => Offset(size.width / 2, size.height / 2),
    };
  }

  @override
  bool shouldRepaint(covariant _PulseRingPainter oldDelegate) {
    return animationValue != oldDelegate.animationValue;
  }
}

class _GravityWavePainter extends CustomPainter {
  _GravityWavePainter({
    required this.intensity,
    required this.color,
    required this.position,
    required this.waveCount,
    required this.waveInterval,
    required this.animationValue,
  });

  final double intensity;
  final Color color;
  final String position;
  final int waveCount;
  final double waveInterval;
  final double animationValue;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width * 0.6;

    for (var i = 0; i < waveCount; i++) {
      final waveProgress = (animationValue * waveInterval + i / waveCount) % 1.0;
      final waveRadius = maxRadius * waveProgress;
      final alpha = intensity * (1.0 - waveProgress) * 0.15;

      final paint = Paint()
        ..color = color.withValues(alpha: alpha)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.0 + waveProgress * 2.0;

      canvas.drawCircle(center, waveRadius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _GravityWavePainter oldDelegate) {
    return animationValue != oldDelegate.animationValue;
  }
}

class _SupernovaPainter extends CustomPainter {
  _SupernovaPainter({
    required this.intensity,
    required this.color,
    required this.position,
    required this.animationValue,
  });

  final double intensity;
  final Color color;
  final String position;
  final double animationValue;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);

    // 核心光芒
    final corePaint = Paint()
      ..shader = RadialGradient(
        colors: [
          color.withValues(alpha: intensity * 0.4),
          color.withValues(alpha: intensity * 0.2),
          color.withValues(alpha: 0.0),
        ],
      ).createShader(Rect.fromCircle(
        center: center,
        radius: 100 + animationValue * 50,
      ));

    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height),
      corePaint,
    );

    // 射线
    final rayPaint = Paint()
      ..color = color.withValues(alpha: intensity * 0.2)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    for (var i = 0; i < 12; i++) {
      final angle = i * pi / 6 + animationValue * pi / 6;
      final rayLength = 150 + animationValue * 100;

      canvas.drawLine(
        center,
        Offset(
          center.dx + cos(angle) * rayLength,
          center.dy + sin(angle) * rayLength,
        ),
        rayPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _SupernovaPainter oldDelegate) {
    return animationValue != oldDelegate.animationValue;
  }
}
