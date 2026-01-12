import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_card.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';

@Deprecated(
    'Use SparkleCard with glass effect parameters. Will be removed in v2.0',)
class GlassCard extends StatefulWidget {
  const GlassCard({
    required this.child,
    super.key,
    this.width,
    this.height,
    this.margin,
    this.padding = const EdgeInsets.all(DS.lg),
    this.borderRadius,
    this.color,
    this.blurSigma = 10.0,
    this.opacity = 0.1,
    this.shadows,
    this.onTap,
    this.enableTapEffect = false,
  });
  final Widget child;
  final double? width;
  final double? height;
  final EdgeInsetsGeometry? margin;
  final EdgeInsetsGeometry padding;
  final BorderRadius? borderRadius;
  final Color? color;
  final double blurSigma;
  final double opacity;
  final List<BoxShadow>? shadows;
  final VoidCallback? onTap;
  final bool enableTapEffect;

  @override
  State<GlassCard> createState() => _GlassCardState();
}

class _GlassCardState extends State<GlassCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 100),
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.98).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Create SparkleCard with glass effect
    // Don't pass onTap to SparkleCard when enableTapEffect is true (handled by animation wrapper)
    final sparkleCard = SparkleCard(
      padding: widget.padding,
      margin: widget.margin,
      backgroundColor: _getGlassColor(context),
      borderColor: _getBorderColor(context),
      borderRadius: widget.borderRadius,
      onTap: widget.onTap != null && !widget.enableTapEffect
          ? () {
              HapticFeedback.lightImpact();
              widget.onTap!();
            }
          : null,
      child: widget.child,
    );

    // Wrap with width/height constraints if specified
    Widget content = sparkleCard;
    if (widget.width != null || widget.height != null) {
      content = SizedBox(
        width: widget.width,
        height: widget.height,
        child: sparkleCard,
      );
    }

    // Apply glass blur effect
    final glassContent = BackdropFilter(
      filter:
          ImageFilter.blur(sigmaX: widget.blurSigma, sigmaY: widget.blurSigma),
      child: content,
    );

    // Add tap animation if enabled
    if (widget.onTap != null && widget.enableTapEffect) {
      return _buildAnimatedGlassCard(glassContent);
    }

    return glassContent;
  }

  Color _getGlassColor(BuildContext context) {
    final baseColor =
        widget.color ?? SparkleContextExtension(context).colors.surfacePrimary;
    return baseColor.withValues(alpha: widget.opacity);
  }

  Color _getBorderColor(BuildContext context) =>
      SparkleContextExtension(context)
          .colors
          .surfaceSecondary
          .withValues(alpha: 0.2);

  Widget _buildAnimatedGlassCard(Widget glassContent) => GestureDetector(
        onTapDown: (_) => _controller.forward(),
        onTapUp: (_) => _controller.reverse(),
        onTapCancel: () => _controller.reverse(),
        onTap: () {
          HapticFeedback.lightImpact();
          widget.onTap!();
        },
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: glassContent,
        ),
      );
}
