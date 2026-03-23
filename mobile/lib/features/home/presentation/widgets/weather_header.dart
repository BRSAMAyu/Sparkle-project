import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

/// WeatherHeader - Full-screen animated background weather system
class WeatherHeader extends ConsumerStatefulWidget {
  const WeatherHeader({super.key});

  @override
  ConsumerState<WeatherHeader> createState() => _WeatherHeaderState();
}

class _WeatherHeaderState extends ConsumerState<WeatherHeader>
    with TickerProviderStateMixin {
  late AnimationController _mainAnimationController;
  late AnimationController _particleController;
  late Animation<double> _pulseAnimation;

  // Random seed for consistent particle positions
  final Random _random = Random(42);
  late List<_Particle> _particles;
  late List<_Star> _stars;
  late List<_Meteor> _meteors;
  late List<_RainDrop> _rainDrops;
  late List<_Cloud> _clouds;

  @override
  void initState() {
    super.initState();
    _initAnimations();
    _initParticles();
  }

  void _initAnimations() {
    // Main animation for pulse effects (sunny glow, star twinkle)
    _mainAnimationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    // Particle drift animation (clouds, rain, meteors)
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat();

    _pulseAnimation = Tween<double>(begin: 0.8, end: 1.2).animate(
      CurvedAnimation(parent: _mainAnimationController, curve: Curves.easeInOut),
    );
  }

  void _initParticles() {
    // Initialize stars (shared across weather types)
    _stars = List.generate(20, (i) => _Star(
        x: _random.nextDouble(),
        y: _random.nextDouble() * 0.5,
        size: 0.5 + _random.nextDouble() * 1.5,
        baseOpacity: 0.2 + _random.nextDouble() * 0.3,
        twinkleSpeed: 0.5 + _random.nextDouble() * 1.5,
      ),);

    // Initialize particles for sunny weather (sun rays)
    _particles = List.generate(8, (i) => _Particle(
        angle: (i * pi / 4),
        baseRadius: 30.0 + i * 15.0,
      ),);

    // Initialize clouds for cloudy weather
    _clouds = List.generate(5, (i) => _Cloud(
        x: _random.nextDouble(),
        y: 0.05 + _random.nextDouble() * 0.25,
        size: 40 + _random.nextDouble() * 60,
        speed: 0.1 + _random.nextDouble() * 0.2,
        opacity: 0.03 + _random.nextDouble() * 0.05,
      ),);

    // Initialize rain drops for rainy weather
    _rainDrops = List.generate(40, (i) => _RainDrop(
        x: _random.nextDouble(),
        startY: -0.1 - _random.nextDouble() * 0.5,
        speed: 0.8 + _random.nextDouble() * 0.4,
        length: 10 + _random.nextDouble() * 15,
        opacity: 0.1 + _random.nextDouble() * 0.15,
      ),);

    // Initialize meteors for meteor weather
    _meteors = List.generate(6, (i) => _Meteor(
        startX: 0.2 + _random.nextDouble() * 0.6,
        startY: _random.nextDouble() * 0.2,
        length: 30 + _random.nextDouble() * 50,
        speed: 1.5 + _random.nextDouble() * 1.0,
        delay: i * 0.15,
      ),);
  }

  @override
  void dispose() {
    _mainAnimationController.dispose();
    _particleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final weatherType = dashboardState.weather.type;

    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: DS.durationSlow,
      curve: Curves.easeOutCubic,
      builder: (context, value, child) => Opacity(
        opacity: value,
        child: Transform.translate(
          offset: Offset(0, (1 - value) * 18),
          child: child,
        ),
      ),
      child: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: BoxDecoration(
          gradient: _getWeatherGradient(weatherType, isDark),
        ),
        child: Stack(
          children: [
            // Animated star field (always present, intensity varies)
            _buildAnimatedStarField(weatherType),

            // Weather-specific animated effects
            _buildWeatherEffects(weatherType, accentColor: DS.brandPrimary),

            // Corner overlay for weather status
            Positioned(
              top: MediaQuery.of(context).padding.top + 8,
              right: 16,
              child: _buildWeatherStatus(
                weatherType,
                dashboardState.weather.condition,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnimatedStarField(String weatherType) {
    // Stars are most visible in meteor weather, dimmed in others
    final starIntensity = switch (weatherType) {
      'meteor' => 1.0,
      'sunny' => 0.3,
      'cloudy' => 0.2,
      'rainy' => 0.1,
      _ => 0.3,
    };

    return AnimatedBuilder(
      animation: _mainAnimationController,
      builder: (context, child) => CustomPaint(
          size: Size.infinite,
          painter: _AnimatedStarPainter(
            stars: _stars,
            animationValue: _mainAnimationController.value,
            color: DS.brandPrimary,
            intensity: starIntensity,
          ),
        ),
    );
  }

  Widget _buildWeatherEffects(String type, {required Color accentColor}) {
    switch (type) {
      case 'sunny':
        return _buildSunnyEffects(accentColor);
      case 'cloudy':
        return _buildCloudyEffects(accentColor);
      case 'rainy':
        return _buildRainyEffects(accentColor);
      case 'meteor':
        return _buildMeteorEffects(accentColor);
      default:
        return _buildSunnyEffects(accentColor);
    }
  }

  /// Sunny: Pulsing sun rays with glow effect
  Widget _buildSunnyEffects(Color accentColor) => Stack(
      children: [
        // Central sun glow
        Positioned(
          right: -50,
          top: -30,
          child: AnimatedBuilder(
            animation: _pulseAnimation,
            builder: (context, child) => Container(
                width: 200 * _pulseAnimation.value,
                height: 200 * _pulseAnimation.value,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      accentColor.withValues(alpha: 0.15),
                      accentColor.withValues(alpha: 0.05),
                      accentColor.withValues(alpha: 0.0),
                    ],
                  ),
                ),
              ),
          ),
        ),
        // Sun rays (expanding rings)
        AnimatedBuilder(
          animation: _mainAnimationController,
          builder: (context, child) => CustomPaint(
              size: Size.infinite,
              painter: _SunRayPainter(
                particles: _particles,
                animationValue: _mainAnimationController.value,
                accentColor: accentColor,
              ),
            ),
        ),
      ],
    );

  /// Cloudy: Drifting clouds with breathing opacity
  Widget _buildCloudyEffects(Color accentColor) => AnimatedBuilder(
      animation: _particleController,
      builder: (context, child) => CustomPaint(
          size: Size.infinite,
          painter: _CloudPainter(
            clouds: _clouds,
            animationValue: _particleController.value,
            accentColor: accentColor,
            breathingValue: _mainAnimationController.value,
          ),
        ),
    );

  /// Rainy: Falling rain drops with splash effect
  Widget _buildRainyEffects(Color accentColor) => Stack(
      children: [
        // Dark overlay for rainy mood
        Positioned.fill(
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  accentColor.withValues(alpha: 0.02),
                  Colors.transparent,
                ],
              ),
            ),
          ),
        ),
        // Rain drops
        AnimatedBuilder(
          animation: _particleController,
          builder: (context, child) => CustomPaint(
              size: Size.infinite,
              painter: _RainPainter(
                rainDrops: _rainDrops,
                animationValue: _particleController.value,
                accentColor: accentColor,
              ),
            ),
        ),
      ],
    );

  /// Meteor: Shooting stars with trails and twinkling energy particles
  Widget _buildMeteorEffects(Color accentColor) => Stack(
      children: [
        // Energy particles floating
        AnimatedBuilder(
          animation: _mainAnimationController,
          builder: (context, child) => CustomPaint(
              size: Size.infinite,
              painter: _EnergyParticlePainter(
                animationValue: _mainAnimationController.value,
                accentColor: accentColor,
              ),
            ),
        ),
        // Shooting meteors
        AnimatedBuilder(
          animation: _particleController,
          builder: (context, child) => CustomPaint(
              size: Size.infinite,
              painter: _MeteorPainter(
                meteors: _meteors,
                animationValue: _particleController.value,
                accentColor: accentColor,
              ),
            ),
        ),
      ],
    );

  Widget _buildWeatherStatus(String type, String condition) => Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _getWeatherTitle(type),
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(width: 6),
            _buildWeatherIcon(type),
          ],
        )
            .animate(onPlay: (controller) => controller.repeat(reverse: true))
            .fadeIn(duration: 2000.ms)
            .scale(
              begin: const Offset(0.95, 0.95),
              end: const Offset(1.0, 1.0),
              duration: 2000.ms,
            ),
        Text(
          condition,
          style: TextStyle(
            fontSize: 10,
            color: DS.textSecondary.withValues(alpha: 0.7),
          ),
        ),
      ],
    );

  Widget _buildWeatherIcon(String type) {
    IconData icon;
    switch (type) {
      case 'sunny':
        icon = Icons.wb_sunny_rounded;
      case 'cloudy':
        icon = Icons.cloud_rounded;
      case 'rainy':
        icon = Icons.thunderstorm_rounded;
      case 'meteor':
        icon = Icons.auto_awesome_rounded;
      default:
        icon = Icons.wb_sunny_rounded;
    }
    return Icon(icon, color: DS.brandPrimaryConst, size: 18)
        .animate(onPlay: (controller) => controller.repeat(reverse: true))
        .scale(
          begin: const Offset(0.9, 0.9),
          end: const Offset(1.1, 1.1),
          duration: 1500.ms,
          curve: Curves.easeInOut,
        );
  }

  LinearGradient _getWeatherGradient(String type, bool isDark) {
    switch (type) {
      case 'sunny':
        return LinearGradient(
          colors: isDark
              ? [DS.surfaceAmbient, DS.surfacePrimary, DS.surfaceSecondary]
              : [DS.neutral50, DS.neutral100, DS.neutral200],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'cloudy':
        return LinearGradient(
          colors: isDark
              ? [DS.surfaceAmbient, DS.surfacePrimary, DS.surfaceSecondary]
              : [DS.neutral100, DS.neutral200, DS.neutral300],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'rainy':
        return LinearGradient(
          colors: isDark
              ? [DS.surfaceAmbient, DS.surfacePrimary, DS.surfaceSecondary]
              : [DS.neutral100, DS.neutral200, DS.neutral300],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'meteor':
        return LinearGradient(
          colors: isDark
              ? [DS.surfaceAmbient, DS.surfacePrimary, DS.galaxyBackground]
              : [DS.neutral100, DS.neutral200, DS.neutral300],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      default:
        return LinearGradient(
          colors: isDark
              ? [DS.surfaceAmbient, DS.surfacePrimary]
              : [DS.neutral50, DS.neutral100],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
    }
  }

  String _getWeatherTitle(String type) {
    switch (type) {
      case 'sunny':
        return '晴空万里';
      case 'cloudy':
        return '薄雾弥漫';
      case 'rainy':
        return '风雨欲来';
      case 'meteor':
        return '繁星入梦';
      default:
        return '晴空万里';
    }
  }
}

// ============== Data Classes ==============

class _Star {
  final double x;
  final double y;
  final double size;
  final double baseOpacity;
  final double twinkleSpeed;

  _Star({
    required this.x,
    required this.y,
    required this.size,
    required this.baseOpacity,
    required this.twinkleSpeed,
  });
}

class _Particle {
  final double angle;
  final double baseRadius;

  _Particle({required this.angle, required this.baseRadius});
}

class _Cloud {
  final double x;
  final double y;
  final double size;
  final double speed;
  final double opacity;

  _Cloud({
    required this.x,
    required this.y,
    required this.size,
    required this.speed,
    required this.opacity,
  });
}

class _RainDrop {
  final double x;
  final double startY;
  final double speed;
  final double length;
  final double opacity;

  _RainDrop({
    required this.x,
    required this.startY,
    required this.speed,
    required this.length,
    required this.opacity,
  });
}

class _Meteor {
  final double startX;
  final double startY;
  final double length;
  final double speed;
  final double delay;

  _Meteor({
    required this.startX,
    required this.startY,
    required this.length,
    required this.speed,
    required this.delay,
  });
}

// ============== Custom Painters ==============

class _AnimatedStarPainter extends CustomPainter {
  final List<_Star> stars;
  final double animationValue;
  final Color color;
  final double intensity;

  _AnimatedStarPainter({
    required this.stars,
    required this.animationValue,
    required this.color,
    required this.intensity,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;

    for (final star in stars) {
      // Calculate twinkle effect
      final twinkle = sin(animationValue * 2 * pi * star.twinkleSpeed) * 0.3 + 0.7;
      final opacity = star.baseOpacity * twinkle * intensity;

      paint.color = color.withValues(alpha: opacity);

      final position = Offset(
        star.x * size.width,
        star.y * size.height,
      );

      canvas.drawCircle(position, star.size, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _AnimatedStarPainter oldDelegate) => animationValue != oldDelegate.animationValue ||
        intensity != oldDelegate.intensity;
}

class _SunRayPainter extends CustomPainter {
  final List<_Particle> particles;
  final double animationValue;
  final Color accentColor;

  _SunRayPainter({
    required this.particles,
    required this.animationValue,
    required this.accentColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    final center = Offset(size.width * 0.85, size.height * 0.15);

    for (var i = 0; i < particles.length; i++) {
      final particle = particles[i];
      // Pulsing expansion effect
      final pulse = 0.8 + animationValue * 0.4;
      final radius = particle.baseRadius * pulse;

      // Fade out as rings expand
      final opacity = 0.08 * (1 - i / particles.length) * (1 - animationValue * 0.3);
      paint.color = accentColor.withValues(alpha: opacity);

      canvas.drawCircle(center, radius, paint);
    }

    // Add subtle sun rays
    paint.strokeWidth = 0.5;
    for (var i = 0; i < 12; i++) {
      final angle = i * pi / 6 + animationValue * pi / 12;
      final innerRadius = 30.0;
      final outerRadius = 80 + animationValue * 20;

      final start = Offset(
        center.dx + cos(angle) * innerRadius,
        center.dy + sin(angle) * innerRadius,
      );
      final end = Offset(
        center.dx + cos(angle) * outerRadius,
        center.dy + sin(angle) * outerRadius,
      );

      paint.color = accentColor.withValues(alpha: 0.06);
      canvas.drawLine(start, end, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _SunRayPainter oldDelegate) => animationValue != oldDelegate.animationValue;
}

class _CloudPainter extends CustomPainter {
  final List<_Cloud> clouds;
  final double animationValue;
  final Color accentColor;
  final double breathingValue;

  _CloudPainter({
    required this.clouds,
    required this.animationValue,
    required this.accentColor,
    required this.breathingValue,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;

    for (final cloud in clouds) {
      // Calculate drifting position
      final drift = (animationValue * cloud.speed + cloud.x) % 1.5 - 0.25;
      final x = drift * size.width;

      // Breathing opacity effect
      final breathing = sin(breathingValue * pi) * 0.02;
      final opacity = cloud.opacity + breathing;

      paint.color = accentColor.withValues(alpha: opacity);

      // Draw cloud as multiple overlapping circles
      final baseY = cloud.y * size.height;
      _drawCloudShape(canvas, paint, Offset(x, baseY), cloud.size);
    }
  }

  void _drawCloudShape(Canvas canvas, Paint paint, Offset center, double size) {
    canvas.drawCircle(center, size, paint);
    canvas.drawCircle(Offset(center.dx - size * 0.6, center.dy + size * 0.2), size * 0.7, paint);
    canvas.drawCircle(Offset(center.dx + size * 0.5, center.dy + size * 0.1), size * 0.6, paint);
  }

  @override
  bool shouldRepaint(covariant _CloudPainter oldDelegate) => animationValue != oldDelegate.animationValue ||
        breathingValue != oldDelegate.breathingValue;
}

class _RainPainter extends CustomPainter {
  final List<_RainDrop> rainDrops;
  final double animationValue;
  final Color accentColor;

  _RainPainter({
    required this.rainDrops,
    required this.animationValue,
    required this.accentColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;

    for (final drop in rainDrops) {
      // Calculate falling position with wrap-around
      final normalizedSpeed = drop.speed / 3;
      final progress = (animationValue * normalizedSpeed + drop.startY) % 1.2;
      final y = progress * size.height;

      final x = drop.x * size.width;

      paint.color = accentColor.withValues(alpha: drop.opacity);

      // Draw rain drop as a thin rectangle
      canvas.drawRect(
        Rect.fromLTWH(x, y, 1.5, drop.length),
        paint,
      );
    }

    // Add some splash effects at the bottom
    final splashPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.5;

    for (var i = 0; i < 10; i++) {
      final x = (i / 10 + animationValue * 0.1) % 1.0 * size.width;
      final splashProgress = (animationValue * 2 + i * 0.1) % 1.0;
      final splashRadius = splashProgress * 5;
      final splashOpacity = (1 - splashProgress) * 0.1;

      splashPaint.color = accentColor.withValues(alpha: splashOpacity);
      canvas.drawCircle(
        Offset(x, size.height * 0.95),
        splashRadius,
        splashPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _RainPainter oldDelegate) => animationValue != oldDelegate.animationValue;
}

class _MeteorPainter extends CustomPainter {
  final List<_Meteor> meteors;
  final double animationValue;
  final Color accentColor;

  _MeteorPainter({
    required this.meteors,
    required this.animationValue,
    required this.accentColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    for (final meteor in meteors) {
      // Calculate meteor position with delay
      final adjustedValue = (animationValue + meteor.delay) % 1.0;
      final progress = adjustedValue * meteor.speed;

      // Only show meteor for part of the cycle
      if (progress > 1.0) continue;

      final startX = meteor.startX * size.width;
      final startY = meteor.startY * size.height;

      // Meteor travels diagonally down-left
      final travel = progress * size.width * 0.4;
      final endX = startX - travel;
      final endY = startY + travel * 0.6;

      // Trail effect - gradient opacity along the tail
      final trailLength = meteor.length * (1 - progress * 0.5);
      final tailX = endX + cos(-0.5) * trailLength;
      final tailY = endY - sin(-0.5) * trailLength;

      // Draw meteor trail with gradient effect
      for (var i = 0; i < 5; i++) {
        final t = i / 5;
        final segmentEndX = tailX + (endX - tailX) * t;
        final segmentEndY = tailY + (endY - tailY) * t;
        final segmentStartX = tailX + (endX - tailX) * (t + 0.2);
        final segmentStartY = tailY + (endY - tailY) * (t + 0.2);

        paint.strokeWidth = 1.5 * (1 - t * 0.5);
        paint.color = accentColor.withValues(alpha: 0.3 * (1 - t) * (1 - progress));

        canvas.drawLine(
          Offset(segmentStartX, segmentStartY),
          Offset(segmentEndX, segmentEndY),
          paint,
        );
      }

      // Bright head of meteor
      paint.style = PaintingStyle.fill;
      paint.color = accentColor.withValues(alpha: 0.4 * (1 - progress));
      canvas.drawCircle(Offset(endX, endY), 2, paint);
      paint.style = PaintingStyle.stroke;
    }
  }

  @override
  bool shouldRepaint(covariant _MeteorPainter oldDelegate) => animationValue != oldDelegate.animationValue;
}

class _EnergyParticlePainter extends CustomPainter {
  final double animationValue;
  final Color accentColor;

  _EnergyParticlePainter({
    required this.animationValue,
    required this.accentColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;
    final random = Random(123);

    // Floating energy particles
    for (var i = 0; i < 30; i++) {
      final baseX = random.nextDouble();
      final baseY = random.nextDouble();

      // Floating motion
      final floatX = sin(animationValue * 2 * pi + i) * 0.02;
      final floatY = cos(animationValue * 2 * pi + i * 0.7) * 0.01;

      final x = (baseX + floatX) * size.width;
      final y = (baseY + floatY) * size.height;

      // Pulsing opacity
      final pulse = sin(animationValue * 2 * pi * 2 + i * 0.5) * 0.5 + 0.5;
      final opacity = 0.05 + pulse * 0.1;

      paint.color = accentColor.withValues(alpha: opacity);

      final particleSize = 1 + random.nextDouble() * 2;
      canvas.drawCircle(Offset(x, y), particleSize, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _EnergyParticlePainter oldDelegate) => animationValue != oldDelegate.animationValue;
}
