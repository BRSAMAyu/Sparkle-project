import 'dart:async';

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/physics.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_layout_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_camera.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_gesture_handler.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class GalaxyScreen extends ConsumerStatefulWidget {
  const GalaxyScreen({super.key});

  @override
  ConsumerState<GalaxyScreen> createState() => _GalaxyScreenState();
}

class _GalaxyScreenState extends ConsumerState<GalaxyScreen>
    with TickerProviderStateMixin {
  late final GalaxyGestureHandler _gestureHandler;
  late final Ticker _flingTicker;
  late final GalaxySpatialIndex _spatialIndex;
  late final GalaxyLabelCache _labelCache;
  late final GalaxyEdgePictureCache _edgePictureCache;
  late final AnimationController _tapFeedbackController;
  late final Animation<double> _tapFeedbackAnimation;

  GalaxyGraphResponse? _graph;
  Map<String, Offset> _positions = const <String, Offset>{};
  Map<String, GalaxyNodeModel> _nodesById = const <String, GalaxyNodeModel>{};
  GalaxyCamera _camera = const GalaxyCamera(
    offset: Offset.zero,
    scale: 0.15,
    viewportSize: Size.zero,
  );
  FrictionSimulation? _flingX;
  FrictionSimulation? _flingY;
  Object? _loadError;
  String? _selectedNodeId;
  String? _draggingNodeId;
  String? _tapFeedbackNodeId;
  String? _pendingNavigationNodeId;
  GalaxyNodeModel? _previewNode;
  Offset? _previewScreenPosition;
  Size _viewportSize = Size.zero;
  bool _isLoading = true;
  bool _didFitInitialCamera = false;
  int _sceneVersion = 0;

  @override
  void initState() {
    super.initState();
    _spatialIndex = GalaxySpatialIndex();
    _labelCache = GalaxyLabelCache();
    _edgePictureCache = GalaxyEdgePictureCache();
    _gestureHandler = GalaxyGestureHandler(
      screenToWorld: (screenPoint) => _camera.screenToWorld(screenPoint),
      hitTestNode: _hitTestNode,
      onCommand: _handleGestureCommand,
    );
    _flingTicker = createTicker(_handleFlingTick);
    _tapFeedbackController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
    );
    _tapFeedbackAnimation = TweenSequence<double>([
      TweenSequenceItem<double>(
        tween: Tween<double>(
          begin: 0,
          end: 1,
        ).chain(CurveTween(curve: Curves.easeOutBack)),
        weight: 55,
      ),
      TweenSequenceItem<double>(
        tween: Tween<double>(
          begin: 1,
          end: 0,
        ).chain(CurveTween(curve: Curves.easeOut)),
        weight: 45,
      ),
    ]).animate(_tapFeedbackController)
      ..addListener(() {
        if (!mounted || _tapFeedbackNodeId == null) {
          return;
        }
        setState(() {});
      });
    _tapFeedbackController.addStatusListener(_handleTapFeedbackStatus);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      unawaited(_loadGraph());
    });
  }

  @override
  void dispose() {
    _gestureHandler.dispose();
    _labelCache.clear();
    _edgePictureCache.clear();
    _flingTicker.dispose();
    _tapFeedbackController
      ..removeStatusListener(_handleTapFeedbackStatus)
      ..dispose();
    super.dispose();
  }

  Future<void> _loadGraph() async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });

    final repository = ref.read(enhancedGalaxyRepositoryProvider);
    final result = await repository.getGraph();

    if (!mounted) {
      return;
    }

    if (result.isSuccess && result.data != null) {
      final graph = result.data!;
      final positions = _resolvePositions(graph);
      final nodesById = {
        for (final node in graph.nodes) node.id: node,
      };
      _spatialIndex.build(positions, graph.nodes);
      _labelCache.clear();
      _edgePictureCache.clear();
      setState(() {
        _graph = graph;
        _positions = positions;
        _nodesById = nodesById;
        _isLoading = false;
        _didFitInitialCamera = false;
        _sceneVersion++;
      });
      _fitCameraIfPossible(force: true);
      return;
    }

    setState(() {
      _isLoading = false;
      _loadError = result.error ?? '知识星图加载失败';
    });
  }

  Map<String, Offset> _resolvePositions(GalaxyGraphResponse graph) {
    final stablePositions = <String, Offset>{};
    for (final node in graph.nodes) {
      if (node.hasStablePosition) {
        stablePositions[node.id] = Offset(node.positionX!, node.positionY!);
      }
    }

    if (stablePositions.length == graph.nodes.length) {
      return stablePositions;
    }

    return GalaxyLayoutEngine.calculateInitialLayout(
      nodes: graph.nodes,
      edges: graph.edges,
      existingPositions: stablePositions.isEmpty ? null : stablePositions,
    );
  }

  void _fitCameraIfPossible({bool force = false}) {
    if (_viewportSize == Size.zero || _graph == null) {
      return;
    }

    if (_didFitInitialCamera && !force) {
      return;
    }

    final bounds = _computeWorldBounds();
    setState(() {
      _camera = GalaxyCamera.fitRect(
        worldBounds: bounds,
        viewportSize: _viewportSize,
      );
      _didFitInitialCamera = true;
    });
  }

  Rect _computeWorldBounds() {
    if (_positions.isEmpty) {
      return Rect.fromCircle(center: Offset.zero, radius: 240);
    }

    var minX = double.infinity;
    var minY = double.infinity;
    var maxX = double.negativeInfinity;
    var maxY = double.negativeInfinity;

    for (final position in _positions.values) {
      minX = minDouble(minX, position.dx);
      minY = minDouble(minY, position.dy);
      maxX = maxDouble(maxX, position.dx);
      maxY = maxDouble(maxY, position.dy);
    }

    return Rect.fromLTRB(minX, minY, maxX, maxY);
  }

  GalaxyNodeHit? _hitTestNode(Offset worldPoint) {
    if (_graph == null || _positions.isEmpty || _spatialIndex.size == 0) {
      return null;
    }

    final tapRadius = maxDouble(20 / _camera.scale, 16);
    return _spatialIndex.queryNearest(worldPoint, tapRadius);
  }

  void _handleGestureCommand(GalaxyGestureCommand command) {
    if (command is PanCommand) {
      _stopFling();
      setState(() {
        _cancelTapFeedbackState();
        _clearPreviewState();
        _camera = _camera.applyPan(command.delta);
      });
      return;
    }

    if (command is ZoomCommand) {
      _stopFling();
      setState(() {
        _cancelTapFeedbackState();
        _clearPreviewState();
        _camera = _camera.applyZoom(command.scaleDelta, command.focalPoint);
      });
      return;
    }

    if (command is TapCommand) {
      if (command.hit == null) {
        setState(() {
          _selectedNodeId = null;
          _cancelTapFeedbackState();
          _clearPreviewState();
        });
        return;
      }

      _startTapFeedback(command.hit!.nodeId);
      return;
    }

    if (command is LongPressCommand) {
      if (command.hit == null) {
        setState(() {
          _selectedNodeId = null;
          _clearPreviewState();
        });
        return;
      }

      final previewNode = _nodesById[command.hit!.nodeId];
      if (previewNode == null) {
        return;
      }

      setState(() {
        _cancelTapFeedbackState();
        _selectedNodeId = previewNode.id;
        _draggingNodeId = null;
        _previewNode = previewNode;
        _previewScreenPosition = _computePreviewPosition(
          anchor: _camera.worldToScreen(command.hit!.worldPosition),
        );
        _edgePictureCache.clear();
      });
      return;
    }

    if (command is DragNodeCommand) {
      final currentPosition = _positions[command.nodeId];
      if (currentPosition == null) {
        return;
      }

      final worldDelta = Offset(
        command.screenDelta.dx / _camera.scale,
        command.screenDelta.dy / _camera.scale,
      );

      setState(() {
        _cancelTapFeedbackState();
        _clearPreviewState();
        _selectedNodeId = command.nodeId;
        _draggingNodeId = command.nodeId;
        _positions = Map<String, Offset>.from(_positions)
          ..[command.nodeId] = currentPosition + worldDelta;
        _edgePictureCache.clear();
      });
      return;
    }

    if (command is FlingCommand) {
      _startFling(command.velocity);
    }
  }

  void _handleTapFeedbackStatus(AnimationStatus status) {
    if (status != AnimationStatus.completed || !mounted) {
      return;
    }

    final nodeId = _pendingNavigationNodeId;
    setState(() {
      _tapFeedbackNodeId = null;
      _pendingNavigationNodeId = null;
    });
    _tapFeedbackController.reset();

    if (nodeId != null) {
      unawaited(
        context.pushNamed(
          'knowledgeDetail',
          pathParameters: {'id': nodeId},
        ),
      );
    }
  }

  void _startTapFeedback(String nodeId) {
    setState(() {
      _clearPreviewState();
      _selectedNodeId = nodeId;
      _tapFeedbackNodeId = nodeId;
      _pendingNavigationNodeId = nodeId;
      _draggingNodeId = null;
    });
    _tapFeedbackController
      ..stop()
      ..reset();
    unawaited(_tapFeedbackController.forward());
  }

  void _cancelTapFeedbackState() {
    if (_tapFeedbackNodeId == null &&
        _pendingNavigationNodeId == null &&
        !_tapFeedbackController.isAnimating) {
      return;
    }

    _tapFeedbackController
      ..stop()
      ..reset();
    _tapFeedbackNodeId = null;
    _pendingNavigationNodeId = null;
  }

  void _clearPreviewState() {
    _previewNode = null;
    _previewScreenPosition = null;
  }

  Offset _computePreviewPosition({required Offset anchor}) {
    const cardWidth = 220.0;
    const cardHeight = 132.0;
    const gap = 16.0;
    const edgePadding = 12.0;

    var left = anchor.dx + gap;
    var top = anchor.dy + gap;

    if (_viewportSize.width - left < cardWidth) {
      left = anchor.dx - cardWidth - gap;
    }
    if (_viewportSize.height - top < cardHeight) {
      top = anchor.dy - cardHeight - gap;
    }

    left =
        left.clamp(edgePadding, _viewportSize.width - cardWidth - edgePadding);
    top =
        top.clamp(edgePadding, _viewportSize.height - cardHeight - edgePadding);
    return Offset(left, top);
  }

  void _handlePointerDown(PointerDownEvent event) {
    if (_tapFeedbackController.isAnimating ||
        _pendingNavigationNodeId != null) {
      setState(_cancelTapFeedbackState);
    }
    _gestureHandler.handlePointerDown(event);
  }

  void _handlePointerUp(PointerUpEvent event) {
    _gestureHandler.handlePointerUp(event);
    _finalizePointerSequence();
  }

  void _handlePointerCancel(PointerCancelEvent event) {
    _gestureHandler.handlePointerCancel(event);
    _finalizePointerSequence();
  }

  void _handlePointerSignal(PointerSignalEvent event) {
    if (_previewNode != null ||
        _tapFeedbackController.isAnimating ||
        _pendingNavigationNodeId != null) {
      setState(() {
        _clearPreviewState();
        _cancelTapFeedbackState();
      });
    }
    _gestureHandler.handlePointerSignal(event);
  }

  void _finalizePointerSequence() {
    final dragNodeId = _draggingNodeId;
    if (_previewNode == null && dragNodeId == null) {
      return;
    }

    final graph = _graph;
    final dragPosition = dragNodeId == null ? null : _positions[dragNodeId];
    setState(() {
      _clearPreviewState();
      if (dragNodeId != null) {
        _draggingNodeId = null;
        _sceneVersion++;
      }
    });

    if (dragNodeId != null && graph != null && dragPosition != null) {
      _spatialIndex.build(_positions, graph.nodes);
      _edgePictureCache.clear();
      unawaited(
        ref
            .read(enhancedGalaxyRepositoryProvider)
            .updateNodePosition(dragNodeId, dragPosition),
      );
    }
  }

  void _startFling(Velocity velocity) {
    _flingX = FrictionSimulation(
      0.12,
      _camera.offset.dx,
      velocity.pixelsPerSecond.dx,
    );
    _flingY = FrictionSimulation(
      0.12,
      _camera.offset.dy,
      velocity.pixelsPerSecond.dy,
    );

    if (!_flingTicker.isActive) {
      unawaited(_flingTicker.start());
    }
  }

  void _handleFlingTick(Duration elapsed) {
    final simulationX = _flingX;
    final simulationY = _flingY;
    if (simulationX == null || simulationY == null) {
      _stopFling();
      return;
    }

    final time = elapsed.inMicroseconds / Duration.microsecondsPerSecond;
    if (simulationX.isDone(time) && simulationY.isDone(time)) {
      _stopFling();
      return;
    }

    setState(() {
      _camera = _camera.copyWith(
        offset: Offset(
          simulationX.x(time),
          simulationY.x(time),
        ),
      );
    });
  }

  void _stopFling() {
    _flingX = null;
    _flingY = null;
    if (_flingTicker.isActive) {
      _flingTicker.stop();
    }
  }

  void _updateViewportSize(Size nextSize) {
    if (_viewportSize == nextSize || nextSize == Size.zero) {
      return;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || _viewportSize == nextSize || nextSize == Size.zero) {
        return;
      }

      final previousSize = _viewportSize;
      final resizedCamera = previousSize == Size.zero
          ? _camera.copyWith(viewportSize: nextSize)
          : _camera.withViewportSize(nextSize);
      final shouldFit = !_didFitInitialCamera && _graph != null;

      setState(() {
        _viewportSize = nextSize;
        _camera = shouldFit
            ? GalaxyCamera.fitRect(
                worldBounds: _computeWorldBounds(),
                viewportSize: nextSize,
              )
            : resizedCamera;
        if (shouldFit) {
          _didFitInitialCamera = true;
        }
        if (_previewNode != null && _previewScreenPosition != null) {
          final nodeId = _previewNode!.id;
          final anchor = _positions[nodeId];
          if (anchor != null) {
            _previewScreenPosition = _computePreviewPosition(
              anchor: _camera.worldToScreen(anchor),
            );
          }
        }
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final backgroundColor = isDarkMode ? Colors.black : Colors.white;

    return Scaffold(
      backgroundColor: backgroundColor,
      body: LayoutBuilder(
        builder: (context, constraints) {
          _updateViewportSize(
            Size(constraints.maxWidth, constraints.maxHeight),
          );

          if (_isLoading) {
            return _StatusPanel(
              backgroundColor: backgroundColor,
              foregroundColor: isDarkMode ? Colors.white : Colors.black,
              title: '知识星图加载中',
            );
          }

          if (_loadError != null) {
            return _StatusPanel(
              backgroundColor: backgroundColor,
              foregroundColor: isDarkMode ? Colors.white : Colors.black,
              title: '知识星图加载失败',
              message: '$_loadError',
              actionLabel: '重试',
              onAction: _loadGraph,
            );
          }

          final graph = _graph;
          if (graph == null) {
            return _StatusPanel(
              backgroundColor: backgroundColor,
              foregroundColor: isDarkMode ? Colors.white : Colors.black,
              title: '暂无星图数据',
            );
          }

          return Listener(
            behavior: HitTestBehavior.opaque,
            onPointerDown: _handlePointerDown,
            onPointerMove: _gestureHandler.handlePointerMove,
            onPointerUp: _handlePointerUp,
            onPointerCancel: _handlePointerCancel,
            onPointerSignal: _handlePointerSignal,
            child: Stack(
              children: [
                RepaintBoundary(
                  child: CustomPaint(
                    painter: StarMapPainter(
                      camera: _camera,
                      nodesById: _nodesById,
                      edges: graph.edges,
                      positions: _positions,
                      spatialIndex: _spatialIndex,
                      labelCache: _labelCache,
                      edgePictureCache: _edgePictureCache,
                      sceneVersion: _sceneVersion,
                      selectedNodeId: _selectedNodeId,
                      draggingNodeId: _draggingNodeId,
                      tapFeedbackNodeId: _tapFeedbackNodeId,
                      tapFeedbackProgress: _tapFeedbackAnimation.value,
                      isDarkMode: isDarkMode,
                    ),
                    child: const SizedBox.expand(),
                  ),
                ),
                if (_previewNode != null && _previewScreenPosition != null)
                  Positioned(
                    left: _previewScreenPosition!.dx,
                    top: _previewScreenPosition!.dy,
                    child: GalaxyNodePreviewCard(node: _previewNode!),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _StatusPanel extends StatelessWidget {
  const _StatusPanel({
    required this.backgroundColor,
    required this.foregroundColor,
    required this.title,
    this.message,
    this.actionLabel,
    this.onAction,
  });

  final Color backgroundColor;
  final Color foregroundColor;
  final String title;
  final String? message;
  final String? actionLabel;
  final Future<void> Function()? onAction;

  @override
  Widget build(BuildContext context) => ColoredBox(
        color: backgroundColor,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: foregroundColor,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                  textAlign: TextAlign.center,
                ),
                if (message != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    message!,
                    style: TextStyle(
                      color: foregroundColor.withValues(alpha: 0.72),
                      fontSize: 14,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
                if (actionLabel != null && onAction != null) ...[
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () => unawaited(onAction!()),
                    child: Text(actionLabel!),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
}

double minDouble(double a, double b) => a < b ? a : b;

double maxDouble(double a, double b) => a > b ? a : b;
