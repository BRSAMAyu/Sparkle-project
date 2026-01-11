import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
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
  late final AnimationController _selectionPulseController;
  final List<AnimationController> _transientControllers = [];
  bool _isDisposing = false;

  // State
  bool _isEntering = true;

  // Active animations
  final List<_ActiveEnergyTransfer> _activeEnergyTransfers = [];
  final List<_ActiveSuccessAnimation> _activeSuccessAnimations = [];

  // Canvas constants
  static const double _canvasPadding = 400.0;
  static const double _canvasSize =
      GalaxyLayoutEngine.outerRadius * 2 + _canvasPadding * 2;
  static const double _canvasCenter = _canvasSize / 2;
  static const double _centralFlameSize = 60.0;

  // Track last scale to avoid unnecessary updates
  double _lastScale = 1.0;

  // Gesture conflict resolution
  bool _hasDragged = false;
  Offset? _dragStartOffset;

  @override
  void initState() {
    super.initState();
    _renderEngine = GalaxyRenderEngine();

    _selectionPulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    // Listen to transformation changes for scale updates
    _transformationController.addListener(_onTransformChanged);

    // Start Performance Monitoring
    PerformanceService.instance.startMonitoring();

    // Defer initial centering until we know screen size (in build) or post frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final size = MediaQuery.of(context).size;

      // Start at 0.15 scale (Universe View) centered
      const initialScale = 0.15;
      // To center canvas point (_canvasCenter, _canvasCenter) at screen center (w/2, h/2) with scale S:
      // Tx = w/2 - _canvasCenter * S
      final tx = size.width / 2 - _canvasCenter * initialScale;
      final ty = size.height / 2 - _canvasCenter * initialScale;

      _transformationController.value = Matrix4.identity()
        ..translate(tx, ty)
        ..scale(initialScale);

      unawaited(ref.read(galaxyProvider.notifier).loadGalaxy());
      unawaited(_renderEngine.prewarm());
    });
  }

  @override
  void dispose() {
    _isDisposing = true;
    for (final controller in _transientControllers) {
      controller.dispose();
    }
    _transientControllers.clear();
    _selectionPulseController.dispose();
    _transformationController.removeListener(_onTransformChanged);
    _transformationController.dispose();
    _renderEngine.dispose();
    PerformanceService.instance.stopMonitoring();
    super.dispose();
  }

  /// Handle transformation changes to update scale in provider
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

    final matrix = _transformationController.value;
    final inverseMatrix = matrix.clone()..invert();
    final topLeft = MatrixUtils.transformPoint(inverseMatrix, Offset.zero);
    final bottomRight = MatrixUtils.transformPoint(
      inverseMatrix,
      Offset(size.width, size.height),
    );
    final viewport = Rect.fromPoints(topLeft, bottomRight)
        .shift(const Offset(-_canvasCenter, -_canvasCenter));
    ref.read(galaxyProvider.notifier).updateViewport(viewport);
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

  /// Handle tap on canvas to detect node clicks
  void _handleTapUp(TapUpDetails details) {
    if (_isEntering) return;

    // Prevent tap if user has dragged (gesture conflict resolution)
    if (_hasDragged) return;

    final galaxyState = ref.read(galaxyProvider);
    if (galaxyState.nodes.isEmpty) return;

    // Convert screen tap to canvas coordinates
    final canvasTap = _screenToCanvas(details.localPosition);

    // Get current scale for dynamic hit radius
    final scale = _transformationController.value.getMaxScaleOnAxis();
    final hitRadius = 30 / scale; // Larger hit area when zoomed out

    // Find the tapped node
    // Check visible nodes first for optimization
    final searchNodes = galaxyState.visibleNodes.isNotEmpty
        ? galaxyState.visibleNodes
        : galaxyState.nodes;

    for (final node in searchNodes) {
      final nodePos = galaxyState.nodePositions[node.id];
      if (nodePos == null) continue;

      // Add canvas center offset to get actual position
      final actualPos = nodePos + const Offset(_canvasCenter, _canvasCenter);
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

    // Prevent long press if user has dragged (gesture conflict resolution)
    if (_hasDragged) return;

    final galaxyState = ref.read(galaxyProvider);
    final canvasTap = _screenToCanvas(details.localPosition);
    final scale = _transformationController.value.getMaxScaleOnAxis();
    final hitRadius = 30 / scale;

    final searchNodes = galaxyState.visibleNodes.isNotEmpty
        ? galaxyState.visibleNodes
        : galaxyState.nodes;

    for (final node in searchNodes) {
      final nodePos = galaxyState.nodePositions[node.id];
      if (nodePos == null) continue;
      final actualPos = nodePos + const Offset(_canvasCenter, _canvasCenter);

      if ((canvasTap - actualPos).distance <
          hitRadius + (node.importance * 2)) {
        // Long press - Navigate
        context.push('/galaxy/node/${node.id}');
        // Also select it to be consistent
        ref.read(galaxyProvider.notifier).selectNode(node.id);
        HapticFeedback.mediumImpact();
        return;
      }
    }
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
    final nodeIndex = galaxyState.nodes.indexWhere((n) => n.id == nodeId);
    if (nodeIndex == -1) return;
    final node = galaxyState.nodes[nodeIndex];

    // Get the node's canvas position (already centered to the star map canvas)
    final nodeCanvasPosition = galaxyState.nodePositions[nodeId];
    if (nodeCanvasPosition == null) return;

    // Convert to screen coordinates
    // Note: nodePositions are relative to canvas center, we need to add the center offset
    final centeredCanvasPos =
        nodeCanvasPosition + const Offset(_canvasCenter, _canvasCenter);
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

    final centeredCanvasPos =
        nodeCanvasPosition + const Offset(_canvasCenter, _canvasCenter);
    final targetScreenPos = _canvasToScreen(centeredCanvasPos);

    // Start success animation at target location
    _renderEngine.addBurst(
      screenPosition: targetScreenPos,
      screenSize: MediaQuery.of(context).size,
      strength: 1.0,
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

    // Target scale (zoom in slightly if too far out)
    final currentScale = _transformationController.value.getMaxScaleOnAxis();
    final targetScale = currentScale < 0.8 ? 1.0 : currentScale;

    // Node position in canvas coordinates (0,0 is top-left of the star map canvas)
    // Provider positions are relative to center (0,0), so add offset
    final canvasX = nodePos.dx + _canvasCenter;
    final canvasY = nodePos.dy + _canvasCenter;

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

  void _showSearchDialog() {
    showDialog(
      context: context,
      builder: (context) => GalaxySearchDialog(
        onNodeSelected: (nodeId) {
          _animateToNode(nodeId);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final galaxyState = ref.watch(galaxyProvider);
    final safePadding = MediaQuery.of(context).padding;

    return Scaffold(
      backgroundColor: DS.brandPrimary, // Deep space
      body: Stack(
        children: [
          Positioned.fill(
            child: GalaxyShaderBackground(engine: _renderEngine),
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
          GestureDetector(
            onPanStart: (details) {
              _hasDragged = true;
              _dragStartOffset = details.localPosition;
            },
            onPanUpdate: (details) {
              // Track if user actually dragged significant distance
              if (_dragStartOffset != null) {
                final distance =
                    (details.localPosition - _dragStartOffset!).distance;
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
            child: InteractiveViewer(
              transformationController: _transformationController,
              boundaryMargin: const EdgeInsets.all(2000), // Huge scroll area
              minScale: 0.1,
              maxScale: 3.0,
              constrained: false, // Infinite canvas
              child: SizedBox(
                width: _canvasSize,
                height: _canvasSize,
                child: AnimatedBuilder(
                  animation: Listenable.merge([
                    _transformationController,
                    _selectionPulseController,
                    PerformanceService.instance.currentTier,
                    PerformanceService.instance.currentDpr,
                  ]),
                  builder: (context, child) {
                    final scale = _transformationController.value
                        .getMaxScaleOnAxis();
                    // Calculate viewport for culling optimization
                    final matrix = _transformationController.value;
                    final screenSize = MediaQuery.of(context).size;
                    final inverseMatrix = matrix.clone()..invert();
                    final topLeft = MatrixUtils.transformPoint(
                        inverseMatrix, Offset.zero,);
                    final bottomRight = MatrixUtils.transformPoint(
                      inverseMatrix,
                      Offset(screenSize.width, screenSize.height),
                    );
                    final viewport =
                        Rect.fromPoints(topLeft, bottomRight).shift(
                            const Offset(
                                -_canvasCenter, -_canvasCenter,),);

                    // Convert to Compact models with centered positions for rendering
                    final compactNodes =
                        galaxyState.visibleNodes.map((node) {
                      final pos = galaxyState.nodePositions[node.id] ??
                          Offset.zero;
                      return node.toCompact(pos.dx + _canvasCenter,
                          pos.dy + _canvasCenter,);
                    }).toList();

                    final selectedHash =
                        galaxyState.selectedNodeId?.hashCode;
                    final expandedHashes = galaxyState
                        .expandedEdgeNodeIds
                        .map((id) => id.hashCode)
                        .toSet();
                    final animationHashes = galaxyState
                        .nodeAnimationProgress
                        .map((id, val) => MapEntry(id.hashCode, val));

                    final painter = StarMapPainter(
                      nodes: compactNodes,
                      edges: galaxyState.visibleEdges,
                      scale: scale,
                      performanceTier: PerformanceService.instance.currentTier.value,
                      currentDpr: PerformanceService.instance.currentDpr.value,
                      aggregationLevel: galaxyState.aggregationLevel,
                      clusters: _centerClusters(galaxyState.clusters,
                          _canvasCenter, _canvasCenter,),
                      viewport: viewport,
                      center:
                          const Offset(_canvasCenter, _canvasCenter),
                      selectedNodeIdHash: selectedHash,
                      expandedEdgeNodeIdHashes: expandedHashes,
                      nodeAnimationProgress: animationHashes,
                      selectionPulse: _selectionPulseController.value,
                    );

                    final content = Stack(
                      children: [
                        // 1. Background: Sector nebula and stars (Static, Cached)
                        const Positioned.fill(
                          child: TiledSectorBackground(
                            width: _canvasSize,
                            height: _canvasSize,
                          ),
                        ),

                        // 2. Central Flame at canvas center (Static position)
                        Positioned(
                          left: _canvasCenter - _centralFlameSize / 2,
                          top: _canvasCenter - _centralFlameSize / 2,
                          child: Opacity(
                            opacity: _isEntering ? 0.0 : 1.0,
                            child: CentralFlame(
                              intensity: galaxyState.userFlameIntensity,
                              size: _centralFlameSize,
                            ),
                          ),
                        ),

                        // 3. Star map on top (Dynamic with Culling)
                        Positioned.fill(
                          child: Opacity(
                            opacity: _isEntering ? 0.0 : 1.0,
                            child: CustomPaint(painter: painter),
                          ),
                        ),
                      ],
                    );

                    // DPR Scaling Logic
                    final devicePixelRatio = MediaQuery.of(context).devicePixelRatio;
                    final currentDpr = PerformanceService.instance.currentDpr.value;
                    final renderScale = (currentDpr / devicePixelRatio).clamp(0.1, 1.0);

                    if (renderScale > 0.99) {
                      return content;
                    }

                    // Render at lower resolution and scale up
                    return Transform.scale(
                      scale: 1 / renderScale,
                      alignment: Alignment.topLeft,
                      transformHitTests: false,
                      child: RepaintBoundary(
                        child: SizedBox(
                          width: _canvasSize * renderScale,
                          height: _canvasSize * renderScale,
                          child: FittedBox(
                            fit: BoxFit.fill,
                            child: SizedBox(
                              width: _canvasSize,
                              height: _canvasSize,
                              child: content,
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
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
                final tx = size.width / 2 - _canvasCenter * targetScale;
                final ty = size.height / 2 - _canvasCenter * targetScale;
                final targetMatrix = Matrix4.identity()
                  ..translate(tx, ty)
                  ..scale(targetScale);

                final animation = Matrix4Tween(
                  begin: startMatrix,
                  end: targetMatrix,
                ).animate(CurvedAnimation(
                    parent: controller, curve: Curves.easeOutCubic,),);

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
          if (!_isEntering && Navigator.canPop(context))
            Positioned(
              top: safePadding.top + 8,
              left: 16,
              child: IconButton(
                icon: Icon(Icons.arrow_back, color: DS.brandPrimary),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ),

          // 5.1 Search Button (Top Right)
          if (!_isEntering)
            Positioned(
              top: safePadding.top + 8,
              right: 16,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    icon: Icon(Icons.search, color: DS.brandPrimary),
                    onPressed: _showSearchDialog,
                  ),
                  IconButton(
                    icon: Icon(Icons.refresh, color: DS.brandPrimary),
                    onPressed: () {
                      HapticFeedback.selectionClick();
                      unawaited(ref
                          .read(galaxyProvider.notifier)
                          .loadGalaxy(forceRefresh: true),);
                    },
                  ),
                ],
              ),
            ),

          if (!_isEntering)
            Positioned(
              top: safePadding.top + 56,
              left: 20,
              right: 20,
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
              bottom: safePadding.bottom + 40,
              left: 20,
              child: GalaxyMiniMap(
                transformationController: _transformationController,
                canvasSize: _canvasSize,
                screenSize: MediaQuery.of(context).size,
              ),
            ),

          // 6.1 Guide Button (Above Mini Map)
          if (!_isEntering)
            Positioned(
              bottom: safePadding.bottom + 180, // Above mini map
              left: 30, // Slightly indented
              child: FloatingActionButton.small(
                heroTag: 'guide_btn',
                backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
                foregroundColor: DS.brandPrimary,
                elevation: 0,
                shape: CircleBorder(
                    side: BorderSide(
                        color: DS.brandPrimary.withValues(alpha: 0.3),),),
                child: const Icon(Icons.explore),
                onPressed: () async {
                  final nodeId =
                      await ref.read(galaxyProvider.notifier).predictNextNode();
                  if (!mounted) return;
                  if (nodeId != null) {
                    _animateToNode(nodeId);
                  } else {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('暂无推荐，请先探索一些节点吧！')),
                    );
                  }
                },
              ),
            ),

          // 6.2 Zoom Controls (Right side, above Spark button)
          if (!_isEntering)
            Positioned(
              bottom: safePadding.bottom + 120,
              right: 20,
              child: ZoomControls(
                transformationController: _transformationController,
              ),
            ),

          // 7. Spark Button (Bottom Right)
          if (!_isEntering)
            Positioned(
              bottom: safePadding.bottom + 40,
              right: 20,
              child: FloatingActionButton(
                mini: true,
                backgroundColor: DS.brandPrimary.withValues(alpha: 0.9),
                child: Icon(Icons.bolt, color: DS.brandPrimary),
                onPressed: () {
                  // Pick a random node to spark for demo
                  if (galaxyState.nodes.isNotEmpty) {
                    final node = galaxyState.nodes[
                        DateTime.now().millisecond % galaxyState.nodes.length];
                    _sparkNodeWithAnimation(node.id);
                  }
                },
              ),
            ),

          if (galaxyState.isLoading &&
              galaxyState.nodes.isEmpty &&
              !_isEntering)
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
                        padding: EdgeInsets.only(bottom: safePadding.bottom),
                        child: NodePreviewCard(
                          node: node,
                          onClose: () =>
                              ref.read(galaxyProvider.notifier).deselectNode(),
                          onTap: () => context.push('/galaxy/node/${node.id}'),
                        ),
                      );
                    },
                  )
                : const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }

  // Helper to shift logical (0,0) to center of the star map canvas
  Map<String, Offset> _centerPositions(
          Map<String, Offset> raw, double cx, double cy,) =>
      raw.map((key, value) => MapEntry(key, value + Offset(cx, cy)));

  // Helper to shift cluster positions to center of the star map canvas
  Map<String, ClusterInfo> _centerClusters(
          Map<String, ClusterInfo> raw, double cx, double cy,) =>
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
