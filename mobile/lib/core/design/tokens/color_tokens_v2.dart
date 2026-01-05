import 'package:flutter/material.dart';

/// Sparkle design color tokens (v2).
///
/// NOTE: Brightness decisions live only in this design layer.
/// UI must NOT perform isDark/brightness checks.
@immutable
class SparkleColors {
  const SparkleColors({required this.brightness});

  final Brightness brightness;

  bool get _isDark => brightness == Brightness.dark;

  // Brand
  Color get brandPrimary => _RawColors.brandBlue;
  Color get brandSecondary => _RawColors.brandPurple;
  Color get ctaAccent => _RawColors.sparkOrange;

  // Surfaces
  Color get surfacePrimary =>
      _isDark ? _RawColors.neutral900 : _RawColors.white;
  Color get surfaceSecondary =>
      _isDark ? _RawColors.neutral800 : _RawColors.neutral200;
  Color get surfaceTertiary =>
      _isDark ? _RawColors.neutral700 : _RawColors.neutral300;

  // Text
  Color get textPrimary => _isDark ? _RawColors.white : _RawColors.neutral900;
  Color get textSecondary =>
      _isDark ? _RawColors.neutral300 : _RawColors.neutral600;
  Color get textMuted => textSecondary.withValues(alpha: 0.7);

  // Borders / dividers
  Color get borderDefault =>
      _isDark ? _RawColors.neutral700 : _RawColors.neutral300;
  Color get divider => borderDefault;

  // Semantic colors
  Color get semanticSuccess => _isDark
      ? _RawColors.semanticSuccessDark
      : _RawColors.semanticSuccessLight;
  Color get semanticWarning => _RawColors.semanticWarning;
  Color get semanticError => _RawColors.semanticError;

  // Task colors
  Color get taskSocial => _RawColors.taskSocial;

  // Gradients
  LinearGradient get brandGradient => LinearGradient(
        colors: _isDark
            ? _RawColors.brandGradientDark
            : _RawColors.brandGradientLight,
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );

  // User chat bubble gradient must be cold brand gradient (no orange).
  LinearGradient get userChatBubbleGradient => brandGradient;
}

/// Private raw palette. Do not export or use directly in UI.
class _RawColors {
  _RawColors._();

  static const Color white = Color(0xFFFFFFFF);

  static const Color neutral200 = Color(0xFFF5F5F5);
  static const Color neutral300 = Color(0xFFE0E0E0);
  static const Color neutral600 = Color(0xFF757575);
  static const Color neutral700 = Color(0xFF424242);
  static const Color neutral800 = Color(0xFF1E1E1E);
  static const Color neutral900 = Color(0xFF121212);

  static const Color brandBlue = Color(0xFF4361EE);
  static const Color brandPurple = Color(0xFF7209B7);
  static const Color brandCyan = Color(0xFF4CC9F0);

  static const Color sparkOrange = Color(0xFFFF6B35);
  static const Color taskSocial = Color(0xFFFFB703);
  static const Color semanticSuccessLight = Color(0xFF2E7D32);
  static const Color semanticSuccessDark = Color(0xFF66BB6A);
  static const Color semanticWarning = Color(0xFFFFA000);
  static const Color semanticError = Color(0xFFE53935);

  static const List<Color> brandGradientLight = [
    brandCyan,
    brandBlue,
  ];

  static const List<Color> brandGradientDark = [
    brandBlue,
    brandPurple,
  ];
}
