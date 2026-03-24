import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';

class SceneAtmosphereLayer extends StatefulWidget {
  const SceneAtmosphereLayer({
    required this.atmosphere,
    super.key,
  });

  final ExperienceAtmosphere atmosphere;

  @override
  State<SceneAtmosphereLayer> createState() => _SceneAtmosphereLayerState();
}

class _SceneAtmosphereLayerState extends State<SceneAtmosphereLayer>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 12000),
    );
    unawaited(_controller.repeat());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.atmosphere == ExperienceAtmosphere.none) {
      return const SizedBox.shrink();
    }

    if (context.reduceMotion) {
      return IgnorePointer(
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: _staticGradient(widget.atmosphere),
          ),
        ),
      );
    }

    return IgnorePointer(
      child: RepaintBoundary(
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, _) => CustomPaint(
            painter: _SceneAtmospherePainter(
              atmosphere: widget.atmosphere,
              progress: _controller.value,
            ),
            child: const SizedBox.expand(),
          ),
        ),
      ),
    );
  }

  Gradient? _staticGradient(ExperienceAtmosphere atmosphere) {
    switch (atmosphere) {
      case ExperienceAtmosphere.none:
        return null;
      case ExperienceAtmosphere.dashboardGlow:
        return LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            DS.capsuleAccent.withValues(alpha: 0.06),
            Colors.transparent,
          ],
        );
      case ExperienceAtmosphere.galaxyDrift:
        return RadialGradient(
          center: const Alignment(0.2, -0.6),
          radius: 1.2,
          colors: [
            DS.info.withValues(alpha: 0.08),
            Colors.transparent,
          ],
        );
      case ExperienceAtmosphere.achievementGlow:
        return RadialGradient(
          center: const Alignment(0, -0.3),
          radius: 1.0,
          colors: [
            DS.warning.withValues(alpha: 0.1),
            Colors.transparent,
          ],
        );
      case ExperienceAtmosphere.focusBreath:
        return RadialGradient(
          radius: 1.0,
          colors: [
            DS.info.withValues(alpha: 0.06),
            Colors.transparent,
          ],
        );
      case ExperienceAtmosphere.socialWarm:
        return LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.warning.withValues(alpha: 0.07),
            DS.brandPrimary.withValues(alpha: 0.04),
            Colors.transparent,
          ],
        );
      case ExperienceAtmosphere.seedsOrganic:
        return RadialGradient(
          center: const Alignment(-0.4, -0.4),
          radius: 1.1,
          colors: [
            DS.success.withValues(alpha: 0.08),
            Colors.transparent,
          ],
        );
      case ExperienceAtmosphere.insightsMist:
        return LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: [
            DS.info.withValues(alpha: 0.05),
            DS.brandPrimary.withValues(alpha: 0.04),
            Colors.transparent,
          ],
        );
    }
  }
}

class _SceneAtmospherePainter extends CustomPainter {
  const _SceneAtmospherePainter({
    required this.atmosphere,
    required this.progress,
  });

  final ExperienceAtmosphere atmosphere;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    switch (atmosphere) {
      case ExperienceAtmosphere.none:
        return;
      case ExperienceAtmosphere.dashboardGlow:
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * 0.78, size.height * 0.08),
          radius: size.width * 0.6,
          color: DS.capsuleAccent.withValues(alpha: 0.1),
        );
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * 0.2, size.height * 0.22),
          radius: size.width * 0.42,
          color: DS.brandPrimary.withValues(alpha: 0.04),
        );
      case ExperienceAtmosphere.galaxyDrift:
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * (0.22 + progress * 0.08), size.height * 0.16),
          radius: size.width * 0.48,
          color: DS.info.withValues(alpha: 0.08),
        );
        _paintParticles(
          canvas,
          size,
          count: 20,
          baseColor: DS.textPrimary.withValues(alpha: 0.18),
          verticalAmplitude: 18,
        );
      case ExperienceAtmosphere.achievementGlow:
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * 0.5, size.height * 0.24),
          radius: size.width * (0.42 + 0.03 * math.sin(progress * math.pi * 2)),
          color: DS.warning.withValues(alpha: 0.12),
        );
        _paintParticles(
          canvas,
          size,
          count: 14,
          baseColor: DS.warning.withValues(alpha: 0.2),
          verticalAmplitude: 10,
        );
      case ExperienceAtmosphere.focusBreath:
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * 0.5, size.height * 0.42),
          radius: size.width * (0.28 + 0.02 * math.sin(progress * math.pi * 2)),
          color: DS.info.withValues(alpha: 0.08),
        );
      case ExperienceAtmosphere.socialWarm:
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * 0.14, size.height * 0.18),
          radius: size.width * 0.44,
          color: DS.warning.withValues(alpha: 0.08),
        );
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * 0.82, size.height * 0.76),
          radius: size.width * 0.34,
          color: DS.brandPrimary.withValues(alpha: 0.05),
        );
      case ExperienceAtmosphere.seedsOrganic:
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * 0.18, size.height * 0.2),
          radius: size.width * 0.38,
          color: DS.success.withValues(alpha: 0.08),
        );
        _paintParticles(
          canvas,
          size,
          count: 12,
          baseColor: DS.success.withValues(alpha: 0.16),
          verticalAmplitude: 14,
        );
      case ExperienceAtmosphere.insightsMist:
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * 0.72, size.height * 0.16),
          radius: size.width * 0.46,
          color: DS.info.withValues(alpha: 0.06),
        );
        _paintGlow(
          canvas,
          size,
          center: Offset(size.width * 0.24, size.height * 0.66),
          radius: size.width * 0.36,
          color: DS.brandPrimary.withValues(alpha: 0.05),
        );
    }
  }

  void _paintGlow(
    Canvas canvas,
    Size size, {
    required Offset center,
    required double radius,
    required Color color,
  }) {
    final rect = Rect.fromCircle(center: center, radius: radius);
    final paint = Paint()
      ..shader = RadialGradient(
        colors: [
          color,
          color.withValues(alpha: color.a * 0.35),
          Colors.transparent,
        ],
        stops: const [0, 0.52, 1],
      ).createShader(rect)
      ..blendMode = BlendMode.plus;
    canvas.drawCircle(center, radius, paint);
  }

  void _paintParticles(
    Canvas canvas,
    Size size, {
    required int count,
    required Color baseColor,
    required double verticalAmplitude,
  }) {
    final paint = Paint()..color = baseColor;
    for (var i = 0; i < count; i++) {
      final seed = i / count;
      final x = size.width * (0.08 + 0.84 * seed);
      final yBase = size.height * (0.14 + (seed * 0.72));
      final y = yBase +
          math.sin((progress * math.pi * 2) + seed * math.pi * 2) *
              verticalAmplitude;
      final radius = 1.2 + (i % 3) * 0.7;
      paint.color = baseColor.withValues(
        alpha: (0.06 + (1 - seed) * 0.18).clamp(0.0, 1.0),
      );
      canvas.drawCircle(Offset(x, y), radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _SceneAtmospherePainter oldDelegate) =>
      oldDelegate.atmosphere != atmosphere || oldDelegate.progress != progress;
}
