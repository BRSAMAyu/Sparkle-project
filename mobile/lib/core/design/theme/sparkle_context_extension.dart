import 'package:flutter/material.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/design/tokens/color_tokens_v2.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart'
    show SparkleSpacing, SparkleTypography;

/// BuildContext helpers for Sparkle design tokens.
extension SparkleContextExtension on BuildContext {
  SparkleThemeExtension get sparkle {
    final extension = Theme.of(this).extension<SparkleThemeExtension>();
    assert(extension != null,
        'SparkleThemeExtension is not registered on ThemeData.',);
    return extension!;
  }

  SparkleColors get colors => sparkle.colors;
  SparkleTypography get typo => sparkle.typography;
  SparkleSpacing get space => sparkle.spacing;
  SparkleRadius get radius => sparkle.radius;
  SparkleMotionTokens get motion => sparkle.motion;

  bool get canBlur => sparkle.enableBlur;
  bool get canGlow => sparkle.enableGlow;
  bool get canComplexAnimate => sparkle.enableComplexAnimation;
}
