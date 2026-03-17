import 'dart:math';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/domain/services/emotion_visual_blending_service.dart';

/// 天气层 - 根据用户状态自动显示天气效果
///
/// 天气层独立于用户选择的场景，作为半透明叠加层
class WeatherLayer extends StatefulWidget {
  const WeatherLayer({
    super.key,
    required this.weatherType,
    this.weatherCondition,
    required this.blendParams,
    required this.mainAnimation,
    required this.particleAnimation,
  });

  final String weatherType;
  final String? weatherCondition;
  final VisualBlendParams blendParams;
  final Animation<double> mainAnimation;
  final Animation<double> particleAnimation;

  @override
  State<WeatherLayer> createState() => _WeatherLayerState();
}

class _WeatherLayerState extends State<WeatherLayer> {
  late List<_WeatherParticle> _particles;
  final Random _random = Random(42);

  double get _density =>
      widget.blendParams.particleDensity.clamp(0.2, 1.0);

  double get _speedMultiplier =>
      widget.blendParams.animationSpeed.clamp(0.3, 1.8);

  double get _opacityScale {
    final densityScale = (0.5 + _density * 0.6).clamp(0.4, 1.1);
    final moodScale = (0.7 + _speedMultiplier * 0.2).clamp(0.6, 1.1);
    return (densityScale * moodScale).clamp(0.4, 1.2);
  }

  Color get _accentColor {
    final baseColor = Color.lerp(
      DS.brandPrimary,
      widget.blendParams.primaryTint,
      0.45,
    ) ?? DS.brandPrimary;

    // 浅色模式：增加对比度
    final isDark = Theme.of(context).brightness == Brightness.dark;
    if (!isDark) {
      // 浅色模式下使用更深的颜色
      final hsl = HSLColor.fromColor(baseColor);
      return hsl.withLightness(0.35).toColor();
    }
    return baseColor;
  }

  double get _layerOpacity =>
      (0.4 + widget.blendParams.backgroundOpacity * 0.6)
          .clamp(0.35, 0.7);

  @override
  void initState() {
    super.initState();
    _initParticles();
  }

  @override
  void didUpdateWidget(WeatherLayer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.weatherType != widget.weatherType ||
        oldWidget.blendParams.particleDensity !=
            widget.blendParams.particleDensity) {
      _initParticles();
    }
  }

  void _initParticles() {
    switch (widget.weatherType) {
      case 'sunny':
        _particles = _initSunnyParticles();
        break;
      case 'cloudy':
        _particles = _initCloudyParticles();
        break;
      case 'rainy':
        _particles = _initRainyParticles();
        break;
      case 'meteor':
        _particles = _initMeteorParticles();
        break;
      default:
        _particles = _initSunnyParticles();
        break;
    }
  }

  int _scaledCount(int base, {required int min}) {
    final scaled = (base * _density).round();
    return scaled.clamp(min, (base * 2).round());
  }

  List<_WeatherParticle> _initSunnyParticles() {
    final count = _scaledCount(8, min: 4);
    return List.generate(count, (i) {
      return _WeatherParticle(
        x: 0.8 + _random.nextDouble() * 0.2,
        y: 0.1 + _random.nextDouble() * 0.2,
        size: 30.0 + i * 15.0,
        angle: i * pi / 4,
        speed: 0.5 + _random.nextDouble() * 0.5,
      );
    });
  }

  List<_WeatherParticle> _initCloudyParticles() {
    final count = _scaledCount(5, min: 3);
    return List.generate(count, (i) {
      return _WeatherParticle(
        x: _random.nextDouble(),
        y: 0.05 + _random.nextDouble() * 0.25,
        size: 40 + _random.nextDouble() * 60,
        speed: 0.1 + _random.nextDouble() * 0.2,
        opacity: 0.03 + _random.nextDouble() * 0.05,
      );
    });
  }

  List<_WeatherParticle> _initRainyParticles() {
    final count = _scaledCount(40, min: 16);
    return List.generate(count, (i) {
      return _WeatherParticle(
        x: _random.nextDouble(),
        y: -0.1 - _random.nextDouble() * 0.5,
        size: 10 + _random.nextDouble() * 15,
        speed: 0.8 + _random.nextDouble() * 0.4,
        opacity: 0.1 + _random.nextDouble() * 0.15,
      );
    });
  }

  List<_WeatherParticle> _initMeteorParticles() {
    final count = _scaledCount(6, min: 3);
    return List.generate(count, (i) {
      return _WeatherParticle(
        x: 0.2 + _random.nextDouble() * 0.6,
        y: _random.nextDouble() * 0.2,
        size: 30 + _random.nextDouble() * 50,
        speed: 1.5 + _random.nextDouble() * 1.0,
        delay: i * 0.15,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    // 天气层使用半透明叠加
    return Opacity(
      opacity: _layerOpacity,
      child: AnimatedBuilder(
        animation: Listenable.merge([
          widget.mainAnimation,
          widget.particleAnimation,
        ]),
        builder: (context, child) {
          return CustomPaint(
            size: Size.infinite,
            painter: _WeatherPainter(
              weatherType: widget.weatherType,
              particles: _particles,
              accentColor: _accentColor,
              mainValue: widget.mainAnimation.value,
              particleValue: widget.particleAnimation.value,
              speedMultiplier: _speedMultiplier,
              opacityScale: _opacityScale,
            ),
          );
        },
      ),
    );
  }
}

class _WeatherParticle {
  _WeatherParticle({
    this.x = 0,
    this.y = 0,
    this.size = 10,
    this.angle = 0,
    this.speed = 1,
    this.opacity = 0.5,
    this.delay = 0,
  });

  double x;
  double y;
  final double size;
  final double angle;
  final double speed;
  final double opacity;
  final double delay;
}

class _WeatherPainter extends CustomPainter {
  _WeatherPainter({
    required this.weatherType,
    required this.particles,
    required this.accentColor,
    required this.mainValue,
    required this.particleValue,
    required this.speedMultiplier,
    required this.opacityScale,
  });

  final String weatherType;
  final List<_WeatherParticle> particles;
  final Color accentColor;
  final double mainValue;
  final double particleValue;
  final double speedMultiplier;
  final double opacityScale;

  @override
  void paint(Canvas canvas, Size size) {
    switch (weatherType) {
      case 'sunny':
        _paintSunny(canvas, size);
        break;
      case 'cloudy':
        _paintCloudy(canvas, size);
        break;
      case 'rainy':
        _paintRainy(canvas, size);
        break;
      case 'meteor':
        _paintMeteor(canvas, size);
        break;
      default:
        _paintSunny(canvas, size);
        break;
    }
  }

  void _paintSunny(Canvas canvas, Size size) {
    final mainPhase = (mainValue * speedMultiplier) % 1.0;
    final brightnessScale = (0.8 + speedMultiplier * 0.25).clamp(0.7, 1.3);
    // 太阳位置
    final sunCenter = Offset(size.width * 0.85, size.height * 0.15);
    final pulseRadius = 80.0 + mainPhase * 20;

    // 太阳光晕
    final glowPaint = Paint()
      ..shader = RadialGradient(
        colors: [
          accentColor.withValues(alpha: 0.2 * brightnessScale),
          accentColor.withValues(alpha: 0.1 * brightnessScale),
          accentColor.withValues(alpha: 0.0),
        ],
      ).createShader(Rect.fromCircle(center: sunCenter, radius: pulseRadius));

    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height),
      glowPaint,
    );

    // 太阳射线
    for (final particle in particles) {
      final rayPaint = Paint()
        ..color =
            accentColor.withValues(alpha: 0.1 * brightnessScale * opacityScale)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2;

      final rayLength = particle.size * (0.8 + mainPhase * 0.4);
      final angle = particle.angle + mainPhase * 0.1;

      canvas.drawLine(
        sunCenter,
        Offset(
          sunCenter.dx + cos(angle) * rayLength,
          sunCenter.dy + sin(angle) * rayLength,
        ),
        rayPaint,
      );
    }
  }

  void _paintCloudy(Canvas canvas, Size size) {
    final mainPhase = (mainValue * speedMultiplier) % 1.0;
    final particlePhase = (particleValue * speedMultiplier) % 1.0;
    for (final cloud in particles) {
      final x = (cloud.x + particlePhase * cloud.speed) % 1.2 - 0.1;
      final y = cloud.y;
      final opacity =
          cloud.opacity * (0.8 + mainPhase * 0.4) * opacityScale;

      final cloudPaint = Paint()
        ..color = accentColor.withValues(alpha: opacity)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 20);

      // 绘制云朵（多个圆形组成）
      final cloudCenter = Offset(x * size.width, y * size.height);
      canvas.drawCircle(cloudCenter, cloud.size, cloudPaint);
      canvas.drawCircle(
        Offset(cloudCenter.dx - cloud.size * 0.6, cloudCenter.dy + cloud.size * 0.2),
        cloud.size * 0.7,
        cloudPaint,
      );
      canvas.drawCircle(
        Offset(cloudCenter.dx + cloud.size * 0.5, cloudCenter.dy + cloud.size * 0.15),
        cloud.size * 0.6,
        cloudPaint,
      );
    }
  }

  void _paintRainy(Canvas canvas, Size size) {
    final particlePhase = (particleValue * speedMultiplier) % 1.0;
    final dropLengthScale = (0.7 + speedMultiplier * 0.5).clamp(0.6, 1.6);
    for (final drop in particles) {
      final x = drop.x * size.width;
      final y =
          ((drop.y + particlePhase * drop.speed) % 1.2 - 0.1) * size.height;
      final dropLength = drop.size * dropLengthScale;

      final rainPaint = Paint()
        ..color =
            accentColor.withValues(alpha: drop.opacity * opacityScale)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5;

      // 雨滴线条
      canvas.drawLine(
        Offset(x, y),
        Offset(x - 5, y + dropLength),
        rainPaint,
      );
    }
  }

  void _paintMeteor(Canvas canvas, Size size) {
    final particlePhase = (particleValue * speedMultiplier) % 1.0;
    final glowScale = (0.75 + speedMultiplier * 0.35).clamp(0.6, 1.4);
    for (final meteor in particles) {
      final progress = (particlePhase + meteor.delay) % 1.0;
      final x = (meteor.x - progress * 0.5) * size.width;
      final y = (meteor.y + progress * 0.3) * size.height;

      // 流星尾迹
      final trailPaint = Paint()
        ..shader = LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: [
            accentColor.withValues(alpha: 0.5 * glowScale * opacityScale),
            accentColor.withValues(alpha: 0.0),
          ],
        ).createShader(Rect.fromLTWH(
          x - meteor.size,
          y - meteor.size * 0.5,
          meteor.size,
          meteor.size * 0.5,
        ));

      final path = Path();
      path.moveTo(x, y);
      path.lineTo(x + meteor.size, y - meteor.size * 0.3);
      path.lineTo(x + meteor.size * 1.2, y - meteor.size * 0.15);
      path.close();

      canvas.drawPath(path, trailPaint);

      // 流星头部
      final headPaint = Paint()
        ..color =
            accentColor.withValues(alpha: 0.8 * glowScale * opacityScale);
      canvas.drawCircle(Offset(x, y), 2, headPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _WeatherPainter oldDelegate) {
    return mainValue != oldDelegate.mainValue ||
        particleValue != oldDelegate.particleValue ||
        speedMultiplier != oldDelegate.speedMultiplier ||
        opacityScale != oldDelegate.opacityScale ||
        accentColor != oldDelegate.accentColor ||
        weatherType != oldDelegate.weatherType ||
        particles != oldDelegate.particles;
  }
}
