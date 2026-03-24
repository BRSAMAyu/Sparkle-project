import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/animation_lifecycle_mixin.dart';
import 'package:sparkle/core/design/widgets/global_particle_counter.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

enum MilestoneLevel {
  none,
  bronze,
  silver,
  gold,
  platinum,
}

class AchievementMilestoneBadge extends StatefulWidget {
  const AchievementMilestoneBadge({
    required this.progress,
    required this.rarity,
    super.key,
  });

  final double progress; // 0.0 - 1.0
  final AchievementRarity rarity;

  @override
  State<AchievementMilestoneBadge> createState() =>
      _AchievementMilestoneBadgeState();
}

class _AchievementMilestoneBadgeState extends State<AchievementMilestoneBadge>
    with TickerProviderStateMixin, AnimationLifecycleMixin {
  static const int _platinumParticles = 6;
  late final AnimationController _controller;
  bool _reduceMotion = false;
  bool _particlesEnabled = false;
  int _registeredParticleCount = 0;

  MilestoneLevel get _milestone {
    final progress = widget.progress;
    if (progress >= 1.0) return MilestoneLevel.platinum;
    if (progress >= 0.75) return MilestoneLevel.gold;
    if (progress >= 0.50) return MilestoneLevel.silver;
    if (progress >= 0.25) return MilestoneLevel.bronze;
    return MilestoneLevel.none;
  }

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: DS.motionDuration(SparkleMotionToken.hero),
    );

    registerController(
      _controller,
      onResume: () => _controller.repeat(),
    );
    _updateParticleRegistration(force: true);
    _startAnimations();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final reduceMotion = context.reduceMotion;
    if (reduceMotion == _reduceMotion) return;
    _reduceMotion = reduceMotion;
    if (_reduceMotion) {
      _controller.stop();
      _releaseParticles();
    } else {
      _updateParticleRegistration(force: true);
      _startAnimations();
    }
  }

  @override
  void didUpdateWidget(covariant AchievementMilestoneBadge oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_milestone.index > _milestoneForProgress(oldWidget.progress).index) {
      unawaited(
        SensoryFeedbackService.emit(
          _milestone == MilestoneLevel.platinum
              ? SensoryFeedbackEvent.achievementRare
              : SensoryFeedbackEvent.success,
        ),
      );
    }
    if (oldWidget.progress != widget.progress) {
      _updateParticleRegistration(force: true);
      _startAnimations();
    }
  }

  MilestoneLevel _milestoneForProgress(double progress) {
    if (progress >= 1.0) return MilestoneLevel.platinum;
    if (progress >= 0.75) return MilestoneLevel.gold;
    if (progress >= 0.50) return MilestoneLevel.silver;
    if (progress >= 0.25) return MilestoneLevel.bronze;
    return MilestoneLevel.none;
  }

  void _startAnimations() {
    if (_reduceMotion || _milestone == MilestoneLevel.none) return;
    if (!_controller.isAnimating) {
      _controller.repeat();
    }
  }

  void _updateParticleRegistration({bool force = false}) {
    final wantsParticles =
        !_reduceMotion && _milestone == MilestoneLevel.platinum;
    final desiredCount = wantsParticles ? _platinumParticles : 0;

    if (!force && desiredCount == _registeredParticleCount) return;
    _releaseParticles();

    if (desiredCount > 0 &&
        GlobalParticleCounter.tryAddParticles(desiredCount)) {
      _registeredParticleCount = desiredCount;
      _particlesEnabled = true;
    }
  }

  void _releaseParticles() {
    if (_registeredParticleCount > 0) {
      GlobalParticleCounter.releaseParticles(_registeredParticleCount);
      _registeredParticleCount = 0;
    }
    _particlesEnabled = false;
  }

  @override
  void dispose() {
    _releaseParticles();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final milestone = _milestone;
    if (milestone == MilestoneLevel.none) {
      return const SizedBox.shrink();
    }

    final colors = _milestoneColors(milestone);
    final glow = Color.lerp(
          colors.glow,
          _rarityAccent(widget.rarity),
          0.25,
        ) ??
        colors.glow;
    const size = 22.0;

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          if (milestone.index >= MilestoneLevel.gold.index && !_reduceMotion)
            AnimatedBuilder(
              animation: _controller,
              builder: (context, _) {
                final pulse =
                    0.35 + 0.2 * math.sin(_controller.value * math.pi * 2);
                return Container(
                  width: size + 6,
                  height: size + 6,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: glow.withValues(alpha: pulse),
                        blurRadius: 8,
                        spreadRadius: 1,
                      ),
                    ],
                  ),
                );
              },
            ),
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: colors.background,
              border: Border.all(
                color: colors.border,
                width: 1.4,
              ),
            ),
          ),
          if (milestone.index >= MilestoneLevel.silver.index && !_reduceMotion)
            Positioned.fill(
              child: AnimatedBuilder(
                animation: _controller,
                builder: (context, _) {
                  final sweepPosition = -1.0 + _controller.value * 3.0;
                  return ClipOval(
                    child: ShaderMask(
                      shaderCallback: (bounds) => LinearGradient(
                        begin: Alignment(sweepPosition - 0.3, 0),
                        end: Alignment(sweepPosition + 0.3, 0),
                        colors: [
                          Colors.transparent,
                          colors.shimmer,
                          Colors.transparent,
                        ],
                        stops: const [0.0, 0.5, 1.0],
                      ).createShader(bounds),
                      blendMode: BlendMode.srcATop,
                      child: Container(
                        color: Colors.white,
                      ),
                    ),
                  );
                },
              ),
            ),
          if (milestone == MilestoneLevel.platinum && _particlesEnabled)
            Positioned.fill(
              child: RepaintBoundary(
                child: CustomPaint(
                  painter: _MilestoneParticlePainter(
                    animationValue: _controller.value,
                    color: glow,
                  ),
                ),
              ),
            ),
          if (milestone == MilestoneLevel.platinum)
            Icon(
              Icons.emoji_events_rounded,
              size: 12,
              color: colors.border,
            ),
        ],
      ),
    );
  }

  _MilestoneColors _milestoneColors(MilestoneLevel level) {
    switch (level) {
      case MilestoneLevel.bronze:
        return _MilestoneColors(
          border: DS.warning.withValues(alpha: 0.7),
          background: DS.warning.withValues(alpha: 0.12),
          glow: DS.warning,
          shimmer: DS.warning.withValues(alpha: 0.5),
        );
      case MilestoneLevel.silver:
        return _MilestoneColors(
          border: DS.neutral300,
          background: DS.neutral200,
          glow: DS.neutral400,
          shimmer: DS.neutral100,
        );
      case MilestoneLevel.gold:
        return _MilestoneColors(
          border: DS.warning,
          background: DS.warning.withValues(alpha: 0.15),
          glow: DS.warning,
          shimmer: DS.warning.withValues(alpha: 0.6),
        );
      case MilestoneLevel.platinum:
        return _MilestoneColors(
          border: DS.info,
          background: DS.info.withValues(alpha: 0.12),
          glow: DS.info,
          shimmer: DS.info.withValues(alpha: 0.6),
        );
      case MilestoneLevel.none:
        return _MilestoneColors(
          border: DS.neutral300,
          background: DS.neutral200,
          glow: DS.neutral300,
          shimmer: DS.neutral200,
        );
    }
  }

  Color _rarityAccent(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return DS.rarityCommon;
      case AchievementRarity.rare:
        return DS.rarityRare;
      case AchievementRarity.epic:
        return DS.rarityEpic;
      case AchievementRarity.legendary:
        return DS.rarityLegendary;
    }
  }
}

class _MilestoneColors {
  _MilestoneColors({
    required this.border,
    required this.background,
    required this.glow,
    required this.shimmer,
  });

  final Color border;
  final Color background;
  final Color glow;
  final Color shimmer;
}

class _MilestoneParticlePainter extends CustomPainter {
  _MilestoneParticlePainter({
    required this.animationValue,
    required this.color,
  });

  final double animationValue;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final paint = Paint()..style = PaintingStyle.fill;

    for (var i = 0; i < 6; i++) {
      final angle = (i / 6) * math.pi * 2 + animationValue * math.pi * 2;
      final radius = 8 + (i % 2) * 3;
      final offset = Offset(
        center.dx + math.cos(angle) * radius,
        center.dy + math.sin(angle) * radius,
      );
      paint.color = color.withValues(alpha: 0.5);
      canvas.drawCircle(offset, 1.4, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _MilestoneParticlePainter oldDelegate) => animationValue != oldDelegate.animationValue;
}
