import 'dart:ui';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class GlassCard extends StatelessWidget {
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

  const GlassCard({
    required this.child, super.key,
    this.width,
    this.height,
    this.margin,
    this.padding = const EdgeInsets.all(16.0),
    this.borderRadius,
    this.color,
    this.blurSigma = 10.0,
    this.opacity = 0.1,
    this.shadows,
    this.onTap,
    this.enableTapEffect = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // Default glass color based on theme
    final defaultColor = isDark 
        ? AppDesignTokens.neutral900.withOpacity(opacity) 
        : Colors.white.withOpacity(opacity);
    
    // Default border radius
    final defaultBorderRadius = borderRadius ?? AppDesignTokens.borderRadius20;
    
    // Default shadows
    final defaultShadows = shadows ?? [
      BoxShadow(
        color: isDark 
