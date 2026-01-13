import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_optimization_config.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_layout_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_performance_monitor.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

/// Aggregation level based on zoom scale (5 levels)
enum AggregationLevel {
  universe, // < 0.2: Sector centroids only
  galaxy, // 0.2-0.4: Root nodes only
  cluster, // 0.4-0.6: Importance >= 3
  nebula, // 0.6-0.8: Importance >= 2
  full, // >= 0.8: All nodes
}

class GalaxyState {
  GalaxyState({
    this.nodes = const [],
    this.edges = const [],
    this.nodePositions = const {},
    this.visibleNodes = const [],
    this.visibleEdges = const [],
    this.userFlameIntensity = 0.0,
    this.isLoading = false,
    this.isOptimizing = false,
    this.currentScale = 1.0,
    this.aggregationLevel = AggregationLevel.full,
    this.clusters = const {},
    this.viewport,
    this.predictedNodeId,
    this.lastError,
    this.isUsingCache = false,
    this.selectedNodeId,
    this.expandedEdgeNodeIds = const {},
    this.nodeAnimationProgress = const {},
    this.optimizationConfig = GalaxyOptimizationConfig.standard,
  });

  static const Object _noChange = Object();
  final List<GalaxyNodeModel> nodes;
  final List<GalaxyEdgeModel> edges; // All edges
  final Map<String, Offset> nodePositions;

  // Pre-computed visible subset for rendering
  final List<GalaxyNodeModel> visibleNodes;
  final List<GalaxyEdgeModel> visibleEdges;

  final double userFlameIntensity;
  final bool isLoading;
  final bool isOptimizing; // Whether force-directed optimization is running
  final double currentScale; // Current zoom scale
  final AggregationLevel aggregationLevel; // Current aggregation level
  final Map<String, ClusterInfo>
      clusters; // Cluster information for aggregated view
  final Rect? viewport; // Current visible viewport for culling
  final String? predictedNodeId;
  final GalaxyError? lastError;
  final bool isUsingCache;

  // Interaction state
  final String? selectedNodeId;
  final Set<String>
      expandedEdgeNodeIds; // Nodes whose connections should be fully visible
  final Map<String, double>
      nodeAnimationProgress; // 0.0 to 1.0 for bloom/shrink animation
  
  // Performance Config
  final GalaxyOptimizationConfig optimizationConfig;

  GalaxyState copyWith({
    List<GalaxyNodeModel>? nodes,
    List<GalaxyEdgeModel>? edges,
    Map<String, Offset>? nodePositions,
    List<GalaxyNodeModel>? visibleNodes,
    List<GalaxyEdgeModel>? visibleEdges,
    double? userFlameIntensity,
    bool? isLoading,
    bool? isOptimizing,
    double? currentScale,
    AggregationLevel? aggregationLevel,
    Map<String, ClusterInfo>? clusters,
    Rect? viewport,
    String? predictedNodeId,
    Object? lastError = _noChange,
    bool? isUsingCache,
    String? selectedNodeId,
    Set<String>? expandedEdgeNodeIds,
    Map<String, double>? nodeAnimationProgress,
    GalaxyOptimizationConfig? optimizationConfig,
  }) =>
      GalaxyState(
        nodes: nodes ?? this.nodes,
        edges: edges ?? this.edges,
        nodePositions: nodePositions ?? this.nodePositions,
        visibleNodes: visibleNodes ?? this.visibleNodes,
        visibleEdges: visibleEdges ?? this.visibleEdges,
        userFlameIntensity: userFlameIntensity ?? this.userFlameIntensity,
        isLoading: isLoading ?? this.isLoading,
        isOptimizing: isOptimizing ?? this.isOptimizing,
        currentScale: currentScale ?? this.currentScale,
        aggregationLevel: aggregationLevel ?? this.aggregationLevel,
        clusters: clusters ?? this.clusters,
        viewport: viewport ?? this.viewport,
        predictedNodeId: predictedNodeId ?? this.predictedNodeId,
        lastError: identical(lastError, _noChange)
            ? this.lastError
            : lastError as GalaxyError?,
        isUsingCache: isUsingCache ?? this.isUsingCache,
        selectedNodeId: selectedNodeId ?? this.selectedNodeId,
        expandedEdgeNodeIds: expandedEdgeNodeIds ?? this.expandedEdgeNodeIds,
        nodeAnimationProgress:
            nodeAnimationProgress ?? this.nodeAnimationProgress,
        optimizationConfig: optimizationConfig ?? this.optimizationConfig,
      );
}

/// Information about a cluster of nodes
class ClusterInfo {
  // IDs of nodes in this cluster

  ClusterInfo({
    required this.id,
    required this.name,
    required this.position,
    required this.nodeCount,
    required this.totalMastery,
    required this.sector,
    required this.childNodeIds,
  });
  final String id; // Cluster ID (parent node ID or sector code)
  final String name; // Display name
  final Offset position; // Center position
  final int nodeCount; // Number of nodes in cluster
  final double totalMastery; // Average mastery of nodes
  final SectorEnum sector; // Primary sector
  final List<String> childNodeIds;
}

final galaxyProvider =
    StateNotifierProvider<GalaxyNotifier, GalaxyState>((ref) {
  final repository = ref.watch(enhancedGalaxyRepositoryProvider);
  return GalaxyNotifier(repository);
});

class GalaxyNotifier extends StateNotifier<GalaxyState> {
  GalaxyNotifier(this._repository) : super(GalaxyState()) {
    _initEventsListener();
    _initPerformanceMonitor();
  }
  final EnhancedGalaxyRepository _repository;
  StreamSubscription? _eventsSubscription;
  Timer? _eventsReconnectTimer;
  int _layoutRequestId = 0;

  // Animation timer for bloom/shrink effects
  Timer? _animationTimer;
  static const double _animationDuration = 300; // ms
  static const int _animationFps = 60;
  static const double _animationStep = 1000 / _animationFps; // ~16.67ms
  
  // Performance Monitor
  VoidCallback? _tierListener;

  void _initPerformanceMonitor() {
    // Start monitoring
    GalaxyPerformanceMonitor.instance.startMonitoring();
    
    // Set initial config
    final initialTier = _mapPerformanceTier(
      PerformanceService.instance.currentTier.value,
    );
    state = state.copyWith(
      optimizationConfig: GalaxyOptimizationConfig.fromTier(initialTier),
    );

    // Listen for changes
    _tierListener = () {
      if (!mounted) return;
      final tier = _mapPerformanceTier(
        PerformanceService.instance.currentTier.value,
      );
      state = state.copyWith(
        optimizationConfig: GalaxyOptimizationConfig.fromTier(tier),
      );
    };
    PerformanceService.instance.currentTier.addListener(_tierListener!);
  }

  @override
  void dispose() {
    _eventsSubscription?.cancel();
    _eventsReconnectTimer?.cancel();
    _animationTimer?.cancel();
    _viewportThrottleTimer?.cancel();
    final tierListener = _tierListener;
    if (tierListener != null) {
      PerformanceService.instance.currentTier.removeListener(tierListener);
    }
    // Do not stop monitoring here as it might be used by other parts or singleton lifecycle
    // But for this screen it's probably fine. Let's keep it running for now or stop it?
    // If GalaxyScreen is the only consumer, we could stop it.
    // GalaxyPerformanceMonitor.instance.stopMonitoring(); 
    super.dispose();
  }

  PerformanceTier _mapPerformanceTier(PerformanceTier tier) => tier;

  void _initEventsListener() {
    _eventsSubscription?.cancel();
    _eventsSubscription = _repository.getGalaxyEventsStream().listen(
      (event) {
        if (event.event == 'nodes_expanded') {
          _handleNodesExpanded(event.jsonData);
        } else if (event.event == 'galaxy.node.updated') {
          _handleNodeUpdated(event.jsonData);
        }
      },
      onError: (error, stack) {
        debugPrint('Galaxy events stream error: $error');
        _scheduleEventsReconnect();
      },
      onDone: _scheduleEventsReconnect,
    );
  }

  void _scheduleEventsReconnect() {
    if (!mounted) return;
    _eventsSubscription?.cancel();
    _eventsReconnectTimer?.cancel();
    _eventsReconnectTimer = Timer(const Duration(seconds: 5), () {
      if (mounted) _initEventsListener();
    });
  }

  void _handleNodesExpanded(Map<String, dynamic>? data) {
    if (data == null || data['nodes'] == null) return;
    loadGalaxy(forceRefresh: true);
  }

  void _handleNodeUpdated(Map<String, dynamic>? data) {
    if (data == null || data['node_id'] == null || data['new_mastery'] == null) {
      return;
    }

    final nodeId = data['node_id'] as String;
    final newMastery = (data['new_mastery'] as num).toInt();

    // Optimistic update of local state
    final updatedNodes = state.nodes.map((node) {
      if (node.id == nodeId) {
        return node.copyWith(masteryScore: newMastery);
      }
      return node;
    }).toList();

    // Re-calculate clusters if necessary (since mastery affects cluster stats)
    final updatedClusters = _calculateClusters(
      state.aggregationLevel,
      nodes: updatedNodes,
      positions: state.nodePositions,
    );

    state = state.copyWith(
      nodes: updatedNodes,
      clusters: updatedClusters,
    );
    
    // Recalculate visibility in case mastery affects filtering (though currently it mostly doesn't)
    _recalculateVisibility();
  }

  Future<void> loadGalaxy({bool forceRefresh = false}) async {
    state = state.copyWith(isLoading: true, lastError: null);
    final requestId = ++_layoutRequestId;
    try {
      final result = await _repository.getGraph(forceRefresh: forceRefresh);
      if (!mounted || requestId != _layoutRequestId) return;

      if (result.isFailure || result.data == null) {
        final error = result.error ?? 'Unknown error';
        final galaxyError = error is GalaxyError
            ? error
            : GalaxyError.unknown(error.toString());
        state = state.copyWith(
          isLoading: false,
          isOptimizing: false,
          lastError: galaxyError,
          isUsingCache: false,
        );
        return;
      }

      final response = result.data;
      final aggregationLevel = _levelForScale(state.currentScale);
      final selectedNodeId = state.selectedNodeId;
      final predictedNodeId = state.predictedNodeId;
      final hasSelected = selectedNodeId != null &&
          response.nodes.any((node) => node.id == selectedNodeId);
      final hasPredicted = predictedNodeId != null &&
          response.nodes.any((node) => node.id == predictedNodeId);
      final expandedEdgeNodeIds = hasSelected
          ? _collectExpandedEdges(selectedNodeId, response.edges)
          : const <String>{};

      // Step 1: 使用新的布局引擎进行快速初始布局
      final quickPositions = GalaxyLayoutEngine.calculateInitialLayout(
        nodes: response.nodes,
        edges: response.edges,
        existingPositions:
            state.nodePositions.isNotEmpty ? state.nodePositions : null,
      );

      state = state.copyWith(
        nodes: response.nodes,
        edges: response.edges,
        nodePositions: quickPositions,
        userFlameIntensity: response.userFlameIntensity,
        aggregationLevel: aggregationLevel,
        clusters: _calculateClusters(
          aggregationLevel,
          nodes: response.nodes,
          positions: quickPositions,
        ),
        selectedNodeId: hasSelected ? selectedNodeId : null,
        expandedEdgeNodeIds: expandedEdgeNodeIds,
        predictedNodeId: hasPredicted ? predictedNodeId : null,
        isLoading: false,
        isOptimizing: response.nodes.isNotEmpty,
        isUsingCache: result.isFromCache,
        lastError: null,
      );
      _recalculateVisibility(withAnimation: true);

      // Step 2: 在后台进行力导向优化
      if (response.nodes.isNotEmpty) {
        _optimizeLayoutAsync(
          response.nodes,
          response.edges,
          quickPositions,
          requestId,
        );
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        isOptimizing: false,
        lastError: GalaxyError.unknown(e.toString()),
        isUsingCache: false,
      );
      debugPrint('Error loading galaxy: $e');
    }
  }

  Future<void> _optimizeLayoutAsync(
    List<GalaxyNodeModel> nodes,
    List<GalaxyEdgeModel> edges,
    Map<String, Offset> initialPositions,
    int requestId,
  ) async {
    try {
      // 使用新的布局引擎进行力导向优化
      final optimizedPositions =
          await GalaxyLayoutEngineAsync.optimizeLayoutAsync(
        nodes: nodes,
        edges: edges,
        initialPositions: initialPositions,
      );

      // Only update if we're still mounted and not loading something new
      if (mounted && !state.isLoading && requestId == _layoutRequestId) {
        state = state.copyWith(
          nodePositions: optimizedPositions,
          isOptimizing: false,
          clusters: _calculateClusters(
            state.aggregationLevel,
            nodes: state.nodes,
            positions: optimizedPositions,
          ),
        );
        _recalculateVisibility();
      }
    } catch (e) {
      debugPrint('Error optimizing layout: $e');
      state = state.copyWith(isOptimizing: false);
    }
  }

  // Throttling for viewport updates
  Timer? _viewportThrottleTimer;
  Rect? _pendingViewport;

  /// 更新视口（用于视口裁剪优化）
  void updateViewport(Rect viewport) {
    _pendingViewport = viewport;

    // Cancel existing throttle timer
    _viewportThrottleTimer?.cancel();

    // Throttle to 100ms (60fps friendly)
    _viewportThrottleTimer = Timer(const Duration(milliseconds: 100), () {
      if (_pendingViewport == null) return;

      final viewport = _pendingViewport;
      _pendingViewport = null;

      // Only update if viewport changed significantly
      if (state.viewport != null) {
        final old = state.viewport;
        final dx = (old.center.dx - viewport.center.dx).abs();
        final dy = (old.center.dy - viewport.center.dy).abs();
        final dw = (old.width - viewport.width).abs();
        final dh = (old.height - viewport.height).abs();

        // If moved less than 50px, skip update
        if (dx < 50 && dy < 50 && dw < 50 && dh < 50) {
          return;
        }
      }

      state = state.copyWith(viewport: viewport);
      _recalculateVisibility();
    });
  }

  /// Handle node selection
  void selectNode(String nodeId) {
    if (state.selectedNodeId == nodeId) return;
    if (state.nodes.isEmpty) return;

    // Find related nodes to expand connections
    final expanded = _collectExpandedEdges(nodeId, state.edges);

    state = state.copyWith(
      selectedNodeId: nodeId,
      expandedEdgeNodeIds: expanded,
    );
    _recalculateVisibility();
  }

  /// Handle deselection
  void deselectNode() {
    if (state.selectedNodeId == null) return;

    // Manually create new state to ensure null is set
    state = GalaxyState(
      nodes: state.nodes,
      edges: state.edges,
      nodePositions: state.nodePositions,
      visibleNodes: state.visibleNodes,
      visibleEdges: state.visibleEdges,
      userFlameIntensity: state.userFlameIntensity,
      isLoading: state.isLoading,
      isOptimizing: state.isOptimizing,
      currentScale: state.currentScale,
      aggregationLevel: state.aggregationLevel,
      clusters: state.clusters,
      viewport: state.viewport,
      predictedNodeId: state.predictedNodeId,
      lastError: state.lastError,
      isUsingCache: state.isUsingCache,
      expandedEdgeNodeIds: {}, // CLEAR
      nodeAnimationProgress: state.nodeAnimationProgress,
    );
    _recalculateVisibility();
  }

  Future<GalaxyError?> sparkNode(String id) async {
    final result = await _repository.sparkNode(id);
    if (result.error != null) {
      final error = result.error;
      final galaxyError =
          error is GalaxyError ? error : GalaxyError.unknown(error.toString());
      state = state.copyWith(lastError: galaxyError);
      return galaxyError;
    }
    await loadGalaxy(forceRefresh: true);
    return null;
  }

  Future<String?> predictNextNode() async {
    try {
      final result = await _repository.predictNextNode();
      final detail = result.data;
      if (detail?.node != null) {
        state = state.copyWith(predictedNodeId: detail!.node.id);
        return detail.node.id;
      }
    } catch (e) {
      debugPrint('Error predicting next node: $e');
    }
    return null;
  }

  Future<List<GalaxySearchResult>> searchNodes(String query) async {
    final result = await _repository.searchNodes(query);
    return result.data ?? [];
  }

  /// Update current scale and recalculate aggregation level
  void updateScale(double scale) {
    if ((scale - state.currentScale).abs() < 0.01) return;

    // Determine aggregation level based on 5-level LOD
    final newLevel = _levelForScale(scale);

    // Only recalculate clusters if level changed
    if (newLevel != state.aggregationLevel) {
      final clusters = _calculateClusters(newLevel);
      state = state.copyWith(
        currentScale: scale,
        aggregationLevel: newLevel,
        clusters: clusters,
      );
      // Trigger animation when LOD changes
      _recalculateVisibility(withAnimation: true);
    } else {
      state = state.copyWith(currentScale: scale);
      // Even if level didn't change, viewport culling might change with scale?
      // Actually usually viewport updates happen separately via updateViewport.
      // But if we zoomed, the viewport in world coordinates changed, so the screen might call updateViewport separately.
      // So we don't strictly need to recalculate visibility here unless we want to do strict scale-based filtering.
      _recalculateVisibility();
    }
  }

  void _recalculateVisibility({bool withAnimation = false}) {
    final visibleNodes = _computeVisibleNodes();
    final visibleEdges = _computeVisibleEdges(visibleNodes);

    if (withAnimation) {
      // Start bloom animation for new nodes
      _startBloomAnimation(visibleNodes);
    } else {
      state = state.copyWith(
        visibleNodes: visibleNodes,
        visibleEdges: visibleEdges,
        nodeAnimationProgress: const {}, // Clear animations
      );
    }
  }

  /// Start bloom animation for nodes
  void _startBloomAnimation(List<GalaxyNodeModel> newVisibleNodes) {
    // Cancel existing timer
    _animationTimer?.cancel();

    // Initialize animation progress for all visible nodes
    final animationProgress = <String, double>{};
    for (final node in newVisibleNodes) {
      animationProgress[node.id] = 0.0;
    }

    // Update state with initial animation progress
    state = state.copyWith(
      visibleNodes: newVisibleNodes,
      visibleEdges: _computeVisibleEdges(newVisibleNodes),
      nodeAnimationProgress: animationProgress,
    );

    // Start animation timer
    final startTime = DateTime.now().millisecondsSinceEpoch;
    _animationTimer =
        Timer.periodic(Duration(milliseconds: _animationStep.toInt()), (timer) {
      if (!mounted) {
        timer.cancel();
        _animationTimer = null;
        return;
      }

      final elapsed = DateTime.now().millisecondsSinceEpoch - startTime;
      final progress = (elapsed / _animationDuration).clamp(0.0, 1.0);

      // EaseOutBack curve
      final easedProgress = _easeOutBack(progress);

      // Update all node animations
      final updatedProgress = state.nodeAnimationProgress
          .map((id, _) => MapEntry(id, easedProgress));

      if (progress >= 1.0) {
        timer.cancel();
        _animationTimer = null;
        // Final state: all at 1.0
        state = state.copyWith(
          nodeAnimationProgress: const {},
        );
      } else {
        state = state.copyWith(
          nodeAnimationProgress: updatedProgress,
        );
      }
    });
  }

  /// EaseOutBack curve for bloom effect
  double _easeOutBack(double x) {
    const c1 = 1.70158;
    const c3 = c1 + 1.0;
    return 1 + c3 * pow(x - 1, 3) + c1 * pow(x - 1, 2);
  }

  AggregationLevel _levelForScale(double scale) {
    if (scale < 0.2) {
      return AggregationLevel.universe;
    }
    if (scale < 0.4) {
      return AggregationLevel.galaxy;
    }
    if (scale < 0.6) {
      return AggregationLevel.cluster;
    }
    if (scale < 0.8) {
      return AggregationLevel.nebula;
    }
    return AggregationLevel.full;
  }

  Set<String> _collectExpandedEdges(
      String nodeId, List<GalaxyEdgeModel> edges,) {
    final expanded = <String>{nodeId};
    for (final edge in edges) {
      if (edge.sourceId == nodeId) expanded.add(edge.targetId);
      if (edge.targetId == nodeId) expanded.add(edge.sourceId);
    }
    return expanded;
  }

  /// Calculate visible nodes based on LOD and Viewport
  List<GalaxyNodeModel> _computeVisibleNodes() {
    if (state.nodes.isEmpty) return [];

    final nodes = state.nodes;
    final posMap = state.nodePositions;
    final level = state.aggregationLevel;
    final viewport = state.viewport;

    // 1. LOD Filtering
    var filteredNodes = <GalaxyNodeModel>[];

    switch (level) {
      case AggregationLevel.universe:
        // Universe level: No individual nodes, handled by clusters/sectors
        return [];

      case AggregationLevel.galaxy:
        // Galaxy level: Only root nodes (importance=5 or no parent)
        filteredNodes = nodes
            .where((n) => n.importance >= 5 || n.parentId == null)
            .toList();

      case AggregationLevel.cluster:
        // Cluster level: Importance >= 3
        filteredNodes = nodes.where((n) => n.importance >= 3).toList();

      case AggregationLevel.nebula:
        // Nebula level: Importance >= 2
        filteredNodes = nodes.where((n) => n.importance >= 2).toList();

      case AggregationLevel.full:
        // Full level: All nodes
        filteredNodes = nodes;
    }

    // Always include selected node and its neighbors if any
    if (state.selectedNodeId != null) {
      final selectedId = state.selectedNodeId;
      final extras = nodes.where((n) =>
          n.id == selectedId || state.expandedEdgeNodeIds.contains(n.id),);
      // Merge effectively
      final existingIds = filteredNodes.map((n) => n.id).toSet();
      for (final extra in extras) {
        if (!existingIds.contains(extra.id)) {
          filteredNodes.add(extra);
        }
      }
    }

    // 2. Viewport Culling
    if (viewport == null) return filteredNodes;

    // Expand viewport slightly for smooth entry
    final cullingRect = viewport.inflate(100);

    return filteredNodes.where((node) {
      final pos = posMap[node.id];
      if (pos == null) return false;
      return cullingRect.contains(pos);
    }).toList();
  }

  /// Calculate visible edges based on visible nodes and LOD
  List<GalaxyEdgeModel> _computeVisibleEdges(
      List<GalaxyNodeModel> visibleNodes,) {
    if (visibleNodes.isEmpty) return [];

    final visibleNodeIds = visibleNodes.map((n) => n.id).toSet();
    final edges = state.edges;
    final level = state.aggregationLevel;
    final scale = state.currentScale;

    return edges.where((edge) {
      // 1. Both ends must be visible
      if (!visibleNodeIds.contains(edge.sourceId) ||
          !visibleNodeIds.contains(edge.targetId)) {
        return false;
      }

      // 2. Connection importance filtering

      // Always show expanded edges (connected to selected node)
      if (state.expandedEdgeNodeIds.contains(edge.sourceId) &&
          state.expandedEdgeNodeIds.contains(edge.targetId)) {
        return true;
      }

      // LOD based rules
      if (level == AggregationLevel.universe) return false;

      if (level == AggregationLevel.galaxy) {
        // Only root-root connections
        return true;
      }

      // For Cluster/Nebula/Full:

      // Structural edges (parent-child) are prioritized
      if (edge.relationType == EdgeRelationType.parentChild) {
        // Show if both nodes are important enough
        return true;
      }

      // Other relations (similar, related, etc.)
      // Only show if scale is high enough or explicitly expanded
      if (scale < 0.8) {
        return false; // Hide clutter at lower zooms
      }

      return true;
    }).toList();
  }

  /// Calculate clusters based on aggregation level
  Map<String, ClusterInfo> _calculateClusters(
    AggregationLevel level, {
    List<GalaxyNodeModel>? nodes,
    Map<String, Offset>? positions,
  }) {
    final sourceNodes = nodes ?? state.nodes;
    final posMap = positions ?? state.nodePositions;
    // Return empty for levels where we render individual nodes extensively
    if (level == AggregationLevel.full || level == AggregationLevel.nebula) {
      return {};
    }

    final clusters = <String, ClusterInfo>{};

    if (level == AggregationLevel.cluster) {
      // Group by parent node (Cluster level)
      // Logic: Aggregate nodes that are NOT shown individually
      // Actually simpler: Just calculate clusters for ALL parents,
      // and Painter decides to draw them if the parent itself is not rendered as a node?
      // Or just standard clustering for visual aid.
      // Let's stick to previous logic but mapped to new level.

      final parentGroups = <String, List<GalaxyNodeModel>>{};

      for (final node in sourceNodes) {
        final parentId = node.parentId ?? node.id;
        parentGroups.putIfAbsent(parentId, () => []);
        parentGroups[parentId]!.add(node);
      }

      for (final entry in parentGroups.entries) {
        final parentId = entry.key;
        final groupNodes = entry.value;
        final parentNode = sourceNodes.firstWhere(
          (n) => n.id == parentId,
          orElse: () => groupNodes.first,
        );

        var center = Offset.zero;
        double totalMastery = 0;
        final childIds = <String>[];

        for (final node in groupNodes) {
          final pos = posMap[node.id];
          if (pos != null) center += pos;
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
    } else if (level == AggregationLevel.universe ||
        level == AggregationLevel.galaxy) {
      // Group by sector
      final sectorGroups = <SectorEnum, List<GalaxyNodeModel>>{};

      for (final node in sourceNodes) {
        sectorGroups.putIfAbsent(node.sector, () => []);
        sectorGroups[node.sector]!.add(node);
      }

      for (final entry in sectorGroups.entries) {
        final sector = entry.key;
        final sectorNodes = entry.value;
        final style = SectorConfig.getStyle(sector);

        var center = Offset.zero;
        double totalMastery = 0;
        final childIds = <String>[];

        for (final node in sectorNodes) {
          final pos = posMap[node.id];
          if (pos != null) center += pos;
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
