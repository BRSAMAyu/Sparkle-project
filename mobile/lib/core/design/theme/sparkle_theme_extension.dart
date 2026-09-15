import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/design/tokens/task_colors.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart'
    show SparkleColors, SparkleSpacing, SparkleTypography, ThemeManager;

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
    required this.taskColors,
  });

  factory SparkleThemeExtension.light({
    PerformanceTier tier = PerformanceTier.high,
    SparkleColors? colors,
    SparkleTypography? typography,
    SparkleSpacing? spacing,
  }) =>
      SparkleThemeExtension(
        colors: colors ??
            ThemeManager().themeForBrightness(Brightness.light).colors,
        typography: typography ?? SparkleTypography.standard(),
        spacing: spacing ?? const SparkleSpacing(),
        radius: const SparkleRadius(),
        motion: const SparkleMotionTokens(),
        performanceTier: tier,
        taskColors: const TaskColors(brightness: Brightness.light),
      );

  factory SparkleThemeExtension.dark({
    PerformanceTier tier = PerformanceTier.high,
    SparkleColors? colors,
    SparkleTypography? typography,
    SparkleSpacing? spacing,
  }) =>
      SparkleThemeExtension(
        colors:
            colors ?? ThemeManager().themeForBrightness(Brightness.dark).colors,
        typography: typography ?? SparkleTypography.standard(),
        spacing: spacing ?? const SparkleSpacing(),
        radius: const SparkleRadius(),
        motion: const SparkleMotionTokens(),
        performanceTier: tier,
        taskColors: const TaskColors(brightness: Brightness.dark),
      );

  final SparkleColors colors;
  final SparkleTypography typography;
  final SparkleSpacing spacing;
  final SparkleRadius radius;
  final SparkleMotionTokens motion;
  final PerformanceTier performanceTier;
  final TaskColors taskColors;

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
    TaskColors? taskColors,
  }) =>
      SparkleThemeExtension(
        colors: colors ?? this.colors,
        typography: typography ?? this.typography,
        spacing: spacing ?? this.spacing,
        radius: radius ?? this.radius,
        motion: motion ?? this.motion,
        performanceTier: performanceTier ?? this.performanceTier,
        taskColors: taskColors ?? this.taskColors,
      );

  @override
  SparkleThemeExtension lerp(
    ThemeExtension<SparkleThemeExtension>? other,
    double t,
  ) {
    if (other is! SparkleThemeExtension) return this;
    return SparkleThemeExtension(
      colors: colors.lerp(other.colors, t),
      typography: t < 0.5 ? typography : other.typography,
      spacing: t < 0.5 ? spacing : other.spacing,
      radius: radius.lerp(other.radius, t),
      motion: t < 0.5 ? motion : other.motion,
      performanceTier: t < 0.5 ? performanceTier : other.performanceTier,
      taskColors: t < 0.5 ? taskColors : other.taskColors,
    );
  }
}

/// Minimal radius tokens.
/// TRACKED(TD-010): Align with unified radius system when available.
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

  SparkleRadius lerp(SparkleRadius other, double t) => SparkleRadius(
        xs: lerpDouble(xs, other.xs, t)!,
        sm: lerpDouble(sm, other.sm, t)!,
        md: lerpDouble(md, other.md, t)!,
        lg: lerpDouble(lg, other.lg, t)!,
        xl: lerpDouble(xl, other.xl, t)!,
        full: t < 0.5 ? full : other.full,
      );
}

/// Minimal motion tokens backed by SparkleMotion.
/// TRACKED(TD-010): Replace with a full motion token system when available.
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
