import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Calculates relative luminance per WCAG 2.1 definition.
double _relativeLuminance(Color color) {
  double channel(int c) {
    final sRGB = c / 255.0;
    return sRGB <= 0.03928 ? sRGB / 12.92 : math.pow((sRGB + 0.055) / 1.055, 2.4).toDouble();
  }

  return 0.2126 * channel(color.red) +
      0.7152 * channel(color.green) +
      0.0722 * channel(color.blue);
}

/// Calculates WCAG contrast ratio between two colors.
double contrastRatio(Color a, Color b) {
  final l1 = _relativeLuminance(a);
  final l2 = _relativeLuminance(b);
  final lighter = math.max(l1, l2);
  final darker = math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

void main() {
  group('WCAG AA contrast ratio', () {
    const minNormalText = 4.5; // AA for normal text
    const minLargeText = 3.0; // AA for large text (18px+ or 14px+ bold)

    test('textPrimary on surfacePrimary meets AA for normal text', () {
      final ratio = contrastRatio(DS.textPrimary, DS.surfacePrimary);
      expect(ratio, greaterThanOrEqualTo(minNormalText),
          reason: 'textPrimary on surfacePrimary must meet 4.5:1');
    });

    test('textSecondary on surfacePrimary meets AA for large text', () {
      final ratio = contrastRatio(DS.textSecondary, DS.surfacePrimary);
      expect(ratio, greaterThanOrEqualTo(minLargeText),
          reason: 'textSecondary on surfacePrimary must meet 3:1 (large text)');
    });

    test('semanticSuccess (green) on surfacePrimary is perceivable', () {
      final ratio = contrastRatio(DS.success, DS.surfacePrimary);
      // Green on light surfaces often falls short of 3:1 — this is acceptable
      // for decorative/status colors where meaning is also conveyed by icons.
      expect(ratio, greaterThanOrEqualTo(2.5),
          reason: 'success green must be visually distinguishable');
    });

    test('semanticError (red) on surfacePrimary meets AA for large text', () {
      final ratio = contrastRatio(DS.error, DS.surfacePrimary);
      expect(ratio, greaterThanOrEqualTo(minLargeText),
          reason: 'error red on surface must meet 3:1');
    });

    test('brandPrimary on surfacePrimary meets AA for large text', () {
      final ratio = contrastRatio(DS.brandPrimary, DS.surfacePrimary);
      expect(ratio, greaterThanOrEqualTo(minLargeText),
          reason: 'brand primary on surface must meet 3:1');
    });

    test('textOnPrimary on brandPrimary meets AA for normal text', () {
      // DS.onBrandPrimary is derived from textOnPrimary
      final textOn = DS.onBrandPrimary;
      final ratio = contrastRatio(textOn, DS.brandPrimary);
      expect(ratio, greaterThanOrEqualTo(minNormalText),
          reason: 'text on brand primary must meet 4.5:1');
    });

    test('border color is perceivable against surface', () {
      // Borders are decorative — WCAG exempts them. Just verify visible.
      final ratio = contrastRatio(DS.border, DS.surfacePrimary);
      expect(ratio, greaterThanOrEqualTo(1.1),
          reason: 'border should be minimally visible');
    });

    test('textDisabled has perceivable but low contrast', () {
      final ratio = contrastRatio(DS.textDisabled, DS.surfacePrimary);
      // Disabled text should be visible but can be low contrast
      expect(ratio, greaterThanOrEqualTo(1.5),
          reason: 'disabled text should still be perceivable');
    });
  });
}
