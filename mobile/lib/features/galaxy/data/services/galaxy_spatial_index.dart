import 'dart:math' as math;
import 'dart:ui';

import 'package:sparkle/shared/entities/galaxy_model.dart';

class GalaxyNodeHit {
  const GalaxyNodeHit({
    required this.nodeId,
    required this.worldPosition,
    required this.distance,
  });

  final String nodeId;
  final Offset worldPosition;
  final double distance;
}

class GalaxySpatialIndex {
  GalaxySpatialIndex({this.cellSize = 200});

  final double cellSize;
  final Map<_GridCell, List<_GridEntry>> _cells =
      <_GridCell, List<_GridEntry>>{};
  final Map<String, _GridEntry> _entriesById = <String, _GridEntry>{};

  int get size => _entriesById.length;

  void clear() {
    _cells.clear();
    _entriesById.clear();
  }

  void build(Map<String, Offset> positions, List<GalaxyNodeModel> nodes) {
    clear();

    for (final node in nodes) {
      final position = positions[node.id];
      if (position == null) {
        continue;
      }

      final entry = _GridEntry(
        nodeId: node.id,
        position: position,
        radius: node.radius,
      );
      final cell = _cellFor(position);
      _cells.putIfAbsent(cell, () => <_GridEntry>[]).add(entry);
      _entriesById[node.id] = entry;
    }
  }

  List<String> queryRect(Rect worldRect) {
    if (_cells.isEmpty) {
      return const <String>[];
    }

    final ids = <String>{};
    final minCellX = _cellCoord(worldRect.left);
    final maxCellX = _cellCoord(worldRect.right);
    final minCellY = _cellCoord(worldRect.top);
    final maxCellY = _cellCoord(worldRect.bottom);

    for (var x = minCellX; x <= maxCellX; x++) {
      for (var y = minCellY; y <= maxCellY; y++) {
        final bucket = _cells[_GridCell(x, y)];
        if (bucket == null) {
          continue;
        }

        for (final entry in bucket) {
          if (worldRect.inflate(entry.radius).contains(entry.position)) {
            ids.add(entry.nodeId);
          }
        }
      }
    }

    return ids.toList(growable: false);
  }

  GalaxyNodeHit? queryNearest(Offset worldPoint, double maxRadius) {
    if (_cells.isEmpty) {
      return null;
    }

    final cellRadius = (maxRadius / cellSize).ceil();
    final centerCell = _cellFor(worldPoint);
    GalaxyNodeHit? nearest;

    for (var dx = -cellRadius; dx <= cellRadius; dx++) {
      for (var dy = -cellRadius; dy <= cellRadius; dy++) {
        final bucket = _cells[_GridCell(centerCell.x + dx, centerCell.y + dy)];
        if (bucket == null) {
          continue;
        }

        for (final entry in bucket) {
          final allowedRadius = math.max(maxRadius, entry.radius);
          final distance = (entry.position - worldPoint).distance;
          if (distance > allowedRadius) {
            continue;
          }

          if (nearest == null || distance < nearest.distance) {
            nearest = GalaxyNodeHit(
              nodeId: entry.nodeId,
              worldPosition: entry.position,
              distance: distance,
            );
          }
        }
      }
    }

    return nearest;
  }

  _GridCell _cellFor(Offset position) => _GridCell(
        _cellCoord(position.dx),
        _cellCoord(position.dy),
      );

  int _cellCoord(double value) => (value / cellSize).floor();
}

class _GridEntry {
  const _GridEntry({
    required this.nodeId,
    required this.position,
    required this.radius,
  });

  final String nodeId;
  final Offset position;
  final double radius;
}

class _GridCell {
  const _GridCell(this.x, this.y);

  final int x;
  final int y;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is _GridCell &&
          runtimeType == other.runtimeType &&
          x == other.x &&
          y == other.y;

  @override
  int get hashCode => Object.hash(x, y);
}
