import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_scene_snapshot.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_layout_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_render_engine.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/energy_particle.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_error_dialog.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_search_dialog.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/node_preview_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_success_animation.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/zoom_controls.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';
import 'package:sparkle/shared/models/compact_knowledge_node.dart';

class GalaxyScreen extends ConsumerStatefulWidget {
  const GalaxyScreen({super.key});

  @override
  ConsumerState<GalaxyScreen> createState() => _GalaxyScreenState();
}

class _GalaxyScreenState extends ConsumerState<GalaxyScreen>
    with TickerProviderStateMixin {
  final TransformationController _transformationController =
      TransformationController();
  late final GalaxyRenderEngine _renderEngine;
  late final GalaxyNotifier _galaxyNotifier;
  late final AnimationController _selectionPulseController;
  final List<AnimationController> _transientControllers = [];
  ProviderSubscription<GalaxyState>? _focusSubscription;
  bool _isDisposing = false;
  bool _layoutAdjustmentScheduled = false;
  Timer? _loadingTimeoutTimer;

  // State
  bool _hasCentered = false;
  bool _loadingTimedOut = false;
  Size? _lastLayoutSize;
  bool _showDebugOverlay = false;
  final Set<int> _activePointers = <int>{};
  String? _draggingNodeId;
  String? _pendingLongPressNodeId;
  Offset? _gestureStartFocalPoint;
  double? _gestureStartScale;
  Matrix4? _gestureStartMatrix;

  // Active animations
  final List<_ActiveEnergyTransfer> _activeEnergyTransfers = [];
  final List<_ActiveSuccessAnimation> _activeSuccessAnimations = [];

  final double _canvasCenter =
      GalaxyLayoutEngine.canvasCenter; // Canvas center coordinate (2900)
  final double _canvasSize =
      GalaxyLayoutEngine.canvasSize; // Canvas size (5800)

  // Track last scale to avoid unnecessary updates
  double _lastScale = 1.0;

  // 🔧 性能优化: 缓存 Viewport 计算结果
  Rect? _cachedAbsoluteViewport;
  Rect? _cachedRelativeViewport;
  Rect? _lastReportedRelativeViewport;
  Matrix4? _lastViewportMatrix;
  Timer? _cameraStateSyncTimer;

  // 🔧 性能优化: 缓存 StarMapPainter
  StarMapPainter? _cachedPainter;
  int? _lastPainterSignature;
  GalaxySceneSnapshot? _cachedSceneSnapshot;

  // Gesture conflict resolution
  bool _hasDragged = false;
  Offset? _dragStartOffset;

  @override
  void initState() {
    super.initState();
    _galaxyNotifier = ref.read(galaxyProvider.notifier);
    _renderEngine = GalaxyRenderEngine();

    _selectionPulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..value = 0.35;

    // Listen to transformation changes for scale updates
    _transformationController.addListener(_onTransformChanged);

    // Start Performance Monitoring
    PerformanceService.instance.startMonitoring();

    // Delay provider mutations until after the first frame.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      unawaited(_galaxyNotifier.loadGalaxy());
    });
    // Hide loading indicator after 5 seconds (timeout mechanism)
    _loadingTimeoutTimer = Timer(const Duration(seconds: 5), () {
      if (mounted) setState(() => _loadingTimedOut = true);
    });
  }

  void _performInitialCentering(Size size) {
    // Start at 0.15 scale (Universe View) centered
    const initialScale = 0.15;

    // To center canvas point (_canvasCenter, _canvasCenter) at screen center (w/2, h/2) with scale S:
    // Tx = w/2 - _canvasCenter * S
    final tx = size.width / 2 - _canvasCenter * initialScale;
    final ty = size.height / 2 - _canvasCenter * initialScale;

    // Use standard Matrix4 methods to avoid deprecation warnings
    // T * S transformation
    _transformationController.value = Matrix4.identity()
      ..translateByDouble(tx, ty, 0, 1)
      ..scaleByDouble(initialScale, initialScale, 1, 1);
  }

  void _recenterForResize({
    required Size oldSize,
    required Size newSize,
  }) {
    if (oldSize.width <= 0 || oldSize.height <= 0) return;
    if (newSize.width <= 0 || newSize.height <= 0) return;

    // Keep the same canvas point under the previous screen center.
    final oldCenter = Offset(oldSize.width / 2, oldSize.height / 2);
    final canvasPoint = _screenToCanvas(oldCenter);
    final scale = _transformationController.value.getMaxScaleOnAxis();

    final tx = newSize.width / 2 - canvasPoint.dx * scale;
    final ty = newSize.height / 2 - canvasPoint.dy * scale;

    _transformationController.value = Matrix4.identity()
      ..translateByDouble(tx, ty, 0, 1)
      ..scaleByDouble(scale, scale, 1, 1);
  }

  void _scheduleLayoutAdjustment(VoidCallback callback) {
    if (_layoutAdjustmentScheduled || !mounted) return;
    _layoutAdjustmentScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _layoutAdjustmentScheduled = false;
      if (!mounted || _isDisposing) return;
      callback();
    });
  }

  @override
  void dispose() {
    _isDisposing = true;
    for (final controller in _transientControllers) {
      controller.dispose();
    }
    _transientControllers.clear();
    _galaxyNotifier.clearEvidenceHighlight();
    _galaxyNotifier.clearFocusBounds();
    _galaxyNotifier.clearFocusNode();
    _selectionPulseController.dispose();
    _transformationController.removeListener(_onTransformChanged);
    _transformationController.dispose();
    _focusSubscription?.close();
    _renderEngine.dispose();
    _loadingTimeoutTimer?.cancel();
    _cameraStateSyncTimer?.cancel();
    PerformanceService.instance.stopMonitoring();
    super.dispose();
  }

  /// Handle transformation changes to update scale in provider
  /// 🔧 优化: 缓存 viewport 计算，避免重复的矩阵求逆
  void _onTransformChanged() {
    final scale = _transformationController.value.getMaxScaleOnAxis();

    // Keep camera state local during active interaction. Provider persistence is synced lazily.
    if ((scale - _lastScale).abs() > 0.02) {
      _lastScale = scale;
      _scheduleCameraStateSync();
    }

    if (!mounted) return;
    final size = MediaQuery.of(context).size;
    if (size.width <= 0 || size.height <= 0) return;

    final currentMatrix = _transformationController.value;

    // 🔧 优化: 只在矩阵真正变化时重新计算 viewport
    // 比较矩阵是否变化（检查关键元素）
    final shouldRecalculate = _lastViewportMatrix == null ||
        !_matricesEqual(currentMatrix, _lastViewportMatrix!);

    if (shouldRecalculate) {
      _lastViewportMatrix = currentMatrix.clone();

      final inverseMatrix = currentMatrix.clone()..invert();
      final topLeft = MatrixUtils.transformPoint(inverseMatrix, Offset.zero);
      final bottomRight = MatrixUtils.transformPoint(
        inverseMatrix,
        Offset(size.width, size.height),
      );

      // Absolute Viewport (Canvas Coordinates 0..5000) - For Painter
      _cachedAbsoluteViewport = Rect.fromPoints(topLeft, bottomRight);

      // Relative Viewport (Center Relative -2500..2500) - For Provider Culling
      final nextRelativeViewport = _cachedAbsoluteViewport!.shift(
        Offset(-_canvasCenter, -_canvasCenter),
      );
      _cachedRelativeViewport = nextRelativeViewport;
      if (_viewportChangedSignificantly(nextRelativeViewport)) {
        _lastReportedRelativeViewport = nextRelativeViewport;
      }
    }
  }

  void _scheduleCameraStateSync() {
    _cameraStateSyncTimer?.cancel();
    _cameraStateSyncTimer = Timer(const Duration(milliseconds: 220), () {
      if (!mounted || _isDisposing) {
        return;
      }
      ref.read(galaxyProvider.notifier).updateScale(_lastScale);
    });
  }

  void _cancelTransientCameraAnimations() {
    for (final controller in List<AnimationController>.from(
      _transientControllers,
    )) {
      controller.stop();
      controller.dispose();
      _transientControllers.remove(controller);
    }
  }

  /// 🔧 检查矩阵是否实质性变化（比较关键元素）
  bool _matricesEqual(Matrix4 a, Matrix4 b) {
    const threshold = 0.001; // 1像素以内的变化忽略
    return (a[0] - b[0]).abs() < threshold && // scale x
        (a[5] - b[5]).abs() < threshold && // scale y
        (a[12] - b[12]).abs() < threshold && // translate x
        (a[13] - b[13]).abs() < threshold; // translate y
  }

  /// 🔧 检查 viewport 是否显著变化
  bool _viewportChangedSignificantly(Rect newViewport) {
    final old = _lastReportedRelativeViewport;
    if (old == null) return true;
    const threshold = 50.0; // 50 个单位的变化才更新

    return (newViewport.left - old.left).abs() > threshold ||
        (newViewport.top - old.top).abs() > threshold ||
        (newViewport.right - old.right).abs() > threshold ||
        (newViewport.bottom - old.bottom).abs() > threshold;
  }

  /// Convert a canvas position (in the star map space) to screen coordinates
  Offset _canvasToScreen(Offset canvasPosition) {
    final matrix = _transformationController.value;
    // Apply the transformation matrix to get screen position
    final transformed = MatrixUtils.transformPoint(matrix, canvasPosition);
    return transformed;
  }

  /// Get the screen center position (where the central flame is displayed)
  Offset _getScreenCenter() {
    final size = MediaQuery.of(context).size;
    return Offset(size.width / 2, size.height / 2);
  }

  /// Convert screen position to canvas coordinates
  Offset _screenToCanvas(Offset screenPosition) {
    final matrix = _transformationController.value.clone()..invert();
    return MatrixUtils.transformPoint(matrix, screenPosition);
  }

  /// 🔧 性能优化: 构建优化的星图层
  /// 只在数据真正变化时重建 painter，避免每帧重建
  Widget _buildOptimizedStarMapLayer(
    GalaxyState galaxyState,
    double canvasCenter,
    double canvasSize,
  ) {
    // 监听数据变化（nodes, edges, selection 等）
    // 但不监听高频动画（selectionPulse）
    return AnimatedBuilder(
      animation: Listenable.merge([
        _transformationController, // 变换变化
        PerformanceService.instance.currentTier, // 性能档位变化
        PerformanceService.instance.currentDpr, // DPR 变化
        // ❌ 不再监听 _selectionPulseController - 避免每帧重建
      ]),
      builder: (context, child) {
        // 检查是否需要重建 painter
        final needsRebuild = _shouldRebuildPainter(galaxyState);
        final sceneSnapshot = _cachedSceneSnapshot;

        if (needsRebuild || sceneSnapshot == null) {
          _cachedSceneSnapshot = _createSceneSnapshot(galaxyState);
        }
        final activeSnapshot = _cachedSceneSnapshot!;
        _cachedPainter = _createStarMapPainter(galaxyState, activeSnapshot);

        return Stack(
          children: [
            Positioned.fill(
              child: RepaintBoundary(
                child: CustomPaint(
                  painter: _cachedPainter,
                ),
              ),
            ),
            if (activeSnapshot.budget.showLabels &&
                activeSnapshot.viewport.scale >= 0.75)
              Positioned.fill(
                child: IgnorePointer(
                  child: _GalaxyLabelOverlay(
                    snapshot: activeSnapshot,
                    nodeNameLookup: {
                      for (final node in galaxyState.nodes)
                        node.id.hashCode: node.name,
                    },
                  ),
                ),
              ),
            if (galaxyState.selectedNodeId != null ||
                galaxyState.highlightedNodeIdHashes.isNotEmpty)
              Positioned.fill(
                child: IgnorePointer(
                  child: RepaintBoundary(
                    child: CustomPaint(
                      painter: SelectionOverlayPainter(
                        nodes: activeSnapshot.nodes,
                        viewMatrix: _transformationController.value.clone(),
                        selectedNodeIdHash:
                            galaxyState.selectedNodeId?.hashCode,
                        highlightedNodeIdHashes:
                            galaxyState.highlightedNodeIdHashes,
                        performanceTier:
                            PerformanceService.instance.currentTier.value,
                        selectionPulse: 0.35,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }

  /// 🔧 检查是否需要重建 painter
  bool _shouldRebuildPainter(GalaxyState state) {
    final signature = _createPainterSignature(state);
    if (_cachedPainter == null || _lastPainterSignature != signature) {
      _lastPainterSignature = signature;
      return true;
    }
    return false;
  }

  /// 🔧 创建 StarMapPainter
  StarMapPainter _createStarMapPainter(
    GalaxyState galaxyState,
    GalaxySceneSnapshot snapshot,
  ) {
    return StarMapPainter(
      nodes: snapshot.nodes,
      edges: snapshot.edges,
      viewMatrix: snapshot.viewport.matrix,
      maxEdges: snapshot.budget.maxEdges,
      maxLabels: snapshot.budget.maxLabels,
      showLabels: snapshot.budget.showLabels,
      showTags: snapshot.budget.showTags,
      showEdgeGlow: snapshot.budget.showEdgeGlow,
      scale: snapshot.viewport.scale,
      performanceTier: PerformanceService.instance.currentTier.value,
      currentDpr: PerformanceService.instance.currentDpr.value,
      aggregationLevel: galaxyState.aggregationLevel,
      clusters: _centerClusters(
        galaxyState.clusters,
        galaxyState.canvasCenter,
        galaxyState.canvasCenter,
      ),
      viewport: snapshot.viewport.absoluteViewport,
      center: Offset(galaxyState.canvasCenter, galaxyState.canvasCenter),
      selectedNodeIdHash: snapshot.selectedNodeIdHash,
      highlightedNodeIdHashes: snapshot.highlightedNodeIdHashes,
      highlightRevision: snapshot.highlightRevision,
      expandedEdgeNodeIdHashes: snapshot.expandedEdgeNodeIdHashes,
      nodeAnimationProgress: const {},
      selectionPulse: 0.0,
    );
  }

  /// 🔧 计算 viewport (fallback when cache not available)
  Rect _calculateViewport(Size screenSize) {
    final matrix = _transformationController.value;
    final inverseMatrix = matrix.clone()..invert();
    final topLeft = MatrixUtils.transformPoint(inverseMatrix, Offset.zero);
    final bottomRight = MatrixUtils.transformPoint(
      inverseMatrix,
      Offset(screenSize.width, screenSize.height),
    );
    return Rect.fromPoints(topLeft, bottomRight);
  }

  GalaxySceneSnapshot _createSceneSnapshot(GalaxyState galaxyState) {
    final absoluteViewport = _cachedAbsoluteViewport ??
        _calculateViewport(MediaQuery.of(context).size);
    final relativeViewport = _cachedRelativeViewport ??
        absoluteViewport.shift(Offset(-_canvasCenter, -_canvasCenter));
    final scale = _transformationController.value.getMaxScaleOnAxis();
    final viewportBucket = Object.hash(
      (absoluteViewport.center.dx / 160).round(),
      (absoluteViewport.center.dy / 160).round(),
      (absoluteViewport.width / 160).round(),
      (absoluteViewport.height / 160).round(),
    );
    final zoomBucket = (scale * 10).round();

    final viewportState = GalaxyViewportState(
      matrix: _transformationController.value.clone(),
      absoluteViewport: absoluteViewport,
      relativeViewport: relativeViewport,
      scale: scale,
      viewportBucket: viewportBucket,
      zoomBucket: zoomBucket,
    );
    final budget = _resolveRenderBudget(scale);
    final visibleNodes =
        _collectVisibleNodes(galaxyState, viewportState, budget);
    final compactNodes = visibleNodes.map((node) {
      final pos = galaxyState.nodePositions[node.id] ?? Offset.zero;
      return node.toCompact(
        pos.dx + galaxyState.canvasCenter,
        pos.dy + galaxyState.canvasCenter,
      );
    }).toList(growable: false);
    final visibleNodeIdsByHash = <int, String>{
      for (final node in visibleNodes) node.id.hashCode: node.id,
    };
    final visibleEdges = _collectVisibleEdges(
      galaxyState,
      visibleNodes,
      viewportState,
      budget,
    );
    final hitTargets = compactNodes
        .map(
          (node) => GalaxyHitTarget(
            nodeId: visibleNodeIdsByHash[node.idHash] ?? '',
            nodeHash: node.idHash,
            position: Offset(node.x, node.y),
            radius: (20 + (node.importance * 3)) / scale.clamp(0.35, 1.6),
          ),
        )
        .where((target) => target.nodeId.isNotEmpty)
        .toList(growable: false);

    return GalaxySceneSnapshot(
      viewport: viewportState,
      budget: budget,
      nodes: compactNodes,
      edges: visibleEdges,
      hitTargets: hitTargets,
      selectedNodeIdHash: galaxyState.selectedNodeId?.hashCode,
      highlightedNodeIdHashes: galaxyState.highlightedNodeIdHashes,
      expandedEdgeNodeIdHashes:
          galaxyState.expandedEdgeNodeIds.map((id) => id.hashCode).toSet(),
      highlightRevision: galaxyState.highlightRevision,
    );
  }

  GalaxyRenderBudget _resolveRenderBudget(double scale) {
    final tier = PerformanceService.instance.currentTier.value;
    switch (tier) {
      case PerformanceTier.ultra:
        return GalaxyRenderBudget(
          maxNodes: scale >= 0.95
              ? 320
              : scale >= 0.55
                  ? 230
                  : 140,
          maxEdges: scale >= 0.95
              ? 500
              : scale >= 0.55
                  ? 260
                  : 120,
          maxLabels: scale >= 0.95
              ? 52
              : scale >= 0.55
                  ? 28
                  : 12,
          showLabels: scale >= 0.42,
          showTags: scale >= 0.9,
          showEdgeGlow: true,
          labelScaleThreshold: 0.42,
        );
      case PerformanceTier.high:
        return GalaxyRenderBudget(
          maxNodes: scale >= 0.95
              ? 260
              : scale >= 0.55
                  ? 190
                  : 120,
          maxEdges: scale >= 0.95
              ? 380
              : scale >= 0.55
                  ? 220
                  : 100,
          maxLabels: scale >= 0.95
              ? 40
              : scale >= 0.55
                  ? 22
                  : 10,
          showLabels: scale >= 0.48,
          showTags: scale >= 1.0,
          showEdgeGlow: true,
          labelScaleThreshold: 0.48,
        );
      case PerformanceTier.medium:
        return GalaxyRenderBudget(
          maxNodes: scale >= 0.95
              ? 180
              : scale >= 0.55
                  ? 140
                  : 96,
          maxEdges: scale >= 0.95
              ? 220
              : scale >= 0.55
                  ? 150
                  : 72,
          maxLabels: scale >= 0.95
              ? 22
              : scale >= 0.55
                  ? 14
                  : 6,
          showLabels: scale >= 0.58,
          showTags: false,
          showEdgeGlow: false,
          labelScaleThreshold: 0.58,
        );
      case PerformanceTier.low:
        return GalaxyRenderBudget(
          maxNodes: scale >= 0.95 ? 120 : 80,
          maxEdges: scale >= 0.95 ? 120 : 48,
          maxLabels: scale >= 0.95 ? 12 : 4,
          showLabels: scale >= 0.72,
          showTags: false,
          showEdgeGlow: false,
          labelScaleThreshold: 0.72,
        );
    }
  }

  List<GalaxyNodeModel> _collectVisibleNodes(
    GalaxyState galaxyState,
    GalaxyViewportState viewportState,
    GalaxyRenderBudget budget,
  ) {
    final stickyIds = <String>{
      if (galaxyState.selectedNodeId != null) galaxyState.selectedNodeId!,
      ...galaxyState.highlightedNodeIds,
      ...galaxyState.expandedEdgeNodeIds,
    };
    final cullingRect = viewportState.relativeViewport.inflate(360);
    final candidates = galaxyState.nodes.where((node) {
      final pos = galaxyState.nodePositions[node.id];
      if (pos == null) {
        return false;
      }
      if (stickyIds.contains(node.id)) {
        return true;
      }
      if (!cullingRect.contains(pos)) {
        return false;
      }
      if (viewportState.scale < 0.3) {
        return node.importance >= 4 || node.parentId == null;
      }
      if (viewportState.scale < 0.52) {
        return node.importance >= 3 || node.parentId == null;
      }
      if (viewportState.scale < 0.82) {
        return node.importance >= 2;
      }
      return true;
    }).toList();
    candidates.sort((a, b) {
      final aPinned = stickyIds.contains(a.id);
      final bPinned = stickyIds.contains(b.id);
      if (aPinned != bPinned) {
        return aPinned ? -1 : 1;
      }
      final byImportance = b.importance.compareTo(a.importance);
      if (byImportance != 0) {
        return byImportance;
      }
      final center = viewportState.relativeViewport.center;
      final aPos = galaxyState.nodePositions[a.id] ?? Offset.zero;
      final bPos = galaxyState.nodePositions[b.id] ?? Offset.zero;
      return (aPos - center)
          .distanceSquared
          .compareTo((bPos - center).distanceSquared);
    });
    return candidates.take(budget.maxNodes).toList(growable: false);
  }

  List<GalaxyEdgeModel> _collectVisibleEdges(
    GalaxyState galaxyState,
    List<GalaxyNodeModel> visibleNodes,
    GalaxyViewportState viewportState,
    GalaxyRenderBudget budget,
  ) {
    final visibleIds = visibleNodes.map((node) => node.id).toSet();
    final edges = galaxyState.edges.where((edge) {
      if (!visibleIds.contains(edge.sourceId) ||
          !visibleIds.contains(edge.targetId)) {
        return false;
      }
      if (viewportState.scale < 0.56 &&
          edge.relationType != EdgeRelationType.parentChild) {
        return false;
      }
      return true;
    }).toList();
    edges.sort((a, b) {
      final aPinned = galaxyState.expandedEdgeNodeIds.contains(a.sourceId) ||
          galaxyState.expandedEdgeNodeIds.contains(a.targetId);
      final bPinned = galaxyState.expandedEdgeNodeIds.contains(b.sourceId) ||
          galaxyState.expandedEdgeNodeIds.contains(b.targetId);
      if (aPinned != bPinned) {
        return aPinned ? -1 : 1;
      }
      if (a.relationType == EdgeRelationType.parentChild &&
          b.relationType != EdgeRelationType.parentChild) {
        return -1;
      }
      if (b.relationType == EdgeRelationType.parentChild &&
          a.relationType != EdgeRelationType.parentChild) {
        return 1;
      }
      return b.strength.compareTo(a.strength);
    });
    return edges.take(budget.maxEdges).toList(growable: false);
  }

  int _createPainterSignature(GalaxyState galaxyState) {
    final scaleBucket =
        (_transformationController.value.getMaxScaleOnAxis() * 10).round();
    final viewport = _cachedAbsoluteViewport;
    final viewportBucket = viewport == null
        ? 0
        : Object.hash(
            (viewport.center.dx / 120).round(),
            (viewport.center.dy / 120).round(),
            (viewport.width / 120).round(),
            (viewport.height / 120).round(),
          );
    final nodeSample = Object.hashAll(
      galaxyState.nodes.take(12).map(
        (node) {
          final pos = galaxyState.nodePositions[node.id] ?? Offset.zero;
          return Object.hash(node.id, pos.dx.round(), pos.dy.round());
        },
      ),
    );
    final edgeSample = Object.hashAll(
      galaxyState.edges.take(12).map(
            (edge) =>
                Object.hash(edge.sourceId, edge.targetId, edge.relationType),
          ),
    );

    return Object.hashAll([
      galaxyState.nodes.length,
      galaxyState.edges.length,
      galaxyState.aggregationLevel,
      galaxyState.highlightRevision,
      PerformanceService.instance.currentTier.value,
      PerformanceService.instance.currentDpr.value.round(),
      scaleBucket,
      viewportBucket,
      nodeSample,
      edgeSample,
    ]);
  }

  /// Handle tap on canvas to detect node clicks
  void _handleTapUp(TapUpDetails details) {
    if (_draggingNodeId != null) return;
    _pendingLongPressNodeId = null;

    // Prevent tap if user has dragged (gesture conflict resolution)
    if (_hasDragged) return;

    final nodeId = _hitTestNode(details.localPosition);
    if (nodeId != null) {
      unawaited(context.push('/galaxy/node/$nodeId'));
      HapticFeedback.selectionClick();
      return;
    }

    // If no node hit, deselect
    ref.read(galaxyProvider.notifier).deselectNode();
  }

  /// Handle long press to navigate directly
  void _handleLongPressStart(LongPressStartDetails details) {
    final nodeId = _hitTestNode(details.localPosition);
    if (nodeId == null) return;
    _pendingLongPressNodeId = nodeId;
    _draggingNodeId = null;
    _hasDragged = false;
    ref.read(galaxyProvider.notifier).selectNode(nodeId);
    HapticFeedback.selectionClick();
  }

  void _handleLongPressMoveUpdate(LongPressMoveUpdateDetails details) {
    var nodeId = _draggingNodeId;
    final pendingNodeId = _pendingLongPressNodeId;
    if (nodeId == null && pendingNodeId != null) {
      if (details.localOffsetFromOrigin.distance <= 12) {
        return;
      }
      nodeId = pendingNodeId;
      _pendingLongPressNodeId = null;
      _draggingNodeId = nodeId;
      _hasDragged = true;
      ref.read(galaxyProvider.notifier).beginNodeDrag(nodeId);
      HapticFeedback.mediumImpact();
    }
    if (nodeId == null) return;
    final galaxyState = ref.read(galaxyProvider);
    final canvasPoint = _screenToCanvas(details.localPosition);
    final relativePosition = canvasPoint -
        Offset(galaxyState.canvasCenter, galaxyState.canvasCenter);
    ref
        .read(galaxyProvider.notifier)
        .updateDraggedNodePosition(nodeId, relativePosition);
  }

  void _handleLongPressEnd(LongPressEndDetails details) {
    _pendingLongPressNodeId = null;
    if (_draggingNodeId == null) return;
    final notifier = ref.read(galaxyProvider.notifier);
    _draggingNodeId = null;
    unawaited(notifier.endNodeDrag());
    Future.delayed(const Duration(milliseconds: 80), () {
      _hasDragged = false;
      _dragStartOffset = null;
    });
  }

  void _handleScaleStart(ScaleStartDetails details) {
    _cancelTransientCameraAnimations();
    _gestureStartFocalPoint = details.localFocalPoint;
    _gestureStartScale = _transformationController.value.getMaxScaleOnAxis();
    _gestureStartMatrix = _transformationController.value.clone();
    _dragStartOffset = details.localFocalPoint;
    _hasDragged = false;
    _pendingLongPressNodeId = null;
  }

  void _handleScaleUpdate(ScaleUpdateDetails details, Size viewportSize) {
    if (_draggingNodeId != null) return;

    final startFocal = _gestureStartFocalPoint;
    final startMatrix = _gestureStartMatrix;
    if (startFocal == null || startMatrix == null) return;

    if (_dragStartOffset != null &&
        (details.localFocalPoint - _dragStartOffset!).distance > 8) {
      _hasDragged = true;
    }

    final startScale = _gestureStartScale ?? 1.0;
    final nextScale = (startScale * details.scale).clamp(0.14, 4.0);
    final scaleRatio = nextScale / startScale;
    final nextMatrix = Matrix4.identity()
      ..translateByDouble(
        details.localFocalPoint.dx,
        details.localFocalPoint.dy,
        0,
        1,
      )
      ..scaleByDouble(scaleRatio, scaleRatio, 1, 1)
      ..translateByDouble(-startFocal.dx, -startFocal.dy, 0, 1);
    nextMatrix.multiply(startMatrix);

    _transformationController.value =
        _clampMatrixToViewport(nextMatrix, viewportSize);
  }

  void _handleScaleEnd(ScaleEndDetails details) {
    _gestureStartFocalPoint = null;
    _gestureStartScale = null;
    _gestureStartMatrix = null;
    _pendingLongPressNodeId = null;
    Future.delayed(const Duration(milliseconds: 80), () {
      _hasDragged = false;
      _dragStartOffset = null;
    });
  }

  Matrix4 _clampMatrixToViewport(Matrix4 matrix, Size viewportSize) {
    final scale = matrix.getMaxScaleOnAxis();
    const overscroll = 160.0;
    final minTranslateX =
        viewportSize.width - (_canvasSize * scale) - overscroll;
    final minTranslateY =
        viewportSize.height - (_canvasSize * scale) - overscroll;
    const maxTranslate = overscroll;

    final clampedX = matrix[12].clamp(minTranslateX, maxTranslate).toDouble();
    final clampedY = matrix[13].clamp(minTranslateY, maxTranslate).toDouble();

    return Matrix4.identity()
      ..translateByDouble(clampedX, clampedY, 0, 1)
      ..scaleByDouble(scale, scale, 1, 1);
  }

  String? _hitTestNode(Offset localPosition) {
    final snapshot =
        _cachedSceneSnapshot ?? _createSceneSnapshot(ref.read(galaxyProvider));
    final canvasTap = _screenToCanvas(localPosition);
    for (final target in snapshot.hitTargets) {
      if ((canvasTap - target.position).distance <= target.radius) {
        return target.nodeId;
      }
    }
    return null;
  }

  /// Parse a hex color string to Color
  Color _parseColor(String? hex) {
    if (hex == null || hex.isEmpty) return DS.brandPrimary;
    try {
      return Color(int.parse(hex.replaceFirst('#', '0xFF')));
    } catch (e) {
      return DS.brandPrimary;
    }
  }

  /// Start the energy transfer animation to a specific node
  void _sparkNodeWithAnimation(String nodeId) {
    final galaxyState = ref.read(galaxyProvider);
    final canvasCenter = galaxyState.canvasCenter;
    final nodeIndex = galaxyState.nodes.indexWhere((n) => n.id == nodeId);
    if (nodeIndex == -1) return;
    final node = galaxyState.nodes[nodeIndex];

    // Get the node's canvas position (already centered to the star map canvas)
    final nodeCanvasPosition = galaxyState.nodePositions[nodeId];
    if (nodeCanvasPosition == null) return;

    // Convert to screen coordinates
    // Note: nodePositions are relative to canvas center, we need to add the center offset
    final centeredCanvasPos =
        nodeCanvasPosition + Offset(canvasCenter, canvasCenter);
    final targetScreenPos = _canvasToScreen(centeredCanvasPos);
    final sourceScreenPos = _getScreenCenter();

    final targetColor = _parseColor(node.baseColor);

    // Add active transfer
    final transferKey = UniqueKey();
    setState(() {
      _activeEnergyTransfers.add(
        _ActiveEnergyTransfer(
          key: transferKey,
          nodeId: nodeId,
          sourcePosition: sourceScreenPos,
          targetPosition: targetScreenPos,
          targetColor: targetColor,
        ),
      );
    });
  }

  /// Called when energy particle hits the target star
  Future<void> _onEnergyTransferComplete(_ActiveEnergyTransfer transfer) async {
    // Trigger the actual data update
    final error =
        await ref.read(galaxyProvider.notifier).sparkNode(transfer.nodeId);

    // Remove transfer animation
    setState(() {
      _activeEnergyTransfers.remove(transfer);
    });

    // Get updated target position (in case view shifted slightly)
    final galaxyState = ref.read(galaxyProvider);
    final nodeCanvasPosition = galaxyState.nodePositions[transfer.nodeId];
    if (nodeCanvasPosition == null) return;
    final canvasCenter = galaxyState.canvasCenter;

    final centeredCanvasPos =
        nodeCanvasPosition + Offset(canvasCenter, canvasCenter);
    final targetScreenPos = _canvasToScreen(centeredCanvasPos);

    // Start success animation at target location
    _renderEngine.addBurst(
      screenPosition: targetScreenPos,
      screenSize: MediaQuery.of(context).size,
    );

    final successKey = UniqueKey();
    setState(() {
      _activeSuccessAnimations.add(
        _ActiveSuccessAnimation(
          key: successKey,
          position: targetScreenPos,
          color: transfer.targetColor,
        ),
      );
    });

    if (!mounted) return;

    if (error != null) {
      GalaxyErrorSnackBar.show(context, error: error);
      return;
    }

    // Show feedback
    final nodeIndex =
        galaxyState.nodes.indexWhere((n) => n.id == transfer.nodeId);
    if (nodeIndex == -1) return;
    final node = galaxyState.nodes[nodeIndex];
    HapticFeedback.lightImpact();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('${node.name} 点亮成功!'),
        duration: const Duration(seconds: 1),
        backgroundColor: transfer.targetColor.withValues(alpha: 0.9),
      ),
    );
  }

  /// Called when success animation completes
  void _onSuccessAnimationComplete(_ActiveSuccessAnimation animation) {
    setState(() {
      _activeSuccessAnimations.remove(animation);
    });
  }

  /// Animate camera to focus on a specific node
  void _animateToNode(String nodeId) {
    _cancelTransientCameraAnimations();
    final galaxyState = ref.read(galaxyProvider);
    final nodePos = galaxyState.nodePositions[nodeId];
    if (nodePos == null) return;

    final screenSize = MediaQuery.of(context).size;
    final canvasCenter = galaxyState.canvasCenter;

    // Target scale (zoom in slightly if too far out)
    final currentScale = _transformationController.value.getMaxScaleOnAxis();
    final targetScale = currentScale < 0.8 ? 1.0 : currentScale;

    // Node position in canvas coordinates (0,0 is top-left of the star map canvas)
    // Provider positions are relative to center (0,0), so add offset
    final canvasX = nodePos.dx + canvasCenter;
    final canvasY = nodePos.dy + canvasCenter;

    // Calculate translation to center the node
    // Tx = ScreenCenterX - NodeCanvasX * Scale
    final tx = screenSize.width / 2 - canvasX * targetScale;
    final ty = screenSize.height / 2 - canvasY * targetScale;

    final targetMatrix = Matrix4.identity()..setTranslationRaw(tx, ty, 0.0);

    // Apply scale manually to avoid deprecation warning
    targetMatrix[0] = targetScale;
    targetMatrix[5] = targetScale;
    targetMatrix[10] = 1.0;

    // Animate
    final controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 420),
    );
    _transientControllers.add(controller);

    final animation = Matrix4Tween(
      begin: _transformationController.value,
      end: targetMatrix,
    ).animate(
      CurvedAnimation(
        parent: controller,
        curve: Curves.easeOutCubic,
      ),
    );

    animation.addListener(() {
      _transformationController.value = animation.value;
    });

    controller.forward().whenComplete(() {
      if (_isDisposing) return;
      if (_transientControllers.remove(controller)) {
        controller.dispose();
      }
    });

    // Show a hint
    if (!mounted) return;
    final nodeIndex = galaxyState.nodes.indexWhere((n) => n.id == nodeId);
    if (nodeIndex == -1) return;
    final node = galaxyState.nodes[nodeIndex];
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('推荐学习: ${node.name}'),
        backgroundColor: DS.brandPrimary,
        duration: const Duration(seconds: 3),
        action: SnackBarAction(
          label: '查看',
          textColor: DS.brandPrimary,
          onPressed: () => context.push('/galaxy/node/$nodeId'),
        ),
      ),
    );
  }

  void _resetToInitialView() {
    _cancelTransientCameraAnimations();
    final size = MediaQuery.of(context).size;
    if (size.width <= 0 || size.height <= 0) return;

    const targetScale = 0.25;
    final tx = size.width / 2 - _canvasCenter * targetScale;
    final ty = size.height / 2 - _canvasCenter * targetScale;

    final targetMatrix = Matrix4.identity()
      ..translateByDouble(tx, ty, 0, 1)
      ..scaleByDouble(targetScale, targetScale, 1, 1);

    final controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 360),
    );
    _transientControllers.add(controller);

    final animation = Matrix4Tween(
      begin: _transformationController.value,
      end: targetMatrix,
    ).animate(
      CurvedAnimation(parent: controller, curve: Curves.easeInOutCubic),
    );

    animation.addListener(() {
      _transformationController.value = animation.value;
    });

    controller.forward().whenComplete(() {
      if (_isDisposing) return;
      if (_transientControllers.remove(controller)) {
        controller.dispose();
      }
    });
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('已回到全局视图'),
        duration: Duration(milliseconds: 900),
      ),
    );
  }

  void _showSearchDialog() {
    showDialog<void>(
      context: context,
      builder: (context) => GalaxySearchDialog(
        onNodeSelected: _animateToNode,
      ),
    );
  }

  Future<void> _handleGuideTap() async {
    final nodeId = await ref.read(galaxyProvider.notifier).predictNextNode();
    if (!mounted) return;
    if (nodeId != null) {
      _animateToNode(nodeId);
    } else {
      AppFeedback.info(context, '暂无推荐，请先探索一些节点吧！');
    }
  }

  @override
  Widget build(BuildContext context) {
    final galaxyState = ref.watch(galaxyProvider);
    final canvasSize = galaxyState.canvasSize;
    final canvasCenter = galaxyState.canvasCenter;
    final safePadding = MediaQuery.of(context).padding;
    final screenSize = MediaQuery.of(context).size;
    final isLandscapeMobile = ResponsiveSystem.isLandscapeMobile(context);
    final hasTightHeight = screenSize.height < 680;
    const overlayButtonSize = 44.0;
    const overlayButtonGap = 12.0;

    final overlayInset = ResponsiveSystem.resolve(
      context: context,
      mobile: 16.0,
      tablet: 20.0,
      desktop: 24.0,
      wide: 32.0,
    );
    final bottomInset = safePadding.bottom +
        ResponsiveSystem.resolve(
          context: context,
          mobile: 32.0,
          tablet: 40.0,
          desktop: 48.0,
          wide: 56.0,
        );
    final zoomSliderHeight = ResponsiveSystem.resolve(
      context: context,
      mobile: isLandscapeMobile ? 96.0 : 140.0,
      tablet: 150.0,
      desktop: 160.0,
      wide: 180.0,
    );
    var nodePreviewBottomInset = bottomInset +
        ResponsiveSystem.resolve(
          context: context,
          mobile: 64.0,
          tablet: 72.0,
          desktop: 80.0,
          wide: 96.0,
        );
    if (hasTightHeight) {
      nodePreviewBottomInset =
          nodePreviewBottomInset.clamp(bottomInset + 40, bottomInset + 200);
    }
    final globalViewBottom = bottomInset + overlayButtonSize + overlayButtonGap;
    final zoomControlsBottom =
        globalViewBottom + overlayButtonSize + overlayButtonGap;

    return Scaffold(
      backgroundColor: DS.galaxyBackground, // Deep space background
      body: Listener(
        onPointerDown: (event) => _activePointers.add(event.pointer),
        onPointerUp: (event) => _activePointers.remove(event.pointer),
        onPointerCancel: (event) => _activePointers.remove(event.pointer),
        child: GestureDetector(
          behavior: HitTestBehavior.translucent,
          onDoubleTap: kDebugMode
              ? () {
                  setState(() {
                    _showDebugOverlay = !_showDebugOverlay;
                  });
                }
              : null,
          onLongPressStart: kDebugMode
              ? (_) {
                  if (_activePointers.length >= 3) {
                    setState(() {
                      _showDebugOverlay = !_showDebugOverlay;
                    });
                  }
                }
              : null,
          child: Stack(
            children: [
              Positioned.fill(
                child: const _GalaxyBackdrop(),
              ),

              // 1. Star Map (Interactive)
              LayoutBuilder(
                builder: (context, constraints) {
                  final size = constraints.biggest;

                  if (!_hasCentered && size.width > 0 && size.height > 0) {
                    _scheduleLayoutAdjustment(() {
                      _performInitialCentering(size);
                      _hasCentered = true;
                    });
                  } else if (_lastLayoutSize != null &&
                      _lastLayoutSize != size &&
                      size.width > 0 &&
                      size.height > 0) {
                    _scheduleLayoutAdjustment(() {
                      _recenterForResize(
                        oldSize: _lastLayoutSize!,
                        newSize: size,
                      );
                    });
                  }
                  _lastLayoutSize = size;

                  return GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onScaleStart: _handleScaleStart,
                    onScaleUpdate: (details) =>
                        _handleScaleUpdate(details, size),
                    onScaleEnd: _handleScaleEnd,
                    onTapUp: _handleTapUp,
                    onLongPressStart: _handleLongPressStart,
                    onLongPressMoveUpdate: _handleLongPressMoveUpdate,
                    onLongPressEnd: _handleLongPressEnd,
                    child: SizedBox.expand(
                      child: _buildOptimizedStarMapLayer(
                        galaxyState,
                        canvasCenter,
                        canvasSize,
                      ),
                    ),
                  );
                },
              ),

              // 3. Energy Transfer Animations Layer
              ..._activeEnergyTransfers.map(
                (transfer) => Positioned.fill(
                  child: IgnorePointer(
                    child: EnergyTransferAnimation(
                      key: transfer.key,
                      sourcePosition: transfer.sourcePosition,
                      targetPosition: transfer.targetPosition,
                      targetColor: transfer.targetColor,
                      onComplete: () =>
                          unawaited(_onEnergyTransferComplete(transfer)),
                    ),
                  ),
                ),
              ),

              // 4. Success Animations Layer
              ..._activeSuccessAnimations.map(
                (animation) => Positioned.fill(
                  child: IgnorePointer(
                    child: StarSuccessAnimation(
                      key: animation.key,
                      position: animation.position,
                      color: animation.color,
                      onComplete: () => _onSuccessAnimationComplete(animation),
                    ),
                  ),
                ),
              ),

              // 5. UI Overlays (Back button)
              Positioned(
                top: safePadding.top + 8,
                left: overlayInset,
                child: SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  size: 40,
                  icon: Icon(Icons.arrow_back, color: DS.brandPrimary),
                  onPressed: () => context.pop(),
                ),
              ),

              // 5.1 Search Button (Top Right)
              Positioned(
                top: safePadding.top + 8,
                right: overlayInset,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      size: 40,
                      icon: Icon(Icons.search, color: DS.brandPrimary),
                      onPressed: _showSearchDialog,
                    ),
                    SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      size: 40,
                      icon: Icon(Icons.refresh, color: DS.brandPrimary),
                      onPressed: () {
                        HapticFeedback.selectionClick();
                        unawaited(
                          ref
                              .read(galaxyProvider.notifier)
                              .loadGalaxy(forceRefresh: true),
                        );
                      },
                    ),
                    if (kDebugMode)
                      Tooltip(
                        message: 'Toggle LOD Debug Overlay',
                        child: SparkleIconButton(
                          variant: ButtonVariant.ghost,
                          size: 40,
                          icon: Icon(
                            _showDebugOverlay
                                ? Icons.bug_report
                                : Icons.bug_report_outlined,
                            color: DS.brandPrimaryConst,
                          ),
                          onPressed: () {
                            setState(() {
                              _showDebugOverlay = !_showDebugOverlay;
                            });
                          },
                        ),
                      ),
                  ],
                ),
              ),

              Positioned(
                top: safePadding.top + 56,
                left: overlayInset,
                right: overlayInset,
                child: Center(
                  child: OfflineIndicator(
                    isUsingCache: galaxyState.isUsingCache,
                    onRetry: galaxyState.isUsingCache
                        ? () => unawaited(
                              ref
                                  .read(galaxyProvider.notifier)
                                  .loadGalaxy(forceRefresh: true),
                            )
                        : null,
                  ),
                ),
              ),

              // 6.1 Guide Button
              Positioned(
                bottom: bottomInset,
                left: overlayInset,
                child: SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  size: overlayButtonSize,
                  icon: Icon(Icons.explore, color: DS.brandPrimary),
                  onPressed: () {
                    unawaited(_handleGuideTap());
                  },
                ),
              ),

              // 6.2 Zoom Controls (Right side, above Spark button)
              Positioned(
                bottom: zoomControlsBottom,
                right: overlayInset,
                child: ZoomControls(
                  transformationController: _transformationController,
                  viewportSize: screenSize,
                  sliderHeight: zoomSliderHeight,
                ),
              ),

              // 7. Spark Button (Bottom Right)
              Positioned(
                bottom: bottomInset,
                right: overlayInset,
                child: SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  size: overlayButtonSize,
                  icon: Icon(Icons.bolt, color: DS.brandPrimary),
                  onPressed: () {
                    if (galaxyState.nodes.isNotEmpty) {
                      final node = galaxyState.nodes[
                          DateTime.now().millisecond %
                              galaxyState.nodes.length];
                      _sparkNodeWithAnimation(node.id);
                    }
                  },
                ),
              ),

              Positioned(
                bottom: globalViewBottom,
                right: overlayInset,
                child: Tooltip(
                  message: '回到全局视图',
                  child: SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    size: overlayButtonSize,
                    onPressed: _resetToInitialView,
                    icon: const Icon(Icons.public),
                  ),
                ),
              ),

              if (galaxyState.isLoading &&
                  galaxyState.nodes.isEmpty &&
                  !_loadingTimedOut)
                const Center(child: CircularProgressIndicator()),

              if (galaxyState.lastError != null && galaxyState.nodes.isEmpty)
                Positioned.fill(
                  child: GalaxyErrorPlaceholder(
                    error: galaxyState.lastError!,
                    onRetry: () => unawaited(
                      ref
                          .read(galaxyProvider.notifier)
                          .loadGalaxy(forceRefresh: true),
                    ),
                  ),
                ),

              // 8. Node Preview Card (Overlay)
              if (galaxyState.selectedNodeId != null &&
                  galaxyState.nodes.isNotEmpty)
                Builder(
                  key: ValueKey(galaxyState.selectedNodeId),
                  builder: (context) {
                    final node = galaxyState.nodes.firstWhere(
                      (n) => n.id == galaxyState.selectedNodeId,
                      orElse: () => galaxyState.nodes.first,
                    );
                    return Padding(
                      padding: EdgeInsets.only(bottom: safePadding.bottom),
                      child: NodePreviewCard(
                        node: node,
                        onClose: () =>
                            ref.read(galaxyProvider.notifier).deselectNode(),
                        onTap: () => context.push('/galaxy/node/${node.id}'),
                        bottomInset: isLandscapeMobile
                            ? bottomInset + 56
                            : nodePreviewBottomInset,
                      ),
                    );
                  },
                ),

              if (kDebugMode && _showDebugOverlay)
                Positioned(
                  top: safePadding.top + 56,
                  right: overlayInset,
                  child: _GalaxyDebugOverlay(
                    scale: galaxyState.currentScale,
                    aggregationLevel: galaxyState.aggregationLevel,
                    viewport: galaxyState.viewport,
                    visibleNodes: galaxyState.visibleNodes.length,
                    visibleEdges: galaxyState.visibleEdges.length,
                    screenSize: screenSize,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  // Helper to shift cluster positions to center of the star map canvas
  Map<String, ClusterInfo> _centerClusters(
    Map<String, ClusterInfo> raw,
    double cx,
    double cy,
  ) =>
      raw.map(
        (key, cluster) => MapEntry(
          key,
          ClusterInfo(
            id: cluster.id,
            name: cluster.name,
            position: cluster.position + Offset(cx, cy),
            nodeCount: cluster.nodeCount,
            totalMastery: cluster.totalMastery,
            sector: cluster.sector,
            childNodeIds: cluster.childNodeIds,
          ),
        ),
      );
}

class SelectionOverlayPainter extends CustomPainter {
  SelectionOverlayPainter({
    required this.nodes,
    required this.viewMatrix,
    required this.selectedNodeIdHash,
    required this.highlightedNodeIdHashes,
    required this.performanceTier,
    required this.selectionPulse,
  });

  final List<CompactKnowledgeNode> nodes;
  final Matrix4 viewMatrix;
  final int? selectedNodeIdHash;
  final Set<int> highlightedNodeIdHashes;
  final dynamic performanceTier;
  final double selectionPulse;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.transform(viewMatrix.storage);

    final nodePositions = <int, Offset>{};
    for (final node in nodes) {
      nodePositions[node.idHash] = Offset(node.x, node.y);
    }

    if (selectedNodeIdHash != null) {
      final selectedPosition = nodePositions[selectedNodeIdHash!];
      if (selectedPosition != null) {
        final radius = 40.0 + (selectionPulse * 8.0);
        final outline = Paint()
          ..color =
              DS.brandPrimary.withValues(alpha: 0.35 + (selectionPulse * 0.2))
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0 + selectionPulse;
        canvas.drawCircle(selectedPosition, radius, outline);

        if (performanceTier == PerformanceTier.ultra ||
            performanceTier == PerformanceTier.high) {
          final fill = Paint()
            ..color = DS.brandPrimary
                .withValues(alpha: 0.08 + (selectionPulse * 0.05))
            ..style = PaintingStyle.fill;
          canvas.drawCircle(selectedPosition, 40.0, fill);
        }
      }
    }

    if (highlightedNodeIdHashes.isEmpty) {
      return;
    }

    final highlightPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5
      ..color = DS.info.withValues(alpha: 0.55);
    final pulseRadius = 24.0 + (selectionPulse * 4.0);
    for (final nodeHash in highlightedNodeIdHashes) {
      if (nodeHash == selectedNodeIdHash) {
        continue;
      }
      final position = nodePositions[nodeHash];
      if (position == null) {
        continue;
      }
      canvas.drawCircle(position, pulseRadius, highlightPaint);
    }

    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant SelectionOverlayPainter oldDelegate) =>
      oldDelegate.selectionPulse != selectionPulse ||
      oldDelegate.selectedNodeIdHash != selectedNodeIdHash ||
      oldDelegate.highlightedNodeIdHashes != highlightedNodeIdHashes ||
      oldDelegate.viewMatrix != viewMatrix ||
      !identical(oldDelegate.nodes, nodes);
}

class _GalaxyLabelOverlay extends StatelessWidget {
  const _GalaxyLabelOverlay({
    required this.snapshot,
    required this.nodeNameLookup,
  });

  final GalaxySceneSnapshot snapshot;
  final Map<int, String> nodeNameLookup;

  @override
  Widget build(BuildContext context) {
    final labels = snapshot.nodes
        .where((node) => node.isUnlocked || node.importance >= 2)
        .take(snapshot.budget.maxLabels)
        .toList(growable: false);

    return Stack(
      children: labels.map((node) {
        final label = nodeNameLookup[node.idHash];
        if (label == null || label.isEmpty) {
          return const SizedBox.shrink();
        }
        return Positioned(
          left: node.x - 56,
          top: node.y + (14 + (node.importance * 2)) + 8,
          width: 112,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: DS.surfaceOverlay.withValues(alpha: 0.82),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: DS.labelSmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        );
      }).toList(growable: false),
    );
  }
}

class _GalaxyBackdrop extends StatelessWidget {
  const _GalaxyBackdrop();

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: CustomPaint(
        painter: _GalaxyBackdropPainter(
          isDark: Theme.of(context).brightness == Brightness.dark,
        ),
        size: Size.infinite,
      ),
    );
  }
}

class _GalaxyBackdropPainter extends CustomPainter {
  const _GalaxyBackdropPainter({required this.isDark});

  final bool isDark;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final background = Paint()
      ..shader = RadialGradient(
        center: const Alignment(0, -0.18),
        radius: 1.12,
        colors: [
          (isDark ? const Color(0xFF263545) : const Color(0xFFE7EDF3))
              .withValues(alpha: 0.96),
          (isDark ? const Color(0xFF141B24) : const Color(0xFFF3F5F7))
              .withValues(alpha: 0.99),
          isDark ? const Color(0xFF090D13) : const Color(0xFFFAFBFC),
        ],
      ).createShader(rect);
    canvas.drawRect(rect, background);

    final glowPaint = Paint()..blendMode = BlendMode.screen;
    final glows = <({Offset center, double radius, Color color})>[
      (
        center: Offset(size.width * 0.16, size.height * 0.24),
        radius: size.shortestSide * 0.30,
        color: const Color(0xFF7F97B5).withValues(alpha: isDark ? 0.10 : 0.12),
      ),
      (
        center: Offset(size.width * 0.84, size.height * 0.18),
        radius: size.shortestSide * 0.24,
        color: const Color(0xFF9BAEC0).withValues(alpha: isDark ? 0.08 : 0.10),
      ),
      (
        center: Offset(size.width * 0.54, size.height * 0.78),
        radius: size.shortestSide * 0.32,
        color: const Color(0xFF3A526C).withValues(alpha: isDark ? 0.11 : 0.07),
      ),
    ];
    for (final glow in glows) {
      glowPaint.shader = RadialGradient(
        colors: [
          glow.color,
          glow.color.withValues(alpha: glow.color.a * 0.42),
          Colors.transparent,
        ],
      ).createShader(Rect.fromCircle(center: glow.center, radius: glow.radius));
      canvas.drawCircle(glow.center, glow.radius, glowPaint);
    }

    final starPaint = Paint()..style = PaintingStyle.fill;
    for (var index = 0; index < 96; index++) {
      final x = (math.sin(index * 91.17) * 0.5 + 0.5) * size.width;
      final y = (math.cos(index * 57.31) * 0.5 + 0.5) * size.height;
      final radius = 0.6 + (index % 3) * 0.35;
      final alpha =
          isDark ? 0.16 + (index % 4) * 0.04 : 0.10 + (index % 4) * 0.03;
      starPaint.color =
          Colors.white.withValues(alpha: alpha.clamp(0.08, 0.30));
      canvas.drawCircle(Offset(x, y), radius, starPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _GalaxyBackdropPainter oldDelegate) =>
      oldDelegate.isDark != isDark;
}

class _GalaxyDebugOverlay extends StatelessWidget {
  const _GalaxyDebugOverlay({
    required this.scale,
    required this.aggregationLevel,
    required this.viewport,
    required this.visibleNodes,
    required this.visibleEdges,
    required this.screenSize,
  });

  final double scale;
  final AggregationLevel aggregationLevel;
  final Rect? viewport;
  final int visibleNodes;
  final int visibleEdges;
  final Size screenSize;

  @override
  Widget build(BuildContext context) {
    final category = ResponsiveSystem.getCategory(context);
    final viewportText = viewport == null
        ? 'viewport: null'
        : 'vp ${viewport!.width.toStringAsFixed(0)}x${viewport!.height.toStringAsFixed(0)}';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: DS.surfaceHigh.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: DS.neutral700),
      ),
      child: DefaultTextStyle(
        style: TextStyle(color: DS.textPrimary, fontSize: 11),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('scale: ${scale.toStringAsFixed(2)}'),
            Text('lod: ${aggregationLevel.name}'),
            Text('nodes: $visibleNodes edges: $visibleEdges'),
            Text(
              'screen: ${screenSize.width.toStringAsFixed(0)}x${screenSize.height.toStringAsFixed(0)}',
            ),
            Text('category: ${category.name}'),
            Text(viewportText),
          ],
        ),
      ),
    );
  }
}

/// Data class for active energy transfer animation
class _ActiveEnergyTransfer {
  _ActiveEnergyTransfer({
    required this.key,
    required this.nodeId,
    required this.sourcePosition,
    required this.targetPosition,
    required this.targetColor,
  });
  final Key key;
  final String nodeId;
  final Offset sourcePosition;
  final Offset targetPosition;
  final Color targetColor;
}

/// Data class for active success animation
class _ActiveSuccessAnimation {
  _ActiveSuccessAnimation({
    required this.key,
    required this.position,
    required this.color,
  });
  final Key key;
  final Offset position;
  final Color color;
}
