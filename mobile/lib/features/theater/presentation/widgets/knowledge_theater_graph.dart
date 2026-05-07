import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_force_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class KnowledgeTheaterGraph extends StatefulWidget {
  const KnowledgeTheaterGraph({
    required this.nodes,
    required this.edges,
    this.focusNodeIds = const <String>[],
    this.routeNodeIds = const <String>[],
    this.expandToFill = false,
    this.selectedNodeId,
    this.onNodeTap,
    this.onEdgeLongPress,
    super.key,
  });

  final List<TheaterGraphNode> nodes;
  final List<TheaterGraphEdge> edges;
  final List<String> focusNodeIds;
  final List<String> routeNodeIds;
  final bool expandToFill;
  final String? selectedNodeId;
  final ValueChanged<TheaterGraphNode>? onNodeTap;
  final void Function(TheaterGraphEdge edge, Offset globalPosition)?
      onEdgeLongPress;

  @override
  State<KnowledgeTheaterGraph> createState() => _KnowledgeTheaterGraphState();
}

class _KnowledgeTheaterGraphState extends State<KnowledgeTheaterGraph>
    with SingleTickerProviderStateMixin {
  late final GalaxyForceEngine _forceEngine;
  late final GalaxySpatialIndex _spatialIndex;
  late final AnimationController _pulseController;
  late final TransformationController _transformationController;
  Timer? _timer;
  Map<String, Offset> _positions = const <String, Offset>{};
  Map<String, Set<String>> _adjacency = const <String, Set<String>>{};
  Map<String, double> _edgeStrengths = const <String, double>{};
  Matrix4 _defaultTransform = Matrix4.identity();
  Size _viewportSize = Size.zero;
  Size _canvasSize = Size.zero;
  bool _hasAdjustedViewport = false;

  @override
  void initState() {
    super.initState();
    _forceEngine = GalaxyForceEngine(
      springRestLength: 112,
      repulsionRadius: 240,
      repulsionK: 9000,
      centerGravity: 0.002,
    );
    _spatialIndex = GalaxySpatialIndex();
    _transformationController = TransformationController();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    );
    unawaited(_pulseController.repeat(reverse: true));
    _rebuildLayout();
  }

  @override
  void didUpdateWidget(covariant KnowledgeTheaterGraph oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.nodes != widget.nodes ||
        oldWidget.edges != widget.edges ||
        oldWidget.focusNodeIds != widget.focusNodeIds ||
        oldWidget.routeNodeIds != widget.routeNodeIds ||
        oldWidget.selectedNodeId != widget.selectedNodeId) {
      _rebuildLayout();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _transformationController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  void _rebuildLayout() {
    _timer?.cancel();
    final nodes = widget.nodes;
    final angleStep = nodes.isEmpty ? 0 : (math.pi * 2) / nodes.length;
    final nextPositions = <String, Offset>{};
    for (var index = 0; index < nodes.length; index++) {
      final angle = angleStep * index;
      nextPositions[nodes[index].id] = Offset(
        math.cos(angle) * 120,
        math.sin(angle) * 120,
      );
    }

    final adjacency = <String, Set<String>>{};
    final strengths = <String, double>{};
    for (final edge in widget.edges) {
      adjacency.putIfAbsent(edge.sourceId, () => <String>{}).add(edge.targetId);
      adjacency.putIfAbsent(edge.targetId, () => <String>{}).add(edge.sourceId);
      strengths[
              GalaxyForceEngine.edgeStrengthKey(edge.sourceId, edge.targetId)] =
          0.85 + edge.strength;
      strengths[
              GalaxyForceEngine.edgeStrengthKey(edge.targetId, edge.sourceId)] =
          0.85 + edge.strength;
    }

    _positions = nextPositions;
    _adjacency = adjacency;
    _edgeStrengths = strengths;
    _tickLayout();
    _timer = Timer.periodic(const Duration(milliseconds: 20), (_) {
      _tickLayout();
    });
  }

  void _tickLayout() {
    final currentPositions = _positions;
    if (currentPositions.isEmpty) {
      return;
    }

    _spatialIndex
      ..clear()
      ..build(
        currentPositions,
        widget.nodes
            .map(
              (node) => GalaxyNodeModel(
                id: node.id,
                name: node.name,
                importance: 2,
                sector: SectorEnum.wisdom,
                isUnlocked: true,
                masteryScore: node.currentMastery.round(),
              ),
            )
            .toList(),
      );

    final tick = _forceEngine.tick(
      positions: currentPositions,
      adjacency: _adjacency,
      edgeStrengths: _edgeStrengths,
      spatialIndex: _spatialIndex,
      viewport: const Rect.fromLTWH(-280, -240, 560, 480),
    );
    if (!mounted) {
      return;
    }
    setState(() => _positions = tick.positions);
    if (tick.isSettled) {
      _timer?.cancel();
    }
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final viewportSize = Size(constraints.maxWidth, constraints.maxHeight);
          final canvasSize = _resolveCanvasSize(viewportSize);
          _syncViewport(canvasSize: canvasSize, viewportSize: viewportSize);
          final stage = RepaintBoundary(
            child: AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) => SizedBox(
                width: canvasSize.width,
                height: canvasSize.height,
                child: CustomPaint(
                  painter: _KnowledgeTheaterPainter(
                  nodes: widget.nodes,
                  edges: widget.edges,
                  positions: _positions,
                  focusNodeIds: widget.focusNodeIds.toSet(),
                  routeNodeIds: widget.routeNodeIds.toSet(),
                  selectedNodeId: widget.selectedNodeId,
                  pulseValue: _pulseController.value,
                  backgroundColors: <Color>[
                    Theme.of(context)
                        .colorScheme
                        .surfaceContainerHighest
                        .withValues(alpha: 0.98),
                    Theme.of(context)
                        .colorScheme
                        .surfaceContainerHigh
                        .withValues(alpha: 0.92),
                    Theme.of(context).colorScheme.surface.withValues(alpha: 0.98),
                  ],
                  edgeColor: DS.info,
                  focusEdgeColor: DS.warning,
                  lowRiskColor: DS.success,
                  mediumRiskColor: DS.warning,
                  highRiskColor: DS.error,
                  labelColor: Theme.of(context).colorScheme.onSurface,
                ),
              ),
            ),
          ),
          );
          return ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: InteractiveViewer(
              transformationController: _transformationController,
              constrained: false,
              boundaryMargin: const EdgeInsets.all(240),
              minScale: 0.78,
              maxScale: 2.2,
              onInteractionStart: (_) => _hasAdjustedViewport = true,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTapUp: (details) =>
                    _handleTapUp(details.localPosition, canvasSize),
                onLongPressStart: (details) => _handleLongPressStart(
                  details.localPosition,
                  details.globalPosition,
                  canvasSize,
                ),
                onDoubleTap: _resetViewport,
                child: widget.expandToFill
                    ? SizedBox(
                        width: canvasSize.width,
                        height: canvasSize.height,
                        child: stage,
                      )
                    : AspectRatio(
                        aspectRatio: 1.3,
                        child: stage,
                      ),
              ),
            ),
          );
        },
      );

  Size _resolveCanvasSize(Size viewportSize) => Size(
        math.max(920, viewportSize.width * 1.7),
        math.max(720, viewportSize.height * 1.45),
      );

  void _syncViewport({
    required Size canvasSize,
    required Size viewportSize,
  }) {
    if (_canvasSize == canvasSize && _viewportSize == viewportSize) {
      return;
    }
    _canvasSize = canvasSize;
    _viewportSize = viewportSize;
    _defaultTransform = Matrix4.identity();
    _defaultTransform.setTranslationRaw(
      (viewportSize.width - canvasSize.width) / 2,
      (viewportSize.height - canvasSize.height) / 2,
      0,
    );
    if (_hasAdjustedViewport) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      _transformationController.value = Matrix4.copy(_defaultTransform);
    });
  }

  void _handleTapUp(Offset localPosition, Size size) {
    final node = _hitTestNode(localPosition, size);
    if (node == null) {
      return;
    }
    widget.onNodeTap?.call(node);
  }

  void _handleLongPressStart(
    Offset localPosition,
    Offset globalPosition,
    Size size,
  ) {
    final edge = _hitTestEdge(localPosition, size);
    if (edge == null) {
      return;
    }
    widget.onEdgeLongPress?.call(edge, globalPosition);
  }

  TheaterGraphNode? _hitTestNode(Offset localPosition, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    for (final node in widget.nodes.reversed) {
      final world = _positions[node.id];
      if (world == null) {
        continue;
      }
      final point = _transformPoint(center, world);
      final radius = _nodeRadius(node);
      if ((localPosition - point).distance <= radius + 14) {
        return node;
      }
    }
    return null;
  }

  TheaterGraphEdge? _hitTestEdge(Offset localPosition, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    TheaterGraphEdge? bestEdge;
    var bestDistance = double.infinity;
    for (final edge in widget.edges) {
      final source = _positions[edge.sourceId];
      final target = _positions[edge.targetId];
      if (source == null || target == null) {
        continue;
      }
      final p1 = _transformPoint(center, source);
      final p2 = _transformPoint(center, target);
      final control = Offset(
        (p1.dx + p2.dx) / 2 + (p2.dy - p1.dy) * 0.12,
        (p1.dy + p2.dy) / 2 + (p1.dx - p2.dx) * 0.12,
      );
      final distance = _distanceToQuadraticBezier(
        point: localPosition,
        start: p1,
        control: control,
        end: p2,
      );
      if (distance < bestDistance) {
        bestDistance = distance;
        bestEdge = edge;
      }
    }
    return bestDistance <= 18 ? bestEdge : null;
  }

  double _distanceToQuadraticBezier({
    required Offset point,
    required Offset start,
    required Offset control,
    required Offset end,
  }) {
    var best = double.infinity;
    for (var index = 0; index <= 24; index++) {
      final t = index / 24;
      final sample = _quadraticPoint(start, control, end, t);
      best = math.min(best, (sample - point).distance);
    }
    return best;
  }

  Offset _quadraticPoint(Offset start, Offset control, Offset end, double t) {
    final oneMinusT = 1 - t;
    return Offset(
      (oneMinusT * oneMinusT * start.dx) +
          (2 * oneMinusT * t * control.dx) +
          (t * t * end.dx),
      (oneMinusT * oneMinusT * start.dy) +
          (2 * oneMinusT * t * control.dy) +
          (t * t * end.dy),
    );
  }

  double _nodeRadius(TheaterGraphNode node) =>
      (node.sourceType == 'hybrid_reference' ? 14.0 : 18.0) +
      ((node.predictedMastery - node.currentMastery) / 18)
          .clamp(0, node.sourceType == 'hybrid_reference' ? 5 : 8)
          .toDouble();

  Offset _transformPoint(Offset center, Offset world) => center + world;

  void _resetViewport() {
    setState(() {
      _hasAdjustedViewport = false;
      _transformationController.value = Matrix4.copy(_defaultTransform);
    });
  }
}

class _KnowledgeTheaterPainter extends CustomPainter {
  const _KnowledgeTheaterPainter({
    required this.nodes,
    required this.edges,
    required this.positions,
    required this.focusNodeIds,
    required this.routeNodeIds,
    required this.selectedNodeId,
    required this.pulseValue,
    required this.backgroundColors,
    required this.edgeColor,
    required this.focusEdgeColor,
    required this.lowRiskColor,
    required this.mediumRiskColor,
    required this.highRiskColor,
    required this.labelColor,
  });

  final List<TheaterGraphNode> nodes;
  final List<TheaterGraphEdge> edges;
  final Map<String, Offset> positions;
  final Set<String> focusNodeIds;
  final Set<String> routeNodeIds;
  final String? selectedNodeId;
  final double pulseValue;
  final List<Color> backgroundColors;
  final Color edgeColor;
  final Color focusEdgeColor;
  final Color lowRiskColor;
  final Color mediumRiskColor;
  final Color highRiskColor;
  final Color labelColor;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final background = Paint()
      ..shader = LinearGradient(
        colors: backgroundColors,
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, background);

    for (final edge in edges) {
      final source = positions[edge.sourceId];
      final target = positions[edge.targetId];
      if (source == null || target == null) {
        continue;
      }
      final p1 = center + source;
      final p2 = center + target;
      final control = Offset(
        (p1.dx + p2.dx) / 2 + (p2.dy - p1.dy) * 0.12,
        (p1.dy + p2.dy) / 2 + (p1.dx - p2.dx) * 0.12,
      );
      final path = Path()
        ..moveTo(p1.dx, p1.dy)
        ..quadraticBezierTo(control.dx, control.dy, p2.dx, p2.dy);
      final isFocused = focusNodeIds.contains(edge.sourceId) &&
          focusNodeIds.contains(edge.targetId);
      final isRouteEdge = routeNodeIds.contains(edge.sourceId) &&
          routeNodeIds.contains(edge.targetId);
      canvas.drawPath(
        path,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = isFocused
              ? 3.2
              : (isRouteEdge ? 2.6 : (1.0 + edge.strength * 1.6))
          ..color = (isFocused
                  ? focusEdgeColor
                  : (isRouteEdge ? labelColor : edgeColor))
              .withValues(
            alpha: _edgeAlpha(
              edge,
              isFocused: isFocused,
              isRouteEdge: isRouteEdge,
            ),
          ),
      );
    }

    for (final node in nodes) {
      final world = positions[node.id];
      if (world == null) {
        continue;
      }
      final point = center + world;
      final isFocused = focusNodeIds.isEmpty || focusNodeIds.contains(node.id);
      final isRouteNode = routeNodeIds.contains(node.id);
      final isSelected = node.id == selectedNodeId;
      final color = _riskColor(node.riskLevel);
      final masteryColor = Color.lerp(
            highRiskColor.withValues(alpha: 0.88),
            lowRiskColor.withValues(alpha: 0.94),
            (node.predictedMastery / 100).clamp(0.0, 1.0),
          ) ??
          color;
      final radius = (node.sourceType == 'hybrid_reference' ? 14.0 : 18.0) +
          ((node.predictedMastery - node.currentMastery) / 18)
              .clamp(0, node.sourceType == 'hybrid_reference' ? 5 : 8)
              .toDouble();
      final pulseRadius = radius + (isSelected ? 14 : 8) + (pulseValue * 8);
      final pulseAlpha = isSelected
          ? (0.22 + (pulseValue * 0.18))
          : (isFocused ? (0.16 + (pulseValue * 0.14)) : 0.06);

      canvas
        ..drawCircle(
          point,
          pulseRadius,
          Paint()..color = masteryColor.withValues(alpha: pulseAlpha),
        )
        ..drawCircle(
          point,
          radius + (isSelected ? 14 : 10),
          Paint()
            ..color = masteryColor.withValues(
              alpha: isSelected
                  ? 0.26
                  : (isFocused ? 0.24 : (isRouteNode ? 0.16 : 0.08)),
            ),
        )
        ..drawCircle(
          point,
          radius,
          Paint()
            ..shader = RadialGradient(
              colors: <Color>[Colors.white, masteryColor],
            ).createShader(
              Rect.fromCircle(center: point, radius: radius),
            ),
        );

      if (isSelected || isRouteNode) {
        canvas.drawCircle(
          point,
          radius + 3,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = isSelected ? 2.4 : 1.4
            ..color = labelColor.withValues(alpha: isSelected ? 0.72 : 0.34),
        );
      }

      if (node.sourceType == 'graph_explicit') {
        canvas.drawCircle(
          point,
          radius + 6,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.4
            ..color = labelColor.withValues(alpha: 0.28),
        );
      } else if (node.sourceType == 'hybrid_reference') {
        canvas.drawCircle(
          point,
          radius + 5,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.2
            ..color = edgeColor.withValues(alpha: 0.28),
        );
      }

      if (node.candidateStatus == 'pending_review') {
        canvas.drawCircle(
          point,
          radius + 8,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.6
            ..color = mediumRiskColor.withValues(alpha: 0.34),
        );
      }

      final textPainter = TextPainter(
        text: TextSpan(
          text: node.name,
          style: TextStyle(
            color: labelColor.withValues(
              alpha: isSelected ? 1 : (isFocused ? 0.96 : 0.72),
            ),
            fontSize: isSelected ? 11.5 : 11,
            fontWeight: isSelected ? DS.fontWeightBold : DS.fontWeightSemibold,
            fontFamilyFallback: sparkleFontFallback,
          ),
        ),
        maxLines: 1,
        ellipsis: '…',
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: 92);
      textPainter.paint(
        canvas,
        Offset(point.dx - textPainter.width / 2, point.dy + radius + 6),
      );
    }
  }

  Color _riskColor(String level) {
    switch (level) {
      case 'high':
        return highRiskColor;
      case 'medium':
        return mediumRiskColor;
      default:
        return lowRiskColor;
    }
  }

  double _edgeAlpha(
    TheaterGraphEdge edge, {
    required bool isFocused,
    required bool isRouteEdge,
  }) {
    if (isFocused) {
      return 0.92;
    }
    if (isRouteEdge) {
      return 0.62;
    }
    if (edge.sourceType == 'hybrid_reference') {
      return 0.22;
    }
    return edge.sourceType == 'graph_explicit' ? 0.44 : 0.34;
  }

  @override
  bool shouldRepaint(covariant _KnowledgeTheaterPainter oldDelegate) =>
      oldDelegate.nodes != nodes ||
      oldDelegate.edges != edges ||
      oldDelegate.positions != positions ||
      oldDelegate.focusNodeIds != focusNodeIds ||
      oldDelegate.routeNodeIds != routeNodeIds ||
      oldDelegate.selectedNodeId != selectedNodeId ||
      oldDelegate.pulseValue != pulseValue;
}
