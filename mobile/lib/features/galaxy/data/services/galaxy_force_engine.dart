import 'dart:math' as math;
import 'dart:ui';

import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';

class GalaxyForceTickResult {
  const GalaxyForceTickResult({
    required this.positions,
    required this.isSettled,
  });

  final Map<String, Offset> positions;
  final bool isSettled;
}

class GalaxyForceEngine {
  GalaxyForceEngine({
    double damping = 0.88,
    double springK = 0.045,
    double repulsionK = 12000,
    double centerGravity = 0.0016,
    double maxVelocity = 14,
    double repulsionRadius = 340,
    double springRestLength = 128,
  })  : _damping = damping,
        _springK = springK,
        _repulsionK = repulsionK,
        _centerGravity = centerGravity,
        _maxVelocity = maxVelocity,
        _repulsionRadius = repulsionRadius,
        _springRestLength = springRestLength;

  double _damping;
  double _springK;
  double _repulsionK;
  double _centerGravity;
  double _maxVelocity;
  double _repulsionRadius;
  double _springRestLength;

  double get damping => _damping;
  double get springK => _springK;
  double get repulsionK => _repulsionK;
  double get centerGravity => _centerGravity;
  double get maxVelocity => _maxVelocity;
  double get repulsionRadius => _repulsionRadius;
  double get springRestLength => _springRestLength;

  void updateParameters({
    double? damping,
    double? springK,
    double? repulsionK,
    double? centerGravity,
    double? maxVelocity,
    double? repulsionRadius,
    double? springRestLength,
  }) {
    if (damping != null) {
      _damping = damping;
    }
    if (springK != null) {
      _springK = springK;
    }
    if (repulsionK != null) {
      _repulsionK = repulsionK;
    }
    if (centerGravity != null) {
      _centerGravity = centerGravity;
    }
    if (maxVelocity != null) {
      _maxVelocity = maxVelocity;
    }
    if (repulsionRadius != null) {
      _repulsionRadius = repulsionRadius;
    }
    if (springRestLength != null) {
      _springRestLength = springRestLength;
    }
  }

  final Map<String, Offset> _velocities = <String, Offset>{};
  final Set<String> _activeNodeIds = <String>{};
  String? _anchoredNodeId;

  bool get hasActiveSimulation =>
      _activeNodeIds.isNotEmpty || _anchoredNodeId != null;

  void clear() {
    _velocities.clear();
    _activeNodeIds.clear();
    _anchoredNodeId = null;
  }

  void anchorNode(String nodeId, Map<String, Set<String>> adjacency) {
    _anchoredNodeId = nodeId;
    _activeNodeIds
      ..clear()
      ..addAll(_collectNeighborhood(nodeId, adjacency, depth: 2))
      ..remove(nodeId);
    for (final activeNodeId in _activeNodeIds) {
      _velocities.putIfAbsent(activeNodeId, () => Offset.zero);
    }
  }

  void releaseAnchor() {
    final anchoredNodeId = _anchoredNodeId;
    if (anchoredNodeId != null) {
      _activeNodeIds.add(anchoredNodeId);
      _velocities.putIfAbsent(anchoredNodeId, () => Offset.zero);
    }
    _anchoredNodeId = null;
  }

  GalaxyForceTickResult tick({
    required Map<String, Offset> positions,
    required Map<String, Set<String>> adjacency,
    required Map<String, double> edgeStrengths,
    required GalaxySpatialIndex spatialIndex,
    Rect? viewport,
  }) {
    if (_activeNodeIds.isEmpty && _anchoredNodeId == null) {
      return GalaxyForceTickResult(
        positions: positions,
        isSettled: true,
      );
    }

    final nextPositions = Map<String, Offset>.from(positions);
    var settled = true;
    final nodesToSimulate = _activeNodeIds.toList(growable: false);

    for (final nodeId in nodesToSimulate) {
      if (nodeId == _anchoredNodeId) {
        continue;
      }

      final position = nextPositions[nodeId];
      if (position == null) {
        _activeNodeIds.remove(nodeId);
        _velocities.remove(nodeId);
        continue;
      }

      var totalForce = Offset.zero;
      for (final neighborId in adjacency[nodeId] ?? const <String>{}) {
        final neighborPosition = nextPositions[neighborId];
        if (neighborPosition == null) {
          continue;
        }

        final delta = neighborPosition - position;
        final distance = math.max(delta.distance, 1.0);
        final direction = delta / distance;
        final relationStrength =
            edgeStrengths[_edgeStrengthKey(nodeId, neighborId)] ?? 1;
        final targetDistance = (_springRestLength *
                (1.08 - (relationStrength - 1).clamp(0.0, 0.65) * 0.18))
            .clamp(84.0, 156.0);
        final stretch = distance - targetDistance;
        totalForce += direction * stretch * _springK * relationStrength;
      }

      final repulsionRect =
          Rect.fromCircle(center: position, radius: _repulsionRadius);
      final nearbyNodeIds = spatialIndex.queryRect(repulsionRect);
      for (final nearbyNodeId in nearbyNodeIds) {
        if (nearbyNodeId == nodeId) {
          continue;
        }

        final otherPosition = nextPositions[nearbyNodeId];
        if (otherPosition == null) {
          continue;
        }

        final delta = position - otherPosition;
        final distance = math.max(delta.distance, 12.0);
        if (distance > _repulsionRadius) {
          continue;
        }

        final falloff = 1 - (distance / _repulsionRadius);
        totalForce += (delta / distance) *
            ((_repulsionK * falloff.clamp(0.0, 1.0)) / (distance * distance));
      }

      totalForce += Offset(-position.dx, -position.dy) * _centerGravity;

      var velocity = (_velocities[nodeId] ?? Offset.zero) + totalForce;
      velocity = velocity * _damping;
      final velocityDistance = velocity.distance;
      if (velocityDistance < 0.12 && totalForce.distance < 0.08) {
        _velocities[nodeId] = Offset.zero;
        nextPositions[nodeId] = position;
        continue;
      }
      if (velocityDistance > _maxVelocity) {
        velocity = (velocity / velocityDistance) * _maxVelocity;
      }

      final nextPosition = position + velocity;
      if (viewport == null ||
          viewport.inflate(_repulsionRadius).contains(nextPosition)) {
        nextPositions[nodeId] = nextPosition;
      } else {
        nextPositions[nodeId] = position + velocity * 0.35;
      }

      _velocities[nodeId] = velocity;
      if (velocity.distance >= 0.1) {
        settled = false;
      }
    }

    if (settled && _anchoredNodeId == null) {
      clear();
    }

    return GalaxyForceTickResult(
      positions: nextPositions,
      isSettled: settled && _anchoredNodeId == null,
    );
  }

  Set<String> _collectNeighborhood(
    String originId,
    Map<String, Set<String>> adjacency, {
    required int depth,
  }) {
    final visited = <String>{originId};
    final frontier = <String>{originId};

    for (var currentDepth = 0; currentDepth < depth; currentDepth++) {
      final nextFrontier = <String>{};
      for (final nodeId in frontier) {
        for (final neighborId in adjacency[nodeId] ?? const <String>{}) {
          if (visited.add(neighborId)) {
            nextFrontier.add(neighborId);
          }
        }
      }
      frontier
        ..clear()
        ..addAll(nextFrontier);
      if (frontier.isEmpty) {
        break;
      }
    }

    return visited;
  }

  static String edgeStrengthKey(String first, String second) =>
      _edgeStrengthKey(first, second);

  static String _edgeStrengthKey(String first, String second) =>
      first.compareTo(second) <= 0 ? '$first::$second' : '$second::$first';
}
