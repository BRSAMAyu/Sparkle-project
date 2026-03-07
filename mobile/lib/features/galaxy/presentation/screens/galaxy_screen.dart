import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_layout_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_render_engine.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/central_flame.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/energy_particle.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_entrance_animation.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_error_dialog.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_mini_map.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_search_dialog.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_shader_background.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/node_preview_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/parallax_star_background.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_background_painter.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_success_animation.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/zoom_controls.dart';
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
  bool _isEntering = true;
  bool _hasCentered = false;
  bool _loadingTimedOut = false;
  Size? _lastLayoutSize;
  bool _showDebugOverlay = kDebugMode;
  final Set<int> _activePointers = <int>{};
  String? _draggingNodeId;

  // Active animations
  final List<_ActiveEnergyTransfer> _activeEnergyTransfers = [];
  final List<_ActiveSuccessAnimation> _activeSuccessAnimations = [];

  // Canvas constants - use layout engine constants
  static const double _centralFlameSize = 60.0;
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

  // 🔧 性能优化: 缓存 StarMapPainter
  StarMapPainter? _cachedPainter;
  int? _lastPainterSignature;

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
    )..repeat(reverse: true);

    // Listen to transformation changes for scale updates
    _transformationController.addListener(_onTransformChanged);

    // Start Performance Monitoring
    PerformanceService.instance.startMonitoring();

    // Delay provider mutations until after the first frame.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      unawaited(_galaxyNotifier.loadGalaxy());
    });
    unawaited(_renderEngine.prewarm());

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
    PerformanceService.instance.stopMonitoring();
    super.dispose();
  }

  /// Handle transformation changes to update scale in provider
  /// 🔧 优化: 缓存 viewport 计算，避免重复的矩阵求逆
  void _onTransformChanged() {
    final scale = _transformationController.value.getMaxScaleOnAxis();

    // Only update if scale changed significantly (avoid excessive updates during pan)
    if ((scale - _lastScale).abs() > 0.02) {
      _lastScale = scale;
      ref.read(galaxyProvider.notifier).updateScale(scale);
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
        ref.read(galaxyProvider.notifier).updateViewport(nextRelativeViewport);
      }
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

        if (needsRebuild) {
          _cachedPainter = _createStarMapPainter(galaxyState, canvasCenter);
        }

        // 使用 RepaintBoundary 隔离动画层
        return Stack(
          children: [
            // 1. Background: Sector nebula and stars (Static, Cached)
            Positioned.fill(
              child: RepaintBoundary(
                child: TiledSectorBackground(
                  width: canvasSize,
                  height: canvasSize,
                ),
              ),
            ),

            // 2. Central Flame at canvas center (Static position)
            Positioned(
              left: canvasCenter - _centralFlameSize / 2,
              top: canvasCenter - _centralFlameSize / 2,
              child: Opacity(
                opacity: _isEntering ? 0.0 : 1.0,
                child: CentralFlame(
                  intensity: galaxyState.userFlameIntensity,
                  size: _centralFlameSize,
                ),
              ),
            ),

            // 3. Static star map layer
            Positioned.fill(
              child: Opacity(
                opacity: _isEntering ? 0.0 : 1.0,
                child: RepaintBoundary(
                  child: CustomPaint(
                    painter: _cachedPainter,
                  ),
                ),
              ),
            ),

            // 4. Lightweight overlay for selection and evidence pulses
            if (galaxyState.selectedNodeId != null ||
                galaxyState.highlightedNodeIdHashes.isNotEmpty)
              Positioned.fill(
                child: IgnorePointer(
                  child: Opacity(
                    opacity: _isEntering ? 0.0 : 1.0,
                    child: RepaintBoundary(
                      child: AnimatedBuilder(
                        animation: _selectionPulseController,
                        builder: (context, child) {
                          final throttledPulse =
                              (_selectionPulseController.value * 15).round() /
                                  15.0;
                          return CustomPaint(
                            painter: SelectionOverlayPainter(
                              nodes: galaxyState.visibleCompactNodes,
                              selectedNodeIdHash:
                                  galaxyState.selectedNodeId?.hashCode,
                              highlightedNodeIdHashes:
                                  galaxyState.highlightedNodeIdHashes,
                              performanceTier:
                                  PerformanceService.instance.currentTier.value,
                              selectionPulse: throttledPulse,
                            ),
                          );
                        },
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
    double canvasCenter,
  ) {
    final scale = _transformationController.value.getMaxScaleOnAxis();

    // 🔧 使用缓存的 viewport 计算结果
    final absoluteViewport = _cachedAbsoluteViewport ??
        _calculateViewport(MediaQuery.of(context).size);

    // 🔧 性能优化: 直接使用 Provider 预计算的 CompactNode 列表
    // 避免每次渲染时都映射节点列表 (节省 5-10ms/帧 for 500+ nodes)
    final compactNodes = galaxyState.visibleCompactNodes;

    final selectedHash = galaxyState.selectedNodeId?.hashCode;
    final highlightedHashes = galaxyState.highlightedNodeIdHashes;
    final expandedHashes =
        galaxyState.expandedEdgeNodeIds.map((id) => id.hashCode).toSet();
    final animationHashes = galaxyState.nodeAnimationProgress
        .map((id, val) => MapEntry(id.hashCode, val));

    return StarMapPainter(
      nodes: compactNodes,
      edges: galaxyState.visibleEdges,
      scale: scale,
      performanceTier: PerformanceService.instance.currentTier.value,
      currentDpr: PerformanceService.instance.currentDpr.value,
      aggregationLevel: galaxyState.aggregationLevel,
      clusters: _centerClusters(
        galaxyState.clusters,
        canvasCenter,
        canvasCenter,
      ),
      viewport: absoluteViewport,
      center: Offset(canvasCenter, canvasCenter),
      selectedNodeIdHash: selectedHash,
      highlightedNodeIdHashes: highlightedHashes,
      highlightRevision: galaxyState.highlightRevision,
      expandedEdgeNodeIdHashes: expandedHashes,
      nodeAnimationProgress: animationHashes,
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
      galaxyState.visibleCompactNodes.take(12).map(
          (node) => Object.hash(node.idHash, node.x.round(), node.y.round())),
    );
    final edgeSample = Object.hashAll(
      galaxyState.visibleEdges.take(12).map(
            (edge) =>
                Object.hash(edge.sourceId, edge.targetId, edge.relationType),
          ),
    );

    return Object.hashAll([
      galaxyState.visibleCompactNodes.length,
      galaxyState.visibleEdges.length,
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
    if (_isEntering) return;
    if (_draggingNodeId != null) return;

    // Prevent tap if user has dragged (gesture conflict resolution)
    if (_hasDragged) return;

    final galaxyState = ref.read(galaxyProvider);
    if (galaxyState.nodes.isEmpty) return;
    final canvasCenter = galaxyState.canvasCenter;

    // Convert screen tap to canvas coordinates
    final canvasTap = _screenToCanvas(details.localPosition);

    // Get current scale for dynamic hit radius
    final scale = _transformationController.value.getMaxScaleOnAxis();
    final effectiveScale = scale.clamp(0.3, 2.0);
    final hitRadius = 30 / effectiveScale; // Stable hit area across zooms

    // Find the tapped node
    // Check visible nodes first for optimization
    final searchNodes = galaxyState.visibleNodes.isNotEmpty
        ? galaxyState.visibleNodes
        : galaxyState.nodes;

    for (final node in searchNodes) {
      final nodePos = galaxyState.nodePositions[node.id];
      if (nodePos == null) continue;

      // Add canvas center offset to get actual position
      final actualPos = nodePos + Offset(canvasCenter, canvasCenter);
      final distance = (canvasTap - actualPos).distance;

      // Hit test
      if (distance < hitRadius + (node.importance * 2)) {
        // Node tapped - Select it
        ref.read(galaxyProvider.notifier).selectNode(node.id);
        HapticFeedback.selectionClick();
        return;
      }
    }

    // If no node hit, deselect
    ref.read(galaxyProvider.notifier).deselectNode();
  }

  /// Handle long press to navigate directly
  void _handleLongPressStart(LongPressStartDetails details) {
    if (_isEntering) return;
    final nodeId = _hitTestNode(details.localPosition);
    if (nodeId == null) return;
    _draggingNodeId = nodeId;
    _hasDragged = true;
    ref.read(galaxyProvider.notifier).beginNodeDrag(nodeId);
    HapticFeedback.mediumImpact();
  }

  void _handleLongPressMoveUpdate(LongPressMoveUpdateDetails details) {
    final nodeId = _draggingNodeId;
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
    if (_draggingNodeId == null) return;
    final notifier = ref.read(galaxyProvider.notifier);
    _draggingNodeId = null;
    unawaited(notifier.endNodeDrag());
    Future.delayed(const Duration(milliseconds: 80), () {
      _hasDragged = false;
      _dragStartOffset = null;
    });
  }

  String? _hitTestNode(Offset localPosition) {
    final galaxyState = ref.read(galaxyProvider);
    final canvasCenter = galaxyState.canvasCenter;
    final canvasTap = _screenToCanvas(localPosition);
    final scale = _transformationController.value.getMaxScaleOnAxis();
    final effectiveScale = scale.clamp(0.3, 2.0);
    final hitRadius = 30 / effectiveScale;

    final searchNodes = galaxyState.visibleNodes.isNotEmpty
        ? galaxyState.visibleNodes
        : galaxyState.nodes;

    for (final node in searchNodes) {
      final nodePos = galaxyState.nodePositions[node.id];
      if (nodePos == null) continue;
      final actualPos = nodePos + Offset(canvasCenter, canvasCenter);

      if ((canvasTap - actualPos).distance <
          hitRadius + (node.importance * 2)) {
        return node.id;
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
      duration: const Duration(milliseconds: 1500),
    );
    _transientControllers.add(controller);

    final animation = Matrix4Tween(
      begin: _transformationController.value,
      end: targetMatrix,
    ).animate(
      CurvedAnimation(
        parent: controller,
        curve: Curves.easeInOutCubic,
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
      duration: const Duration(milliseconds: 700),
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
    final reduceBackgroundEffects = _activePointers.isNotEmpty || _hasDragged;

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
    final minimapSizeBase = ResponsiveSystem.resolve(
      context: context,
      mobile: 96.0,
      tablet: 120.0,
      desktop: 140.0,
      wide: 160.0,
    );
    final minimapSize =
        isLandscapeMobile ? minimapSizeBase * 0.8 : minimapSizeBase;
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
    // Zoom controls should be positioned above the spark button (bottomInset)
    // and reset button (bottomInset + 56). Adding 56 for reset button height + 12 gap.
    final zoomControlsBottom = isLandscapeMobile
        ? bottomInset + 56 + 48 + 12 // Above reset button with gap
        : bottomInset +
            56 +
            48 +
            12; // Same for portrait - consistent positioning

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
                child: GalaxyShaderBackground(
                  engine: _renderEngine,
                  enabled: !reduceBackgroundEffects,
                ),
              ),
              // 0. Parallax Background (Deepest Layer)
              Positioned.fill(
                child: ValueListenableBuilder<bool>(
                  valueListenable: _renderEngine.isReady,
                  builder: (context, isReady, child) => ParallaxStarBackground(
                    transformationController: _transformationController,
                    drawBackground: !isReady,
                  ),
                ),
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
                    onPanStart: (details) {
                      _hasDragged = true;
                      _dragStartOffset = details.localPosition;
                    },
                    onPanUpdate: (details) {
                      // Track if user actually dragged significant distance
                      if (_dragStartOffset != null) {
                        final distance =
                            (details.localPosition - _dragStartOffset!)
                                .distance;
                        if (distance > 10) {
                          _hasDragged = true;
                        }
                      }
                    },
                    onPanEnd: (details) {
                      // Reset after a short delay to allow tap detection
                      Future.delayed(const Duration(milliseconds: 100), () {
                        _hasDragged = false;
                        _dragStartOffset = null;
                      });
                    },
                    onTapUp: _handleTapUp,
                    onLongPressStart: _handleLongPressStart,
                    onLongPressMoveUpdate: _handleLongPressMoveUpdate,
                    onLongPressEnd: _handleLongPressEnd,
                    child: InteractiveViewer(
                      transformationController: _transformationController,
                      alignment: Alignment.topLeft,
                      boundaryMargin:
                          const EdgeInsets.all(2000), // Huge scroll area
                      minScale: 0.1,
                      maxScale: 5.0,
                      panEnabled: _draggingNodeId == null,
                      scaleEnabled: _draggingNodeId == null,
                      constrained: false, // Infinite canvas
                      child: SizedBox(
                        width: _canvasSize,
                        height: _canvasSize,
                        // 🔧 优化: 构建优化的星图层
                        child: _buildOptimizedStarMapLayer(
                            galaxyState, canvasCenter, canvasSize),
                      ),
                    ),
                  );
                },
              ),

              // 2. Entrance Animation Layer
              if (_isEntering)
                GalaxyEntranceAnimation(
                  onComplete: () {
                    setState(() {
                      _isEntering = false;
                    });

                    // Entrance Phase 2: Smooth Zoom from 0.15 to 0.25
                    final controller = AnimationController(
                      vsync: this,
                      duration: const Duration(seconds: 2),
                    );

                    final startMatrix = _transformationController.value;
                    // Calculate target matrix for 0.25 scale (still centered)
                    final size = MediaQuery.of(context).size;
                    const targetScale = 0.25;
                    final tx = size.width / 2 - canvasCenter * targetScale;
                    final ty = size.height / 2 - canvasCenter * targetScale;
                    final targetMatrix = Matrix4.identity()
                      ..translateByDouble(tx, ty, 0, 1)
                      ..scaleByDouble(targetScale, targetScale, 1, 1);

                    final animation = Matrix4Tween(
                      begin: startMatrix,
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

                    controller.forward().whenComplete(controller.dispose);
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
              if (!_isEntering)
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
              if (!_isEntering)
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

              if (!_isEntering)
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

              // 6. Mini Map (Bottom Left)
              if (!_isEntering)
                Positioned(
                  bottom: bottomInset,
                  left: overlayInset,
                  child: GalaxyMiniMap(
                    transformationController: _transformationController,
                    canvasSize: canvasSize,
                    screenSize: screenSize,
                    minimapSize: minimapSize,
                  ),
                ),

              // 6.1 Guide Button (Above Mini Map)
              if (!_isEntering)
                Positioned(
                  bottom: bottomInset + minimapSize + 12,
                  left: overlayInset + 8,
                  child: SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    size: 40,
                    icon: Icon(Icons.explore, color: DS.brandPrimary),
                    onPressed: () {
                      unawaited(_handleGuideTap());
                    },
                  ),
                ),

              // 6.2 Zoom Controls (Right side, above Spark button)
              if (!_isEntering)
                Positioned(
                  bottom: zoomControlsBottom,
                  right: overlayInset,
                  child: ZoomControls(
                    transformationController: _transformationController,
                    sliderHeight: zoomSliderHeight,
                  ),
                ),

              // 7. Spark Button (Bottom Right)
              if (!_isEntering)
                Positioned(
                  bottom: bottomInset,
                  right: overlayInset,
                  child: SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    size: 48,
                    icon: Icon(Icons.bolt, color: DS.brandPrimary),
                    onPressed: () {
                      // Pick a random node to spark for demo
                      if (galaxyState.nodes.isNotEmpty) {
                        final node = galaxyState.nodes[
                            DateTime.now().millisecond %
                                galaxyState.nodes.length];
                        _sparkNodeWithAnimation(node.id);
                      }
                    },
                  ),
                ),

              if (!_isEntering)
                Positioned(
                  bottom: bottomInset + 56,
                  right: overlayInset,
                  child: Tooltip(
                    message: '回到全局视图',
                    child: SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      size: 40,
                      onPressed: _resetToInitialView,
                      icon: const Icon(Icons.public),
                    ),
                  ),
                ),

              if (galaxyState.isLoading &&
                  galaxyState.nodes.isEmpty &&
                  !_isEntering &&
                  !_loadingTimedOut)
                const Center(child: CircularProgressIndicator()),

              if (!_isEntering &&
                  galaxyState.lastError != null &&
                  galaxyState.nodes.isEmpty)
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
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 200),
                transitionBuilder: (child, animation) => FadeTransition(
                  opacity: animation,
                  child: ScaleTransition(
                    scale: Tween<double>(begin: 0.9, end: 1.0).animate(
                      CurvedAnimation(
                        parent: animation,
                        curve: Curves.easeOutCubic,
                      ),
                    ),
                    child: child,
                  ),
                ),
                child: galaxyState.selectedNodeId != null &&
                        galaxyState.nodes.isNotEmpty
                    ? Builder(
                        key: ValueKey(galaxyState.selectedNodeId),
                        builder: (context) {
                          final node = galaxyState.nodes.firstWhere(
                            (n) => n.id == galaxyState.selectedNodeId,
                            orElse: () => galaxyState.nodes.first,
                          );
                          return Padding(
                            padding:
                                EdgeInsets.only(bottom: safePadding.bottom),
                            child: NodePreviewCard(
                              node: node,
                              onClose: () => ref
                                  .read(galaxyProvider.notifier)
                                  .deselectNode(),
                              onTap: () =>
                                  context.push('/galaxy/node/${node.id}'),
                              bottomInset: isLandscapeMobile
                                  ? bottomInset + 56
                                  : nodePreviewBottomInset,
                            ),
                          );
                        },
                      )
                    : const SizedBox.shrink(),
              ),

              if (kDebugMode && _showDebugOverlay && !_isEntering)
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
    required this.selectedNodeIdHash,
    required this.highlightedNodeIdHashes,
    required this.performanceTier,
    required this.selectionPulse,
  });

  final List<CompactKnowledgeNode> nodes;
  final int? selectedNodeIdHash;
  final Set<int> highlightedNodeIdHashes;
  final PerformanceTier performanceTier;
  final double selectionPulse;

  @override
  void paint(Canvas canvas, Size size) {
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
  }

  @override
  bool shouldRepaint(covariant SelectionOverlayPainter oldDelegate) =>
      oldDelegate.selectionPulse != selectionPulse ||
      oldDelegate.selectedNodeIdHash != selectedNodeIdHash ||
      oldDelegate.highlightedNodeIdHashes != highlightedNodeIdHashes ||
      !identical(oldDelegate.nodes, nodes);
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
