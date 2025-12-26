import 'dart:math';
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/data/repositories/galaxy_repository.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

/// Aggregation level based on zoom scale
enum AggregationLevel {
  full,      // Show all individual nodes (scale >= 0.6)
  clustered, // Aggregate by parent node (scale >= 0.3)
  sectors,   // Only show sector centroids (scale < 0.3)
}

class GalaxyState {
  final List<GalaxyNodeModel> nodes;
  final Map<String, Offset> nodePositions;
  final double userFlameIntensity;
  final bool isLoading;
  final bool isOptimizing;  // Whether force-directed optimization is running
  final double currentScale;  // Current zoom scale
  final AggregationLevel aggregationLevel;  // Current aggregation level
  final Map<String, ClusterInfo> clusters;  // Cluster information for aggregated view

  GalaxyState({
    this.nodes = const [],
    this.nodePositions = const {},
    this.userFlameIntensity = 0.0,
    this.isLoading = false,
    this.isOptimizing = false,
    this.currentScale = 1.0,
    this.aggregationLevel = AggregationLevel.full,
    this.clusters = const {},
  });

  GalaxyState copyWith({
    List<GalaxyNodeModel>? nodes,
    Map<String, Offset>? nodePositions,
    double? userFlameIntensity,
    bool? isLoading,
    bool? isOptimizing,
    double? currentScale,
    AggregationLevel? aggregationLevel,
    Map<String, ClusterInfo>? clusters,
  }) {
    return GalaxyState(
      nodes: nodes ?? this.nodes,
      nodePositions: nodePositions ?? this.nodePositions,
      userFlameIntensity: userFlameIntensity ?? this.userFlameIntensity,
      isLoading: isLoading ?? this.isLoading,
      isOptimizing: isOptimizing ?? this.isOptimizing,
      currentScale: currentScale ?? this.currentScale,
      aggregationLevel: aggregationLevel ?? this.aggregationLevel,
      clusters: clusters ?? this.clusters,
    );
  }
}

/// Information about a cluster of nodes
class ClusterInfo {
  final String id;  // Cluster ID (parent node ID or sector code)
  final String name;  // Display name
  final Offset position;  // Center position
  final int nodeCount;  // Number of nodes in cluster
  final double totalMastery;  // Average mastery of nodes
  final SectorEnum sector;  // Primary sector
  final List<String> childNodeIds;  // IDs of nodes in this cluster

  ClusterInfo({
    required this.id,
    required this.name,
    required this.position,
    required this.nodeCount,
    required this.totalMastery,
    required this.sector,
    required this.childNodeIds,
  });
}

final galaxyProvider = StateNotifierProvider<GalaxyNotifier, GalaxyState>((ref) {
  final repository = ref.watch(galaxyRepositoryProvider);
  return GalaxyNotifier(repository);
});

class GalaxyNotifier extends StateNotifier<GalaxyState> {
  final GalaxyRepository _repository;
  StreamSubscription? _eventsSubscription;

  GalaxyNotifier(this._repository) : super(GalaxyState()) {
    _initEventsListener();
  }

  @override
  void dispose() {
    _eventsSubscription?.cancel();
    super.dispose();
  }

  void _initEventsListener() {
    _eventsSubscription = _repository.getGalaxyEventsStream().listen((event) {
      if (event.event == 'nodes_expanded') {
        _handleNodesExpanded(event.jsonData);
      }
    });
  }

  void _handleNodesExpanded(Map<String, dynamic>? data) {
    if (data == null || data['nodes'] == null) return;
    loadGalaxy();
  }

  Future<void> loadGalaxy() async {
    state = state.copyWith(isLoading: true);
    try {
      final response = await _repository.getGraph();

      // Step 1: Quick spiral layout for immediate display
      final quickPositions = _calculateQuickLayout(response.nodes);
      state = state.copyWith(
        nodes: response.nodes,
        nodePositions: quickPositions,
        userFlameIntensity: response.userFlameIntensity,
        isLoading: false,
        isOptimizing: true,
      );

      // Step 2: Optimize in background using force-directed algorithm
      _optimizeLayoutAsync(response.nodes, quickPositions);
    } catch (e) {
      state = state.copyWith(isLoading: false);
      debugPrint('Error loading galaxy: $e');
    }
  }

  Future<void> _optimizeLayoutAsync(
    List<GalaxyNodeModel> nodes,
    Map<String, Offset> initialPositions,
  ) async {
    try {
      // Prepare data for compute isolate
      final data = _LayoutData(
        nodes: nodes.map((n) => _SimpleNode(
          id: n.id,
          parentId: n.parentId,
          sector: n.sector,
          importance: n.importance,
        )).toList(),
        initialPositions: initialPositions,
      );

      // Run force-directed optimization in isolate
      final optimizedPositions = await compute(_forceDirectedLayout, data);

      // Only update if we're still mounted and not loading something new
      if (mounted && !state.isLoading) {
        state = state.copyWith(
          nodePositions: optimizedPositions,
          isOptimizing: false,
        );
      }
    } catch (e) {
      debugPrint('Error optimizing layout: $e');
      state = state.copyWith(isOptimizing: false);
    }
  }

  Future<void> sparkNode(String id) async {
    try {
      await _repository.sparkNode(id);
      await loadGalaxy();
    } catch (e) {
      debugPrint('Error sparking node: $e');
    }
  }

  /// Update current scale and recalculate aggregation level
  void updateScale(double scale) {
    if ((scale - state.currentScale).abs() < 0.01) return;

    // Determine aggregation level based on scale thresholds
    AggregationLevel newLevel;
    if (scale >= 0.6) {
      newLevel = AggregationLevel.full;
    } else if (scale >= 0.3) {
      newLevel = AggregationLevel.clustered;
    } else {
      newLevel = AggregationLevel.sectors;
    }

    // Only recalculate clusters if level changed
    if (newLevel != state.aggregationLevel) {
      final clusters = _calculateClusters(newLevel);
      state = state.copyWith(
        currentScale: scale,
        aggregationLevel: newLevel,
        clusters: clusters,
      );
    } else {
      state = state.copyWith(currentScale: scale);
    }
  }

  /// Calculate clusters based on aggregation level
  Map<String, ClusterInfo> _calculateClusters(AggregationLevel level) {
    if (level == AggregationLevel.full) {
      return {};
    }

    final Map<String, ClusterInfo> clusters = {};

    if (level == AggregationLevel.clustered) {
      // Group by parent node
      final Map<String, List<GalaxyNodeModel>> parentGroups = {};

      for (final node in state.nodes) {
        final parentId = node.parentId ?? node.id; // Root nodes are their own cluster
        parentGroups.putIfAbsent(parentId, () => []);
        parentGroups[parentId]!.add(node);
      }

      // Create cluster for each group
      for (final entry in parentGroups.entries) {
        final parentId = entry.key;
        final groupNodes = entry.value;

        // Find the parent node (or first node if it's a root)
        final parentNode = state.nodes.firstWhere(
          (n) => n.id == parentId,
          orElse: () => groupNodes.first,
        );

        // Calculate center position (average of all node positions)
        Offset center = Offset.zero;
        double totalMastery = 0;
        final childIds = <String>[];

        for (final node in groupNodes) {
          final pos = state.nodePositions[node.id];
          if (pos != null) {
            center += pos;
          }
          totalMastery += node.masteryScore;
          childIds.add(node.id);
        }

        if (groupNodes.isNotEmpty) {
          center = center / groupNodes.length.toDouble();
        }

        clusters[parentId] = ClusterInfo(
          id: parentId,
          name: parentNode.name,
          position: center,
          nodeCount: groupNodes.length,
          totalMastery: totalMastery / groupNodes.length,
          sector: parentNode.sector,
          childNodeIds: childIds,
        );
      }
    } else if (level == AggregationLevel.sectors) {
      // Group by sector
      final Map<SectorEnum, List<GalaxyNodeModel>> sectorGroups = {};

      for (final node in state.nodes) {
        sectorGroups.putIfAbsent(node.sector, () => []);
        sectorGroups[node.sector]!.add(node);
      }

      // Create cluster for each sector
      for (final entry in sectorGroups.entries) {
        final sector = entry.key;
        final sectorNodes = entry.value;
        final style = SectorConfig.getStyle(sector);

        // Calculate sector centroid
        Offset center = Offset.zero;
        double totalMastery = 0;
        final childIds = <String>[];

        for (final node in sectorNodes) {
          final pos = state.nodePositions[node.id];
          if (pos != null) {
            center += pos;
          }
          totalMastery += node.masteryScore;
          childIds.add(node.id);
        }

        if (sectorNodes.isNotEmpty) {
          center = center / sectorNodes.length.toDouble();
        }

        final clusterId = 'sector_${sector.name}';
        clusters[clusterId] = ClusterInfo(
          id: clusterId,
          name: style.name,
          position: center,
          nodeCount: sectorNodes.length,
          totalMastery: totalMastery / sectorNodes.length,
          sector: sector,
          childNodeIds: childIds,
        );
      }
    }

    return clusters;
  }

  /// Quick spiral layout for immediate display
  /// Distributes nodes in their respective sectors using a spiral pattern
  Map<String, Offset> _calculateQuickLayout(List<GalaxyNodeModel> nodes) {
    final Map<String, Offset> positions = {};
    final Random random = Random(42);

    // Group nodes by sector
    final Map<SectorEnum, List<GalaxyNodeModel>> sectorGroups = {};
    for (final node in nodes) {
      sectorGroups.putIfAbsent(node.sector, () => []);
      sectorGroups[node.sector]!.add(node);
    }

    // Sort nodes in each sector: roots first, then by importance
    for (final sector in sectorGroups.keys) {
      sectorGroups[sector]!.sort((a, b) {
        if (a.parentId == null && b.parentId != null) return -1;
        if (a.parentId != null && b.parentId == null) return 1;
        return b.importance.compareTo(a.importance);
      });
    }

    // Place nodes using spiral layout within each sector
    for (final entry in sectorGroups.entries) {
      final sector = entry.key;
      final sectorNodes = entry.value;
      final style = SectorConfig.getStyle(sector);

      // Convert angles to radians
      final baseAngleRad = (style.baseAngle - 90) * pi / 180; // -90 to start from top
      final sweepAngleRad = style.sweepAngle * pi / 180;

      int index = 0;
      for (final node in sectorNodes) {
        if (node.parentId == null) {
          // Root nodes: spiral outward from center
          final spiralIndex = index;
          final radius = 180 + spiralIndex * 35; // Increasing radius
          final angleOffset = (spiralIndex * 0.3) % 1.0; // Spread within sector
          final angle = baseAngleRad + sweepAngleRad * (0.2 + angleOffset * 0.6);

          // Add slight randomness for organic feel
          final noise = (random.nextDouble() - 0.5) * 20;
          positions[node.id] = Offset(
            (radius + noise) * cos(angle),
            (radius + noise) * sin(angle),
          );
          index++;
        } else {
          // Child nodes: cluster around parent
          final parentPos = positions[node.parentId];
          if (parentPos != null) {
            final dist = 50.0 + (5 - node.importance) * 12.0;
            final angle = random.nextDouble() * 2 * pi;
            final noise = (random.nextDouble() - 0.5) * 10;

            positions[node.id] = parentPos + Offset(
              (dist + noise) * cos(angle),
              (dist + noise) * sin(angle),
            );
          } else {
            // Orphan fallback: place in sector
            final radius = 250 + random.nextDouble() * 100;
            final angle = baseAngleRad + random.nextDouble() * sweepAngleRad;
            positions[node.id] = Offset(radius * cos(angle), radius * sin(angle));
          }
        }
      }
    }

    return positions;
  }
}

/// Simple node data for passing to isolate
class _SimpleNode {
  final String id;
  final String? parentId;
  final SectorEnum sector;
  final int importance;

  _SimpleNode({
    required this.id,
    required this.parentId,
    required this.sector,
    required this.importance,
  });
}

/// Data package for compute isolate
class _LayoutData {
  final List<_SimpleNode> nodes;
  final Map<String, Offset> initialPositions;

  _LayoutData({required this.nodes, required this.initialPositions});
}

/// Force-directed layout optimization (runs in isolate)
Map<String, Offset> _forceDirectedLayout(_LayoutData data) {
  final nodes = data.nodes;
  final positions = Map<String, Offset>.from(data.initialPositions);

  if (nodes.isEmpty) return positions;

  // Parameters
  const int iterations = 80;
  const double repulsionStrength = 800.0;
  const double attractionStrength = 0.02;
  const double minDistance = 40.0;
  const double maxDisplacement = 30.0;
  const double damping = 0.85;

  // Create parent-child lookup
  final Map<String, List<String>> children = {};
  for (final node in nodes) {
    if (node.parentId != null) {
      children.putIfAbsent(node.parentId!, () => []);
      children[node.parentId]!.add(node.id);
    }
  }

  // Sector constraints (to keep nodes in their sectors)
  final sectorStyles = <String, (double, double)>{}; // id -> (baseAngle, sweepAngle)
  for (final node in nodes) {
    final style = SectorConfig.getStyle(node.sector);
    sectorStyles[node.id] = (
      (style.baseAngle - 90) * pi / 180,
      style.sweepAngle * pi / 180,
    );
  }

  // Velocity for momentum
  final velocity = <String, Offset>{};
  for (final node in nodes) {
    velocity[node.id] = Offset.zero;
  }

  for (int iter = 0; iter < iterations; iter++) {
    // Reduce strength over iterations (simulated annealing)
    final temp = 1.0 - (iter / iterations);

    for (final nodeA in nodes) {
      var force = Offset.zero;
      final posA = positions[nodeA.id]!;

      // Repulsion from all other nodes
      for (final nodeB in nodes) {
        if (nodeA.id == nodeB.id) continue;
        final posB = positions[nodeB.id]!;
        final delta = posA - posB;
        var distance = delta.distance;
        if (distance < 1) distance = 1;

        if (distance < minDistance * 3) {
          // Strong repulsion when close
          final repulsion = repulsionStrength * temp / (distance * distance);
          force += Offset(
            delta.dx / distance * repulsion,
            delta.dy / distance * repulsion,
          );
        }
      }

      // Attraction to parent
      if (nodeA.parentId != null) {
        final parentPos = positions[nodeA.parentId];
        if (parentPos != null) {
          final delta = parentPos - posA;
          final distance = delta.distance;
          if (distance > 50) {
            force += Offset(
              delta.dx * attractionStrength * temp,
              delta.dy * attractionStrength * temp,
            );
          }
        }
      }

      // Mild attraction to children (to keep groups together)
      final nodeChildren = children[nodeA.id];
      if (nodeChildren != null) {
        for (final childId in nodeChildren) {
          final childPos = positions[childId];
          if (childPos != null) {
            final delta = childPos - posA;
            final distance = delta.distance;
            if (distance > 80) {
              force += Offset(
                delta.dx * attractionStrength * 0.5 * temp,
                delta.dy * attractionStrength * 0.5 * temp,
              );
            }
          }
        }
      }

      // Center gravity (mild attraction to origin to prevent drift)
      final distFromCenter = posA.distance;
      if (distFromCenter > 800) {
        force -= Offset(
          posA.dx * 0.001 * temp,
          posA.dy * 0.001 * temp,
        );
      }

      // Update velocity with damping
      velocity[nodeA.id] = (velocity[nodeA.id]! + force) * damping;

      // Clamp displacement
      var displacement = velocity[nodeA.id]!;
      final mag = displacement.distance;
      if (mag > maxDisplacement) {
        displacement = displacement / mag * maxDisplacement;
      }

      // Apply displacement
      var newPos = posA + displacement;

      // Constrain to sector (soft constraint)
      final (baseAngle, sweepAngle) = sectorStyles[nodeA.id]!;
      final nodeAngle = atan2(newPos.dy, newPos.dx);
      final endAngle = baseAngle + sweepAngle;

      // Check if angle is within sector
      double normalizedAngle = nodeAngle;
      while (normalizedAngle < baseAngle) {
        normalizedAngle += 2 * pi;
      }
      while (normalizedAngle >= baseAngle + 2 * pi) {
        normalizedAngle -= 2 * pi;
      }

      if (normalizedAngle < baseAngle || normalizedAngle > endAngle) {
        // Gently push back toward sector center
        final centerAngle = baseAngle + sweepAngle / 2;
        final targetAngle = centerAngle + (normalizedAngle - centerAngle) * 0.9;
        final dist = newPos.distance;
        newPos = Offset(dist * cos(targetAngle), dist * sin(targetAngle));
      }

      positions[nodeA.id] = newPos;
    }
  }

  return positions;
}
