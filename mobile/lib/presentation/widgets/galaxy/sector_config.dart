import 'dart:ui';
import 'package:sparkle/data/models/galaxy_model.dart';

/// Sector visual style configuration
class SectorStyle {
  final String name;
  final Color primaryColor;
  final Color glowColor;
  final double baseAngle;
  final double sweepAngle;
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

class SectorConfig {
  static const double _sectorSweep = 51.43;

  /// 使用 final 而不是 const 以避免枚举重命名后的常量初始化冲突
  static final Map<SectorEnum, SectorStyle> styles = {
    SectorEnum.cosmos: const SectorStyle(
      name: '理性星域',
      primaryColor: Color(0xFF00BFFF),
      glowColor: Color(0xFF87CEEB),
      baseAngle: 0.0,
      sweepAngle: _sectorSweep,
      keywords: ['数学', '物理', '化学', '天文', '逻辑学'],
    ),
    SectorEnum.tech: const SectorStyle(
      name: '造物星域',
      primaryColor: Color(0xFFC0C0C0),
      glowColor: Color(0xFFE8E8E8),
      baseAngle: _sectorSweep,
      sweepAngle: _sectorSweep,
      keywords: ['计算机', '工程', 'AI', '建筑', '制造'],
    ),
    SectorEnum.art: const SectorStyle(
      name: '灵感星域',
      primaryColor: Color(0xFFFF00FF),
      glowColor: Color(0xFFFFB6C1),
      baseAngle: _sectorSweep * 2,
      sweepAngle: _sectorSweep,
      keywords: ['设计', '音乐', '绘画', '文学', 'ACG'],
    ),
    SectorEnum.civilization: const SectorStyle(
      name: '文明星域',
      primaryColor: Color(0xFFFFD700),
      glowColor: Color(0xFFFFF8DC),
      baseAngle: _sectorSweep * 3,
      sweepAngle: _sectorSweep,
      keywords: ['历史', '经济', '政治', '社会学', '法律'],
    ),
    SectorEnum.life: const SectorStyle(
      name: '生活星域',
      primaryColor: Color(0xFF32CD32),
      glowColor: Color(0xFF90EE90),
      baseAngle: _sectorSweep * 4,
      sweepAngle: _sectorSweep,
      keywords: ['健身', '烹饪', '医学', '心理', '理财'],
    ),
    SectorEnum.wisdom: const SectorStyle(
      name: '智慧星域',
      primaryColor: Color(0xFFFFFFFF),
      glowColor: Color(0xFFF0F8FF),
      baseAngle: _sectorSweep * 5,
      sweepAngle: _sectorSweep,
      keywords: ['哲学', '宗教', '方法论', '元认知'],
    ),
    SectorEnum.voidSector: const SectorStyle(
      name: '暗物质区',
      primaryColor: Color(0xFF2F4F4F),
      glowColor: Color(0xFF696969),
      baseAngle: _sectorSweep * 6,
      sweepAngle: _sectorSweep,
      keywords: ['未归类', '跨领域', '新兴概念'],
    ),
  };

  static SectorStyle getStyle(SectorEnum sector) {
    return styles[sector] ?? styles[SectorEnum.voidSector]!;
  }

  static Color getColor(SectorEnum sector) {
    return getStyle(sector).primaryColor;
  }

  static Color getGlowColor(SectorEnum sector) {
    return getStyle(sector).glowColor;
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