import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/animation_lifecycle_mixin.dart';
import 'package:sparkle/core/design/widgets/global_particle_counter.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// Rarity threshold: shimmer only applies to rare+ items.
const shimmerRarities = {
  AchievementRarity.rare,
  AchievementRarity.epic,
  AchievementRarity.legendary,
};

/// Duration window for the "newly unlocked" glow pulse.
const newlyUnlockedWindow = Duration(minutes: 5);

/// Unified rarity visual wrapper that provides consistent visual effects
/// across achievement cards, visual element cards, and shop items.
///
/// Effects by rarity:
/// - Common: 1px static border, solid background, no effects
/// - Rare: 1.5px border + subtle shimmer, single-color light gradient, entry fade glow
/// - Epic: 2px gradient border (slow rotation), dual-color gradient, continuous pulse glow, 2 orbital particles
/// - Legendary: 2px rainbow gradient border (rotation), triple-color gradient, glow halo + breathing, 4 orbital particles + shimmer
class RarityVisualWrapper extends StatefulWidget {
  const RarityVisualWrapper({
    required this.rarity,
    required this.child,
    required this.borderRadius,
    super.key,
    this.showShimmer = true,
    this.showGlow = true,
    this.showParticles = false,
    this.isNewlyUnlocked = false,
    this.isEquipped = false,
    this.unlockedAt,
  });

  /// The rarity level - supports both AchievementRarity and VisualElementRarity
  final dynamic rarity;

  /// The child widget to wrap
  final Widget child;

  /// Border radius for the effects
  final BorderRadius borderRadius;

  /// Whether to show shimmer effect (for rare+ items)
  final bool showShimmer;

  /// Whether to show glow effect (for newly unlocked items)
  final bool showGlow;

  /// Whether to show orbital particles (for full-screen/dialog scenarios)
  final bool showParticles;

  /// Whether this item was recently unlocked (within 5 minutes)
  final bool isNewlyUnlocked;

  /// Whether this item is currently equipped
  final bool isEquipped;

  /// When the item was unlocked (for newly unlocked detection)
  final DateTime? unlockedAt;

  @override
  State<RarityVisualWrapper> createState() => _RarityVisualWrapperState();
}

class _RarityVisualWrapperState extends State<RarityVisualWrapper>
    with TickerProviderStateMixin, AnimationLifecycleMixin {
  late AnimationController _shimmerController;
  late AnimationController _glowController;
  late AnimationController _particleController;
  late AnimationController _borderRotationController;
  bool _reduceMotion = false;
  bool _particlesEnabled = false;
  int _registeredParticleCount = 0;

  @override
  void initState() {
    super.initState();
    _initControllers();
    _updateParticleRegistration(force: true);
    _startAnimations();
  }

  void _initControllers() {
    // Shimmer sweep animation (3s cycle)
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2400),
    );

    // Glow pulse animation (1.6s cycle)
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    );

    // Orbital particles animation (3s cycle)
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    );

    // Border rotation animation (4s cycle for Epic, 2.5s for Legendary)
    _borderRotationController = AnimationController(
      vsync: this,
      duration: _getBorderRotationDuration(),
    );

    registerController(
      _shimmerController,
      onResume: () => _shimmerController.repeat(),
    );
    registerController(
      _glowController,
      onResume: () => _glowController.repeat(reverse: true),
    );
    registerController(
      _particleController,
      onResume: () => _particleController.repeat(),
    );
    registerController(
      _borderRotationController,
      onResume: () => _borderRotationController.repeat(),
    );
  }

  Duration _getBorderRotationDuration() {
    final level = _getRarityLevel();
    switch (level) {
      case _RarityLevel.epic:
        return const Duration(milliseconds: 4000);
      case _RarityLevel.legendary:
        return const Duration(milliseconds: 2500);
      default:
        return const Duration(milliseconds: 4000);
    }
  }

  void _startAnimations() {
    if (_reduceMotion) return;
    final level = _getRarityLevel();

    // Shimmer for rare+
    if (widget.showShimmer && level.index >= _RarityLevel.rare.index) {
      _shimmerController.repeat();
    }

    // Glow for newly unlocked
    if (widget.showGlow && _isActuallyNewlyUnlocked) {
      _glowController.repeat(reverse: true);
    }

    // Particles for epic+ when enabled
    if (_particlesEnabled) {
      _particleController.repeat();
    }

    // Border rotation for epic+
    if (level.index >= _RarityLevel.epic.index) {
      _borderRotationController.repeat();
    }
  }

  void _stopAnimations() {
    _shimmerController.stop();
    _glowController.stop();
    _particleController.stop();
    _borderRotationController.stop();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final reduceMotion = context.reduceMotion;
    if (reduceMotion == _reduceMotion) return;
    _reduceMotion = reduceMotion;
    if (_reduceMotion) {
      _stopAnimations();
      _releaseParticles();
    } else {
      _updateParticleRegistration(force: true);
      _startAnimations();
    }
  }

  bool get _isActuallyNewlyUnlocked {
    if (widget.isNewlyUnlocked) return true;
    final unlockedAt = widget.unlockedAt;
    if (unlockedAt == null) return false;
    return DateTime.now().difference(unlockedAt) < newlyUnlockedWindow;
  }

  _RarityLevel _getRarityLevel() {
    final rarity = widget.rarity;
    if (rarity is AchievementRarity) {
      switch (rarity) {
        case AchievementRarity.common:
          return _RarityLevel.common;
        case AchievementRarity.rare:
          return _RarityLevel.rare;
        case AchievementRarity.epic:
          return _RarityLevel.epic;
        case AchievementRarity.legendary:
          return _RarityLevel.legendary;
      }
    } else if (rarity is VisualElementRarity) {
      switch (rarity) {
        case VisualElementRarity.common:
          return _RarityLevel.common;
        case VisualElementRarity.rare:
          return _RarityLevel.rare;
        case VisualElementRarity.epic:
          return _RarityLevel.epic;
        case VisualElementRarity.legendary:
          return _RarityLevel.legendary;
      }
    }
    return _RarityLevel.common;
  }

  Color _getRarityColor() {
    final rarity = widget.rarity;
    if (rarity is AchievementRarity) {
      return _getAchievementRarityColor(rarity);
    } else if (rarity is VisualElementRarity) {
      return _getVisualElementRarityColor(rarity);
    }
    return DS.neutral400;
  }

  Color _getAchievementRarityColor(AchievementRarity rarity) {
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

  Color _getVisualElementRarityColor(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return DS.rarityCommon;
      case VisualElementRarity.rare:
        return DS.rarityRare;
      case VisualElementRarity.epic:
        return DS.rarityEpic;
      case VisualElementRarity.legendary:
        return DS.rarityLegendary;
    }
  }

  List<Color> _getGradientColors() {
    final level = _getRarityLevel();
    final baseColor = _getRarityColor();

    switch (level) {
      case _RarityLevel.common:
        return [baseColor];
      case _RarityLevel.rare:
        return [baseColor, baseColor.withValues(alpha: 0.7)];
      case _RarityLevel.epic:
        return [baseColor, baseColor.withValues(alpha: 0.8), baseColor.withValues(alpha: 0.6)];
      case _RarityLevel.legendary:
        return [DS.error, DS.warning, DS.success, DS.info];
    }
  }

  @override
  void didUpdateWidget(RarityVisualWrapper oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.rarity != oldWidget.rarity) {
      _borderRotationController.duration = _getBorderRotationDuration();
    }
    if (widget.rarity != oldWidget.rarity ||
        widget.showShimmer != oldWidget.showShimmer ||
        widget.showGlow != oldWidget.showGlow ||
        widget.showParticles != oldWidget.showParticles ||
        widget.isNewlyUnlocked != oldWidget.isNewlyUnlocked) {
      _shimmerController.reset();
      _glowController.reset();
      _particleController.reset();
      _borderRotationController.reset();
      _updateParticleRegistration(force: true);
      _startAnimations();
    }
  }

  @override
  void dispose() {
    _releaseParticles();
    _shimmerController.dispose();
    _glowController.dispose();
    _particleController.dispose();
    _borderRotationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_reduceMotion) {
      return _buildStaticVersion(context);
    }
    return _buildAnimatedVersion(context);
  }

  Widget _buildAnimatedVersion(BuildContext context) {
    final level = _getRarityLevel();
    final rarityColor = _getRarityColor();
    final particleColor = _getAdaptiveParticleColor(
      rarityColor,
      Theme.of(context).brightness,
    );

    final children = <Widget>[widget.child];

    // Shimmer layer (for rare+)
    if (widget.showShimmer && level.index >= _RarityLevel.rare.index) {
      children.add(
        Positioned.fill(
          child: _ShimmerLayer(
            controller: _shimmerController,
            rarityColor: rarityColor,
            borderRadius: widget.borderRadius,
          ),
        ),
      );
    }

    // Glow layer (for newly unlocked)
    if (widget.showGlow && _isActuallyNewlyUnlocked) {
      children.add(
        Positioned.fill(
          child: _GlowLayer(
            controller: _glowController,
            rarityColor: rarityColor,
            borderRadius: widget.borderRadius,
          ),
        ),
      );
    }

    // Rotating gradient border (for epic+)
    if (level.index >= _RarityLevel.epic.index) {
      children.add(
        Positioned.fill(
          child: _RotatingGradientBorder(
            controller: _borderRotationController,
            colors: _getGradientColors(),
            borderRadius: widget.borderRadius,
            borderWidth: level == _RarityLevel.legendary ? 2.5 : 2.0,
          ),
        ),
      );
    }

    // Orbital particles (for epic+ when showParticles is true)
    if (_particlesEnabled) {
      final particleCount = level == _RarityLevel.legendary ? 4 : 2;
      children.add(
        Positioned.fill(
          child: _OrbitalParticlesLayer(
            controller: _particleController,
            rarityColor: particleColor,
            particleCount: particleCount,
          ),
        ),
      );
    }

    return Stack(children: children);
  }

  Widget _buildStaticVersion(BuildContext context) {
    final level = _getRarityLevel();
    final children = <Widget>[widget.child];

    if (level.index >= _RarityLevel.epic.index) {
      children.add(
        Positioned.fill(
          child: CustomPaint(
            painter: _RotatingGradientBorderPainter(
              rotation: 0,
              colors: _getGradientColors(),
              borderRadius: widget.borderRadius,
              borderWidth: level == _RarityLevel.legendary ? 2.5 : 2.0,
            ),
          ),
        ),
      );
    }

    return Stack(children: children);
  }

  Color _getAdaptiveParticleColor(Color baseColor, Brightness brightness) {
    if (brightness == Brightness.dark) return baseColor;
    return baseColor.withValues(
      alpha: (baseColor.a * 1.3).clamp(0.0, 1.0),
    );
  }

  void _releaseParticles() {
    if (_registeredParticleCount > 0) {
      GlobalParticleCounter.releaseParticles(_registeredParticleCount);
      _registeredParticleCount = 0;
    }
    _particlesEnabled = false;
  }

  void _updateParticleRegistration({bool force = false}) {
    final level = _getRarityLevel();
    final wantsParticles =
        widget.showParticles && level.index >= _RarityLevel.epic.index;
    final desiredCount = wantsParticles && !_reduceMotion
        ? (level == _RarityLevel.legendary ? 4 : 2)
        : 0;

    if (!force && desiredCount == _registeredParticleCount) {
      return;
    }

    _releaseParticles();

    if (desiredCount > 0 &&
        GlobalParticleCounter.tryAddParticles(desiredCount)) {
      _registeredParticleCount = desiredCount;
      _particlesEnabled = true;
    }
  }
}

// ---------------------------------------------------------------------------
// Shimmer Layer
// ---------------------------------------------------------------------------

class _ShimmerLayer extends StatelessWidget {
  const _ShimmerLayer({
    required this.controller,
    required this.rarityColor,
    required this.borderRadius,
  });

  final AnimationController controller;
  final Color rarityColor;
  final BorderRadius borderRadius;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: controller,
        builder: (context, _) {
          final sweepPosition = -1.0 + controller.value * 3.0;
          return ClipRRect(
            borderRadius: borderRadius,
            child: Opacity(
              opacity: 0.1,
              child: ShaderMask(
                shaderCallback: (bounds) => LinearGradient(
                  begin: Alignment(sweepPosition - 0.3, 0),
                  end: Alignment(sweepPosition + 0.3, 0),
                  colors: [
                    Colors.transparent,
                    rarityColor,
                    Colors.transparent,
                  ],
                  stops: const [0.0, 0.5, 1.0],
                ).createShader(bounds),
                blendMode: BlendMode.srcATop,
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: borderRadius,
                  ),
                ),
              ),
            ),
          );
        },
      );
}

// ---------------------------------------------------------------------------
// Glow Layer
// ---------------------------------------------------------------------------

class _GlowLayer extends StatelessWidget {
  const _GlowLayer({
    required this.controller,
    required this.rarityColor,
    required this.borderRadius,
  });

  final AnimationController controller;
  final Color rarityColor;
  final BorderRadius borderRadius;

  @override
  Widget build(BuildContext context) {
    final glowAnimation = Tween<double>(begin: 0.15, end: 0.5).animate(
      CurvedAnimation(parent: controller, curve: Curves.easeInOut),
    );

    return AnimatedBuilder(
      animation: glowAnimation,
      builder: (context, _) => IgnorePointer(
        child: Container(
          decoration: BoxDecoration(
            borderRadius: borderRadius,
            border: Border.all(
              color: rarityColor.withValues(alpha: glowAnimation.value),
              width: 2.5,
            ),
            boxShadow: [
              BoxShadow(
                color: rarityColor.withValues(alpha: glowAnimation.value * 0.6),
                blurRadius: 16,
                spreadRadius: 2,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Rotating Gradient Border
// ---------------------------------------------------------------------------

class _RotatingGradientBorder extends StatelessWidget {
  const _RotatingGradientBorder({
    required this.controller,
    required this.colors,
    required this.borderRadius,
    required this.borderWidth,
  });

  final AnimationController controller;
  final List<Color> colors;
  final BorderRadius borderRadius;
  final double borderWidth;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: controller,
        builder: (context, _) => CustomPaint(
          painter: _RotatingGradientBorderPainter(
            rotation: controller.value * 2 * math.pi,
            colors: colors,
            borderRadius: borderRadius,
            borderWidth: borderWidth,
          ),
        ),
      );
}

class _RotatingGradientBorderPainter extends CustomPainter {
  _RotatingGradientBorderPainter({
    required this.rotation,
    required this.colors,
    required this.borderRadius,
    required this.borderWidth,
  });

  final double rotation;
  final List<Color> colors;
  final BorderRadius borderRadius;
  final double borderWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final rrect = borderRadius.toRRect(rect);

    // Create rotating gradient
    final gradient = SweepGradient(
      center: Alignment.center,
      startAngle: rotation,
      endAngle: rotation + 2 * math.pi,
      colors: colors,
      stops: _getStops(),
    );

    final paint = Paint()
      ..shader = gradient.createShader(rect)
      ..style = PaintingStyle.stroke
      ..strokeWidth = borderWidth;

    canvas.drawRRect(rrect, paint);
  }

  List<double> _getStops() {
    final count = colors.length;
    return List.generate(count, (i) => i / (count - 1));
  }

  @override
  bool shouldRepaint(covariant _RotatingGradientBorderPainter old) =>
      rotation != old.rotation;
}

// ---------------------------------------------------------------------------
// Orbital Particles Layer
// ---------------------------------------------------------------------------

class _OrbitalParticlesLayer extends StatelessWidget {
  const _OrbitalParticlesLayer({
    required this.controller,
    required this.rarityColor,
    required this.particleCount,
  });

  final AnimationController controller;
  final Color rarityColor;
  final int particleCount;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: controller,
        builder: (context, _) => CustomPaint(
          painter: _OrbitalParticlesPainter(
            animValue: controller.value,
            rarityColor: rarityColor,
            particleCount: particleCount,
          ),
          size: Size.infinite,
        ),
      );
}

class _OrbitalParticlesPainter extends CustomPainter {
  _OrbitalParticlesPainter({
    required this.animValue,
    required this.rarityColor,
    required this.particleCount,
  });

  final double animValue;
  final Color rarityColor;
  final int particleCount;

  @override
  void paint(Canvas canvas, Size size) {
    if (GlobalParticleCounter.isOverLimit) return;
    final center = Offset(size.width / 2, size.height / 2);
    final baseRadius = (size.width + size.height) / 4;

    final paint = Paint()..style = PaintingStyle.fill;

    for (var i = 0; i < particleCount; i++) {
      final orbitRadius = baseRadius * (0.9 + i * 0.15);
      final speed = 1.0 + i * 0.3;
      final phase = (i * math.pi * 2 / particleCount);
      final angle = animValue * math.pi * 2 * speed + phase;

      final px = center.dx + math.cos(angle) * orbitRadius;
      final py = center.dy + math.sin(angle) * orbitRadius;

      // Outer glow
      paint.color = rarityColor.withValues(alpha: 0.25);
      paint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);
      canvas.drawCircle(Offset(px, py), 2.5, paint);

      // Core
      paint.color = rarityColor.withValues(alpha: 0.7);
      paint.maskFilter = null;
      canvas.drawCircle(Offset(px, py), 1.2, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _OrbitalParticlesPainter old) =>
      animValue != old.animValue;
}

// ---------------------------------------------------------------------------
// Rarity Level Enum
// ---------------------------------------------------------------------------

enum _RarityLevel {
  common,
  rare,
  epic,
  legendary,
}
