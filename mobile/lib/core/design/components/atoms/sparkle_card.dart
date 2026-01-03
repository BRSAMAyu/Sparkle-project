import 'package:flutter/material.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';

/// Sparkle card surface using semantic tokens.
class SparkleCard extends StatelessWidget {
  const SparkleCard({
    required this.child,
    super.key,
    this.padding,
    this.margin,
    this.backgroundColor,
    this.borderColor,
    this.borderRadius,
    this.elevation,
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final Color? backgroundColor;
  final Color? borderColor;
  final BorderRadius? borderRadius;
  final double? elevation;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final radius = borderRadius ?? context.radius.mdRadius;
    final color = backgroundColor ?? context.colors.surfaceSecondary;
    final borderSide = BorderSide(color: borderColor ?? context.colors.borderDefault);
    final content = Padding(
      padding: padding ?? context.space.edge(all: context.space.md),
      child: child,
    );

    return Container(
      margin: margin,
      child: Material(
        color: color,
        elevation: elevation ?? 0,
        shape: RoundedRectangleBorder(borderRadius: radius, side: borderSide),
        clipBehavior: Clip.antiAlias,
        child: onTap == null
            ? content
            : InkWell(
                onTap: onTap,
                borderRadius: radius,
                splashColor: context.colors.brandPrimary.withValues(alpha: 0.12),
                highlightColor: context.colors.brandPrimary.withValues(alpha: 0.06),
                child: content,
              ),
      ),
    );
  }
}
