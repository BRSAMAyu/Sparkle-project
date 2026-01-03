import 'package:flutter/material.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';

/// Sparkle pressable surface that reads semantic tokens from ThemeExtension.
class SparklePressable extends StatelessWidget {
  const SparklePressable({
    required this.child,
    super.key,
    this.onTap,
    this.onLongPress,
    this.enabled = true,
    this.padding,
    this.margin,
    this.borderRadius,
    this.backgroundColor,
    this.border,
    this.semanticLabel,
  });

  final Widget child;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final bool enabled;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final BorderRadius? borderRadius;
  final Color? backgroundColor;
  final BorderSide? border;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final radius = borderRadius ?? context.radius.smRadius;
    final background = backgroundColor ?? Colors.transparent;
    final side = border ?? BorderSide.none;

    return Semantics(
      button: onTap != null,
      enabled: enabled && onTap != null,
      label: semanticLabel,
      child: Container(
        margin: margin,
        child: Material(
          color: background,
          shape: RoundedRectangleBorder(borderRadius: radius, side: side),
          child: InkWell(
            onTap: enabled ? onTap : null,
            onLongPress: enabled ? onLongPress : null,
            borderRadius: radius,
            splashColor: context.colors.brandPrimary.withValues(alpha: 0.12),
            highlightColor: context.colors.brandPrimary.withValues(alpha: 0.06),
            child: Padding(
              padding: padding ?? context.space.edge(horizontal: context.space.sm, vertical: context.space.xs),
              child: child,
            ),
          ),
        ),
      ),
    );
  }
}
