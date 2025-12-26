import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/presentation/widgets/galaxy/flame_core.dart';
import 'package:sparkle/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/presentation/widgets/galaxy/energy_particle.dart';
import 'package:sparkle/presentation/widgets/galaxy/star_success_animation.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_background_painter.dart';

class GalaxyScreen extends ConsumerStatefulWidget {
  const GalaxyScreen({super.key});

  @override
  ConsumerState<GalaxyScreen> createState() => _GalaxyScreenState();
}

class _GalaxyScreenState extends ConsumerState<GalaxyScreen> {
  final TransformationController _transformationController = TransformationController();

  // Active animations
  final List<_ActiveEnergyTransfer> _activeEnergyTransfers = [];
  final List<_ActiveSuccessAnimation> _activeSuccessAnimations = [];

  // Canvas constants
  static const double _canvasSize = 4000.0;
  static const double _canvasCenter = 2000.0;
  static const double _flameCoreSize = 200.0;

  // Track last scale to avoid unnecessary updates
  double _lastScale = 1.0;

  @override
  void initState() {
    super.initState();

    // Listen to transformation changes for scale updates
    _transformationController.addListener(_onTransformChanged);

    // Defer initial centering until we know screen size (in build) or post frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final size = MediaQuery.of(context).size;
      // Center the 4000x4000 canvas
      final x = -_canvasCenter + size.width / 2;
      final y = -_canvasCenter + size.height / 2;
      _transformationController.value = Matrix4.identity()
        ..setTranslationRaw(x, y, 0);

      ref.read(galaxyProvider.notifier).loadGalaxy();
    });
  }

  @override
  void dispose() {
    _transformationController.removeListener(_onTransformChanged);
    _transformationController.dispose();
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
  }

  /// Convert a canvas position (in the 4000x4000 space) to screen coordinates
  Offset _canvasToScreen(Offset canvasPosition) {
    final matrix = _transformationController.value;
    // Apply the transformation matrix to get screen position
    final transformed = MatrixUtils.transformPoint(matrix, canvasPosition);
    return transformed;
  }

  /// Get the screen center position (where the flame core is displayed)
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
    final galaxyState = ref.read(galaxyProvider);
    if (galaxyState.nodes.isEmpty) return;

    // Convert screen tap to canvas coordinates
    final canvasTap = _screenToCanvas(details.localPosition);

    // Get current scale for dynamic hit radius
    final scale = _transformationController.value.getMaxScaleOnAxis();
    final hitRadius = 30 / scale; // Larger hit area when zoomed out

    // Find the tapped node
    for (final node in galaxyState.nodes) {
      final nodePos = galaxyState.nodePositions[node.id];
      if (nodePos == null) continue;

      // Add canvas center offset to get actual position
      final actualPos = nodePos + const Offset(_canvasCenter, _canvasCenter);
      final distance = (canvasTap - actualPos).distance;

      if (distance < hitRadius + (node.importance * 2)) {
        // Node tapped - navigate to detail screen
        context.push('/galaxy/node/${node.id}');
        return;
      }
    }
  }

  /// Parse a hex color string to Color
  Color _parseColor(String? hex) {
    if (hex == null || hex.isEmpty) return Colors.white;
    try {
      return Color(int.parse(hex.replaceFirst('#', '0xFF')));
    } catch (e) {
      return Colors.white;
    }
  }

  /// Start the energy transfer animation to a specific node
  void _sparkNodeWithAnimation(String nodeId) {
    final galaxyState = ref.read(galaxyProvider);
    final node = galaxyState.nodes.firstWhere(
      (n) => n.id == nodeId,
      orElse: () => throw Exception('Node not found'),
    );

    // Get the node's canvas position (already centered to 4000x4000)
    final nodeCanvasPosition = galaxyState.nodePositions[nodeId];
    if (nodeCanvasPosition == null) return;

    // Convert to screen coordinates
    // Note: nodePositions are relative to canvas center, we need to add the center offset
    final centeredCanvasPos = nodeCanvasPosition + const Offset(_canvasCenter, _canvasCenter);
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
  void _onEnergyTransferComplete(_ActiveEnergyTransfer transfer) {
    // Trigger the actual data update
    ref.read(galaxyProvider.notifier).sparkNode(transfer.nodeId);

    // Remove transfer animation
    setState(() {
      _activeEnergyTransfers.remove(transfer);
    });

    // Get updated target position (in case view shifted slightly)
    final galaxyState = ref.read(galaxyProvider);
    final nodeCanvasPosition = galaxyState.nodePositions[transfer.nodeId];
    if (nodeCanvasPosition == null) return;

    final centeredCanvasPos = nodeCanvasPosition + const Offset(_canvasCenter, _canvasCenter);
    final targetScreenPos = _canvasToScreen(centeredCanvasPos);

    // Start success animation at target location
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

    // Show feedback
    final node = galaxyState.nodes.firstWhere(
      (n) => n.id == transfer.nodeId,
      orElse: () => throw Exception('Node not found'),
    );
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

  @override
  Widget build(BuildContext context) {
    final galaxyState = ref.watch(galaxyProvider);

    return Scaffold(
      backgroundColor: Colors.black, // Deep space
      body: Stack(
        children: [
          // 1. Star Map (Interactive) with FlameCore inside canvas
          GestureDetector(
            onTapUp: _handleTapUp,
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
                  animation: _transformationController,
                  builder: (context, child) {
                    final scale = _transformationController.value.getMaxScaleOnAxis();
                    return Stack(
                      children: [
                        // Background: Sector nebula visualization
                        Positioned.fill(
                          child: CustomPaint(
                            painter: SectorBackgroundPainter(
                              canvasSize: _canvasSize,
                            ),
                          ),
                        ),
                        // FlameCore at canvas center (moves with pan/zoom)
                        Positioned(
                          left: _canvasCenter - _flameCoreSize / 2,
                          top: _canvasCenter - _flameCoreSize / 2,
                          child: SizedBox(
                            width: _flameCoreSize,
                            height: _flameCoreSize,
                            child: FlameCore(
                              intensity: galaxyState.userFlameIntensity,
                            ),
                          ),
                        ),
                        // Star map on top
                        Positioned.fill(
                          child: CustomPaint(
                            painter: StarMapPainter(
                              nodes: galaxyState.nodes,
                              positions: _centerPositions(galaxyState.nodePositions, _canvasCenter, _canvasCenter),
                              scale: scale,
                              aggregationLevel: galaxyState.aggregationLevel,
                              clusters: _centerClusters(galaxyState.clusters, _canvasCenter, _canvasCenter),
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ),
          ),

          // 3. Energy Transfer Animations Layer (above everything except UI)
          ..._activeEnergyTransfers.map(
            (transfer) => Positioned.fill(
              child: IgnorePointer(
                child: EnergyTransferAnimation(
                  key: transfer.key,
                  sourcePosition: transfer.sourcePosition,
                  targetPosition: transfer.targetPosition,
                  targetColor: transfer.targetColor,
                  duration: const Duration(milliseconds: 800),
                  onComplete: () => _onEnergyTransferComplete(transfer),
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
            top: 40,
            left: 20,
            child: IconButton(
              icon: const Icon(Icons.arrow_back, color: Colors.white),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ),

          // 6. Spark Button (Bottom Right)
          Positioned(
            bottom: 40,
            right: 20,
            child: FloatingActionButton(
              mini: true,
              backgroundColor: AppDesignTokens.primaryBase.withValues(alpha: 0.9),
              child: const Icon(Icons.bolt, color: Colors.white),
              onPressed: () {
                // Pick a random node to spark for demo
                if (galaxyState.nodes.isNotEmpty) {
                  final node = galaxyState.nodes[DateTime.now().millisecond % galaxyState.nodes.length];
                  _sparkNodeWithAnimation(node.id);
                }
              },
            ),
          ),

          if (galaxyState.isLoading)
            const Center(child: CircularProgressIndicator()),
        ],
      ),
    );
  }

  // Helper to shift logical (0,0) to center of the 4000x4000 canvas
  Map<String, Offset> _centerPositions(Map<String, Offset> raw, double cx, double cy) {
    return raw.map((key, value) => MapEntry(key, value + Offset(cx, cy)));
  }

  // Helper to shift cluster positions to center of the 4000x4000 canvas
  Map<String, ClusterInfo> _centerClusters(Map<String, ClusterInfo> raw, double cx, double cy) {
    return raw.map((key, cluster) => MapEntry(
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
    ),);
  }
}

/// Data class for active energy transfer animation
class _ActiveEnergyTransfer {
  final Key key;
  final String nodeId;
  final Offset sourcePosition;
  final Offset targetPosition;
  final Color targetColor;

  _ActiveEnergyTransfer({
    required this.key,
    required this.nodeId,
    required this.sourcePosition,
    required this.targetPosition,
    required this.targetColor,
  });
}

/// Data class for active success animation
class _ActiveSuccessAnimation {
  final Key key;
  final Offset position;
  final Color color;

  _ActiveSuccessAnimation({
    required this.key,
    required this.position,
    required this.color,
  });
}
