import 'dart:math';

import 'package:flutter/material.dart';

class ThemeUtils {
  const ThemeUtils._();

  static Color getContrastSafeText(
    Color backgroundColor, {
    Color lightText = Colors.white,
    Color darkText = Colors.black,
    double minContrast = 4.5,
  }) {
    final lightRatio = _contrastRatio(backgroundColor, lightText);
    final darkRatio = _contrastRatio(backgroundColor, darkText);

    if (lightRatio >= minContrast && lightRatio >= darkRatio) {
      return lightText;
    }
    if (darkRatio >= minContrast && darkRatio >= lightRatio) {
      return darkText;
    }

    return lightRatio >= darkRatio ? lightText : darkText;
  }

  /// 渐变/双端卡面前景墨色（V4-G06）：固定美术渐变的两端明度可能横跨
  /// 阈值，任一固定墨色必有一端失败。取「双端都达 [minContrast]」的
  /// 候选；都不达时取两端最小对比更高者（调用方按 ACCESSIBILITY_ASSETS
  /// 阈值登记残余风险，不以 fallback 冒充达标）。
  static Color getContrastSafeTextOnGradient(
    Color endA,
    Color endB, {
    Color lightText = Colors.white,
    Color darkText = Colors.black,
    double minContrast = 4.5,
  }) {
    final lightMin = min(
      _contrastRatio(lightText, endA),
      _contrastRatio(lightText, endB),
    );
    final darkMin = min(
      _contrastRatio(darkText, endA),
      _contrastRatio(darkText, endB),
    );

    if (lightMin >= minContrast && lightMin >= darkMin) {
      return lightText;
    }
    if (darkMin >= minContrast && darkMin >= lightMin) {
      return darkText;
    }

    return lightMin >= darkMin ? lightText : darkText;
  }

  /// 给定墨色在渐变两端的最小对比（供守卫钉报告实际下界，不重复实现
  /// 公式；与 [getContrastSafeTextOnGradient] 同一口径）。
  static double minContrastOnGradient(
    Color text,
    Color endA,
    Color endB,
  ) =>
      min(_contrastRatio(text, endA), _contrastRatio(text, endB));

  static double _contrastRatio(Color a, Color b) {
    final luminanceA = a.computeLuminance();
    final luminanceB = b.computeLuminance();
    final lighter = max(luminanceA, luminanceB);
    final darker = min(luminanceA, luminanceB);
    return (lighter + 0.05) / (darker + 0.05);
  }
}
