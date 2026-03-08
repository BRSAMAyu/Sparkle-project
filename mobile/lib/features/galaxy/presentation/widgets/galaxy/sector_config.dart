import 'dart:math' as math;
import 'dart:ui' show lerpDouble;

import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

/// Sector visual style configuration tuned for the galaxy canvas.
class SectorStyle {
  SectorStyle({
    required this.name,
    required this.darkPrimaryColor,
    required this.lightPrimaryColor,
    required this.baseAngle,
    required this.sweepAngle,
    this.keywords = const [],
  });

  final String name;
  final Color darkPrimaryColor;
  final Color lightPrimaryColor;
  final double baseAngle;
  final double sweepAngle;
  final List<String> keywords;

  // Legacy compatibility for existing widgets/services that still read these.
  Color get primaryColor => darkPrimaryColor;
  Color get glowColor => darkGlowColor;

  Color primaryColorFor({required bool isDarkMode}) =>
      isDarkMode ? darkPrimaryColor : lightPrimaryColor;

  Color glowColorFor({required bool isDarkMode}) =>
      _glowColorFor(primaryColorFor(isDarkMode: isDarkMode), isDarkMode);

  Color get darkGlowColor => _glowColorFor(darkPrimaryColor, true);
  Color get lightGlowColor => _glowColorFor(lightPrimaryColor, false);

  List<Color> paletteFor({required bool isDarkMode}) =>
      _generatePalette(primaryColorFor(isDarkMode: isDarkMode), isDarkMode);

  Color getColorByImportance(
    int importance, {
    required bool isDarkMode,
  }) {
    final palette = paletteFor(isDarkMode: isDarkMode);
    final index = (5 - importance).clamp(0, 4);
    return palette[index];
  }

  Color getColorByMastery(
    int importance,
    int masteryScore, {
    required bool isDarkMode,
  }) {
    final baseColor = getColorByImportance(
      importance,
      isDarkMode: isDarkMode,
    );
    final hsl = HSLColor.fromColor(baseColor);
    final targetLightness = (hsl.lightness + (isDarkMode ? 0.1 : 0.06)).clamp(
      isDarkMode ? 0.26 : 0.18,
      isDarkMode ? 0.82 : 0.66,
    );
    final t = (masteryScore / 100).clamp(0.0, 1.0);
    return HSLColor.fromAHSL(
      hsl.alpha,
      hsl.hue,
      hsl.saturation,
      lerpDouble(hsl.lightness, targetLightness, t)!,
    ).toColor();
  }

  static Color _glowColorFor(Color baseColor, bool isDarkMode) {
    final hsl = HSLColor.fromColor(baseColor);
    return HSLColor.fromAHSL(
      1,
      hsl.hue,
      (hsl.saturation * (isDarkMode ? 0.92 : 0.78)).clamp(0.2, 0.75),
      (hsl.lightness + (isDarkMode ? 0.1 : 0.12)).clamp(0.34, 0.84),
    ).toColor();
  }

  static List<Color> _generatePalette(Color primary, bool isDarkMode) {
    final hsl = HSLColor.fromColor(primary);
    return [
      _shade(
        hsl,
        saturationMultiplier: 1.15,
        lightnessMultiplier: 0.85,
        isDarkMode: isDarkMode,
      ),
      _shade(
        hsl,
        saturationMultiplier: 1.05,
        lightnessMultiplier: 0.92,
        isDarkMode: isDarkMode,
      ),
      primary,
      _shade(
        hsl,
        saturationMultiplier: 0.90,
        lightnessMultiplier: 1.08,
        isDarkMode: isDarkMode,
      ),
      _shade(
        hsl,
        saturationMultiplier: 0.75,
        lightnessMultiplier: 1.15,
        isDarkMode: isDarkMode,
      ),
    ];
  }

  static Color _shade(
    HSLColor color, {
    required double saturationMultiplier,
    required double lightnessMultiplier,
    required bool isDarkMode,
  }) {
    final minLightness = isDarkMode ? 0.24 : 0.18;
    final maxLightness = isDarkMode ? 0.82 : 0.72;
    return color
        .withSaturation(
          (color.saturation * saturationMultiplier).clamp(0.2, 0.82),
        )
        .withLightness(
          (color.lightness * lightnessMultiplier)
              .clamp(minLightness, maxLightness),
        )
        .toColor();
  }
}

class SectorConfig {
  static const double _sectorSweep = 51.43;

  static final Map<SectorEnum, SectorStyle> styles = {
    SectorEnum.cosmos: SectorStyle(
      name: '理性星域',
      darkPrimaryColor: const Color(0xFF78A3D1),
      lightPrimaryColor: const Color(0xFF386494),
      baseAngle: 0.0,
      sweepAngle: _sectorSweep,
      keywords: const ['数学', '物理', '化学', '天文', '逻辑学'],
    ),
    SectorEnum.tech: SectorStyle(
      name: '造物星域',
      darkPrimaryColor: const Color(0xFF5AB8CC),
      lightPrimaryColor: const Color(0xFF356E7B),
      baseAngle: _sectorSweep,
      sweepAngle: _sectorSweep,
      keywords: const ['计算机', '工程', 'AI', '建筑', '制造'],
    ),
    SectorEnum.art: SectorStyle(
      name: '灵感星域',
      darkPrimaryColor: const Color(0xFFC97C8F),
      lightPrimaryColor: const Color(0xFF955061),
      baseAngle: _sectorSweep * 2,
      sweepAngle: _sectorSweep,
      keywords: const ['设计', '音乐', '绘画', '文学', 'ACG'],
    ),
    SectorEnum.civilization: SectorStyle(
      name: '文明星域',
      darkPrimaryColor: const Color(0xFFD0A05F),
      lightPrimaryColor: const Color(0xFFA16B2A),
      baseAngle: _sectorSweep * 3,
      sweepAngle: _sectorSweep,
      keywords: const ['历史', '经济', '政治', '社会学', '法律'],
    ),
    SectorEnum.life: SectorStyle(
      name: '生活星域',
      darkPrimaryColor: const Color(0xFF5FAF80),
      lightPrimaryColor: const Color(0xFF3A8552),
      baseAngle: _sectorSweep * 4,
      sweepAngle: _sectorSweep,
      keywords: const ['健身', '烹饪', '医学', '心理', '理财'],
    ),
    SectorEnum.wisdom: SectorStyle(
      name: '智慧星域',
      darkPrimaryColor: const Color(0xFFA181C8),
      lightPrimaryColor: const Color(0xFF67478F),
      baseAngle: _sectorSweep * 5,
      sweepAngle: _sectorSweep,
      keywords: const ['哲学', '宗教', '方法论', '元认知'],
    ),
    SectorEnum.voidSector: SectorStyle(
      name: '暗物质区',
      darkPrimaryColor: const Color(0xFF70798B),
      lightPrimaryColor: const Color(0xFF8A93A8),
      baseAngle: _sectorSweep * 6,
      sweepAngle: _sectorSweep,
      keywords: const ['未归类', '跨领域', '新兴概念'],
    ),
  };

  static SectorStyle getStyle(SectorEnum sector) =>
      styles[sector] ?? styles[SectorEnum.voidSector]!;

  static Color getColor(
    SectorEnum sector, {
    bool isDarkMode = true,
  }) =>
      getStyle(sector).primaryColorFor(isDarkMode: isDarkMode);

  static Color getGlowColor(
    SectorEnum sector, {
    bool isDarkMode = true,
  }) =>
      getStyle(sector).glowColorFor(isDarkMode: isDarkMode);

  static Color getNodeColor({
    required SectorEnum sector,
    required int importance,
    int masteryScore = 0,
    bool isDarkMode = true,
  }) {
    final style = getStyle(sector);
    return style.getColorByMastery(
      importance,
      masteryScore,
      isDarkMode: isDarkMode,
    );
  }

  static Color getNodeColorByImportance(
    SectorEnum sector,
    int importance, {
    bool isDarkMode = true,
  }) {
    final style = getStyle(sector);
    return style.getColorByImportance(importance, isDarkMode: isDarkMode);
  }

  static Color applyImportanceRamp(
    Color baseColor, {
    required int importance,
    required bool isDarkMode,
  }) {
    final hsl = HSLColor.fromColor(baseColor);
    final multipliers = switch (importance.clamp(1, 5)) {
      5 => (1.15, 0.85),
      4 => (1.05, 0.92),
      3 => (1.0, 1.0),
      2 => (0.90, 1.08),
      _ => (0.75, 1.15),
    };
    return HSLColor.fromAHSL(
      hsl.alpha,
      hsl.hue,
      (hsl.saturation * multipliers.$1).clamp(0.2, 0.82),
      (hsl.lightness * multipliers.$2)
          .clamp(isDarkMode ? 0.24 : 0.18, isDarkMode ? 0.82 : 0.72),
    ).toColor();
  }

  static Color computeBlendedColor({
    required GalaxyNodeModel node,
    required Iterable<GalaxyNodeModel> neighbors,
    required bool isDarkMode,
  }) {
    final baseSector = node.sector;
    final baseColor = getColor(baseSector, isDarkMode: isDarkMode);
    if (baseSector == SectorEnum.voidSector) {
      return baseColor;
    }

    var totalNeighbors = 0;
    var crossNeighbors = 0;
    final sectorCounts = <SectorEnum, int>{};

    for (final neighbor in neighbors) {
      totalNeighbors++;
      if (neighbor.sector == baseSector ||
          neighbor.sector == SectorEnum.voidSector) {
        continue;
      }
      crossNeighbors++;
      sectorCounts.update(
        neighbor.sector,
        (count) => count + 1,
        ifAbsent: () => 1,
      );
    }

    if (totalNeighbors == 0 || crossNeighbors == 0 || sectorCounts.isEmpty) {
      return baseColor;
    }

    final crossColor = _averageColors(
      sectorCounts.entries
          .map(
            (entry) => (
              getColor(entry.key, isDarkMode: isDarkMode),
              entry.value.toDouble(),
            ),
          )
          .toList(growable: false),
    );
    final crossRatio = crossNeighbors / totalNeighbors;
    return lerpInHsl(
      baseColor,
      crossColor,
      0.3 * crossRatio.clamp(0.0, 1.0),
      clampSaturationMin: 0.2,
    );
  }

  static Color lerpInHsl(
    Color a,
    Color b,
    double t, {
    double clampSaturationMin = 0.0,
  }) {
    final first = HSLColor.fromColor(a);
    final second = HSLColor.fromColor(b);
    final normalizedT = t.clamp(0.0, 1.0);
    final hue = _lerpHue(first.hue, second.hue, normalizedT);
    final saturation = lerpDouble(
      first.saturation,
      second.saturation,
      normalizedT,
    )!
        .clamp(clampSaturationMin, 0.9);
    final lightness = lerpDouble(
      first.lightness,
      second.lightness,
      normalizedT,
    )!
        .clamp(0.18, 0.82);

    return HSLColor.fromAHSL(
      lerpDouble(first.alpha, second.alpha, normalizedT)!,
      hue,
      saturation,
      lightness,
    ).toColor();
  }

  static double getSectorCenterAngleRadians(SectorEnum sector) {
    final style = getStyle(sector);
    final centerDegrees = style.baseAngle + style.sweepAngle / 2;
    return centerDegrees * math.pi / 180.0;
  }

  static bool isAngleInSector(double angleDegrees, SectorEnum sector) {
    final style = getStyle(sector);
    final normalized = angleDegrees % 360;
    final start = style.baseAngle;
    final end = start + style.sweepAngle;
    return normalized >= start && normalized < end;
  }

  static SectorEnum getSectorForAngle(double angleDegrees) {
    final normalized = angleDegrees % 360;
    for (final entry in styles.entries) {
      if (isAngleInSector(normalized, entry.key)) {
        return entry.key;
      }
    }
    return SectorEnum.voidSector;
  }

  static SectorEnum getSectorForPosition(Offset position) {
    final degrees =
        (math.atan2(position.dy, position.dx) * 180 / math.pi + 90 + 360) % 360;
    return getSectorForAngle(degrees);
  }

  static Color _averageColors(List<(Color, double)> weightedColors) {
    if (weightedColors.isEmpty) {
      return Colors.white;
    }

    var totalWeight = 0.0;
    var sumSin = 0.0;
    var sumCos = 0.0;
    var sumSaturation = 0.0;
    var sumLightness = 0.0;

    for (final entry in weightedColors) {
      final color = HSLColor.fromColor(entry.$1);
      final weight = entry.$2;
      totalWeight += weight;
      final hueRadians = color.hue * math.pi / 180;
      sumSin += math.sin(hueRadians) * weight;
      sumCos += math.cos(hueRadians) * weight;
      sumSaturation += color.saturation * weight;
      sumLightness += color.lightness * weight;
    }

    final averagedHue =
        (math.atan2(sumSin, sumCos) * 180 / math.pi + 360) % 360;
    return HSLColor.fromAHSL(
      1,
      averagedHue,
      (sumSaturation / totalWeight).clamp(0.2, 0.82),
      (sumLightness / totalWeight).clamp(0.18, 0.82),
    ).toColor();
  }

  static double _lerpHue(double a, double b, double t) {
    final delta = ((b - a + 540) % 360) - 180;
    return (a + delta * t + 360) % 360;
  }
}
