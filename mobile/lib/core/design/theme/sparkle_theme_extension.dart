import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart'
    show SparkleColors, SparkleSpacing, SparkleTypography, ThemeManager;

/// 刺激水平档位（U-02 低刺激模式）。
///
/// - [StimulationLevel.standard]：常规档，动效/装饰预算全额（默认档，
///   即低刺激"默认关"）。
/// - [StimulationLevel.low]：低刺激档——动效时长收缩、弹性/过冲曲线
///   撤除、庆祝类装饰预算归零。是"设计减法"的令牌表达，不是空设置值：
///   经 [resolveSparkleMotionTokens] 与 `SparkleStateTokens.forMood`
///   输出与 standard 档不同的真实参数。
enum StimulationLevel { standard, low }

/// 按刺激水平解析动效令牌（U-02 两档真源）。
///
/// standard 档返回既有 [SparkleMotionTokens] 默认值（行为零变化）；
/// low 档：
/// - 时长整体收缩（转场更快落定，减少屏幕运动滞留时间）；
/// - `bounceCurve`（弹性）/`overshootCurve`（过冲）替换为 easeOut
///   ——弹性/过冲是奖励性噪声（DESIGN_DIRECTION：动效解释状态变化，
///   不作为奖励噪声），低刺激下撤除。
/// 其余曲线（standard/enter/exit）保持语义不变。
SparkleMotionTokens resolveSparkleMotionTokens(StimulationLevel level) {
  if (level == StimulationLevel.standard) return const SparkleMotionTokens();
  return const SparkleMotionTokens(
    fast: Duration(milliseconds: 80),
    normal: Duration(milliseconds: 150),
    slow: Duration(milliseconds: 200),
    slower: Duration(milliseconds: 240),
    bounceCurve: Curves.easeOut,
    overshootCurve: Curves.easeOut,
  );
}

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
    this.stimulationLevel = StimulationLevel.standard,
  });

  factory SparkleThemeExtension.light({
    PerformanceTier tier = PerformanceTier.high,
    SparkleColors? colors,
    SparkleTypography? typography,
    SparkleSpacing? spacing,
    StimulationLevel stimulationLevel = StimulationLevel.standard,
  }) =>
      SparkleThemeExtension(
        colors: colors ??
            ThemeManager().themeForBrightness(Brightness.light).colors,
        typography: typography ?? SparkleTypography.standard(),
        spacing: spacing ?? const SparkleSpacing(),
        radius: const SparkleRadius(),
        motion: resolveSparkleMotionTokens(stimulationLevel),
        performanceTier: tier,
        stimulationLevel: stimulationLevel,
      );

  factory SparkleThemeExtension.dark({
    PerformanceTier tier = PerformanceTier.high,
    SparkleColors? colors,
    SparkleTypography? typography,
    SparkleSpacing? spacing,
    StimulationLevel stimulationLevel = StimulationLevel.standard,
  }) =>
      SparkleThemeExtension(
        colors:
            colors ?? ThemeManager().themeForBrightness(Brightness.dark).colors,
        typography: typography ?? SparkleTypography.standard(),
        spacing: spacing ?? const SparkleSpacing(),
        radius: const SparkleRadius(),
        motion: resolveSparkleMotionTokens(stimulationLevel),
        performanceTier: tier,
        stimulationLevel: stimulationLevel,
      );

  final SparkleColors colors;
  final SparkleTypography typography;
  final SparkleSpacing spacing;
  final SparkleRadius radius;
  final SparkleMotionTokens motion;
  final PerformanceTier performanceTier;
  final StimulationLevel stimulationLevel;

  bool get enableBlur => performanceTier == PerformanceTier.high;
  bool get enableGlow => performanceTier == PerformanceTier.high;
  bool get enableComplexAnimation => performanceTier != PerformanceTier.low;

  /// 当前是否低刺激档（U-02）。装饰/动效消费点据此取减法后的预算。
  bool get lowStimulation => stimulationLevel == StimulationLevel.low;

  @override
  SparkleThemeExtension copyWith({
    SparkleColors? colors,
    SparkleTypography? typography,
    SparkleSpacing? spacing,
    SparkleRadius? radius,
    SparkleMotionTokens? motion,
    PerformanceTier? performanceTier,
    StimulationLevel? stimulationLevel,
  }) =>
      SparkleThemeExtension(
        colors: colors ?? this.colors,
        typography: typography ?? this.typography,
        spacing: spacing ?? this.spacing,
        radius: radius ?? this.radius,
        // 档位切换时动效令牌随之重解析（两档输出真实不同）；
        // 显式传入 motion 时以显式值为准。
        motion: motion ??
            resolveSparkleMotionTokens(
              stimulationLevel ?? this.stimulationLevel,
            ),
        performanceTier: performanceTier ?? this.performanceTier,
        stimulationLevel: stimulationLevel ?? this.stimulationLevel,
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
      stimulationLevel: t < 0.5 ? stimulationLevel : other.stimulationLevel,
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
