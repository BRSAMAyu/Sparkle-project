import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/galaxy_layout_engine.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/data/repositories/galaxy_repository.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

/// Aggregation level based on zoom scale
enum AggregationLevel {
  full,      // Show all individual nodes (scale >= 0.6)
  clustered, // Aggregate by parent node (scale >= 0.3)
  sectors,   // Only show sector centroids (scale < 0.3)
}

class GalaxyState { // ID of the predicted next node to learn

  GalaxyState({
    this.nodes = const [],
    this.edges = const [],
    this.nodePositions = const {},
    this.userFlameIntensity = 0.0,
    this.isLoading = false,
    this.isOptimizing = false,
    this.currentScale = 1.0,
    this.aggregationLevel = AggregationLevel.full,
    this.clusters = const {},
    this.viewport,
    this.predictedNodeId,
  });
  final List<GalaxyNodeModel> nodes;
  final List<GalaxyEdgeModel> edges;  // 节点连接
  final Map<String, Offset> nodePositions;
  final double userFlameIntensity;
  final bool isLoading;
  final bool isOptimizing;  // Whether force-directed optimization is running
  final double currentScale;  // Current zoom scale
  final AggregationLevel aggregationLevel;  // Current aggregation level
  final Map<String, ClusterInfo> clusters;  // Cluster information for aggregated view
  final Rect? viewport;  // Current visible viewport for culling
  final String? predictedNodeId;

  GalaxyState copyWith({
    List<GalaxyNodeModel>? nodes,
    List<GalaxyEdgeModel>? edges,
    Map<String, Offset>? nodePositions,
    double? userFlameIntensity,
    bool? isLoading,
    bool? isOptimizing,
    double? currentScale,
    AggregationLevel? aggregationLevel,
    Map<String, ClusterInfo>? clusters,
    Rect? viewport,
    String? predictedNodeId,
  }) => GalaxyState(
      nodes: nodes ?? this.nodes,
      edges: edges ?? this.edges,
      nodePositions: nodePositions ?? this.nodePositions,
      userFlameIntensity: userFlameIntensity ?? this.userFlameIntensity,
      isLoading: isLoading ?? this.isLoading,
      isOptimizing: isOptimizing ?? this.isOptimizing,
      currentScale: currentScale ?? this.currentScale,
      aggregationLevel: aggregationLevel ?? this.aggregationLevel,
      clusters: clusters ?? this.clusters,
      viewport: viewport ?? this.viewport,
      predictedNodeId: predictedNodeId ?? this.predictedNodeId,
    );

  /// 获取可见节点（基于视口裁剪）
  List<GalaxyNodeModel> get visibleNodes {
    if (viewport == null) return nodes;
    final culler = ViewportCuller(viewport: viewport!);
    return culler.filterVisibleNodes(nodes, nodePositions);
  }

  /// 获取可见边（基于视口裁剪）
  List<GalaxyEdgeModel> get visibleEdges {
    if (viewport == null) return edges;
    final culler = ViewportCuller(viewport: viewport!);
    return culler.filterVisibleEdges(edges, nodePositions);
  }
}

/// Information about a cluster of nodes
class ClusterInfo {  // IDs of nodes in this cluster

  ClusterInfo({
    required this.id,
    required this.name,
    required this.position,
    required this.nodeCount,
    required this.totalMastery,
    required this.sector,
    required this.childNodeIds,
  });
  final String id;  // Cluster ID (parent node ID or sector code)
  final String name;  // Display name
  final Offset position;  // Center position
  final int nodeCount;  // Number of nodes in cluster
  final double totalMastery;  // Average mastery of nodes
  final SectorEnum sector;  // Primary sector
  final List<String> childNodeIds;
}

final galaxyProvider = StateNotifierProvider<GalaxyNotifier, GalaxyState>((ref) {
  final repository = ref.watch(galaxyRepositoryProvider);
  return GalaxyNotifier(repository);
});

class GalaxyNotifier extends StateNotifier<GalaxyState> {

  GalaxyNotifier(this._repository) : super(GalaxyState()) {
    _initEventsListener();
  }
  final GalaxyRepository _repository;
  StreamSubscription? _eventsSubscription;

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

      // Step 1: 使用新的布局引擎进行快速初始布局
      final quickPositions = GalaxyLayoutEngine.calculateInitialLayout(
        nodes: response.nodes,
        edges: response.edges,
        existingPositions: state.nodePositions.isNotEmpty ? state.nodePositions : null,
      );

      state = state.copyWith(
        nodes: response.nodes,
        edges: response.edges,
        nodePositions: quickPositions,
        userFlameIntensity: response.userFlameIntensity,
        isLoading: false,
        isOptimizing: true,
      );

      // Step 2: 在后台进行力导向优化
      _optimizeLayoutAsync(response.nodes, response.edges, quickPositions);
    } catch (e) {
      state = state.copyWith(isLoading: false);
      debugPrint('Error loading galaxy: $e');
    }
  }

  Future<void> _optimizeLayoutAsync(
    List<GalaxyNodeModel> nodes,
    List<GalaxyEdgeModel> edges,
    Map<String, Offset> initialPositions,
  ) async {
    try {
      // 使用新的布局引擎进行力导向优化
      final optimizedPositions = await GalaxyLayoutEngine.optimizeLayoutAsync(
        nodes: nodes,
        edges: edges,
        initialPositions: initialPositions,
      );

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

  /// 更新视口（用于视口裁剪优化）
  void updateViewport(Rect viewport) {
    state = state.copyWith(viewport: viewport);
  }

  Future<void> sparkNode(String id) async {
    try {
      await _repository.sparkNode(id);
      await loadGalaxy();
    } catch (e) {
      debugPrint('Error sparking node: $e');
    }
  }

  Future<String?> predictNextNode() async {
    try {
      final detail = await _repository.predictNextNode();
      if (detail != null) {
        state = state.copyWith(predictedNodeId: detail.node.id);
        return detail.node.id;
      }
    } catch (e) {
      debugPrint('Error predicting next node: $e');
    }
    return null;
  }

  Future<List<GalaxySearchResult>> searchNodes(String query) async => _repository.searchNodes(query);

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

    final clusters = <String, ClusterInfo>{};

    if (level == AggregationLevel.clustered) {
      // Group by parent node
      final parentGroups = <String, List<GalaxyNodeModel>>{};

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
        var center = Offset.zero;
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
      final sectorGroups = <SectorEnum, List<GalaxyNodeModel>>{};

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
        var center = Offset.zero;
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

}