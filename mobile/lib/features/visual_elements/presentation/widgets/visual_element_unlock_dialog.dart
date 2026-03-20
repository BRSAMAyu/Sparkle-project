import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/global_particle_counter.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// Visual Element unlock celebration dialog
///
/// Displays tiered celebration effects based on rarity:
/// - Common: Toast + entry fade
/// - Rare: Toast + entry glow (2s)
/// - Epic: Mini confetti (15 particles) + glow pulse
/// - Legendary: Full-screen particle explosion (40 particles) + screen shake
class VisualElementUnlockDialog extends StatefulWidget {
  const VisualElementUnlockDialog({
    required this.elements,
    super.key,
    this.onClose,
    this.onView,
    this.reduceMotion = false,
  });

  /// The newly unlocked visual elements
  final List<VisualElementModel> elements;

  /// Callback when dialog is closed
  final VoidCallback? onClose;

  /// Callback when user wants to view the elements
  final VoidCallback? onView;
  final bool reduceMotion;

  /// Show the unlock dialog
  static Future<void> show(
    BuildContext context, {
    required List<VisualElementModel> elements,
    VoidCallback? onClose,
    VoidCallback? onView,
    bool barrierDismissible = true,
  }) =>
      showGeneralDialog(
        context: context,
        barrierDismissible: barrierDismissible,
        barrierLabel: 'Visual Element Unlock',
        barrierColor: DS.textPrimary.withValues(alpha: 0.7),
        transitionDuration: const Duration(milliseconds: 600),
        pageBuilder: (context, animation, secondaryAnimation) =>
            VisualElementUnlockDialog(
          elements: elements,
          onClose: onClose,
          onView: onView,
          reduceMotion: context.reduceMotion,
        ),
        transitionBuilder: (context, animation, secondaryAnimation, child) =>
            _VisualElementUnlockTransition(
          animation: animation,
          highestRarity: _getHighestRarity(elements),
          reduceMotion: context.reduceMotion,
          child: child,
        ),
      );

  /// Get the highest rarity from a list of elements
  static VisualElementRarity _getHighestRarity(List<VisualElementModel> elements) {
    if (elements.isEmpty) return VisualElementRarity.common;
    return elements
        .map((e) => e.rarity)
        .reduce((a, b) => _rarityLevel(b) > _rarityLevel(a) ? b : a);
  }

  static int _rarityLevel(VisualElementRarity r) {
    switch (r) {
      case VisualElementRarity.common:
        return 0;
      case VisualElementRarity.rare:
        return 1;
      case VisualElementRarity.epic:
        return 2;
      case VisualElementRarity.legendary:
        return 3;
    }
  }

  @override
  State<VisualElementUnlockDialog> createState() =>
      _VisualElementUnlockDialogState();
}

class _VisualElementUnlockDialogState extends State<VisualElementUnlockDialog>
    with TickerProviderStateMixin {
  late AnimationController _scaleController;
  late AnimationController _particleController;
  late AnimationController _glowController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _glowAnimation;
  int _registeredParticleCount = 0;
  bool _particlesEnabled = false;

  bool get _reduceMotion => widget.reduceMotion;

  @override
  void initState() {
    super.initState();
    _initAnimations();
  }

  void _initAnimations() {
    // Scale animation for entrance
    _scaleController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(
        parent: _scaleController,
        curve: Curves.elasticOut,
      ),
    );
    if (_reduceMotion) {
      _scaleController.value = 1.0;
    } else {
      _scaleController.forward();
    }

    // Particle animation for Epic/Legendary
    _particleController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );

    // Glow animation
    _glowController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _glowAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(
        parent: _glowController,
        curve: Curves.easeInOut,
      ),
    );

    if (_reduceMotion) {
      _glowController.value = 1.0;
    }

    _updateParticleRegistration(force: true);
    if (!_reduceMotion) {
      _startRarityAnimations();
    }
    _triggerHapticFeedback();
  }

  void _startRarityAnimations() {
    final highestRarity = VisualElementUnlockDialog._getHighestRarity(widget.elements);

    switch (highestRarity) {
      case VisualElementRarity.common:
        // Just fade in
        break;
      case VisualElementRarity.rare:
        // Glow animation
        _glowController.repeat(reverse: true);
        break;
      case VisualElementRarity.epic:
        // Particles + glow
        _glowController.repeat(reverse: true);
        if (_particlesEnabled) {
          _particleController.repeat();
        }
        break;
      case VisualElementRarity.legendary:
        // Full effects + screen shake
        _glowController.repeat(reverse: true);
        if (_particlesEnabled) {
          _particleController.repeat();
        }
        break;
    }
  }

  int _particleBudgetForRarity(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.legendary:
        return 40;
      case VisualElementRarity.epic:
        return 15;
      case VisualElementRarity.rare:
      case VisualElementRarity.common:
        return 0;
    }
  }

  void _updateParticleRegistration({bool force = false}) {
    final highestRarity =
        VisualElementUnlockDialog._getHighestRarity(widget.elements);
    final desiredCount =
        _reduceMotion ? 0 : _particleBudgetForRarity(highestRarity);

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

  void _triggerHapticFeedback() {
    final highestRarity = VisualElementUnlockDialog._getHighestRarity(widget.elements);

    switch (highestRarity) {
      case VisualElementRarity.common:
        HapticFeedback.lightImpact();
        break;
      case VisualElementRarity.rare:
        HapticFeedback.lightImpact();
        break;
      case VisualElementRarity.epic:
        HapticFeedback.mediumImpact();
        break;
      case VisualElementRarity.legendary:
        HapticFeedback.heavyImpact();
        // Double tap for legendary
        Future.delayed(const Duration(milliseconds: 200), () {
          if (mounted) HapticFeedback.heavyImpact();
        });
        break;
    }
  }

  @override
  void didUpdateWidget(covariant VisualElementUnlockDialog oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.elements != widget.elements ||
        oldWidget.reduceMotion != widget.reduceMotion) {
      _updateParticleRegistration(force: true);
      if (_reduceMotion) {
        _particleController.stop();
        _glowController.stop();
      } else {
        _startRarityAnimations();
      }
    }
  }

  @override
  void dispose() {
    _releaseParticles();
    _scaleController.dispose();
    _particleController.dispose();
    _glowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final highestRarity = VisualElementUnlockDialog._getHighestRarity(widget.elements);
    final colors = _getRarityColors(highestRarity);
    final l10n = context.l10n;

    return Dialog(
      backgroundColor: Colors.transparent,
      elevation: 0,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Background effects (for Epic/Legendary)
          if (!_reduceMotion &&
              (highestRarity == VisualElementRarity.epic ||
                  highestRarity == VisualElementRarity.legendary))
            _buildBackgroundEffects(highestRarity),

          // Particle overlay
          if (_particlesEnabled)
            _buildParticleOverlay(highestRarity),

          // Main content
          _buildContent(context, colors, l10n, highestRarity),
        ],
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    _RarityColors colors,
    AppLocalizations l10n,
    VisualElementRarity highestRarity,
  ) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final dialogWidth = math.min(constraints.maxWidth - 48, 340.0);
        final compact = dialogWidth < 300;

        return ConstrainedBox(
          constraints: BoxConstraints(maxWidth: dialogWidth),
          child: AnimatedBuilder(
            animation: _scaleAnimation,
            builder: (context, _) => Transform.scale(
              scale: _scaleAnimation.value,
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  Positioned.fill(
                    child: IgnorePointer(
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(26),
                          gradient: RadialGradient(
                            center: const Alignment(0.0, -0.3),
                            radius: 1.05,
                            colors: [
                              colors.glow.withValues(alpha: 0.28),
                              colors.glow.withValues(alpha: 0.08),
                              Colors.transparent,
                            ],
                            stops: const [0.0, 0.42, 1.0],
                          ),
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    top: -22,
                    right: compact ? 12 : 18,
                    child: IgnorePointer(
                      child: Container(
                        width: compact ? 58 : 72,
                        height: compact ? 58 : 72,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              Colors.white.withValues(alpha: 0.22),
                              colors.primary.withValues(alpha: 0.12),
                              Colors.transparent,
                            ],
                            stops: const [0.0, 0.5, 1.0],
                          ),
                        ),
                      ),
                    ),
                  ),
                  Container(
                    width: dialogWidth,
                    padding: EdgeInsets.all(compact ? DS.spacing20 : DS.spacing24),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          colors.primary.withValues(alpha: 0.95),
                          colors.secondary.withValues(alpha: 0.9),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(
                        color: colors.border,
                        width: 2,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: colors.glow.withValues(alpha: 0.72),
                          blurRadius: 32,
                          spreadRadius: 4,
                        ),
                      ],
                    ),
                    child: Stack(
                      children: [
                        Positioned.fill(
                          child: IgnorePointer(
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(24),
                                gradient: LinearGradient(
                                  begin: Alignment.topCenter,
                                  end: Alignment.bottomCenter,
                                  colors: [
                                    Colors.white.withValues(alpha: 0.14),
                                    Colors.transparent,
                                    DS.surfacePrimary.withValues(alpha: 0.08),
                                  ],
                                  stops: const [0.0, 0.35, 1.0],
                                ),
                              ),
                            ),
                          ),
                        ),
                        Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            _buildRarityIndicator(highestRarity, l10n),
                            const SizedBox(height: DS.spacing16),
                            _buildIconContainer(colors, highestRarity, _reduceMotion),
                            const SizedBox(height: DS.spacing16),
                            Text(
                              l10n.visualElementUnlockTitle,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: compact ? DS.fontSizeLg : DS.fontSizeXl,
                                fontWeight: DS.fontWeightBold,
                                color: colors.text,
                              ),
                            ),
                            const SizedBox(height: DS.spacing8),
                            Text(
                              l10n.visualElementUnlockSubtitle,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: DS.fontSizeBase,
                                color: colors.text.withValues(alpha: 0.8),
                              ),
                            ),
                            const SizedBox(height: DS.spacing16),
                            if (widget.elements.isNotEmpty) ...[
                              _buildElementsPreview(compact),
                              const SizedBox(height: DS.spacing20),
                            ],
                            _buildActionButtons(context, colors, l10n, compact),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildRarityIndicator(VisualElementRarity rarity, AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: DS.surfacePrimary.withValues(alpha: 0.2),
        borderRadius: DS.borderRadiusFull,
        border: Border.all(
          color: DS.textPrimary.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _getRarityIcon(rarity),
            size: DS.iconSizeXs,
            color: DS.textPrimary.withValues(alpha: 0.9),
          ),
          const SizedBox(width: DS.spacing6),
          Text(
            _getRarityLabel(rarity, l10n),
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              fontWeight: DS.fontWeightMedium,
              color: DS.textPrimary.withValues(alpha: 0.9),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildIconContainer(
    _RarityColors colors,
    VisualElementRarity rarity,
    bool reduceMotion,
  ) {
    if (reduceMotion) {
      return Container(
        width: 80,
        height: 80,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              colors.primary,
              colors.secondary,
            ],
          ),
          boxShadow: [
            BoxShadow(
              color: colors.glow.withValues(alpha: 0.35),
              blurRadius: 20,
              spreadRadius: 1,
            ),
          ],
        ),
        child: Icon(
          _getUnlockIcon(rarity),
          size: 40,
          color: Colors.white,
        ),
      );
    }

    return AnimatedBuilder(
      animation: _glowAnimation,
      builder: (context, child) => Container(
        width: 80,
        height: 80,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              colors.primary,
              colors.secondary,
            ],
          ),
          boxShadow: [
            BoxShadow(
              color: colors.glow.withValues(alpha: _glowAnimation.value * 0.5),
              blurRadius: 24,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Icon(
          _getUnlockIcon(rarity),
          size: 40,
          color: Colors.white,
        ),
      ),
    );
  }

  Widget _buildElementsPreview(bool compact) {
    final displayElements = widget.elements.take(3).toList();
    final hasMore = widget.elements.length > 3;

    return Wrap(
      spacing: DS.spacing8,
      runSpacing: DS.spacing8,
      alignment: WrapAlignment.center,
      children: [
        ...displayElements.map((element) => Container(
              constraints: BoxConstraints(
                maxWidth: compact ? 80 : 100,
              ),
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing8,
                vertical: DS.spacing6,
              ),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    DS.surfacePrimary.withValues(alpha: 0.94),
                    _getElementColor(element.rarity).withValues(alpha: 0.08),
                  ],
                ),
                borderRadius: DS.borderRadius8,
                border: Border.all(
                  color: _getElementColor(element.rarity).withValues(alpha: 0.5),
                ),
                boxShadow: [
                  BoxShadow(
                    color: _getElementColor(element.rarity).withValues(alpha: 0.08),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    _getElementTypeIcon(element.elementType),
                    size: DS.iconSizeXs,
                    color: _getElementColor(element.rarity),
                  ),
                  const SizedBox(width: DS.spacing4),
                  Flexible(
                    child: Text(
                      element.name,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        fontWeight: DS.fontWeightMedium,
                        color: DS.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            )),
        if (hasMore)
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing8,
              vertical: DS.spacing6,
            ),
            decoration: BoxDecoration(
              color: DS.surfaceSecondary.withValues(alpha: 0.9),
              borderRadius: DS.borderRadius8,
            ),
            child: Text(
              '+${widget.elements.length - 3}',
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightMedium,
                color: DS.textSecondary,
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildActionButtons(
    BuildContext context,
    _RarityColors colors,
    AppLocalizations l10n,
    bool compact,
  ) {
    if (compact) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildButton(
            label: l10n.close,
            isPrimary: false,
            colors: colors,
            onPressed: () {
              Navigator.of(context).pop();
              widget.onClose?.call();
            },
          ),
          const SizedBox(height: DS.spacing12),
          if (widget.onView != null)
            _buildButton(
              label: l10n.visualElementViewCollection,
              isPrimary: true,
              colors: colors,
              onPressed: () {
                Navigator.of(context).pop();
                widget.onView?.call();
              },
            ),
        ],
      );
    }

    return Row(
      children: [
        Expanded(
          child: _buildButton(
            label: l10n.close,
            isPrimary: false,
            colors: colors,
            onPressed: () {
              Navigator.of(context).pop();
              widget.onClose?.call();
            },
          ),
        ),
        if (widget.onView != null) ...[
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: _buildButton(
              label: l10n.visualElementViewCollection,
              isPrimary: true,
              colors: colors,
              onPressed: () {
                Navigator.of(context).pop();
                widget.onView?.call();
              },
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildButton({
    required String label,
    required bool isPrimary,
    required _RarityColors colors,
    required VoidCallback onPressed,
  }) {
    return GestureDetector(
      onTap: onPressed,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing12),
        decoration: BoxDecoration(
          color: isPrimary ? colors.primary.withValues(alpha: 0.8) : null,
          border: Border.all(color: colors.border, width: 1.5),
          borderRadius: DS.borderRadius12,
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightMedium,
            color: colors.text,
          ),
        ),
      ),
    );
  }

  Widget _buildBackgroundEffects(VisualElementRarity rarity) {
    if (rarity == VisualElementRarity.legendary) {
      return AnimatedBuilder(
        animation: _particleController,
        builder: (context, child) {
          final progress = _particleController.value;
          return CustomPaint(
            size: const Size(400, 400),
            painter: _RainbowExplosionPainter(progress),
          );
        },
      );
    }
    // Epic pulsing waves
    return AnimatedBuilder(
      animation: _particleController,
      builder: (context, child) => Container(
        width: 400,
        height: 400,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(
            color: DS.rarityEpic.withValues(alpha: 0.2 * (1 - _particleController.value)),
            width: 3,
          ),
        ),
      ),
    );
  }

  Widget _buildParticleOverlay(VisualElementRarity rarity) {
    final particleCount = rarity == VisualElementRarity.legendary ? 40 : 15;
    return Positioned.fill(
      child: CustomPaint(
        painter: _UnlockParticlePainter(
          rarity: rarity,
          animation: _particleController,
          particleCount: particleCount,
        ),
      ),
    );
  }

  _RarityColors _getRarityColors(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return _RarityColors(
          primary: DS.neutral200,
          secondary: DS.neutral300,
          border: DS.neutral400,
          glow: DS.neutral400.withValues(alpha: 0.3),
          text: DS.neutral800,
        );
      case VisualElementRarity.rare:
        return _RarityColors(
          primary: DS.rarityRare,
          secondary: DS.warning,
          border: DS.rarityRare,
          glow: DS.rarityRare.withValues(alpha: 0.5),
          text: DS.rarityRareText,
        );
      case VisualElementRarity.epic:
        return _RarityColors(
          primary: DS.rarityEpic,
          secondary: DS.brandSecondary,
          border: DS.rarityEpic,
          glow: DS.rarityEpic.withValues(alpha: 0.6),
          text: DS.onBrandPrimary,
        );
      case VisualElementRarity.legendary:
        return _RarityColors(
          primary: DS.rarityLegendary,
          secondary: DS.info,
          border: DS.rarityRare,
          glow: DS.rarityRare.withValues(alpha: 0.7),
          text: DS.onBrandPrimary,
        );
    }
  }

  Color _getElementColor(VisualElementRarity rarity) {
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

  IconData _getRarityIcon(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return Icons.circle_outlined;
      case VisualElementRarity.rare:
        return Icons.star_border;
      case VisualElementRarity.epic:
        return Icons.auto_awesome;
      case VisualElementRarity.legendary:
        return Icons.diamond_outlined;
    }
  }

  String _getRarityLabel(VisualElementRarity rarity, AppLocalizations l10n) {
    switch (rarity) {
      case VisualElementRarity.common:
        return l10n.achievementRarityCommon;
      case VisualElementRarity.rare:
        return l10n.achievementRarityRare;
      case VisualElementRarity.epic:
        return l10n.achievementRarityEpic;
      case VisualElementRarity.legendary:
        return l10n.achievementRarityLegendary;
    }
  }

  IconData _getUnlockIcon(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return Icons.lock_open;
      case VisualElementRarity.rare:
        return Icons.card_giftcard;
      case VisualElementRarity.epic:
        return Icons.auto_awesome;
      case VisualElementRarity.legendary:
        return Icons.diamond;
    }
  }

  IconData _getElementTypeIcon(VisualElementType type) {
    switch (type) {
      case VisualElementType.background:
        return Icons.gradient;
      case VisualElementType.particle:
        return Icons.auto_awesome;
      case VisualElementType.effect:
        return Icons.blur_on;
      case VisualElementType.bundle:
        return Icons.inventory_2;
    }
  }
}

// ---------------------------------------------------------------------------
// Transition Animation
// ---------------------------------------------------------------------------

class _VisualElementUnlockTransition extends StatelessWidget {
  const _VisualElementUnlockTransition({
    required this.animation,
    required this.highestRarity,
    required this.reduceMotion,
    required this.child,
  });

  final Animation<double> animation;
  final VisualElementRarity highestRarity;
  final bool reduceMotion;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (reduceMotion) {
      return FadeTransition(
        opacity: CurvedAnimation(
          parent: animation,
          curve: Curves.easeOut,
        ),
        child: child,
      );
    }

    final curve = _getCurveForRarity();
    final curvedAnimation = CurvedAnimation(
      parent: animation,
      curve: curve,
    );

    switch (highestRarity) {
      case VisualElementRarity.common:
        return FadeTransition(
          opacity: curvedAnimation,
          child: ScaleTransition(
            scale: curvedAnimation,
            child: child,
          ),
        );
      case VisualElementRarity.rare:
        return FadeTransition(
          opacity: curvedAnimation,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.5, end: 1.0).animate(
              CurvedAnimation(parent: animation, curve: Curves.elasticOut),
            ),
            child: child,
          ),
        );
      case VisualElementRarity.epic:
      case VisualElementRarity.legendary:
        return FadeTransition(
          opacity: curvedAnimation,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.3, end: 1.0).animate(
              CurvedAnimation(parent: animation, curve: Curves.elasticOut),
            ),
            child: child,
          ),
        );
    }
  }

  Curve _getCurveForRarity() {
    switch (highestRarity) {
      case VisualElementRarity.common:
        return Curves.easeOut;
      case VisualElementRarity.rare:
        return Curves.easeOutBack;
      case VisualElementRarity.epic:
      case VisualElementRarity.legendary:
        return Curves.elasticOut;
    }
  }
}

// ---------------------------------------------------------------------------
// Rarity Colors
// ---------------------------------------------------------------------------

class _RarityColors {
  _RarityColors({
    required this.primary,
    required this.secondary,
    required this.border,
    required this.glow,
    required this.text,
  });

  final Color primary;
  final Color secondary;
  final Color border;
  final Color glow;
  final Color text;
}

// ---------------------------------------------------------------------------
// Particle Painter
// ---------------------------------------------------------------------------

class _UnlockParticlePainter extends CustomPainter {
  _UnlockParticlePainter({
    required this.rarity,
    required this.animation,
    required this.particleCount,
  });

  final VisualElementRarity rarity;
  final Animation<double> animation;
  final int particleCount;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final progress = animation.value;
    final random = math.Random(42);

    final baseColor = _getParticleBaseColor();

    for (var i = 0; i < particleCount; i++) {
      final angle = (i / particleCount) * 2 * math.pi + progress * 0.5;
      final distance = 50 + progress * 150;
      final x = center.dx + math.cos(angle) * distance;
      final y = center.dy + math.sin(angle) * distance;

      final particleSize = rarity == VisualElementRarity.legendary
          ? (4 + random.nextDouble() * 4) * (1 - progress * 0.5)
          : 3.0;

      final paint = Paint()
        ..color = baseColor.withValues(alpha: 0.6 * (1 - progress * 0.8))
        ..style = PaintingStyle.fill;

      canvas.drawCircle(Offset(x, y), particleSize, paint);
    }
  }

  Color _getParticleBaseColor() {
    switch (rarity) {
      case VisualElementRarity.rare:
        return DS.rarityRare;
      case VisualElementRarity.epic:
        return DS.rarityEpic;
      case VisualElementRarity.legendary:
        return DS.rarityLegendary;
      default:
        return DS.neutral400;
    }
  }

  @override
  bool shouldRepaint(covariant _UnlockParticlePainter old) =>
      animation.value != old.animation.value;
}

// ---------------------------------------------------------------------------
// Rainbow Explosion Painter
// ---------------------------------------------------------------------------

class _RainbowExplosionPainter extends CustomPainter {
  _RainbowExplosionPainter(this.progress);

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final colors = [
      DS.rarityLegendary,
      DS.rarityRare,
      DS.success,
      DS.info,
    ];

    for (var i = 0; i < colors.length; i++) {
      final radius = 80 + progress * 120 + i * 30;
      final paint = Paint()
        ..color = colors[i].withValues(alpha: (0.3 - progress * 0.25).clamp(0.0, 0.3))
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3;

      canvas.drawCircle(center, radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _RainbowExplosionPainter old) =>
      progress != old.progress;
}
