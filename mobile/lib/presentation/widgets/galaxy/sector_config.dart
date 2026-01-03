import 'package:flutter/painting.dart';
import 'package:sparkle/data/models/galaxy_model.dart';

/// Sector visual style configuration
class SectorStyle {

  SectorStyle({
    required this.name,
    required this.primaryColor,
    required this.glowColor,
    required this.baseAngle,
    required this.sweepAngle,
    this.keywords = const [],
  }) {
    // 生成星域调色板
    colorPalette = _generatePalette(primaryColor);
  }
  final String name;
  final Color primaryColor;
  final Color glowColor;
  final double baseAngle;
  final double sweepAngle;
  final List<String> keywords;

  /// 星域色系调色板（从深到浅的 5 个层次）
  late final List<Color> colorPalette;

  /// 根据主色生成 5 层调色板
  static List<Color> _generatePalette(Color primary) {
    final hsl = HSLColor.fromColor(primary);
    return [
      // 深色变体（更饱和，更暗，用于重要节点）
      hsl.withSaturation((hsl.saturation * 1.3).clamp(0.0, 1.0))
         .withLightness((hsl.lightness * 0.6).clamp(0.2, 0.8)) // 避免过黑
         .toColor(),
      // 中深色
      hsl.withLightness((hsl.lightness * 0.8).clamp(0.2, 0.9)).toColor(),
      // 主色
      primary,
      // 中浅色
      hsl.withLightness((hsl.lightness * 1.1).clamp(0.0, 0.9)).toColor(),
      // 浅色变体
      hsl.withSaturation((hsl.saturation * 0.8).clamp(0.0, 1.0))
         .withLightness((hsl.lightness * 1.2).clamp(0.0, 0.95))
         .toColor(),
    ];
  }

  /// 根据重要程度获取颜色（1-5 映射到调色板）
  Color getColorByImportance(int importance) {
    final index = (5 - importance).clamp(0, 4);
    return colorPalette[index];
  }

  /// 根据掌握度调整颜色亮度
  Color getColorByMastery(int importance, int masteryScore) {
    final baseColor = getColorByImportance(importance);
    final hsl = HSLColor.fromColor(baseColor);

    // 掌握度越高，颜色越亮，但不能变成纯白
    // 限制最大亮度在 0.85，保证仍有色彩倾向
    final masteryFactor = masteryScore / 100.0;

    // 如果颜色过暗（如在深色背景），提升基础亮度
    var baseLightness = hsl.lightness;
    if (baseLightness < 0.3) {
      baseLightness += 0.2; // 提升深色节点的亮度使其在深背景上可见
    }

    final targetLightness = (baseLightness + 0.2).clamp(0.0, 0.85);
    final newLightness = baseLightness + (targetLightness - baseLightness) * masteryFactor;

    return hsl.withLightness(newLightness.clamp(0.2, 0.85)).toColor();
  }
}

class SectorConfig {
  static const double _sectorSweep = 51.43;

  /// 星域样式配置
  static final Map<SectorEnum, SectorStyle> styles = {
    SectorEnum.cosmos: SectorStyle(
      name: '理性星域',
      primaryColor: const Color(0xFF00BFFF),  // 深天蓝
      glowColor: const Color(0xFF87CEEB),
      baseAngle: 0.0,
      sweepAngle: _sectorSweep,
      keywords: const ['数学', '物理', '化学', '天文', '逻辑学'],
    ),
    SectorEnum.tech: SectorStyle(
      name: '造物星域',
      primaryColor: const Color(0xFF7B68EE),  // 中紫罗兰色（更有科技感）
      glowColor: const Color(0xFFB0C4DE),
      baseAngle: _sectorSweep,
      sweepAngle: _sectorSweep,
      keywords: const ['计算机', '工程', 'AI', '建筑', '制造'],
    ),
    SectorEnum.art: SectorStyle(
      name: '灵感星域',
      primaryColor: const Color(0xFFFF69B4),  // 热粉红
      glowColor: const Color(0xFFFFB6C1),
      baseAngle: _sectorSweep * 2,
      sweepAngle: _sectorSweep,
      keywords: const ['设计', '音乐', '绘画', '文学', 'ACG'],
    ),
    SectorEnum.civilization: SectorStyle(
      name: '文明星域',
      primaryColor: const Color(0xFFFFD700),  // 金色
      glowColor: const Color(0xFFFFF8DC),
      baseAngle: _sectorSweep * 3,
      sweepAngle: _sectorSweep,
      keywords: const ['历史', '经济', '政治', '社会学', '法律'],
    ),
    SectorEnum.life: SectorStyle(
      name: '生活星域',
      primaryColor: const Color(0xFF32CD32),  // 酸橙绿
      glowColor: const Color(0xFF90EE90),
      baseAngle: _sectorSweep * 4,
      sweepAngle: _sectorSweep,
      keywords: const ['健身', '烹饪', '医学', '心理', '理财'],
    ),
    SectorEnum.wisdom: SectorStyle(
      name: '智慧星域',
      primaryColor: const Color(0xFF9575CD),  // Deep Purple 300 - 更清晰的紫色
      glowColor: const Color(0xFFD1C4E9),
      baseAngle: _sectorSweep * 5,
      sweepAngle: _sectorSweep,
      keywords: const ['哲学', '宗教', '方法论', '元认知'],
    ),
    SectorEnum.voidSector: SectorStyle(
      name: '暗物质区',
      primaryColor: const Color(0xFF546E7A),  // Blue Grey 600 - 更深邃的灰蓝
      glowColor: const Color(0xFF78909C),
      baseAngle: _sectorSweep * 6,
      sweepAngle: _sectorSweep,
      keywords: const ['未归类', '跨领域', '新兴概念'],
    ),
  };

  static SectorStyle getStyle(SectorEnum sector) => styles[sector] ?? styles[SectorEnum.voidSector]!;

  static Color getColor(SectorEnum sector) => getStyle(sector).primaryColor;

  static Color getGlowColor(SectorEnum sector) => getStyle(sector).glowColor;

  /// 获取节点颜色（基于星域、重要程度和掌握度）
  ///
  /// [sector] 所属星域
  /// [importance] 重要程度 1-5，越高颜色越深/饱和
  /// [masteryScore] 掌握度 0-100，越高颜色越亮
  static Color getNodeColor({
    required SectorEnum sector,
    required int importance,
    int masteryScore = 0,
  }) {
    final style = getStyle(sector);
    return style.getColorByMastery(importance, masteryScore);
  }

  /// 获取节点调色板中的颜色
  static Color getNodeColorByImportance(SectorEnum sector, int importance) {
    final style = getStyle(sector);
    return style.getColorByImportance(importance);
  }

  static double getSectorCenterAngleRadians(SectorEnum sector) {
    final style = getStyle(sector);
    final centerDegrees = style.baseAngle + style.sweepAngle / 2;
    return centerDegrees * 3.14159265359 / 180.0;
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
}