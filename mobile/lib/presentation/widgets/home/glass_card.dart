import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// GlassCard - Glassmorphism styled card for v2.3 dashboard
///
/// Features:
/// - Frosted glass effect with backdrop blur
/// - Subtle border glow
/// - Optional breathing animation for new content
class GlassCard extends StatefulWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final double? width;
  final double? height;
  final VoidCallback? onTap;
  final bool isBreathing;
  final Color? glowColor;
  final int crossAxisCellCount;
  final int mainAxisCellCount;

  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.width,
    this.height,
    this.onTap,
    this.isBreathing = false,
    this.glowColor,
    this.crossAxisCellCount = 1,
    this.mainAxisCellCount = 1,
  });

  @override
  State<GlassCard> createState() => _GlassCardState();
}

class _GlassCardState extends State<GlassCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _breathingController;
  late Animation<double> _breathingAnimation;

  @override
  void initState() {
    super.initState();
    _breathingController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    );
    _breathingAnimation = Tween<double>(begin: 0.15, end: 0.35).animate(
      CurvedAnimation(parent: _breathingController, curve: Curves.easeInOut),
    );
    if (widget.isBreathing) {
      _breathingController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(GlassCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isBreathing && !_breathingController.isAnimating) {
      _breathingController.repeat(reverse: true);
    } else if (!widget.isBreathing && _breathingController.isAnimating) {
      _breathingController.stop();
    }
  }

  @override
  void dispose() {
    _breathingController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final glowColor = widget.glowColor ?? AppDesignTokens.primaryBase;

    Widget card = AnimatedBuilder(
      animation: _breathingAnimation,
      builder: (context, child) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: AppDesignTokens.borderRadius20,
            border: Border.all(
              color: widget.isBreathing
                  ? glowColor.withOpacity(_breathingAnimation.value)
                  : AppDesignTokens.glassBorder,
              width: widget.isBreathing ? 1.5 : 1,
            ),
            boxShadow: widget.isBreathing
                ? [
                    BoxShadow(
                      color: glowColor.withOpacity(_breathingAnimation.value * 0.5),
                      blurRadius: 20,
                      spreadRadius: 2,
                    ),
                  ]
                : null,
          ),
          child: ClipRRect(
            borderRadius: AppDesignTokens.borderRadius20,
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
              child: Container(
                decoration: BoxDecoration(
                  color: AppDesignTokens.glassBackground,
                  borderRadius: AppDesignTokens.borderRadius20,
                ),
                padding: widget.padding ?? const EdgeInsets.all(16),
                child: widget.child,
              ),
            ),
          ),
        );
      },
    );

    if (widget.onTap != null) {
      card = GestureDetector(
        onTap: widget.onTap,
        child: card,
      );
    }

    return card;
  }
}

/// StaggeredTile helper for Bento Grid layout
class BentoTile {
  final int crossAxisCellCount;
  final int mainAxisCellCount;

  const BentoTile({
    required this.crossAxisCellCount,
    required this.mainAxisCellCount,
  });

  /// 2x2 large card (Focus Card)
  static const BentoTile large = BentoTile(crossAxisCellCount: 2, mainAxisCellCount: 2);

  /// 2x1 wide card (Next Actions)
  static const BentoTile wide = BentoTile(crossAxisCellCount: 2, mainAxisCellCount: 1);

  /// 1x1 small card (Prism, Sprint)
  static const BentoTile small = BentoTile(crossAxisCellCount: 1, mainAxisCellCount: 1);

  /// 1x2 tall card
  static const BentoTile tall = BentoTile(crossAxisCellCount: 1, mainAxisCellCount: 2);
}
