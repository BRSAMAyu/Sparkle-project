import 'dart:ui';
import 'package:sparkle/data/models/galaxy_model.dart';

/// Sector visual style configuration
class SectorStyle {
  /// Chinese name of the sector
  final String name;

  /// Primary color of the sector (main color for nodes)
  final Color primaryColor;

  /// Glow color (for effects and highlights)
  final Color glowColor;

  /// Base angle in degrees (0 = 12 o'clock, clockwise)
  final double baseAngle;

  /// Sweep angle in degrees (how wide the sector is)
  final double sweepAngle;

  /// Keywords/domains covered by this sector
  final List<String> keywords;

  const SectorStyle({
    required this.name,
    required this.primaryColor,
    required this.glowColor,
    required this.baseAngle,
    required this.sweepAngle,
    this.keywords = const [],
  });
}

/// Sector configuration with colors and layout settings
class SectorConfig {
  // Sweep angle for each sector: 360 / 7 ≈ 51.43 degrees
  static const double _sectorSweep = 51.43;

  /// Style definitions for all 7 sectors
  static const Map<SectorEnum, SectorStyle> styles = {
    // COSMOS - 理性星域 (Rational Domain)
    // Mathematics, Physics, Chemistry, Astronomy, Logic
    SectorEnum.COSMOS: SectorStyle(
      name: '理性星域',
      primaryColor: Color(0xFF00BFFF), // Deep Sky Blue
      glowColor: Color(0xFF87CEEB),    // Light Sky Blue
      baseAngle: 0.0,                   // 12 o'clock position
      sweepAngle: _sectorSweep,
      keywords: ['数学', '物理', '化学', '天文', '逻辑学'],
    ),

    // TECH - 造物星域 (Creation Domain)
    // Computer Science, Engineering, AI, Architecture, Manufacturing
    SectorEnum.TECH: SectorStyle(
      name: '造物星域',
      primaryColor: Color(0xFFC0C0C0), // Silver
      glowColor: Color(0xFFE8E8E8),    // Light Gray
      baseAngle: _sectorSweep,
      sweepAngle: _sectorSweep,
      keywords: ['计算机', '工程', 'AI', '建筑', '制造'],
    ),

    // ART - 灵感星域 (Inspiration Domain)
    // Design, Music, Painting, Literature, ACG
    SectorEnum.ART: SectorStyle(
      name: '灵感星域',
      primaryColor: Color(0xFFFF00FF), // Magenta
      glowColor: Color(0xFFFFB6C1),    // Light Pink
      baseAngle: _sectorSweep * 2,
      sweepAngle: _sectorSweep,
      keywords: ['设计', '音乐', '绘画', '文学', 'ACG'],
    ),

    // CIVILIZATION - 文明星域 (Civilization Domain)
    // History, Economics, Politics, Sociology, Law
    SectorEnum.CIVILIZATION: SectorStyle(
      name: '文明星域',
      primaryColor: Color(0xFFFFD700), // Gold
      glowColor: Color(0xFFFFF8DC),    // Cornsilk
      baseAngle: _sectorSweep * 3,
      sweepAngle: _sectorSweep,
      keywords: ['历史', '经济', '政治', '社会学', '法律'],
    ),

    // LIFE - 生活星域 (Life Domain)
    // Fitness, Cooking, Medicine, Psychology, Finance
    SectorEnum.LIFE: SectorStyle(
      name: '生活星域',
      primaryColor: Color(0xFF32CD32), // Lime Green
      glowColor: Color(0xFF90EE90),    // Light Green
      baseAngle: _sectorSweep * 4,
      sweepAngle: _sectorSweep,
      keywords: ['健身', '烹饪', '医学', '心理', '理财'],
    ),

    // WISDOM - 智慧星域 (Wisdom Domain)
    // Philosophy, Religion, Methodology, Metacognition
    SectorEnum.WISDOM: SectorStyle(
      name: '智慧星域',
      primaryColor: Color(0xFFFFFFFF), // White
      glowColor: Color(0xFFF0F8FF),    // Alice Blue
      baseAngle: _sectorSweep * 5,
      sweepAngle: _sectorSweep,
      keywords: ['哲学', '宗教', '方法论', '元认知'],
    ),

    // VOID - 暗物质区 (Dark Matter Zone)
    // Uncategorized, Cross-domain, Emerging concepts
    SectorEnum.VOID: SectorStyle(
      name: '暗物质区',
      primaryColor: Color(0xFF2F4F4F), // Dark Slate Gray
      glowColor: Color(0xFF696969),    // Dim Gray
      baseAngle: _sectorSweep * 6,
      sweepAngle: _sectorSweep,
      keywords: ['未归类', '跨领域', '新兴概念'],
    ),
  };

  /// Get the style for a specific sector
  static SectorStyle getStyle(SectorEnum sector) {
    return styles[sector] ?? styles[SectorEnum.VOID]!;
  }

  /// Get the color for a specific sector (convenience method)
  static Color getColor(SectorEnum sector) {
    return getStyle(sector).primaryColor;
  }

  /// Get the glow color for a specific sector
  static Color getGlowColor(SectorEnum sector) {
    return getStyle(sector).glowColor;
  }

  /// Get angle in radians for the center of a sector
  static double getSectorCenterAngleRadians(SectorEnum sector) {
    final style = getStyle(sector);
    final centerDegrees = style.baseAngle + style.sweepAngle / 2;
    return centerDegrees * 3.14159265359 / 180.0;
  }

  /// Check if an angle (in degrees) is within a sector's range
  static bool isAngleInSector(double angleDegrees, SectorEnum sector) {
    final style = getStyle(sector);
    final normalized = angleDegrees % 360;
    final start = style.baseAngle;
    final end = start + style.sweepAngle;
    return normalized >= start && normalized < end;
  }

  /// Get the sector for a given angle (in degrees)
  static SectorEnum getSectorForAngle(double angleDegrees) {
    final normalized = angleDegrees % 360;
    for (final entry in styles.entries) {
      if (isAngleInSector(normalized, entry.key)) {
        return entry.key;
      }
    }
    return SectorEnum.VOID;
  }
}
