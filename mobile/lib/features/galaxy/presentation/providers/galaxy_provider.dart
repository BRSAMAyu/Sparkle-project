import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_optimization_config.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_layout_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_performance_monitor.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';
import 'package:sparkle/shared/models/compact_knowledge_node.dart';

/// Aggregation level based on zoom scale (5 levels)
enum AggregationLevel {
  universe, // < 0.2: Sector centroids only
  galaxy, // 0.2-0.4: Root nodes only
  cluster, // 0.4-0.6: Importance >= 3
  nebula, // 0.6-0.8: Importance >= 2
  full, // >= 0.8: All nodes
}

/// Shared LOD scale thresholds for Galaxy rendering (must match painter).
class GalaxyLodThresholds {
  const GalaxyLodThresholds._();

  static const double universeMax = 0.2;
  static const double galaxyMax = 0.4;
  static const double clusterMax = 0.6;
  static const double nebulaMax = 0.8;
}

/// Convert from name string for AggregationLevel
AggregationLevel aggregationLevelFromName(String name) {
  for (final level in AggregationLevel.values) {
    if (level.name == name) return level;
  }
  return AggregationLevel.full;
}

class GalaxyState {
  GalaxyState({
    this.nodes = const [],
    this.edges = const [],
    this.nodePositions = const {},
    this.visibleNodes = const [],
    this.visibleEdges = const [],
    this.visibleCompactNodes = const [], // 🔧 性能优化: 预计算的 CompactNode 列表
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
    this.draggingNodeId,
    this.focusNodeId,
    this.focusBounds,
    this.highlightedNodeIds = const {},
    this.highlightedNodeIdHashes = const {},
    this.highlightRevision = 0,
    this.expandedEdgeNodeIds = const {},
    this.nodeAnimationProgress = const {},
    this.optimizationConfig = GalaxyOptimizationConfig.standard,
    this.canvasSize = GalaxyLayoutEngine.canvasSize,
    this.canvasCenter = GalaxyLayoutEngine.canvasCenter,
  });

  static const Object _noChange = Object();
  final List<GalaxyNodeModel> nodes;
  final List<GalaxyEdgeModel> edges; // All edges
  final Map<String, Offset> nodePositions;

  // Pre-computed visible subset for rendering
  final List<GalaxyNodeModel> visibleNodes;
  final List<GalaxyEdgeModel> visibleEdges;
  // 🔧 性能优化: 预计算的 CompactNode 列表 (避免每帧映射)
  final List<CompactKnowledgeNode> visibleCompactNodes;

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
  final String? draggingNodeId;
  final String? focusNodeId;
  final Rect? focusBounds;
  final Set<String> highlightedNodeIds;
  final Set<int> highlightedNodeIdHashes;
  final int highlightRevision;
  final Set<String>
      expandedEdgeNodeIds; // Nodes whose connections should be fully visible
  final Map<String, double>
      nodeAnimationProgress; // 0.0 to 1.0 for bloom/shrink animation

  // Performance Config
  final GalaxyOptimizationConfig optimizationConfig;
  final double canvasSize;
  final double canvasCenter;

  GalaxyState copyWith({
    List<GalaxyNodeModel>? nodes,
    List<GalaxyEdgeModel>? edges,
    Map<String, Offset>? nodePositions,
    List<GalaxyNodeModel>? visibleNodes,
    List<GalaxyEdgeModel>? visibleEdges,
    List<CompactKnowledgeNode>? visibleCompactNodes, // 🔧 新增参数
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
    Object? draggingNodeId = _noChange,
    Object? focusNodeId = _noChange,
    Object? focusBounds = _noChange,
    Set<String>? highlightedNodeIds,
    Set<int>? highlightedNodeIdHashes,
    int? highlightRevision,
    Set<String>? expandedEdgeNodeIds,
    Map<String, double>? nodeAnimationProgress,
    GalaxyOptimizationConfig? optimizationConfig,
    double? canvasSize,
    double? canvasCenter,
  }) =>
      GalaxyState(
        nodes: nodes ?? this.nodes,
        edges: edges ?? this.edges,
        nodePositions: nodePositions ?? this.nodePositions,
        visibleNodes: visibleNodes ?? this.visibleNodes,
        visibleEdges: visibleEdges ?? this.visibleEdges,
        visibleCompactNodes:
            visibleCompactNodes ?? this.visibleCompactNodes, // 🔧 使用新字段
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
        draggingNodeId: identical(draggingNodeId, _noChange)
            ? this.draggingNodeId
            : draggingNodeId as String?,
        focusNodeId: identical(focusNodeId, _noChange)
            ? this.focusNodeId
            : focusNodeId as String?,
        focusBounds: identical(focusBounds, _noChange)
            ? this.focusBounds
            : focusBounds as Rect?,
        highlightedNodeIds: highlightedNodeIds ?? this.highlightedNodeIds,
        highlightedNodeIdHashes:
            highlightedNodeIdHashes ?? this.highlightedNodeIdHashes,
        highlightRevision: highlightRevision ?? this.highlightRevision,
        expandedEdgeNodeIds: expandedEdgeNodeIds ?? this.expandedEdgeNodeIds,
        nodeAnimationProgress:
            nodeAnimationProgress ?? this.nodeAnimationProgress,
        optimizationConfig: optimizationConfig ?? this.optimizationConfig,
        canvasSize: canvasSize ?? this.canvasSize,
        canvasCenter: canvasCenter ?? this.canvasCenter,
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

/// Galaxy view state (persisted portion)
///
/// Only the view-related state that should be persisted across app restarts.
class GalaxyViewState {
  const GalaxyViewState({
    this.currentScale = 1.0,
    this.selectedNodeId,
    this.aggregationLevel = AggregationLevel.full,
  });

  final double currentScale;
  final String? selectedNodeId;
  final AggregationLevel aggregationLevel;

  /// Serialize to JSON
  Map<String, dynamic> toJson() => {
        'currentScale': currentScale,
        'selectedNodeId': selectedNodeId,
        'aggregationLevel': aggregationLevel.name,
      };

  /// Deserialize from JSON
  static GalaxyViewState? fromJson(Map<String, dynamic> json) {
    try {
      return GalaxyViewState(
        currentScale: (json['currentScale'] as num?)?.toDouble() ?? 1.0,
        selectedNodeId: json['selectedNodeId'] as String?,
        aggregationLevel: aggregationLevelFromName(
          json['aggregationLevel'] as String? ?? 'full',
        ),
      );
    } catch (e) {
      return null;
    }
  }

  GalaxyViewState copyWith({
    double? currentScale,
    String? selectedNodeId,
    AggregationLevel? aggregationLevel,
  }) =>
      GalaxyViewState(
        currentScale: currentScale ?? this.currentScale,
        selectedNodeId: selectedNodeId ?? this.selectedNodeId,
        aggregationLevel: aggregationLevel ?? this.aggregationLevel,
      );
}

/// Galaxy view state provider with persistence
///
/// Persists the user's view state (scale, selected node, aggregation level).
final galaxyViewStateProvider =
    StateNotifierProvider<GalaxyViewStateNotifier, GalaxyViewState>(
  GalaxyViewStateNotifier.new,
);

/// Notifier for the galaxy view state
class GalaxyViewStateNotifier extends PersistentStateNotifier<GalaxyViewState> {
  GalaxyViewStateNotifier(super.ref)
      : super(
          namespace: 'galaxy',
          key: 'view_state',
          defaultValue: const GalaxyViewState(),
          toJson: (s) => s.toJson(),
          fromJson: GalaxyViewState.fromJson,
        );

  void updateScale(double scale) {
    state = state.copyWith(currentScale: scale);
  }

  void updateSelectedNode(String? nodeId) {
    state = state.copyWith(selectedNodeId: nodeId);
  }

  void updateAggregationLevel(AggregationLevel level) {
    state = state.copyWith(aggregationLevel: level);
  }

  void updateAll({
    double? scale,
    String? selectedNodeId,
    AggregationLevel? aggregationLevel,
  }) {
    state = GalaxyViewState(
      currentScale: scale ?? state.currentScale,
      selectedNodeId: selectedNodeId ?? state.selectedNodeId,
      aggregationLevel: aggregationLevel ?? state.aggregationLevel,
    );
  }
}

final galaxyProvider =
    StateNotifierProvider<GalaxyNotifier, GalaxyState>((ref) {
  final repository = ref.watch(enhancedGalaxyRepositoryProvider);
  return GalaxyNotifier(repository, ref);
});

/// Broadcast when a node crosses a mastery milestone threshold.
class MasteryMilestoneEvent {
  const MasteryMilestoneEvent({
    required this.nodeId,
    required this.nodeName,
    required this.newMastery,
    required this.milestone,
  });
  final String nodeId;
  final String nodeName;
  final int newMastery;
  final int milestone; // 30, 60, 85, or 95
}

class GalaxyNotifier extends StateNotifier<GalaxyState> {
  GalaxyNotifier(this._repository, this._ref) : super(GalaxyState()) {
    // Load persisted view state
    _loadPersistedState();
    _initEventsListener();
    _initPerformanceMonitor();
  }
  final EnhancedGalaxyRepository _repository;
  final Ref _ref;

  // Mastery milestone broadcast stream
  final _milestoneController =
      StreamController<MasteryMilestoneEvent>.broadcast();
  Stream<MasteryMilestoneEvent> get masteryMilestones =>
      _milestoneController.stream;

  // ignore: cancel_subscriptions
  StreamSubscription<SSEEvent>? _eventsSubscription;
  Timer? _eventsReconnectTimer;
  int _layoutRequestId = 0;
  String? _lastEventId;
  final Map<String, Offset> _dirtyNodePositions = <String, Offset>{};

  // Animation timer for bloom/shrink effects
  Timer? _animationTimer;
  // ignore: unused_field
  static const double _animationDuration = 300; // ms
  static const int _animationFps = 60;
  // ignore: unused_field
  static const double _animationStep = 1000 / _animationFps; // ~16.67ms

  // Performance Monitor
  VoidCallback? _tierListener;

  /// Load persisted view state
  void _loadPersistedState() {
    final viewState = _ref.read(galaxyViewStateProvider);
    if (viewState.currentScale != 1.0) {
      state = state.copyWith(
        currentScale: viewState.currentScale,
        aggregationLevel: _levelForScale(viewState.currentScale),
      );
    }
    if (viewState.selectedNodeId != null) {
      state = state.copyWith(selectedNodeId: viewState.selectedNodeId);
    }
    if (viewState.aggregationLevel != AggregationLevel.full) {
      state = state.copyWith(aggregationLevel: viewState.aggregationLevel);
    }
  }

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
    final eventsSubscription = _eventsSubscription;
    if (eventsSubscription != null) {
      unawaited(eventsSubscription.cancel());
    }
    _eventsReconnectTimer?.cancel();
    _animationTimer?.cancel();
    _viewportThrottleTimer?.cancel();
    final tierListener = _tierListener;
    if (tierListener != null) {
      PerformanceService.instance.currentTier.removeListener(tierListener);
    }
    unawaited(_milestoneController.close());
    // Do not stop monitoring here as it might be used by other parts or singleton lifecycle
    // But for this screen it's probably fine. Let's keep it running for now or stop it?
    // If GalaxyScreen is the only consumer, we could stop it.
    // GalaxyPerformanceMonitor.instance.stopMonitoring();
    super.dispose();
  }

  PerformanceTier _mapPerformanceTier(PerformanceTier tier) => tier;

  void _initEventsListener() {
    final currentSubscription = _eventsSubscription;
    if (currentSubscription != null) {
      unawaited(currentSubscription.cancel());
    }
    _eventsSubscription =
        _repository.getGalaxyEventsStream(lastEventId: _lastEventId).listen(
      (event) {
        if (event.id != null && event.id!.isNotEmpty) {
          _lastEventId = event.id;
        }

        if (event.event == 'nodes_expanded' ||
            event.event == 'galaxy.nodes_expanded') {
          _handleNodesExpanded(event.jsonData);
        } else if (event.event == 'galaxy.node.updated' ||
            event.event == 'galaxy.mastery_updated') {
          _handleNodeUpdated(event.jsonData);
        } else if (event.event == 'evidence_pack') {
          _handleEvidencePack(event.jsonData);
        } else if (event.event == 'galaxy.error.created') {
          _handleErrorCreated(event.jsonData);
        }
      },
      onError: (Object error, StackTrace stack) {
        debugPrint('Galaxy events stream error: $error');
        _scheduleEventsReconnect();
      },
      onDone: _scheduleEventsReconnect,
    );
  }

  void _scheduleEventsReconnect() {
    if (!mounted) return;
    final currentSubscription = _eventsSubscription;
    if (currentSubscription != null) {
      unawaited(currentSubscription.cancel());
    }
    _eventsReconnectTimer?.cancel();
    _eventsReconnectTimer = Timer(const Duration(seconds: 5), () {
      if (mounted) _initEventsListener();
    });
  }

  void _handleNodesExpanded(Map<String, dynamic>? data) {
    if (data == null || data['nodes'] == null) return;
    unawaited(loadGalaxy(forceRefresh: true, showLoading: false));
  }

  static const _masteryMilestones = [30, 60, 85, 95];

  void _handleNodeUpdated(Map<String, dynamic>? data) {
    if (data == null ||
        data['node_id'] == null ||
        data['new_mastery'] == null) {
      return;
    }

    final nodeId = data['node_id'] as String;
    final newMastery = (data['new_mastery'] as num).toInt();

    // Detect milestone crossing before updating state
    final oldNode = state.nodes.where((n) => n.id == nodeId).firstOrNull;
    if (oldNode != null && !_milestoneController.isClosed) {
      final oldMastery = oldNode.masteryScore;
      for (final milestone in _masteryMilestones) {
        if (oldMastery < milestone && newMastery >= milestone) {
          _milestoneController.add(MasteryMilestoneEvent(
            nodeId: nodeId,
            nodeName: oldNode.name,
            newMastery: newMastery,
            milestone: milestone,
          ));
          break; // Only fire the highest milestone crossed
        }
      }
    }

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

  void _handleEvidencePack(Map<String, dynamic>? data) {
    if (data == null) return;
    final nodes = data['nodes'] as List<dynamic>?;
    if (nodes == null || nodes.isEmpty) return;

    final first = nodes.first as Map<String, dynamic>?;
    if (first == null) return;
    final nodeId = first['node_id'] as String?;
    if (nodeId == null || nodeId.isEmpty) return;
    final ids = nodes
        .map((item) => (item as Map<String, dynamic>?)?['node_id'] as String?)
        .whereType<String>()
        .where((id) => id.isNotEmpty)
        .toSet();
    setEvidenceHighlight(ids, focusId: nodeId);
  }

  void _handleErrorCreated(Map<String, dynamic>? data) {
    if (data == null) return;
    final linkedNodeIds = (data['linked_node_ids'] as List<dynamic>?)
        ?.map((item) => item?.toString())
        .whereType<String>()
        .where((id) => id.isNotEmpty)
        .toSet();

    if (linkedNodeIds != null && linkedNodeIds.isNotEmpty) {
      setEvidenceHighlight(linkedNodeIds);
    }

    unawaited(loadGalaxy(forceRefresh: true, showLoading: false));
  }

  void setFocusNode(String nodeId) {
    final expanded = _collectExpandedEdges(nodeId, state.edges);
    state = state.copyWith(
      selectedNodeId: nodeId,
      focusNodeId: nodeId,
      expandedEdgeNodeIds: expanded,
    );
    _recalculateVisibility();
  }

  void setEvidenceHighlight(Set<String> nodeIds, {String? focusId}) {
    final focus = focusId ?? (nodeIds.isNotEmpty ? nodeIds.first : null);
    final expanded =
        focus != null ? _collectExpandedEdges(focus, state.edges) : null;
    final hashes = nodeIds.map((id) => id.hashCode).toSet();
    final bounds = _computeHighlightBounds(nodeIds);
    state = state.copyWith(
      highlightedNodeIds: nodeIds,
      highlightedNodeIdHashes: hashes,
      highlightRevision: state.highlightRevision + 1,
      selectedNodeId: focus ?? state.selectedNodeId,
      focusNodeId: focus,
      focusBounds: bounds,
      expandedEdgeNodeIds: expanded ?? state.expandedEdgeNodeIds,
    );
    _recalculateVisibility();
  }

  void clearFocusNode() {
    if (state.focusNodeId == null) return;
    state = state.copyWith(focusNodeId: null);
  }

  void clearFocusBounds() {
    if (state.focusBounds == null) return;
    state = state.copyWith(focusBounds: null);
  }

  void clearEvidenceHighlight() {
    if (state.highlightedNodeIds.isEmpty) return;
    state = state.copyWith(
      highlightedNodeIds: const {},
      highlightedNodeIdHashes: const {},
      highlightRevision: state.highlightRevision + 1,
    );
  }

  Future<void> loadGalaxy({
    bool forceRefresh = false,
    bool showLoading = true,
  }) async {
    final hadGraph = state.nodes.isNotEmpty || state.edges.isNotEmpty;
    final shouldShowBlockingLoading = showLoading || !hadGraph;
    state = state.copyWith(
      isLoading: shouldShowBlockingLoading,
      lastError: null,
    );
    final requestId = ++_layoutRequestId;
    try {
      final result = await _repository.getGraph(forceRefresh: forceRefresh);
      if (!mounted || requestId != _layoutRequestId) return;

      if (result.isFailure || result.data == null) {
        final error = result.error ?? '未知错误';
        final galaxyError = error is GalaxyError
            ? error
            : GalaxyError.unknown(error.toString());
        if (hadGraph && !shouldShowBlockingLoading) {
          state = state.copyWith(
            isLoading: false,
            isOptimizing: false,
            lastError: null,
          );
          debugPrint('Background galaxy refresh failed: $galaxyError');
          return;
        }
        state = state.copyWith(
          isLoading: false,
          isOptimizing: false,
          lastError: galaxyError,
          isUsingCache: false,
        );
        return;
      }

      final response = result.data!;
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

      final stablePositions = _buildStablePositions(
        response.nodes,
        previousPositions: state.nodePositions,
      );

      state = state.copyWith(
        nodes: response.nodes,
        edges: response.edges,
        nodePositions: stablePositions,
        userFlameIntensity: response.userFlameIntensity,
        aggregationLevel: aggregationLevel,
        clusters: _calculateClusters(
          aggregationLevel,
          nodes: response.nodes,
          positions: stablePositions,
        ),
        selectedNodeId: hasSelected ? selectedNodeId : null,
        expandedEdgeNodeIds: expandedEdgeNodeIds,
        predictedNodeId: hasPredicted ? predictedNodeId : null,
        isLoading: false,
        isOptimizing: false,
        isUsingCache: result.isFromCache,
        lastError: null,
      );
      _recalculateVisibility();
    } catch (e) {
      if (hadGraph && !shouldShowBlockingLoading) {
        state = state.copyWith(
          isLoading: false,
          isOptimizing: false,
          lastError: null,
        );
        debugPrint('Background galaxy refresh threw: $e');
        return;
      }
      state = state.copyWith(
        isLoading: false,
        isOptimizing: false,
        lastError: GalaxyError.unknown(e.toString()),
        isUsingCache: false,
      );
      debugPrint('Error loading galaxy: $e');
    }
  }

  Map<String, Offset> _buildStablePositions(
    List<GalaxyNodeModel> nodes, {
    required Map<String, Offset> previousPositions,
  }) {
    final positions = <String, Offset>{};
    for (final node in nodes) {
      if (node.hasStablePosition) {
        positions[node.id] = Offset(node.positionX!, node.positionY!);
        continue;
      }
      final previous = previousPositions[node.id];
      if (previous != null) {
        positions[node.id] = previous;
        continue;
      }
      positions[node.id] = _fallbackPositionFor(node);
    }
    return positions;
  }

  Offset _fallbackPositionFor(GalaxyNodeModel node) {
    final sectorAngle = (2 * pi / SectorEnum.values.length) * node.sector.index;
    final seed = node.id.hashCode.abs();
    final radius = 260.0 + (node.importance * 110.0) + (seed % 140).toDouble();
    final jitterAngle = ((seed % 37) - 18) * (pi / 180);
    final angle = sectorAngle + jitterAngle;
    return Offset(cos(angle) * radius, sin(angle) * radius);
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
      if (state.viewport != null && viewport != null) {
        final old = state.viewport!;
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
      draggingNodeId: null,
      expandedEdgeNodeIds: expanded,
    );
    // Persist view state
    _ref.read(galaxyViewStateProvider.notifier).updateSelectedNode(nodeId);
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
      visibleCompactNodes: state.visibleCompactNodes,
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
      highlightRevision: state.highlightRevision + 1,
      expandedEdgeNodeIds: {}, // CLEAR
      nodeAnimationProgress: state.nodeAnimationProgress,
      optimizationConfig: state.optimizationConfig,
      focusNodeId: state.focusNodeId,
      focusBounds: state.focusBounds,
      highlightedNodeIds: state.highlightedNodeIds,
      highlightedNodeIdHashes: state.highlightedNodeIdHashes,
      canvasSize: state.canvasSize,
      canvasCenter: state.canvasCenter,
    );
    // Persist view state (clear selection)
    _ref.read(galaxyViewStateProvider.notifier).updateSelectedNode(null);
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
    await loadGalaxy(forceRefresh: true, showLoading: false);
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

  void beginNodeDrag(String nodeId) {
    if (state.draggingNodeId == nodeId) {
      return;
    }
    if (!state.nodePositions.containsKey(nodeId)) {
      return;
    }
    selectNode(nodeId);
    state = state.copyWith(draggingNodeId: nodeId);
  }

  void updateDraggedNodePosition(String nodeId, Offset newPosition) {
    if (state.draggingNodeId != nodeId) {
      return;
    }
    final currentPosition = state.nodePositions[nodeId];
    if (currentPosition == null) {
      return;
    }

    final delta = newPosition - currentPosition;
    if (delta.distanceSquared < 1) {
      return;
    }

    final updatedPositions = Map<String, Offset>.from(state.nodePositions)
      ..[nodeId] = newPosition;
    _dirtyNodePositions[nodeId] = newPosition;

    final neighborIds = <String>{};
    for (final edge in state.edges) {
      if (edge.sourceId == nodeId) {
        neighborIds.add(edge.targetId);
      } else if (edge.targetId == nodeId) {
        neighborIds.add(edge.sourceId);
      }
    }

    for (final neighborId in neighborIds) {
      final neighborPosition = updatedPositions[neighborId];
      if (neighborPosition == null) {
        continue;
      }
      final attraction = delta * 0.14;
      updatedPositions[neighborId] = neighborPosition + attraction;
      _dirtyNodePositions[neighborId] = updatedPositions[neighborId]!;
    }

    var repulsionBudget = 0;
    for (final node in state.nodes) {
      if (node.id == nodeId || neighborIds.contains(node.id)) {
        continue;
      }
      final position = updatedPositions[node.id];
      if (position == null) {
        continue;
      }
      final toDragged = position - newPosition;
      final distance = toDragged.distance;
      if (distance <= 0 || distance > 220) {
        continue;
      }
      final push = (220 - distance) / 220 * 18;
      updatedPositions[node.id] = position + (toDragged / distance) * push;
      _dirtyNodePositions[node.id] = updatedPositions[node.id]!;
      repulsionBudget++;
      if (repulsionBudget >= 10) {
        break;
      }
    }

    state = state.copyWith(
      nodePositions: updatedPositions,
      visibleCompactNodes: _computeCompactNodesForPositions(
        state.visibleNodes,
        updatedPositions,
      ),
    );
  }

  Future<void> endNodeDrag() async {
    final nodeId = state.draggingNodeId;
    state = state.copyWith(draggingNodeId: null);
    if (nodeId == null || _dirtyNodePositions.isEmpty) {
      return;
    }

    state = state.copyWith(
      clusters: _calculateClusters(
        state.aggregationLevel,
        nodes: state.nodes,
        positions: state.nodePositions,
      ),
    );
    final payload = Map<String, Offset>.from(_dirtyNodePositions);
    _dirtyNodePositions.clear();
    final result = await _repository.updateNodePositions(payload);
    if (result.isFailure && mounted) {
      debugPrint('Failed to persist galaxy node positions: ${result.error}');
    }
    _recalculateVisibility();
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
      // Persist view state
      _ref.read(galaxyViewStateProvider.notifier).updateAll(
            scale: scale,
            aggregationLevel: newLevel,
          );
      // Trigger animation when LOD changes
      _recalculateVisibility(withAnimation: true);
    } else {
      state = state.copyWith(currentScale: scale);
      // Persist view state
      _ref.read(galaxyViewStateProvider.notifier).updateScale(scale);
      // Visibility recalculation is driven by throttled viewport updates.
      // Recomputing here on every scale tick causes avoidable jank during pinch.
    }
  }

  void _recalculateVisibility({bool withAnimation = false}) {
    final visibleNodes = _computeVisibleNodes();
    final visibleEdges = _computeVisibleEdges(visibleNodes);
    final visibleCompactNodes = _computeCompactNodes(visibleNodes);
    state = state.copyWith(
      visibleNodes: visibleNodes,
      visibleEdges: visibleEdges,
      visibleCompactNodes: visibleCompactNodes,
      nodeAnimationProgress: const {},
    );
  }

  /// 🔧 性能优化: 预计算 CompactNode 列表
  /// 避免在每次渲染时都映射节点列表
  List<CompactKnowledgeNode> _computeCompactNodes(
    List<GalaxyNodeModel> visibleNodes,
  ) =>
      _computeCompactNodesForPositions(visibleNodes, state.nodePositions);

  List<CompactKnowledgeNode> _computeCompactNodesForPositions(
    List<GalaxyNodeModel> visibleNodes,
    Map<String, Offset> positions,
  ) {
    final canvasCenter = state.canvasCenter;

    return visibleNodes.map((node) {
      final pos = positions[node.id] ?? Offset.zero;
      return node.toCompact(
        pos.dx + canvasCenter,
        pos.dy + canvasCenter,
      );
    }).toList();
  }

  AggregationLevel _levelForScale(double scale) {
    if (scale < GalaxyLodThresholds.universeMax) {
      return AggregationLevel.universe;
    }
    if (scale < GalaxyLodThresholds.galaxyMax) {
      return AggregationLevel.galaxy;
    }
    if (scale < GalaxyLodThresholds.clusterMax) {
      return AggregationLevel.cluster;
    }
    if (scale < GalaxyLodThresholds.nebulaMax) {
      return AggregationLevel.nebula;
    }
    return AggregationLevel.full;
  }

  Set<String> _collectExpandedEdges(
    String nodeId,
    List<GalaxyEdgeModel> edges,
  ) {
    final expanded = <String>{nodeId};
    for (final edge in edges) {
      if (edge.sourceId == nodeId) expanded.add(edge.targetId);
      if (edge.targetId == nodeId) expanded.add(edge.sourceId);
    }
    return expanded;
  }

  Rect? _computeHighlightBounds(Set<String> nodeIds) {
    if (nodeIds.isEmpty) return null;
    double? minX;
    double? minY;
    double? maxX;
    double? maxY;
    for (final nodeId in nodeIds) {
      final pos = state.nodePositions[nodeId];
      if (pos == null) continue;
      minX = minX == null
          ? pos.dx
          : minX < pos.dx
              ? minX
              : pos.dx;
      minY = minY == null
          ? pos.dy
          : minY < pos.dy
              ? minY
              : pos.dy;
      maxX = maxX == null
          ? pos.dx
          : maxX > pos.dx
              ? maxX
              : pos.dx;
      maxY = maxY == null
          ? pos.dy
          : maxY > pos.dy
              ? maxY
              : pos.dy;
    }
    if (minX == null || minY == null || maxX == null || maxY == null) {
      return null;
    }
    return Rect.fromLTRB(minX, minY, maxX, maxY);
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
        // Universe level: Only show highest importance nodes (sector roots)
        // Changed from empty to show important nodes for better UX
        filteredNodes = nodes
            .where((n) => n.importance >= 5 || n.parentId == null)
            .toList();

      case AggregationLevel.galaxy:
        // Galaxy level: Root nodes and important ones (importance >= 3)
        filteredNodes = nodes
            .where((n) => n.importance >= 3 || n.parentId == null)
            .toList();

      case AggregationLevel.cluster:
        // Cluster level: Show most nodes (importance >= 2)
        filteredNodes = nodes.where((n) => n.importance >= 2).toList();

      case AggregationLevel.nebula:
        // Nebula level: Show almost all nodes (importance >= 1)
        filteredNodes = nodes.where((n) => n.importance >= 1).toList();

      case AggregationLevel.full:
        // Full level: All nodes
        filteredNodes = nodes;
    }

    // Always include selected node and its neighbors if any
    if (state.selectedNodeId != null) {
      final selectedId = state.selectedNodeId;
      final extras = nodes.where(
        (n) => n.id == selectedId || state.expandedEdgeNodeIds.contains(n.id),
      );
      // Merge effectively
      final existingIds = filteredNodes.map((n) => n.id).toSet();
      for (final extra in extras) {
        if (!existingIds.contains(extra.id)) {
          filteredNodes.add(extra);
        }
      }
    }

    if (viewport == null) {
      return _prioritizeVisibleNodes(filteredNodes, posMap, Rect.zero);
    }

    final cullingRect = viewport.inflate(500);
    final culledNodes = filteredNodes.where((node) {
      final pos = posMap[node.id];
      if (pos == null) return false;
      return cullingRect.contains(pos);
    }).toList();

    return _prioritizeVisibleNodes(culledNodes, posMap, viewport);
  }

  List<GalaxyNodeModel> _prioritizeVisibleNodes(
    List<GalaxyNodeModel> nodes,
    Map<String, Offset> posMap,
    Rect viewport,
  ) {
    final scale = state.currentScale;
    final dynamicMaxNodes = switch (state.optimizationConfig.targetFps) {
      60 => scale >= 1.2
          ? 420
          : scale >= 0.8
              ? 320
              : scale >= 0.4
                  ? 220
                  : 140,
      _ => scale >= 1.2
          ? 260
          : scale >= 0.8
              ? 200
              : scale >= 0.4
                  ? 150
                  : 96,
    };
    final maxNodes =
        dynamicMaxNodes.clamp(80, state.optimizationConfig.maxNodes);
    if (nodes.length <= maxNodes) {
      return nodes;
    }

    final stickyIds = <String>{
      if (state.selectedNodeId != null) state.selectedNodeId!,
      ...state.expandedEdgeNodeIds,
    };
    final center = viewport == Rect.zero ? Offset.zero : viewport.center;
    final prioritized = List<GalaxyNodeModel>.from(nodes)
      ..sort((a, b) {
        final aPinned = stickyIds.contains(a.id);
        final bPinned = stickyIds.contains(b.id);
        if (aPinned != bPinned) {
          return aPinned ? -1 : 1;
        }

        final importanceOrder = b.importance.compareTo(a.importance);
        if (importanceOrder != 0) {
          return importanceOrder;
        }

        final aPos = posMap[a.id] ?? Offset.zero;
        final bPos = posMap[b.id] ?? Offset.zero;
        return (aPos - center)
            .distanceSquared
            .compareTo((bPos - center).distanceSquared);
      });
    return prioritized.take(maxNodes).toList();
  }

  /// Calculate visible edges based on visible nodes and LOD
  List<GalaxyEdgeModel> _computeVisibleEdges(
    List<GalaxyNodeModel> visibleNodes,
  ) {
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
