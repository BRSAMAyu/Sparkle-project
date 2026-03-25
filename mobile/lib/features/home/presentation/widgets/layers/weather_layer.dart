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

  double get _density => widget.blendParams.particleDensity.clamp(0.2, 1.0);

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
        ) ??
        DS.brandPrimary;

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
      (0.4 + widget.blendParams.backgroundOpacity * 0.6).clamp(0.35, 0.7);

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
    return List.generate(
      count,
      (i) => _WeatherParticle(
        x: 0.8 + _random.nextDouble() * 0.2,
        y: 0.1 + _random.nextDouble() * 0.2,
        size: 30.0 + i * 15.0,
        angle: i * pi / 4,
        speed: 0.5 + _random.nextDouble() * 0.5,
      ),
    );
  }

  List<_WeatherParticle> _initCloudyParticles() {
    final count = _scaledCount(5, min: 3);
    return List.generate(
      count,
      (i) => _WeatherParticle(
        x: _random.nextDouble(),
        y: 0.05 + _random.nextDouble() * 0.25,
        size: 40 + _random.nextDouble() * 60,
        speed: 0.1 + _random.nextDouble() * 0.2,
        opacity: 0.03 + _random.nextDouble() * 0.05,
      ),
    );
  }

  List<_WeatherParticle> _initRainyParticles() {
    final count = _scaledCount(40, min: 16);
    return List.generate(
      count,
      (i) => _WeatherParticle(
        x: _random.nextDouble(),
        y: -0.1 - _random.nextDouble() * 0.5,
        size: 10 + _random.nextDouble() * 15,
        speed: 0.8 + _random.nextDouble() * 0.4,
        opacity: 0.1 + _random.nextDouble() * 0.15,
      ),
    );
  }

  List<_WeatherParticle> _initMeteorParticles() {
    final count = _scaledCount(6, min: 3);
    return List.generate(
      count,
      (i) => _WeatherParticle(
        x: 0.2 + _random.nextDouble() * 0.6,
        y: _random.nextDouble() * 0.2,
        size: 30 + _random.nextDouble() * 50,
        speed: 1.5 + _random.nextDouble() * 1.0,
        delay: i * 0.15,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // 天气层使用半透明叠加
    return Opacity(
      opacity: _layerOpacity,
      child: RepaintBoundary(
        child: AnimatedBuilder(
          animation: Listenable.merge([
            widget.mainAnimation,
            widget.particleAnimation,
          ]),
          builder: (context, child) => CustomPaint(
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
          ),
        ),
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

class _WeatherPalette {
  _WeatherPalette({
    required this.primary,
    required this.secondary,
    required this.highlight,
    required this.skyColors,
    required this.auraCenter,
    required this.auraRadius,
  });

  final Color primary;
  final Color secondary;
  final Color highlight;
  final List<Color> skyColors;
  final Alignment auraCenter;
  final double auraRadius;
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
    _paintAtmosphere(canvas, size);

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

    _paintForegroundVeil(canvas, size);
  }

  void _paintAtmosphere(Canvas canvas, Size size) {
    final palette = _paletteForWeather();

    final skyWash = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: palette.skyColors,
        stops: const [0.0, 0.48, 1.0],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, skyWash);

    final pulse = 0.88 + sin(mainValue * 2 * pi) * 0.12;
    final auraPaint = Paint()
      ..shader = RadialGradient(
        center: palette.auraCenter,
        radius: palette.auraRadius,
        colors: [
          palette.highlight.withValues(alpha: 0.18 * opacityScale * pulse),
          palette.secondary.withValues(alpha: 0.1 * opacityScale),
          Colors.transparent,
        ],
        stops: const [0.0, 0.45, 1.0],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, auraPaint);
  }

  void _paintForegroundVeil(Canvas canvas, Size size) {
    final palette = _paletteForWeather();
    final veilPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          Colors.transparent,
          palette.secondary.withValues(alpha: 0.03 * opacityScale),
          palette.primary.withValues(alpha: 0.1 * opacityScale),
        ],
        stops: const [0.0, 0.62, 1.0],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, veilPaint);

    if (weatherType == 'rainy' || weatherType == 'cloudy') {
      final horizonPaint = Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.transparent,
            palette.highlight.withValues(alpha: 0.02 * opacityScale),
            palette.highlight.withValues(alpha: 0.1 * opacityScale),
          ],
        ).createShader(
          Rect.fromLTWH(0, size.height * 0.62, size.width, size.height * 0.38),
        );
      canvas.drawRect(
        Rect.fromLTWH(0, size.height * 0.62, size.width, size.height * 0.38),
        horizonPaint,
      );
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

    final pollenPaint = Paint()..style = PaintingStyle.fill;
    for (var i = 0; i < 20; i++) {
      final drift = (particleValue + i * 0.07) % 1.0;
      final x = ((0.15 + i * 0.11) % 1.0) * size.width;
      final y = (0.14 + drift * 0.74) * size.height;
      final radius = 1.5 + (i % 3) * 0.8;
      pollenPaint.color = accentColor.withValues(
        alpha: (0.04 + (i % 4) * 0.015) * opacityScale,
      );
      canvas.drawCircle(
        Offset(x + sin(drift * 2 * pi + i) * 8, y),
        radius,
        pollenPaint,
      );
    }
  }

  void _paintCloudy(Canvas canvas, Size size) {
    final mainPhase = (mainValue * speedMultiplier) % 1.0;
    final particlePhase = (particleValue * speedMultiplier) % 1.0;

    final hazePaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          accentColor.withValues(alpha: 0.04 * opacityScale),
          Colors.transparent,
          accentColor.withValues(alpha: 0.03 * opacityScale),
        ],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, hazePaint);

    for (final cloud in particles) {
      final x = (cloud.x + particlePhase * cloud.speed) % 1.2 - 0.1;
      final y = cloud.y;
      final opacity = cloud.opacity * (0.8 + mainPhase * 0.4) * opacityScale;

      final cloudPaint = Paint()
        ..color = accentColor.withValues(alpha: opacity)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 20);

      // 绘制云朵（多个圆形组成）
      final cloudCenter = Offset(x * size.width, y * size.height);
      canvas.drawCircle(cloudCenter, cloud.size, cloudPaint);
      canvas.drawCircle(
        Offset(cloudCenter.dx - cloud.size * 0.6,
            cloudCenter.dy + cloud.size * 0.2),
        cloud.size * 0.7,
        cloudPaint,
      );
      canvas.drawCircle(
        Offset(cloudCenter.dx + cloud.size * 0.5,
            cloudCenter.dy + cloud.size * 0.15),
        cloud.size * 0.6,
        cloudPaint,
      );
    }

    final mistPaint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 24)
      ..color = accentColor.withValues(alpha: 0.06 * opacityScale);
    for (var i = 0; i < 4; i++) {
      final y = size.height * (0.56 + i * 0.08);
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(size.width * (0.25 + i * 0.18), y),
          width: size.width * 0.62,
          height: 44 + i * 12,
        ),
        mistPaint,
      );
    }
  }

  void _paintRainy(Canvas canvas, Size size) {
    final particlePhase = (particleValue * speedMultiplier) % 1.0;
    final dropLengthScale = (0.7 + speedMultiplier * 0.5).clamp(0.6, 1.6);

    final stormWash = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          accentColor.withValues(alpha: 0.14 * opacityScale),
          accentColor.withValues(alpha: 0.05 * opacityScale),
          Colors.transparent,
        ],
      ).createShader(
        Rect.fromLTWH(0, 0, size.width, size.height * 0.55),
      );
    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height * 0.55),
      stormWash,
    );

    for (final drop in particles) {
      final x = drop.x * size.width;
      final y =
          ((drop.y + particlePhase * drop.speed) % 1.2 - 0.1) * size.height;
      final dropLength = drop.size * dropLengthScale;

      final rainPaint = Paint()
        ..color = accentColor.withValues(alpha: drop.opacity * opacityScale)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5;

      // 雨滴线条
      canvas.drawLine(
        Offset(x, y),
        Offset(x - 5, y + dropLength),
        rainPaint,
      );
    }

    final ripplePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8;
    for (var i = 0; i < 8; i++) {
      final progress = (particleValue * 1.4 + i * 0.13) % 1.0;
      final x = ((0.11 + i * 0.12) % 1.0) * size.width;
      final y = size.height * (0.82 + (i % 3) * 0.045);
      ripplePaint.color = accentColor.withValues(
        alpha: (0.12 - progress * 0.1).clamp(0.0, 0.12) * opacityScale,
      );
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(x, y),
          width: 8 + progress * 26,
          height: 3 + progress * 9,
        ),
        ripplePaint,
      );
    }
  }

  void _paintMeteor(Canvas canvas, Size size) {
    final particlePhase = (particleValue * speedMultiplier) % 1.0;
    final glowScale = (0.75 + speedMultiplier * 0.35).clamp(0.6, 1.4);

    final nebulaPaint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(0.5, -0.2),
        radius: 1.1,
        colors: [
          accentColor.withValues(alpha: 0.14 * opacityScale),
          accentColor.withValues(alpha: 0.05 * opacityScale),
          Colors.transparent,
        ],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, nebulaPaint);

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
        ).createShader(
          Rect.fromLTWH(
            x - meteor.size,
            y - meteor.size * 0.5,
            meteor.size,
            meteor.size * 0.5,
          ),
        );

      final path = Path();
      path.moveTo(x, y);
      path.lineTo(x + meteor.size, y - meteor.size * 0.3);
      path.lineTo(x + meteor.size * 1.2, y - meteor.size * 0.15);
      path.close();

      canvas.drawPath(path, trailPaint);

      // 流星头部
      final headPaint = Paint()
        ..color = accentColor.withValues(alpha: 0.8 * glowScale * opacityScale);
      canvas.drawCircle(Offset(x, y), 2, headPaint);
    }

    final sparkPaint = Paint()..style = PaintingStyle.fill;
    for (var i = 0; i < 18; i++) {
      final orbit = (particleValue + i * 0.09) % 1.0;
      final x = ((0.08 + i * 0.17) % 1.0) * size.width;
      final y = (0.12 + ((i % 6) * 0.11) + sin(orbit * 2 * pi + i) * 0.02) *
          size.height;
      sparkPaint.color = accentColor.withValues(
        alpha: (0.06 + (i % 4) * 0.025) * opacityScale,
      );
      canvas.drawCircle(Offset(x, y), 1.2 + (i % 2) * 0.7, sparkPaint);
    }
  }

  _WeatherPalette _paletteForWeather() {
    switch (weatherType) {
      case 'sunny':
        return _WeatherPalette(
          primary: accentColor,
          secondary: Color.lerp(accentColor, const Color(0xFFFFF2C2), 0.55) ??
              accentColor,
          highlight:
              Color.lerp(accentColor, Colors.white, 0.68) ?? Colors.white,
          skyColors: [
            accentColor.withValues(alpha: 0.1 * opacityScale),
            const Color(0xFFFFF4D6).withValues(alpha: 0.06 * opacityScale),
            Colors.transparent,
          ],
          auraCenter: const Alignment(0.82, -0.28),
          auraRadius: 0.95,
        );
      case 'cloudy':
        return _WeatherPalette(
          primary: accentColor,
          secondary: Color.lerp(accentColor, const Color(0xFFD7E0F0), 0.52) ??
              accentColor,
          highlight:
              Color.lerp(accentColor, Colors.white, 0.56) ?? Colors.white,
          skyColors: [
            accentColor.withValues(alpha: 0.07 * opacityScale),
            const Color(0xFFE6ECF5).withValues(alpha: 0.05 * opacityScale),
            Colors.transparent,
          ],
          auraCenter: const Alignment(-0.45, -0.22),
          auraRadius: 1.2,
        );
      case 'rainy':
        return _WeatherPalette(
          primary: accentColor,
          secondary: Color.lerp(accentColor, const Color(0xFF93BCE7), 0.45) ??
              accentColor,
          highlight: Color.lerp(accentColor, Colors.white, 0.4) ?? Colors.white,
          skyColors: [
            accentColor.withValues(alpha: 0.12 * opacityScale),
            const Color(0xFFB8D4EC).withValues(alpha: 0.05 * opacityScale),
            Colors.transparent,
          ],
          auraCenter: const Alignment(0.0, -0.35),
          auraRadius: 1.15,
        );
      case 'meteor':
        return _WeatherPalette(
          primary: accentColor,
          secondary: Color.lerp(accentColor, const Color(0xFF6246EA), 0.5) ??
              accentColor,
          highlight:
              Color.lerp(accentColor, Colors.white, 0.62) ?? Colors.white,
          skyColors: [
            accentColor.withValues(alpha: 0.13 * opacityScale),
            const Color(0xFF1A1235).withValues(alpha: 0.08 * opacityScale),
            Colors.transparent,
          ],
          auraCenter: const Alignment(0.0, -0.48),
          auraRadius: 1.25,
        );
      default:
        return _WeatherPalette(
          primary: accentColor,
          secondary: accentColor,
          highlight: Colors.white,
          skyColors: [
            accentColor.withValues(alpha: 0.08 * opacityScale),
            Colors.transparent,
            Colors.transparent,
          ],
          auraCenter: const Alignment(0.82, -0.28),
          auraRadius: 1.0,
        );
    }
  }

  @override
  bool shouldRepaint(covariant _WeatherPainter oldDelegate) =>
      mainValue != oldDelegate.mainValue ||
      particleValue != oldDelegate.particleValue ||
      speedMultiplier != oldDelegate.speedMultiplier ||
      opacityScale != oldDelegate.opacityScale ||
      accentColor != oldDelegate.accentColor ||
      weatherType != oldDelegate.weatherType ||
      particles != oldDelegate.particles;
}
