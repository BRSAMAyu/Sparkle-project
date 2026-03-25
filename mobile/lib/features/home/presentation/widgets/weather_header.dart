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
      CurvedAnimation(
          parent: _mainAnimationController, curve: Curves.easeInOut),
    );
  }

  void _initParticles() {
    // Initialize stars (shared across weather types)
    _stars = List.generate(
      20,
      (i) => _Star(
        x: _random.nextDouble(),
        y: _random.nextDouble() * 0.5,
        size: 0.5 + _random.nextDouble() * 1.5,
        baseOpacity: 0.2 + _random.nextDouble() * 0.3,
        twinkleSpeed: 0.5 + _random.nextDouble() * 1.5,
      ),
    );

    // Initialize particles for sunny weather (sun rays)
    _particles = List.generate(
      8,
      (i) => _Particle(
        angle: (i * pi / 4),
        baseRadius: 30.0 + i * 15.0,
      ),
    );

    // Initialize clouds for cloudy weather
    _clouds = List.generate(
      5,
      (i) => _Cloud(
        x: _random.nextDouble(),
        y: 0.05 + _random.nextDouble() * 0.25,
        size: 40 + _random.nextDouble() * 60,
        speed: 0.1 + _random.nextDouble() * 0.2,
        opacity: 0.03 + _random.nextDouble() * 0.05,
      ),
    );

    // Initialize rain drops for rainy weather
    _rainDrops = List.generate(
      40,
      (i) => _RainDrop(
        x: _random.nextDouble(),
        startY: -0.1 - _random.nextDouble() * 0.5,
        speed: 0.8 + _random.nextDouble() * 0.4,
        length: 10 + _random.nextDouble() * 15,
        opacity: 0.1 + _random.nextDouble() * 0.15,
      ),
    );

    // Initialize meteors for meteor weather
    _meteors = List.generate(
      6,
      (i) => _Meteor(
        startX: 0.2 + _random.nextDouble() * 0.6,
        startY: _random.nextDouble() * 0.2,
        length: 30 + _random.nextDouble() * 50,
        speed: 1.5 + _random.nextDouble() * 1.0,
        delay: i * 0.15,
      ),
    );
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
            Positioned.fill(
              child: IgnorePointer(
                child: _buildAtmosphereVeil(
                  weatherType,
                  dashboardState.weather.condition,
                ),
              ),
            ),

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

  Widget _buildAtmosphereVeil(String type, String condition) {
    final accent = _weatherAccent(type);
    final secondary = Color.lerp(accent, Colors.white, 0.58) ?? Colors.white;

    return AnimatedBuilder(
      animation: Listenable.merge([
        _mainAnimationController,
        _particleController,
      ]),
      builder: (context, child) {
        final pulse = 0.88 + sin(_mainAnimationController.value * 2 * pi) * 0.1;
        final drift = sin(_particleController.value * 2 * pi) * 18;

        return Stack(
          children: [
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      accent.withValues(alpha: 0.08 * pulse),
                      secondary.withValues(alpha: 0.04 * pulse),
                      Colors.transparent,
                    ],
                    stops: const [0.0, 0.38, 1.0],
                  ),
                ),
              ),
            ),
            Positioned(
              left: -24 + drift,
              right: -24,
              bottom: -32,
              child: IgnorePointer(
                child: Container(
                  height: 180,
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      center: const Alignment(0.0, 1.0),
                      radius: 1.25,
                      colors: [
                        accent.withValues(alpha: 0.12),
                        accent.withValues(alpha: 0.04),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              ),
            ),
            if (condition.isNotEmpty)
              Positioned(
                left: 20,
                bottom: 28,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing10,
                    vertical: DS.spacing8,
                  ),
                  decoration: BoxDecoration(
                    color: DS.surfacePrimary.withValues(alpha: 0.58),
                    borderRadius: DS.borderRadiusFull,
                    border: Border.all(
                      color: accent.withValues(alpha: 0.18),
                    ),
                  ),
                  child: Text(
                    _getWeatherAmbientLine(type),
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: accent,
                      fontWeight: DS.fontWeightMedium,
                    ),
                  ),
                )
                    .animate()
                    .fadeIn(delay: 200.ms, duration: 500.ms)
                    .moveY(begin: 8, end: 0),
              ),
          ],
        );
      },
    );
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

  Widget _buildWeatherStatus(String type, String condition) {
    final accent = _weatherAccent(type);

    return Container(
      constraints: const BoxConstraints(maxWidth: 196),
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            accent.withValues(alpha: 0.16),
            DS.surfacePrimary.withValues(alpha: 0.82),
            DS.surfaceSecondary.withValues(alpha: 0.74),
          ],
          stops: const [0.0, 0.36, 1.0],
        ),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: accent.withValues(alpha: 0.22)),
        boxShadow: [
          BoxShadow(
            color: accent.withValues(alpha: 0.14),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _getWeatherTitle(type),
                      style: TextStyle(
                        fontSize: DS.fontSizeSm,
                        fontWeight: DS.fontWeightBold,
                        color: DS.textPrimary,
                      ),
                    ),
                    const SizedBox(height: DS.spacing2),
                    Text(
                      _getWeatherSubtitle(type),
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.textSecondary,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing8),
              _buildWeatherIcon(type),
            ],
          )
              .animate(onPlay: (controller) => controller.repeat(reverse: true))
              .fadeIn(duration: 2000.ms)
              .scale(
                begin: const Offset(0.97, 0.97),
                end: const Offset(1.0, 1.0),
                duration: 2000.ms,
              ),
          const SizedBox(height: DS.spacing10),
          Wrap(
            alignment: WrapAlignment.end,
            spacing: DS.spacing6,
            runSpacing: DS.spacing6,
            children: [
              _buildWeatherChip(_getWeatherRhythm(type), accent),
              _buildWeatherChip(
                condition.isNotEmpty ? condition : _getWeatherCue(type),
                Color.lerp(accent, DS.info, 0.35) ?? DS.info,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildWeatherChip(String label, Color color) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: color.withValues(alpha: 0.18)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: color,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
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
    final accent = _weatherAccent(type);
    return Container(
      width: 34,
      height: 34,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            accent.withValues(alpha: 0.24),
            accent.withValues(alpha: 0.08),
            Colors.transparent,
          ],
        ),
      ),
      child: Icon(icon, color: accent, size: 18),
    ).animate(onPlay: (controller) => controller.repeat(reverse: true)).scale(
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
              ? [
                  const Color(0xFF1A2338),
                  DS.surfacePrimary,
                  const Color(0xFF2E3A5C),
                ]
              : [
                  const Color(0xFFFFF6DD),
                  const Color(0xFFF9ECD1),
                  const Color(0xFFEAD9B8),
                ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'cloudy':
        return LinearGradient(
          colors: isDark
              ? [
                  const Color(0xFF1A2333),
                  const Color(0xFF243248),
                  const Color(0xFF31445E),
                ]
              : [
                  const Color(0xFFF1F4FA),
                  const Color(0xFFE2E8F1),
                  const Color(0xFFD0D9E6),
                ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'rainy':
        return LinearGradient(
          colors: isDark
              ? [
                  const Color(0xFF101C2B),
                  const Color(0xFF16283A),
                  const Color(0xFF23405E),
                ]
              : [
                  const Color(0xFFE7EEF6),
                  const Color(0xFFD3E1EF),
                  const Color(0xFFB7CBDF),
                ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'meteor':
        return LinearGradient(
          colors: isDark
              ? [
                  const Color(0xFF120E25),
                  const Color(0xFF1D1737),
                  DS.galaxyBackground,
                ]
              : [
                  const Color(0xFFF3EDFF),
                  const Color(0xFFE4DCF9),
                  const Color(0xFFD1C5F1),
                ],
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

  Color _weatherAccent(String type) {
    switch (type) {
      case 'sunny':
        return const Color(0xFFFFC857);
      case 'cloudy':
        return const Color(0xFF8BA3C7);
      case 'rainy':
        return const Color(0xFF66C7F4);
      case 'meteor':
        return const Color(0xFFB78CFF);
      default:
        return DS.brandPrimaryConst;
    }
  }

  String _getWeatherSubtitle(String type) {
    switch (type) {
      case 'sunny':
        return '光感上扬，今天适合持续推进。';
      case 'cloudy':
        return '边界变柔，适合整理与留白。';
      case 'rainy':
        return '环境收拢，适合沉浸专注。';
      case 'meteor':
        return '灵感升空，适合冲刺与突破。';
      default:
        return '今天的气氛已经就位。';
    }
  }

  String _getWeatherRhythm(String type) {
    switch (type) {
      case 'sunny':
        return '节奏: 明亮推进';
      case 'cloudy':
        return '节奏: 柔和过渡';
      case 'rainy':
        return '节奏: 深潜聚焦';
      case 'meteor':
        return '节奏: 高光冲刺';
      default:
        return '节奏: 平稳展开';
    }
  }

  String _getWeatherCue(String type) {
    switch (type) {
      case 'sunny':
        return '保持出发感';
      case 'cloudy':
        return '给思路留白';
      case 'rainy':
        return '收拢注意力';
      case 'meteor':
        return '抓住灵感窗口';
      default:
        return '维持流动状态';
    }
  }

  String _getWeatherAmbientLine(String type) {
    switch (type) {
      case 'sunny':
        return '空气偏亮，视野与动机同时抬升';
      case 'cloudy':
        return '云层压低了噪声，画面更柔和';
      case 'rainy':
        return '雨幕正在帮你屏蔽外界干扰';
      case 'meteor':
        return '星迹正在提醒你记录高光时刻';
      default:
        return '天气正在为今天的节奏定调';
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
      final twinkle =
          sin(animationValue * 2 * pi * star.twinkleSpeed) * 0.3 + 0.7;
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
  bool shouldRepaint(covariant _AnimatedStarPainter oldDelegate) =>
      animationValue != oldDelegate.animationValue ||
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
      final opacity =
          0.08 * (1 - i / particles.length) * (1 - animationValue * 0.3);
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
  bool shouldRepaint(covariant _SunRayPainter oldDelegate) =>
      animationValue != oldDelegate.animationValue;
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
    canvas.drawCircle(Offset(center.dx - size * 0.6, center.dy + size * 0.2),
        size * 0.7, paint);
    canvas.drawCircle(Offset(center.dx + size * 0.5, center.dy + size * 0.1),
        size * 0.6, paint);
  }

  @override
  bool shouldRepaint(covariant _CloudPainter oldDelegate) =>
      animationValue != oldDelegate.animationValue ||
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
  bool shouldRepaint(covariant _RainPainter oldDelegate) =>
      animationValue != oldDelegate.animationValue;
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
        paint.color =
            accentColor.withValues(alpha: 0.3 * (1 - t) * (1 - progress));

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
  bool shouldRepaint(covariant _MeteorPainter oldDelegate) =>
      animationValue != oldDelegate.animationValue;
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
  bool shouldRepaint(covariant _EnergyParticlePainter oldDelegate) =>
      animationValue != oldDelegate.animationValue;
}
