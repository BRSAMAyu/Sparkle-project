import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_force_engine.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class KnowledgeTheaterGraph extends StatefulWidget {
  const KnowledgeTheaterGraph({
    required this.nodes,
    required this.edges,
    this.focusNodeIds = const [],
    super.key,
  });

  final List<TheaterGraphNode> nodes;
  final List<TheaterGraphEdge> edges;
  final List<String> focusNodeIds;

  @override
  State<KnowledgeTheaterGraph> createState() => _KnowledgeTheaterGraphState();
}

class _KnowledgeTheaterGraphState extends State<KnowledgeTheaterGraph> {
  late final GalaxyForceEngine _forceEngine;
  late final GalaxySpatialIndex _spatialIndex;
  Timer? _timer;
  Map<String, Offset> _positions = const {};
  Map<String, Set<String>> _adjacency = const {};
  Map<String, double> _edgeStrengths = const {};

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
    _rebuildLayout();
  }

  @override
  void didUpdateWidget(covariant KnowledgeTheaterGraph oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.nodes != widget.nodes ||
        oldWidget.edges != widget.edges ||
        oldWidget.focusNodeIds != widget.focusNodeIds) {
      _rebuildLayout();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
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
  Widget build(BuildContext context) => ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: AspectRatio(
          aspectRatio: 1.3,
          child: CustomPaint(
            painter: _KnowledgeTheaterPainter(
              nodes: widget.nodes,
              edges: widget.edges,
              positions: _positions,
              focusNodeIds: widget.focusNodeIds.toSet(),
            ),
          ),
        ),
      );
}

class _KnowledgeTheaterPainter extends CustomPainter {
  const _KnowledgeTheaterPainter({
    required this.nodes,
    required this.edges,
    required this.positions,
    required this.focusNodeIds,
  });

  final List<TheaterGraphNode> nodes;
  final List<TheaterGraphEdge> edges;
  final Map<String, Offset> positions;
  final Set<String> focusNodeIds;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final background = Paint()
      ..shader = const LinearGradient(
        colors: [Color(0xFF0B1220), Color(0xFF14243B), Color(0xFF1C3354)],
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
      canvas.drawPath(
        path,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = isFocused ? 3.2 : (1.2 + edge.strength * 1.8)
          ..color =
              (isFocused ? const Color(0xFFF7C873) : const Color(0xFF7BA6FF))
                  .withValues(alpha: isFocused ? 0.92 : 0.38),
      );
    }

    for (final node in nodes) {
      final world = positions[node.id];
      if (world == null) {
        continue;
      }
      final point = center + world;
      final isFocused = focusNodeIds.isEmpty || focusNodeIds.contains(node.id);
      final color = _riskColor(node.riskLevel);
      final radius = 18.0 +
          ((node.predictedMastery - node.currentMastery) / 18)
              .clamp(0, 8)
              .toDouble();

      canvas
        ..drawCircle(
          point,
          radius + 10,
          Paint()..color = color.withValues(alpha: isFocused ? 0.24 : 0.08),
        )
        ..drawCircle(
          point,
          radius,
          Paint()
            ..shader = RadialGradient(
              colors: [Colors.white, color],
            ).createShader(
              Rect.fromCircle(center: point, radius: radius),
            ),
        );

      final textPainter = TextPainter(
        text: TextSpan(
          text: node.name,
          style: TextStyle(
            color: Colors.white.withValues(alpha: isFocused ? 0.96 : 0.72),
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
        maxLines: 1,
        ellipsis: '…',
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: 82);
      textPainter.paint(
        canvas,
        Offset(point.dx - textPainter.width / 2, point.dy + radius + 6),
      );
    }
  }

  Color _riskColor(String level) {
    switch (level) {
      case 'high':
        return const Color(0xFFFF7B54);
      case 'medium':
        return const Color(0xFFFFC857);
      default:
        return const Color(0xFF59D98E);
    }
  }

  @override
  bool shouldRepaint(covariant _KnowledgeTheaterPainter oldDelegate) =>
      oldDelegate.nodes != nodes ||
      oldDelegate.edges != edges ||
      oldDelegate.positions != positions ||
      oldDelegate.focusNodeIds != focusNodeIds;
}
