import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';

class GlassCard extends StatefulWidget {

  GlassCard({
    required this.child,
    super.key,
    this.width,
    this.height,
    this.margin,
    this.padding = EdgeInsets.all(DS.lg),
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

class _GlassCardState extends State<GlassCard> with SingleTickerProviderStateMixin {
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
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // Default glass color based on theme
    final defaultColor = widget.color ?? (isDark 
        ? DS.neutral900.withValues(alpha: widget.opacity)
        : DS.brandPrimary.withValues(alpha: widget.opacity));

    final borderColor = isDark
        ? DS.brandPrimary.withValues(alpha: 0.1)
        : DS.brandPrimary.withValues(alpha: 0.2);

    // Default border radius
    final defaultBorderRadius = widget.borderRadius ?? DS.borderRadius20;

    // Default shadows - subtly customized for glass effect
    final defaultShadows = widget.shadows ?? [
      BoxShadow(
        color: isDark ? DS.brandPrimary.withValues(alpha: 0.3) : DS.brandPrimary.withValues(alpha: 0.05),
        blurRadius: 16,
        offset: const Offset(0, 8),
      ),
    ];

    final Widget content = Container(
      width: widget.width,
      height: widget.height,
      margin: widget.margin,
      decoration: BoxDecoration(
        color: defaultColor,
        borderRadius: defaultBorderRadius,
        border: Border.all(color: borderColor),
        boxShadow: defaultShadows,
      ),
      child: ClipRRect(
        borderRadius: defaultBorderRadius,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: widget.blurSigma, sigmaY: widget.blurSigma),
          child: Padding(
            padding: widget.padding,
            child: widget.child,
          ),
        ),
      ),
    );

    if (widget.onTap != null) {
      if (widget.enableTapEffect) {
        return GestureDetector(
          onTapDown: (_) => _controller.forward(),
          onTapUp: (_) => _controller.reverse(),
          onTapCancel: () => _controller.reverse(),
          onTap: () {
            HapticFeedback.lightImpact();
            widget.onTap!();
          },
          child: ScaleTransition(
            scale: _scaleAnimation,
            child: content,
          ),
        );
      } else {
        return GestureDetector(
          onTap: () {
            HapticFeedback.lightImpact();
            widget.onTap!();
          },
          child: content,
        );
      }
    }

    return content;
  }
}