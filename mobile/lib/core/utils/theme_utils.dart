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

  static double _contrastRatio(Color a, Color b) {
    final luminanceA = a.computeLuminance();
    final luminanceB = b.computeLuminance();
    final lighter = max(luminanceA, luminanceB);
    final darker = min(luminanceA, luminanceB);
    return (lighter + 0.05) / (darker + 0.05);
  }
}
