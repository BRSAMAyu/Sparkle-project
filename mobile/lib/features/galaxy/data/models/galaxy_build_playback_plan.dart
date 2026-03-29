import 'dart:collection';
import 'dart:math' as math;

import 'package:flutter/animation.dart';
import 'package:flutter/foundation.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

const int kGalaxyRootRevealDurationMs = 480;
const int kGalaxyRootPauseMs = 220;
const int kGalaxyEdgeRevealDurationMs = 240;
const int kGalaxyNodeRevealDurationMs = 300;
const int kGalaxyLabelRevealDurationMs = 140;
const int kGalaxySiblingStaggerMs = 110;
const int kGalaxyTimeBucketGapMs = 280;
const int kGalaxyClusterGapMs = 300;

@immutable
class BuildPlanNodeStep {
  const BuildPlanNodeStep({
    required this.nodeId,
    required this.clusterIndex,
    required this.parentRevealId,
    required this.nodeStartMs,
    required this.nodeEndMs,
    required this.labelStartMs,
    required this.labelEndMs,
  });

  final String nodeId;
  final int clusterIndex;
  final String? parentRevealId;
  final int nodeStartMs;
  final int nodeEndMs;
  final int labelStartMs;
  final int labelEndMs;
}

@immutable
class BuildPlanEdgeStep {
  const BuildPlanEdgeStep({
    required this.id,
    required this.sourceId,
    required this.targetId,
    required this.clusterIndex,
    required this.edgeStartMs,
    required this.edgeEndMs,
    required this.relationType,
    required this.strength,
    required this.isSynthetic,
  });

  final String id;
  final String sourceId;
  final String targetId;
  final int clusterIndex;
  final int edgeStartMs;
  final int edgeEndMs;
  final EdgeRelationType relationType;
  final double strength;
  final bool isSynthetic;
}

@immutable
class GalaxyRevealOrderStrategy {
  const GalaxyRevealOrderStrategy({
    this.visibleNeighborBias = 1600,
    this.strongEdgeBias = 420,
    this.centroidBias = 0.32,
  });

  final double visibleNeighborBias;
  final double strongEdgeBias;
  final double centroidBias;

  List<String> orderComponent({
    required String seedId,
    required Set<String> componentIds,
    required Set<String> visibleNodeIds,
    required Map<String, Set<String>> adjacency,
    required Map<String, Offset> positions,
    required double Function(String nodeId) centralityScoreOf,
    required double Function(String nodeId) visibleNeighborScoreOf,
    required double Function(String nodeId) strongestConnectionToVisibleOf,
    required int Function(String leftId, String rightId) fallbackCompare,
  }) {
    final ordered = <String>[];
    final visited = <String>{seedId};
    final queue = Queue<String>()..add(seedId);
    final centroid = _centroidFor(componentIds, positions);

    while (queue.isNotEmpty) {
      final waveCount = queue.length;
      final wave = <String>[];
      for (var index = 0; index < waveCount; index++) {
        wave.add(queue.removeFirst());
      }
      wave.sort((left, right) {
        final leftScore = _waveScore(
          nodeId: left,
          seedId: seedId,
          centroid: centroid,
          positions: positions,
          centralityScoreOf: centralityScoreOf,
          visibleNeighborScoreOf: visibleNeighborScoreOf,
          strongestConnectionToVisibleOf: strongestConnectionToVisibleOf,
        );
        final rightScore = _waveScore(
          nodeId: right,
          seedId: seedId,
          centroid: centroid,
          positions: positions,
          centralityScoreOf: centralityScoreOf,
          visibleNeighborScoreOf: visibleNeighborScoreOf,
          strongestConnectionToVisibleOf: strongestConnectionToVisibleOf,
        );
        final scoreCompare = rightScore.compareTo(leftScore);
        if (scoreCompare != 0) {
          return scoreCompare;
        }
        return fallbackCompare(left, right);
      });
      ordered.addAll(wave);

      final nextWave = <String>{};
      for (final nodeId in wave) {
        for (final neighborId in adjacency[nodeId] ?? const <String>{}) {
          if (!componentIds.contains(neighborId) || !visited.add(neighborId)) {
            continue;
          }
          nextWave.add(neighborId);
        }
      }
      nextWave.forEach(queue.add);
    }

    final missing = componentIds.difference(visited).toList(growable: false)
      ..sort(fallbackCompare);
    ordered.addAll(missing);
    return ordered;
  }

  double _waveScore({
    required String nodeId,
    required String seedId,
    required Offset centroid,
    required Map<String, Offset> positions,
    required double Function(String nodeId) centralityScoreOf,
    required double Function(String nodeId) visibleNeighborScoreOf,
    required double Function(String nodeId) strongestConnectionToVisibleOf,
  }) {
    final position = positions[nodeId] ?? Offset.zero;
    final seedPosition = positions[seedId] ?? Offset.zero;
    final centroidDistance = (position - centroid).distanceSquared;
    final seedDistance = (position - seedPosition).distanceSquared;
    return visibleNeighborScoreOf(nodeId) * visibleNeighborBias +
        strongestConnectionToVisibleOf(nodeId) * strongEdgeBias +
        centralityScoreOf(nodeId) -
        seedDistance * 0.0024 -
        centroidDistance * centroidBias;
  }

  Offset _centroidFor(Set<String> nodeIds, Map<String, Offset> positions) {
    if (nodeIds.isEmpty) {
      return Offset.zero;
    }
    final total = nodeIds.fold<Offset>(
      Offset.zero,
      (sum, nodeId) => sum + (positions[nodeId] ?? Offset.zero),
    );
    return total / nodeIds.length.toDouble();
  }
}

@immutable
class GalaxyBuildPlaybackPlan {
  const GalaxyBuildPlaybackPlan({
    required this.nodeSteps,
    required this.edgeSteps,
    required this.totalDurationMs,
    required this.clusterCount,
  });

  factory GalaxyBuildPlaybackPlan.full({
    required List<GalaxyNodeModel> nodes,
    required List<GalaxyEdgeModel> edges,
    required Map<String, Offset> positions,
    required Map<String, Set<String>> adjacency,
  }) {
    final animatedNodeIds = nodes.map((node) => node.id).toSet();
    return _GalaxyBuildPlaybackPlanner(
      nodes: nodes,
      edges: edges,
      positions: positions,
      adjacency: adjacency,
      animatedNodeIds: animatedNodeIds,
      preRevealedNodeIds: const <String>{},
    ).build();
  }

  factory GalaxyBuildPlaybackPlan.incremental({
    required List<GalaxyNodeModel> nodes,
    required List<GalaxyEdgeModel> edges,
    required Map<String, Offset> positions,
    required Map<String, Set<String>> adjacency,
    required Set<String> animatedNodeIds,
    required Set<String> preRevealedNodeIds,
  }) =>
      _GalaxyBuildPlaybackPlanner(
        nodes: nodes,
        edges: edges,
        positions: positions,
        adjacency: adjacency,
        animatedNodeIds: animatedNodeIds,
        preRevealedNodeIds: preRevealedNodeIds,
      ).build();

  final Map<String, BuildPlanNodeStep> nodeSteps;
  final Map<String, BuildPlanEdgeStep> edgeSteps;
  final int totalDurationMs;
  final int clusterCount;

  bool get isEmpty => nodeSteps.isEmpty;

  Set<String> get animatedNodeIds => nodeSteps.keys.toSet();
  Set<String> get animatedEdgeIds => edgeSteps.keys.toSet();

  double nodeRevealAt(String nodeId, int elapsedMs) {
    final step = nodeSteps[nodeId];
    if (step == null) {
      return 1;
    }
    return _phaseProgress(
      elapsedMs,
      startMs: step.nodeStartMs,
      endMs: step.nodeEndMs,
    );
  }

  double labelRevealAt(String nodeId, int elapsedMs) {
    final step = nodeSteps[nodeId];
    if (step == null) {
      return 1;
    }
    return _phaseProgress(
      elapsedMs,
      startMs: step.labelStartMs,
      endMs: step.labelEndMs,
    );
  }

  double edgeRevealAt(String edgeId, int elapsedMs) {
    final step = edgeSteps[edgeId];
    if (step == null) {
      return 1;
    }
    return _phaseProgress(
      elapsedMs,
      startMs: step.edgeStartMs,
      endMs: step.edgeEndMs,
    );
  }

  int visibleAtMs(String nodeId) {
    final step = nodeSteps[nodeId];
    if (step == null) {
      return 0;
    }
    return step.nodeEndMs;
  }

  static double _phaseProgress(
    int elapsedMs, {
    required int startMs,
    required int endMs,
  }) {
    if (endMs <= startMs) {
      return elapsedMs >= endMs ? 1 : 0;
    }
    if (elapsedMs <= startMs) {
      return 0;
    }
    if (elapsedMs >= endMs) {
      return 1;
    }
    final t = (elapsedMs - startMs) / (endMs - startMs);
    return Curves.easeOutCubic.transform(t.clamp(0.0, 1.0));
  }
}

class _GalaxyBuildPlaybackPlanner {
  _GalaxyBuildPlaybackPlanner({
    required List<GalaxyNodeModel> nodes,
    required List<GalaxyEdgeModel> edges,
    required this.positions,
    required this.adjacency,
    required Set<String> animatedNodeIds,
    required Set<String> preRevealedNodeIds,
  })  : _nodesById = {for (final node in nodes) node.id: node},
        _edges = edges,
        _animatedNodeIds = animatedNodeIds,
        _preRevealedNodeIds = preRevealedNodeIds;

  final Map<String, GalaxyNodeModel> _nodesById;
  final List<GalaxyEdgeModel> _edges;
  final Map<String, Offset> positions;
  final Map<String, Set<String>> adjacency;
  final Set<String> _animatedNodeIds;
  final Set<String> _preRevealedNodeIds;
  final GalaxyRevealOrderStrategy _revealOrderStrategy =
      const GalaxyRevealOrderStrategy();

  final Map<String, BuildPlanNodeStep> _nodeSteps =
      <String, BuildPlanNodeStep>{};
  final Map<String, BuildPlanEdgeStep> _edgeSteps =
      <String, BuildPlanEdgeStep>{};
  final Set<String> _visibleNodeIds = <String>{};

  late final Map<String, List<GalaxyEdgeModel>> _edgesByNode =
      _buildEdgesByNode(_edges);

  int _cursorMs = 0;
  int _maxScheduledMs = 0;
  int _clusterIndex = -1;

  GalaxyBuildPlaybackPlan build() {
    _visibleNodeIds.addAll(_preRevealedNodeIds);

    final unlockedTimed = _sortedTimedAnimatedNodes();
    final unlockedUntimed = _sortedUntimedAnimatedNodes();
    final lockedNodes = _sortedLockedAnimatedNodes();

    _scheduleTimedNodes(unlockedTimed);
    _scheduleFallbackNodes(
      unlockedUntimed,
      addBucketGap: lockedNodes.isNotEmpty,
    );
    _scheduleFallbackNodes(lockedNodes, addBucketGap: false);

    final totalDurationMs = math.max(
      _maxScheduledMs,
      _nodeSteps.values.fold<int>(
        0,
        (maxValue, step) => math.max(maxValue, step.labelEndMs),
      ),
    );

    return GalaxyBuildPlaybackPlan(
      nodeSteps: Map<String, BuildPlanNodeStep>.unmodifiable(_nodeSteps),
      edgeSteps: Map<String, BuildPlanEdgeStep>.unmodifiable(_edgeSteps),
      totalDurationMs: totalDurationMs,
      clusterCount: math.max(0, _clusterIndex + 1),
    );
  }

  List<GalaxyNodeModel> _sortedTimedAnimatedNodes() =>
      _animatedNodes.where((node) => node.firstUnlockAt != null).toList()
        ..sort((left, right) {
          final timeCompare =
              left.firstUnlockAt!.compareTo(right.firstUnlockAt!);
          if (timeCompare != 0) {
            return timeCompare;
          }
          return _fallbackNodeOrder(left, right);
        });

  List<GalaxyNodeModel> _sortedUntimedAnimatedNodes() => _animatedNodes
      .where((node) => node.isUnlocked && node.firstUnlockAt == null)
      .toList()
    ..sort(_fallbackNodeOrder);

  List<GalaxyNodeModel> _sortedLockedAnimatedNodes() =>
      _animatedNodes.where((node) => !node.isUnlocked).toList()
        ..sort(_fallbackNodeOrder);

  Iterable<GalaxyNodeModel> get _animatedNodes => _animatedNodeIds
      .map((nodeId) => _nodesById[nodeId])
      .whereType<GalaxyNodeModel>();

  void _scheduleTimedNodes(List<GalaxyNodeModel> nodes) {
    if (nodes.isEmpty) {
      return;
    }

    final buckets = <int, List<GalaxyNodeModel>>{};
    for (final node in nodes) {
      final bucketKey = node.firstUnlockAt!.millisecondsSinceEpoch;
      buckets.putIfAbsent(bucketKey, () => <GalaxyNodeModel>[]).add(node);
    }

    final orderedKeys = buckets.keys.toList()..sort();
    for (var index = 0; index < orderedKeys.length; index++) {
      final bucketNodes = buckets[orderedKeys[index]]!;
      _scheduleGroup(bucketNodes);
      if (index < orderedKeys.length - 1) {
        _cursorMs =
            math.max(_cursorMs, _maxScheduledMs + kGalaxyTimeBucketGapMs);
      }
    }
  }

  void _scheduleFallbackNodes(
    List<GalaxyNodeModel> nodes, {
    required bool addBucketGap,
  }) {
    if (nodes.isEmpty) {
      return;
    }
    _scheduleGroup(nodes);
    if (addBucketGap) {
      _cursorMs = math.max(_cursorMs, _maxScheduledMs + kGalaxyTimeBucketGapMs);
    }
  }

  void _scheduleGroup(List<GalaxyNodeModel> group) {
    final remainingIds = group.map((node) => node.id).toSet();
    while (remainingIds.isNotEmpty) {
      final seed = _pickNextNode(
        remainingIds.map((nodeId) => _nodesById[nodeId]!).toList(),
      );
      final componentIds = _collectReachableIds(
        seed.id,
        allowedNodeIds: remainingIds,
      );
      final orderedIds = _revealOrderStrategy.orderComponent(
        seedId: seed.id,
        componentIds: componentIds,
        visibleNodeIds: _visibleNodeIds,
        adjacency: adjacency,
        positions: positions,
        centralityScoreOf: _centralityScoreOf,
        visibleNeighborScoreOf: _visibleNeighborScoreOf,
        strongestConnectionToVisibleOf: _strongestConnectionToVisibleOf,
        fallbackCompare: _fallbackNodeIdOrder,
      );
      for (final nodeId in orderedIds) {
        remainingIds.remove(nodeId);
        final parentId = _pickParentId(nodeId);
        _scheduleNode(_nodesById[nodeId]!, parentId: parentId);
      }
    }
  }

  GalaxyNodeModel _pickNextNode(List<GalaxyNodeModel> candidates) {
    if (_visibleNodeIds.isEmpty) {
      return _pickRootNode(candidates);
    }

    final sorted = [...candidates]..sort((left, right) {
        final leftHasVisibleNeighbor = _hasVisibleNeighbor(left.id) ? 0 : 1;
        final rightHasVisibleNeighbor = _hasVisibleNeighbor(right.id) ? 0 : 1;
        if (leftHasVisibleNeighbor != rightHasVisibleNeighbor) {
          return leftHasVisibleNeighbor.compareTo(rightHasVisibleNeighbor);
        }

        final leftDistance = _nearestVisibleDistance(left.id);
        final rightDistance = _nearestVisibleDistance(right.id);
        final distanceCompare = leftDistance.compareTo(rightDistance);
        if (distanceCompare != 0) {
          return distanceCompare;
        }

        return _fallbackNodeOrder(left, right);
      });
    return sorted.first;
  }

  GalaxyNodeModel _pickRootNode(List<GalaxyNodeModel> candidates) {
    final centroid = _positionsCentroid();
    final sorted = [...candidates]..sort((left, right) {
        final leftPos = positions[left.id] ?? Offset.zero;
        final rightPos = positions[right.id] ?? Offset.zero;
        final leftDistance = (leftPos - centroid).distanceSquared;
        final rightDistance = (rightPos - centroid).distanceSquared;
        final leftScore = _centralityScoreOf(left.id);
        final rightScore = _centralityScoreOf(right.id);
        final weightedLeft = leftDistance - leftScore * 10;
        final weightedRight = rightDistance - rightScore * 10;
        final compare = weightedLeft.compareTo(weightedRight);
        if (compare != 0) {
          return compare;
        }
        return _fallbackNodeOrder(left, right);
      });
    return sorted.first;
  }

  int _fallbackNodeOrder(GalaxyNodeModel left, GalaxyNodeModel right) {
    final importanceCompare = right.importance.compareTo(left.importance);
    if (importanceCompare != 0) {
      return importanceCompare;
    }
    final studyCompare = right.studyCount.compareTo(left.studyCount);
    if (studyCompare != 0) {
      return studyCompare;
    }
    return left.name.compareTo(right.name);
  }

  int _fallbackNodeIdOrder(String leftId, String rightId) {
    final left = _nodesById[leftId];
    final right = _nodesById[rightId];
    if (left == null || right == null) {
      return leftId.compareTo(rightId);
    }
    return _fallbackNodeOrder(left, right);
  }

  bool _hasVisibleNeighbor(String nodeId) {
    final neighbors = adjacency[nodeId] ?? const <String>{};
    return neighbors.any(_visibleNodeIds.contains);
  }

  double _visibleNeighborScoreOf(String nodeId) {
    final neighbors = adjacency[nodeId] ?? const <String>{};
    if (neighbors.isEmpty) {
      return 0;
    }
    final visibleCount = neighbors.where(_visibleNodeIds.contains).length;
    return visibleCount / neighbors.length;
  }

  double _strongestConnectionToVisibleOf(String nodeId) {
    final neighbors = adjacency[nodeId] ?? const <String>{};
    var best = 0.0;
    for (final neighborId in neighbors) {
      if (!_visibleNodeIds.contains(neighborId)) {
        continue;
      }
      final strength = _strongestEdgeBetween(nodeId, neighborId)?.strength ?? 0;
      if (strength > best) {
        best = strength;
      }
    }
    return best;
  }

  double _centralityScoreOf(String nodeId) {
    final node = _nodesById[nodeId];
    if (node == null) {
      return 0;
    }
    final degree = (adjacency[nodeId] ?? const <String>{}).length;
    return (node.importance * 110) + (node.studyCount * 24) + (degree * 140);
  }

  String? _pickParentId(String nodeId) {
    final visibleNeighbors = (adjacency[nodeId] ?? const <String>{})
        .where(_visibleNodeIds.contains)
        .map((neighborId) => _nodesById[neighborId])
        .whereType<GalaxyNodeModel>()
        .toList();
    if (visibleNeighbors.isNotEmpty) {
      visibleNeighbors.sort((left, right) {
        final leftEdge = _strongestEdgeBetween(nodeId, left.id);
        final rightEdge = _strongestEdgeBetween(nodeId, right.id);
        final leftStrength = leftEdge?.strength ?? 0;
        final rightStrength = rightEdge?.strength ?? 0;
        final strengthCompare = rightStrength.compareTo(leftStrength);
        if (strengthCompare != 0) {
          return strengthCompare;
        }
        final distanceCompare = _distanceBetween(nodeId, left.id)
            .compareTo(_distanceBetween(nodeId, right.id));
        if (distanceCompare != 0) {
          return distanceCompare;
        }
        return _fallbackNodeOrder(left, right);
      });
      return visibleNeighbors.first.id;
    }

    if (_visibleNodeIds.isEmpty) {
      return null;
    }
    if (!_canReachVisibleNode(nodeId)) {
      return null;
    }

    final sortedVisible = _visibleNodeIds.toList()
      ..sort(
        (left, right) => _distanceBetween(nodeId, left).compareTo(
          _distanceBetween(nodeId, right),
        ),
      );
    return sortedVisible.isEmpty ? null : sortedVisible.first;
  }

  void _scheduleNode(
    GalaxyNodeModel node, {
    required String? parentId,
  }) {
    if (_nodeSteps.containsKey(node.id)) {
      return;
    }

    if (parentId == null) {
      _clusterIndex += 1;
      if (_clusterIndex > 0) {
        _cursorMs = math.max(_cursorMs, _maxScheduledMs + kGalaxyClusterGapMs);
      }
      final nodeStartMs = _cursorMs;
      final nodeEndMs = nodeStartMs + kGalaxyRootRevealDurationMs;
      final labelStartMs = nodeEndMs;
      final labelEndMs = labelStartMs + kGalaxyLabelRevealDurationMs;
      _nodeSteps[node.id] = BuildPlanNodeStep(
        nodeId: node.id,
        clusterIndex: _clusterIndex,
        parentRevealId: null,
        nodeStartMs: nodeStartMs,
        nodeEndMs: nodeEndMs,
        labelStartMs: labelStartMs,
        labelEndMs: labelEndMs,
      );
      _visibleNodeIds.add(node.id);
      _maxScheduledMs = math.max(_maxScheduledMs, labelEndMs);
      _cursorMs = nodeEndMs + kGalaxyRootPauseMs;
      return;
    }

    if (_clusterIndex < 0) {
      _clusterIndex = 0;
    }
    final parentStep = _nodeSteps[parentId];
    final earliestFromParent = parentStep?.nodeEndMs ?? 0;
    final edgeStartMs = math.max(_cursorMs, earliestFromParent);
    final edgeEndMs = edgeStartMs + kGalaxyEdgeRevealDurationMs;
    final nodeStartMs = edgeEndMs;
    final nodeEndMs = nodeStartMs + kGalaxyNodeRevealDurationMs;
    final labelStartMs = nodeEndMs;
    final labelEndMs = labelStartMs + kGalaxyLabelRevealDurationMs;

    final edge = _strongestEdgeBetween(node.id, parentId);
    final edgeId = edge?.id ?? 'synthetic:$parentId->${node.id}';
    _edgeSteps[edgeId] = BuildPlanEdgeStep(
      id: edgeId,
      sourceId: parentId,
      targetId: node.id,
      clusterIndex: _clusterIndex,
      edgeStartMs: edgeStartMs,
      edgeEndMs: edgeEndMs,
      relationType: edge?.relationType ?? EdgeRelationType.related,
      strength: edge?.strength ?? 0.45,
      isSynthetic: edge == null,
    );
    _nodeSteps[node.id] = BuildPlanNodeStep(
      nodeId: node.id,
      clusterIndex: _clusterIndex,
      parentRevealId: parentId,
      nodeStartMs: nodeStartMs,
      nodeEndMs: nodeEndMs,
      labelStartMs: labelStartMs,
      labelEndMs: labelEndMs,
    );
    _visibleNodeIds.add(node.id);
    _maxScheduledMs = math.max(_maxScheduledMs, labelEndMs);
    _cursorMs = edgeStartMs + kGalaxySiblingStaggerMs;
  }

  Map<String, List<GalaxyEdgeModel>> _buildEdgesByNode(
    List<GalaxyEdgeModel> edges,
  ) {
    final map = <String, List<GalaxyEdgeModel>>{};
    for (final edge in edges) {
      map.putIfAbsent(edge.sourceId, () => <GalaxyEdgeModel>[]).add(edge);
      map.putIfAbsent(edge.targetId, () => <GalaxyEdgeModel>[]).add(edge);
    }
    return map;
  }

  GalaxyEdgeModel? _strongestEdgeBetween(String firstId, String secondId) {
    final candidates = _edgesByNode[firstId]
            ?.where(
              (edge) =>
                  (edge.sourceId == firstId && edge.targetId == secondId) ||
                  (edge.sourceId == secondId && edge.targetId == firstId),
            )
            .toList() ??
        const <GalaxyEdgeModel>[];
    if (candidates.isEmpty) {
      return null;
    }
    candidates.sort((left, right) => right.strength.compareTo(left.strength));
    return candidates.first;
  }

  double _nearestVisibleDistance(String nodeId) {
    if (_visibleNodeIds.isEmpty) {
      return double.infinity;
    }
    return _visibleNodeIds
        .map((visibleId) => _distanceBetween(nodeId, visibleId))
        .fold<double>(double.infinity, math.min);
  }

  double _distanceBetween(String firstId, String secondId) {
    final first = positions[firstId] ?? Offset.zero;
    final second = positions[secondId] ?? Offset.zero;
    return (first - second).distanceSquared;
  }

  Set<String> _collectReachableIds(
    String seedId, {
    required Set<String> allowedNodeIds,
  }) {
    final visited = <String>{};
    final queue = Queue<String>()..add(seedId);

    while (queue.isNotEmpty) {
      final current = queue.removeFirst();
      if (!allowedNodeIds.contains(current) || !visited.add(current)) {
        continue;
      }
      for (final neighborId in adjacency[current] ?? const <String>{}) {
        if (allowedNodeIds.contains(neighborId) &&
            !visited.contains(neighborId)) {
          queue.add(neighborId);
        }
      }
    }

    return visited.isEmpty ? {seedId} : visited;
  }

  bool _canReachVisibleNode(String nodeId) {
    final visited = <String>{nodeId};
    final queue = <String>[nodeId];
    while (queue.isNotEmpty) {
      final current = queue.removeAt(0);
      if (_visibleNodeIds.contains(current)) {
        return true;
      }
      for (final neighbor in adjacency[current] ?? const <String>{}) {
        if (visited.add(neighbor)) {
          queue.add(neighbor);
        }
      }
    }
    return false;
  }

  Offset _positionsCentroid() {
    if (positions.isEmpty) {
      return Offset.zero;
    }
    final sum = positions.values.fold<Offset>(
      Offset.zero,
      (current, offset) => current + offset,
    );
    return sum / positions.length.toDouble();
  }
}
