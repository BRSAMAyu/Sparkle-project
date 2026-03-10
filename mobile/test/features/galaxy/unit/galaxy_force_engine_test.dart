import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_force_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

void main() {
  group('GalaxyForceEngine', () {
    test('settles after releasing an anchored neighborhood', () {
      final engine = GalaxyForceEngine(
        damping: 0.78,
        springK: 0.05,
        repulsionK: 2400,
        centerGravity: 0.001,
        maxVelocity: 8,
        repulsionRadius: 240,
      );
      final nodes = [
        _node('a'),
        _node('b'),
        _node('c'),
      ];
      final adjacency = <String, Set<String>>{
        'a': {'b'},
        'b': {'a', 'c'},
        'c': {'b'},
      };
      final edgeStrengths = <String, double>{
        GalaxyForceEngine.edgeStrengthKey('a', 'b'): 1.0,
        GalaxyForceEngine.edgeStrengthKey('b', 'c'): 1.0,
      };
      var positions = <String, Offset>{
        'a': const Offset(-150, 0),
        'b': const Offset(0, 80),
        'c': const Offset(150, -40),
      };
      final index = GalaxySpatialIndex()..build(positions, nodes);

      engine.anchorNode('b', adjacency);
      engine.releaseAnchor();

      var settled = false;
      for (var i = 0; i < 600; i++) {
        final result = engine.tick(
          positions: positions,
          adjacency: adjacency,
          edgeStrengths: edgeStrengths,
          spatialIndex: index,
          viewport: const Rect.fromLTWH(-600, -600, 1200, 1200),
        );
        positions = result.positions;
        index.build(positions, nodes);
        if (result.isSettled) {
          settled = true;
          break;
        }
      }

      expect(settled, isTrue);
      for (final position in positions.values) {
        expect(position.dx.isFinite, isTrue);
        expect(position.dy.isFinite, isTrue);
      }
    });
  });
}

GalaxyNodeModel _node(String id) => GalaxyNodeModel(
      id: id,
      name: id,
      importance: 3,
      sector: SectorEnum.tech,
      isUnlocked: true,
      masteryScore: 60,
    );
