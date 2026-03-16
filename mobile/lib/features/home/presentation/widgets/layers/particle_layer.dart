import 'dart:math';
import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// 粒子层 - 渲染用户选择的粒子效果
class ParticleLayer extends StatefulWidget {
  const ParticleLayer({
    super.key,
    this.element,
    required this.particleAnimation,
    required this.mainAnimation,
  });

  final VisualElementModel? element;
  final Animation<double> particleAnimation;
  final Animation<double> mainAnimation;

  @override
  State<ParticleLayer> createState() => _ParticleLayerState();
}

class _ParticleLayerState extends State<ParticleLayer> {
  late List<_Particle> _particles;
  final Random _random = Random(42);

  @override
  void initState() {
    super.initState();
    _initParticles();
  }

  @override
  void didUpdateWidget(ParticleLayer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.element?.id != widget.element?.id) {
      _initParticles();
    }
  }

  void _initParticles() {
    if (widget.element == null) {
      _particles = [];
      return;
    }

    final config = widget.element!.config;
    final count = config['count'] as int? ?? 50;
    final minSize = (config['min_size'] as num?)?.toDouble() ?? 1.0;
    final maxSize = (config['max_size'] as num?)?.toDouble() ?? 3.0;
    final fallDirection = config['fall_direction'] as String?;

    _particles = List.generate(count, (i) {
      return _Particle(
        x: _random.nextDouble(),
        y: _random.nextDouble(),
        size: minSize + _random.nextDouble() * (maxSize - minSize),
        speed: 0.3 + _random.nextDouble() * 0.7,
        drift: _random.nextDouble() * 2 - 1,
        opacity: 0.3 + _random.nextDouble() * 0.7,
        twinkleSpeed: 0.5 + _random.nextDouble() * 1.5,
        twinkleOffset: _random.nextDouble() * 2 * pi,
        rotation: _random.nextDouble() * 2 * pi,
        fallDirection: fallDirection,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    if (widget.element == null) {
      return const SizedBox.shrink();
    }

    final config = widget.element!.config;
    final shape = config['shape'] as String? ?? 'circle';
    final colors = (config['colors'] as List<dynamic>?)
            ?.map((c) => _parseColor(c as String))
            .toList() ??
        [Colors.white];
    final twinkle = config['twinkle'] as bool? ?? false;
    final drift = config['drift'] as bool? ?? true;
    final speed = (config['speed'] as num?)?.toDouble() ?? 1.0;

    return AnimatedBuilder(
      animation: Listenable.merge([
        widget.particleAnimation,
        widget.mainAnimation,
      ]),
      builder: (context, child) {
        return CustomPaint(
          size: Size.infinite,
          painter: _ParticlePainter(
            particles: _particles,
            colors: colors,
            shape: shape,
            twinkle: twinkle,
            drift: drift,
            speed: speed,
            particleValue: widget.particleAnimation.value,
            mainValue: widget.mainAnimation.value,
          ),
        );
      },
    );
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

class _Particle {
  _Particle({
    required this.x,
    required this.y,
    required this.size,
    required this.speed,
    required this.drift,
    required this.opacity,
    required this.twinkleSpeed,
    required this.twinkleOffset,
    required this.rotation,
    this.fallDirection,
  });

  double x;
  double y;
  final double size;
  final double speed;
  final double drift;
  final double opacity;
  final double twinkleSpeed;
  final double twinkleOffset;
  final double rotation;
  final String? fallDirection;
}

class _ParticlePainter extends CustomPainter {
  _ParticlePainter({
    required this.particles,
    required this.colors,
    required this.shape,
    required this.twinkle,
    required this.drift,
    required this.speed,
    required this.particleValue,
    required this.mainValue,
  });

  final List<_Particle> particles;
  final List<Color> colors;
  final String shape;
  final bool twinkle;
  final bool drift;
  final double speed;
  final double particleValue;
  final double mainValue;

  @override
  void paint(Canvas canvas, Size size) {
    for (var i = 0; i < particles.length; i++) {
      final particle = particles[i];

      // 计算当前位置
      double x = particle.x * size.width;
      double y = particle.y * size.height;

      // 应用漂移
      if (drift) {
        x += particle.drift * 30 * sin(particleValue * 2 * pi + i);
      }

      // 应用下落/上升方向
      if (particle.fallDirection != null) {
        final fallSpeed = speed * particle.speed;
        if (particle.fallDirection == 'down') {
          y = (particle.y + particleValue * fallSpeed) % 1.0 * size.height;
        } else if (particle.fallDirection == 'up') {
          y = (1.0 - (particle.y + particleValue * fallSpeed) % 1.0) * size.height;
        }
      }

      // 计算透明度（闪烁效果）
      double opacity = particle.opacity;
      if (twinkle) {
        final twinkleValue = sin(mainValue * 2 * pi * particle.twinkleSpeed +
            particle.twinkleOffset);
        opacity *= 0.5 + twinkleValue * 0.5;
      }

      final color = colors[i % colors.length].withValues(alpha: opacity);
      final paint = Paint()..color = color;

      // 绘制不同形状
      switch (shape) {
        case 'star':
          _drawStar(canvas, Offset(x, y), particle.size, paint);
        case 'petal':
          _drawPetal(canvas, Offset(x, y), particle.size, paint, particle.rotation);
        case 'snowflake':
          _drawSnowflake(canvas, Offset(x, y), particle.size, paint);
        case 'square':
          canvas.drawRect(
            Rect.fromCenter(
              center: Offset(x, y),
              width: particle.size,
              height: particle.size,
            ),
            paint,
          );
        case 'circle':
        default:
          canvas.drawCircle(Offset(x, y), particle.size, paint);
      }
    }
  }

  void _drawStar(Canvas canvas, Offset center, double size, Paint paint) {
    final path = Path();
    const points = 5;
    const innerRadius = 0.4;

    for (var i = 0; i < points * 2; i++) {
      final radius = i.isEven ? size : size * innerRadius;
      final angle = (i * pi / points) - pi / 2;
      final x = center.dx + cos(angle) * radius;
      final y = center.dy + sin(angle) * radius;

      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    path.close();

    canvas.drawPath(path, paint);
  }

  void _drawPetal(Canvas canvas, Offset center, double size, Paint paint, double rotation) {
    final path = Path();
    final angle = rotation;

    // 绘制花瓣形状
    path.moveTo(center.dx, center.dy);
    path.quadraticBezierTo(
      center.dx + cos(angle) * size * 0.5 + cos(angle + pi / 2) * size * 0.3,
      center.dy + sin(angle) * size * 0.5 + sin(angle + pi / 2) * size * 0.3,
      center.dx + cos(angle) * size,
      center.dy + sin(angle) * size,
    );
    path.quadraticBezierTo(
      center.dx + cos(angle) * size * 0.5 - cos(angle + pi / 2) * size * 0.3,
      center.dy + sin(angle) * size * 0.5 - sin(angle + pi / 2) * size * 0.3,
      center.dx,
      center.dy,
    );

    canvas.drawPath(path, paint);
  }

  void _drawSnowflake(Canvas canvas, Offset center, double size, Paint paint) {
    for (var i = 0; i < 6; i++) {
      final angle = i * pi / 3;
      final x = center.dx + cos(angle) * size;
      final y = center.dy + sin(angle) * size;
      canvas.drawLine(center, Offset(x, y), paint..strokeWidth = 1);
    }
  }

  @override
  bool shouldRepaint(covariant _ParticlePainter oldDelegate) {
    return particleValue != oldDelegate.particleValue ||
        mainValue != oldDelegate.mainValue;
  }
}
