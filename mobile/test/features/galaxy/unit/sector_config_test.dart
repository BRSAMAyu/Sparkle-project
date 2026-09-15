import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

void main() {
  group('SectorConfig color system', () {
    test('explicit node color participates in base color resolution', () {
      final node = GalaxyNodeModel(
        id: 'node-explicit',
        name: 'Neural Style Transfer',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 72,
        baseColor: '#E08A4E',
      );

      final resolved = SectorConfig.resolveNodeBaseColor(
        node: node,
        isDarkMode: true,
      );

      expect(
        HSLColor.fromColor(resolved).hue,
        isNot(
          closeTo(
            HSLColor.fromColor(
              SectorConfig.getColor(SectorEnum.tech),
            ).hue,
            0.01,
          ),
        ),
      );
    });

    test('cross-sector neighbors shift node color away from solo sector base',
        () {
      final node = GalaxyNodeModel(
        id: 'node-cross',
        name: '计算摄影与视觉叙事',
        description: '融合算法、摄影与设计方法',
        importance: 4,
        sector: SectorEnum.tech,
        isUnlocked: true,
        masteryScore: 66,
        tags: const ['摄影', '设计', '算法'],
      );
      final neighbors = [
        GalaxyNodeModel(
          id: 'neighbor-art',
          name: '摄影构图',
          importance: 3,
          sector: SectorEnum.art,
          isUnlocked: true,
          masteryScore: 60,
        ),
        GalaxyNodeModel(
          id: 'neighbor-cosmos',
          name: '图像处理',
          importance: 3,
          sector: SectorEnum.cosmos,
          isUnlocked: true,
          masteryScore: 58,
        ),
      ];

      final base = SectorConfig.resolveNodeBaseColor(
        node: node,
        isDarkMode: true,
      );
      final blended = SectorConfig.computeBlendedColor(
        node: node,
        neighbors: neighbors,
        isDarkMode: true,
      );

      expect(
        HSLColor.fromColor(blended).hue,
        isNot(closeTo(HSLColor.fromColor(base).hue, 0.01)),
      );
    });

    test('void-sector nodes are deterministically varied instead of monochrome',
        () {
      final first = GalaxyNodeModel(
        id: 'void-a',
        name: '跨学科问题定义',
        importance: 3,
        sector: SectorEnum.voidSector,
        isUnlocked: true,
        masteryScore: 40,
      );
      final second = GalaxyNodeModel(
        id: 'void-b',
        name: '新兴概念建模',
        importance: 3,
        sector: SectorEnum.voidSector,
        isUnlocked: true,
        masteryScore: 40,
      );

      final firstColor = SectorConfig.resolveNodeBaseColor(
        node: first,
        isDarkMode: true,
      );
      final secondColor = SectorConfig.resolveNodeBaseColor(
        node: second,
        isDarkMode: true,
      );

      expect(firstColor, isNot(secondColor));
    });
  });
}
