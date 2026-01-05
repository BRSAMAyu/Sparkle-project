import 'package:flutter/material.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/design/tokens/color_tokens_v2.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart'
    show SparkleSpacing, SparkleTypography;

/// Theme extension for semantic design tokens.
///
/// UI must NOT check isDark/brightness directly. Use these tokens instead.
@immutable
class SparkleThemeExtension extends ThemeExtension<SparkleThemeExtension> {
  const SparkleThemeExtension({
    required this.colors,
    required this.typography,
    required this.spacing,
    required this.radius,
    required this.motion,
    required this.performanceTier,
  });

  factory SparkleThemeExtension.light(
          {PerformanceTier tier = PerformanceTier.high,}) =>
      SparkleThemeExtension(
        colors: const SparkleColors(brightness: Brightness.light),
        typography: SparkleTypography.standard(),
        spacing: const SparkleSpacing(),
        radius: const SparkleRadius(),
        motion: const SparkleMotionTokens(),
        performanceTier: tier,
      );

  factory SparkleThemeExtension.dark(
          {PerformanceTier tier = PerformanceTier.high,}) =>
      SparkleThemeExtension(
        colors: const SparkleColors(brightness: Brightness.dark),
        typography: SparkleTypography.standard(),
        spacing: const SparkleSpacing(),
        radius: const SparkleRadius(),
        motion: const SparkleMotionTokens(),
        performanceTier: tier,
      );

  final SparkleColors colors;
  final SparkleTypography typography;
  final SparkleSpacing spacing;
  final SparkleRadius radius;
  final SparkleMotionTokens motion;
  final PerformanceTier performanceTier;

  bool get enableBlur => performanceTier == PerformanceTier.high;
  bool get enableGlow => performanceTier == PerformanceTier.high;
  bool get enableComplexAnimation => performanceTier != PerformanceTier.low;

  @override
  SparkleThemeExtension copyWith({
    SparkleColors? colors,
    SparkleTypography? typography,
    SparkleSpacing? spacing,
    SparkleRadius? radius,
    SparkleMotionTokens? motion,
    PerformanceTier? performanceTier,
  }) =>
      SparkleThemeExtension(
        colors: colors ?? this.colors,
        typography: typography ?? this.typography,
        spacing: spacing ?? this.spacing,
        radius: radius ?? this.radius,
        motion: motion ?? this.motion,
        performanceTier: performanceTier ?? this.performanceTier,
      );

  @override
  SparkleThemeExtension lerp(
      ThemeExtension<SparkleThemeExtension>? other, double t,) {
    if (other is! SparkleThemeExtension) return this;
    // Tokens are discrete; switch at midpoint.
    return t < 0.5 ? this : other;
  }
}

/// Minimal radius tokens.
/// TODO: Align with unified radius system when available.
@immutable
class SparkleRadius {
  const SparkleRadius({
    this.xs = 4.0,
    this.sm = 8.0,
    this.md = 12.0,
    this.lg = 16.0,
    this.xl = 20.0,
    this.full = 999.0,
  });

  final double xs;
  final double sm;
  final double md;
  final double lg;
  final double xl;
  final double full;

  BorderRadius circular(double radius) => BorderRadius.circular(radius);
  BorderRadius get xsRadius => BorderRadius.circular(xs);
  BorderRadius get smRadius => BorderRadius.circular(sm);
  BorderRadius get mdRadius => BorderRadius.circular(md);
  BorderRadius get lgRadius => BorderRadius.circular(lg);
  BorderRadius get xlRadius => BorderRadius.circular(xl);
  BorderRadius get fullRadius => BorderRadius.circular(full);
}

/// Minimal motion tokens backed by SparkleMotion.
/// TODO: Replace with a full motion token system when available.
@immutable
class SparkleMotionTokens {
  const SparkleMotionTokens({
    this.instant = SparkleMotion.instant,
    this.fast = SparkleMotion.fast,
    this.normal = SparkleMotion.normal,
    this.slow = SparkleMotion.slow,
    this.slower = SparkleMotion.slower,
    this.standardCurve = SparkleMotion.standard,
    this.enterCurve = SparkleMotion.enter,
    this.exitCurve = SparkleMotion.exit,
    this.bounceCurve = SparkleMotion.bounce,
    this.overshootCurve = SparkleMotion.overshoot,
  });

  final Duration instant;
  final Duration fast;
  final Duration normal;
  final Duration slow;
  final Duration slower;
  final Curve standardCurve;
  final Curve enterCurve;
  final Curve exitCurve;
  final Curve bounceCurve;
  final Curve overshootCurve;
}
