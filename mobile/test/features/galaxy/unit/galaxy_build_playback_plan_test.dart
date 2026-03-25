import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_build_playback_plan.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

void main() {
  group('GalaxyBuildPlaybackPlan', () {
    test('prioritizes unlocked timeline before locked fallback', () {
      final nodes = [
        _node(
          id: 'root',
          unlocked: true,
          firstUnlockAt: DateTime.parse('2026-03-20T09:00:00Z'),
        ),
        _node(
          id: 'child',
          unlocked: true,
          firstUnlockAt: DateTime.parse('2026-03-21T09:00:00Z'),
        ),
        _node(id: 'locked', unlocked: false),
      ];
      final edges = [
        const GalaxyEdgeModel(
          id: 'root-child',
          sourceId: 'root',
          targetId: 'child',
        ),
        const GalaxyEdgeModel(
          id: 'child-locked',
          sourceId: 'child',
          targetId: 'locked',
        ),
      ];
      final positions = <String, Offset>{
        'root': const Offset(0, 0),
        'child': const Offset(100, 0),
        'locked': const Offset(200, 0),
      };
      final adjacency = <String, Set<String>>{
        'root': {'child'},
        'child': {'root', 'locked'},
        'locked': {'child'},
      };

      final plan = GalaxyBuildPlaybackPlan.full(
        nodes: nodes,
        edges: edges,
        positions: positions,
        adjacency: adjacency,
      );

      expect(plan.nodeSteps['root']!.nodeStartMs,
          lessThan(plan.nodeSteps['child']!.nodeStartMs));
      expect(plan.nodeSteps['child']!.nodeStartMs,
          lessThan(plan.nodeSteps['locked']!.nodeStartMs));
    });

    test('creates multiple clusters for disconnected components', () {
      final nodes = [
        _node(
          id: 'a',
          unlocked: true,
          firstUnlockAt: DateTime.parse('2026-03-20T09:00:00Z'),
        ),
        _node(id: 'b', unlocked: true),
      ];
      final positions = <String, Offset>{
        'a': const Offset(0, 0),
        'b': const Offset(800, 200),
      };
      final adjacency = <String, Set<String>>{
        'a': const <String>{},
        'b': const <String>{},
      };

      final plan = GalaxyBuildPlaybackPlan.full(
        nodes: nodes,
        edges: const <GalaxyEdgeModel>[],
        positions: positions,
        adjacency: adjacency,
      );

      expect(plan.clusterCount, 2);
      expect(plan.nodeSteps['a']!.clusterIndex,
          isNot(plan.nodeSteps['b']!.clusterIndex));
    });

    test('schedules edge before node and label after node', () {
      final nodes = [
        _node(
          id: 'root',
          unlocked: true,
          firstUnlockAt: DateTime.parse('2026-03-20T09:00:00Z'),
        ),
        _node(
          id: 'child',
          unlocked: true,
          firstUnlockAt: DateTime.parse('2026-03-20T10:00:00Z'),
        ),
      ];
      const edge = GalaxyEdgeModel(
        id: 'root-child',
        sourceId: 'root',
        targetId: 'child',
        relationType: EdgeRelationType.prerequisite,
        strength: 0.8,
      );
      final positions = <String, Offset>{
        'root': const Offset(0, 0),
        'child': const Offset(120, 0),
      };
      final adjacency = <String, Set<String>>{
        'root': {'child'},
        'child': {'root'},
      };

      final plan = GalaxyBuildPlaybackPlan.full(
        nodes: nodes,
        edges: const [edge],
        positions: positions,
        adjacency: adjacency,
      );

      final edgeStep = plan.edgeSteps['root-child']!;
      final nodeStep = plan.nodeSteps['child']!;
      expect(edgeStep.edgeEndMs, equals(nodeStep.nodeStartMs));
      expect(nodeStep.labelStartMs, equals(nodeStep.nodeEndMs));
      expect(plan.edgeRevealAt('root-child', edgeStep.edgeStartMs - 1), 0);
      expect(plan.edgeRevealAt('root-child', edgeStep.edgeEndMs), 1);
      expect(plan.nodeRevealAt('child', nodeStep.nodeStartMs - 1), 0);
      expect(plan.nodeRevealAt('child', nodeStep.nodeEndMs), 1);
      expect(plan.labelRevealAt('child', nodeStep.labelStartMs - 1), 0);
      expect(plan.labelRevealAt('child', nodeStep.labelEndMs), 1);
    });
  });
}

GalaxyNodeModel _node({
  required String id,
  required bool unlocked,
  DateTime? firstUnlockAt,
}) =>
    GalaxyNodeModel(
      id: id,
      name: id,
      importance: 3,
      sector: SectorEnum.tech,
      isUnlocked: unlocked,
      masteryScore: unlocked ? 50 : 0,
      firstUnlockAt: firstUnlockAt,
    );
