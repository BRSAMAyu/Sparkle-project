import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/core/services/text_cache.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';
import 'package:sparkle/shared/models/compact_knowledge_node.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';

/// Pre-processed node data for efficient painting
class ProcessedNode {
  ProcessedNode({
    required this.node,
    required this.color,
    required this.radius,
    required this.position,
  });
  final CompactKnowledgeNode node;
  final Color color;
  final double radius;
  final Offset position;
}

/// Pre-processed edge data for efficient painting
class ProcessedEdge {
  ProcessedEdge({
    required this.edge,
    required this.start,
    required this.end,
    required this.startColor,
    required this.endColor,
    required this.distance,
    required this.strokeWidth,
  });
  final GalaxyEdgeModel edge;
  final Offset start;
  final Offset end;
  final Color startColor;
  final Color endColor;
  final double distance;
  final double strokeWidth;
}

/// Relation style configuration
class _RelationStyle {
  const _RelationStyle({
    required this.color,
    this.dashLength = 0,
    this.isDashed = false,
    this.baseWidth = 1.5,
  });
  final Color color;
  final double dashLength;
  final bool isDashed;
  final double baseWidth;

  static _RelationStyle forType(EdgeRelationType type) {
    switch (type) {
      case EdgeRelationType.prerequisite:
        return _RelationStyle(color: DS.info, baseWidth: 2.0);
      case EdgeRelationType.derived:
        return _RelationStyle(color: DS.success, baseWidth: 1.8);
      case EdgeRelationType.related:
        return _RelationStyle(
            color: DS.warning, isDashed: true, dashLength: 8, baseWidth: 1.2,);
      case EdgeRelationType.similar:
        return _RelationStyle(
            color: DS.taskReflection,
            isDashed: true,
            dashLength: 4,
            baseWidth: 1.0,);
      case EdgeRelationType.contrast:
        return _RelationStyle(color: DS.error, isDashed: true, dashLength: 12);
      case EdgeRelationType.application:
        return _RelationStyle(color: DS.taskPlanning);
      case EdgeRelationType.example:
        return _RelationStyle(
            color: DS.textSecondary,
            isDashed: true,
            dashLength: 6,
            baseWidth: 1.0,);
      case EdgeRelationType.parentChild:
        return _RelationStyle(color: DS.brandPrimary, baseWidth: 1.8);
    }
  }
}

class StarMapPainter extends CustomPainter {
  StarMapPainter({
    required this.nodes,
    this.edges = const [],
    this.scale = 1.0,
    this.performanceTier = PerformanceTier.high,
    this.currentDpr = 3.0, // Default to high if not provided
    this.aggregationLevel = AggregationLevel.full,
    this.clusters = const {},
    this.viewport,
    this.center = Offset.zero,
    this.selectedNodeIdHash,
    this.expandedEdgeNodeIdHashes = const {},
    this.nodeAnimationProgress = const {},
    this.selectionPulse = 0.0,
    this.beamFlow = 0.0,
  }) {
    _preprocessData();
  }

  final List<CompactKnowledgeNode> nodes;
  final List<GalaxyEdgeModel> edges;
  final double scale;
  final PerformanceTier performanceTier;
  final double currentDpr;
  final AggregationLevel aggregationLevel;
  final Map<String, ClusterInfo> clusters;
  final Rect? viewport;
  final Offset center;
  final int? selectedNodeIdHash;
  final Set<int> expandedEdgeNodeIdHashes;
  final Map<int, double> nodeAnimationProgress;
  final double selectionPulse;
  final double beamFlow;

  // LOD Thresholds
  static const double _lod0Limit = 0.2;
  static const double _lod1Limit = 0.4;
  static const double _lod2Limit = 0.6;
  static const double _lod3Limit = 0.8;

  static final SmartCache<int, List<ProcessedNode>> _nodeCache =
      SmartCache(maxSize: 10);
  static final SmartCache<int, List<ProcessedEdge>> _edgeCache =
      SmartCache(maxSize: 10);
  static final SmartCache<int, Map<int, Color>> _colorCacheStorage =
      SmartCache(maxSize: 10);
  static final SmartCache<int, Map<int, Offset>> _positionCacheStorage =
      SmartCache(maxSize: 10);
  static final BatchTextRenderer _textRenderer = BatchTextRenderer();

  late final List<ProcessedNode> _processedNodes;
  late final List<ProcessedEdge> _processedEdges;
  late final Map<int, Color> _colorCache;
  late final Map<int, Offset> _positionCache;

  int _generateCacheKey() => Object.hash(
        identityHashCode(nodes),
        identityHashCode(edges),
        nodes.length,
        edges.length,
        nodes.isNotEmpty ? nodes.first.x : 0,
        nodes.length > 10 ? nodes[nodes.length ~/ 2].y : 0,
      );

  void _preprocessData() {
    final cacheKey = _generateCacheKey();

    final cachedNodes = _nodeCache.get(cacheKey);
    final cachedEdges = _edgeCache.get(cacheKey);
    final cachedColors = _colorCacheStorage.get(cacheKey);
    final cachedPositions = _positionCacheStorage.get(cacheKey);

    if (cachedNodes != null &&
        cachedEdges != null &&
        cachedColors != null &&
        cachedPositions != null) {
      _processedNodes = cachedNodes;
      _processedEdges = cachedEdges;
      _colorCache = cachedColors;
      _positionCache = cachedPositions;
      return;
    }

    _colorCache = {};
    _positionCache = {};

    for (final node in nodes) {
      _colorCache[node.idHash] = SectorConfig.getNodeColor(
        sector: SectorEnum.values[node.sectorIndex],
        importance: node.importance,
        masteryScore: node.mastery,
      );
      _positionCache[node.idHash] = Offset(node.x, node.y);
    }

    _processedNodes = [];
    for (final node in nodes) {
      final pos = _positionCache[node.idHash]!;
      final color = _colorCache[node.idHash] ?? DS.brandPrimary;
      final radius = 3.0 + node.importance * 2.0;

      _processedNodes.add(
        ProcessedNode(
          node: node,
          color: color,
          radius: radius,
          position: pos,
        ),
      );
    }

    _processedEdges = [];
    for (final edge in edges) {
      final sourceHash = edge.sourceId.hashCode;
      final targetHash = edge.targetId.hashCode;

      final start = _positionCache[sourceHash];
      final end = _positionCache[targetHash];

      if (start == null || end == null) continue;

      final sourceColor = _colorCache[sourceHash] ?? DS.brandPrimary;
      final targetColor = _colorCache[targetHash] ?? DS.brandPrimary;
      final style = _RelationStyle.forType(edge.relationType);
      final strokeWidth = style.baseWidth * (0.5 + edge.strength * 0.5);

      _processedEdges.add(
        ProcessedEdge(
          edge: edge,
          start: start,
          end: end,
          startColor: sourceColor,
          endColor: targetColor,
          distance: (end - start).distance,
          strokeWidth: strokeWidth,
        ),
      );
    }

    // Parent-child connections
    for (final node in nodes) {
      if (node.parentIdHash != null) {
        final start = _positionCache[node.parentIdHash!];
        final end = _positionCache[node.idHash];

        if (start == null || end == null) continue;

        final parentColor = _colorCache[node.parentIdHash!] ?? DS.brandPrimary;
        final childColor = _colorCache[node.idHash] ?? DS.brandPrimary;

        _processedEdges.add(
          ProcessedEdge(
            edge: GalaxyEdgeModel(
              id: 'p_${node.idHash}',
              sourceId: '',
              targetId: '',
              relationType: EdgeRelationType.parentChild,
              strength: 0.7,
            ),
            start: start,
            end: end,
            startColor: parentColor,
            endColor: childColor,
            distance: (end - start).distance,
            strokeWidth: 1.5,
          ),
        );
      }
    }

    _nodeCache.set(cacheKey, _processedNodes);
    _edgeCache.set(cacheKey, _processedEdges);
    _colorCacheStorage.set(cacheKey, _colorCache);
    _positionCacheStorage.set(cacheKey, _positionCache);
  }

  @override
  void paint(Canvas canvas, Size size) {
    // LOD 0 (<0.2): Centroid Halo + Starfield Labels (Hide all nodes/connections)
    if (scale < _lod0Limit) {
      _drawSectorView(canvas); 
      return; 
    }

    // LOD 1 (0.2-0.4): Large Nodes + Key Labels
    // LOD 2 (0.4-0.6): All Nodes + Parent-Child Connections (Standard Label Density)
    // LOD 3 (0.6-0.8): Associative Connections + Glow (More Labels)
    // LOD 4 (>0.8): Full Text + Dynamic Particles

    // Draw Edges
    // Edges start at L2 (0.4) for parent-child, L3 (0.6) for others
    if (scale >= _lod1Limit) { 
        // Logic check: L2 starts at 0.4.
        if (scale >= _lod1Limit) { // Actually > 0.4 which is L2? No, _lod1Limit is 0.4.
           // Prompt: "Edgers start at L2 (0.4)"
           // My code: if (scale >= _lod1Limit) -> if (scale >= 0.4)
           // If scale < 0.6 (L2), only parent-child.
           _drawEdges(canvas, parentChildOnly: scale < _lod2Limit);
        }
    }

    // Draw Nodes
    // L1 (0.2-0.4): Large Nodes only. L2+ (>0.4): All nodes.
    _drawNodes(canvas, onlyLarge: scale < _lod1Limit);

    // Selection Highlight (Always visible if selected and node is visible)
    if (selectedNodeIdHash != null &&
        _positionCache.containsKey(selectedNodeIdHash)) {
      _drawSelectionHighlight(canvas, _positionCache[selectedNodeIdHash!]!);
    }
  }

  void _drawSelectionHighlight(Canvas canvas, Offset pos) {
    final radius = 40.0 + (selectionPulse * 8.0);
    final opacity = 0.3 + (selectionPulse * 0.2);

    final paint = Paint()
      ..color = DS.brandPrimary.withValues(alpha: opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0 + (selectionPulse * 1.0);

    canvas.drawCircle(pos, radius, paint);
    
    // Fill only if high tier
    if (performanceTier == PerformanceTier.ultra || performanceTier == PerformanceTier.high) {
        paint.color =
            DS.brandPrimary.withValues(alpha: 0.1 + (selectionPulse * 0.05));
        paint.style = PaintingStyle.fill;
        canvas.drawCircle(pos, 40, paint);
    }
  }

  void _drawEdges(Canvas canvas, {required bool parentChildOnly}) {
    // Optimization: If DPR is very low, skip thin lines or use simpler drawing
    final lowRes = currentDpr < 1.5;

    for (final edge in _processedEdges) {
      // Culling
      if (viewport != null) {
        final cRect = viewport!.inflate(50);
        if (!cRect.contains(edge.start - center) &&
            !cRect.contains(edge.end - center)) {
          continue;
        }
      }
      
      if (parentChildOnly && edge.edge.relationType != EdgeRelationType.parentChild) {
        continue;
      }

      // Skip weak non-structural edges on low res
      if (lowRes && edge.edge.strength < 0.5 && edge.edge.relationType != EdgeRelationType.parentChild) {
        continue;
      }

      final style = _RelationStyle.forType(edge.edge.relationType);
      
      // Tier Check: Low tier = no dashed lines, simple lines
      if (performanceTier == PerformanceTier.low || lowRes) {
         final paint = Paint()
           ..color = style.color.withValues(alpha: 0.5)
           ..strokeWidth = edge.strokeWidth;
         canvas.drawLine(edge.start, edge.end, paint);
         continue;
      }

      if (style.isDashed) {
        _drawDashedEdge(canvas, edge, style);
      } else {
        _drawSolidEdge(canvas, edge, style);
      }

      // Arrows only on higher scale/tier
      if (scale > _lod3Limit && (
          edge.edge.relationType == EdgeRelationType.prerequisite ||
          edge.edge.relationType == EdgeRelationType.derived)) {
        _drawArrow(canvas, edge.start, edge.end, style.color, edge.strokeWidth);
      }
    }
  }

  void _drawSolidEdge(Canvas canvas, ProcessedEdge edge, _RelationStyle style) {
    final paint = Paint()
      ..strokeWidth = edge.strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    // Gradient only on Medium+
    if (performanceTier != PerformanceTier.low) {
        // Create a 3-stop gradient to simulate a "pulse" or flow
        // The flow effect shifts the stops based on beamFlow (0.0 -> 1.0)
        final stops = [
          0.0,
          (0.5 + beamFlow) % 1.0, // Moving highlight
          1.0,
        ].toList()..sort();

        // If the highlight wraps around, we need a more complex shader or simply stick to a shifting midpoint
        // Simplified approach: Shift the midpoint color towards the target
        
        paint.shader = ui.Gradient.linear(
            edge.start, 
            edge.end, 
            [
              edge.startColor.withValues(alpha: 0.3 * edge.edge.strength),
              style.color.withValues(alpha: 0.8 * edge.edge.strength), // Highlight
              edge.endColor.withValues(alpha: 0.3 * edge.edge.strength),
            ],
            [
              0.0,
              ((beamFlow * 0.8) + 0.1), // Move from 0.1 to 0.9
              1.0
            ]
        );
    } else {
        paint.color = style.color.withValues(alpha: 0.5);
    }
    
    canvas.drawLine(edge.start, edge.end, paint);
  }

  void _drawDashedEdge(
      Canvas canvas, ProcessedEdge edge, _RelationStyle style,) {
    final paint = Paint()
      ..color = Color.lerp(edge.startColor, style.color, 0.5)!
          .withValues(alpha: 0.5 * edge.edge.strength)
      ..strokeWidth = edge.strokeWidth
      ..style = PaintingStyle.stroke;

    final length = (edge.end - edge.start).distance;
    final unit = (edge.end - edge.start) / length;
    final dash = style.dashLength;
    final gap = dash * 0.6;

    double curr = 0;
    while (curr < length) {
      final seg = math.min(dash, length - curr);
      canvas.drawLine(
          edge.start + unit * curr, edge.start + unit * (curr + seg), paint,);
      curr += dash + gap;
    }
  }

  void _drawArrow(
      Canvas canvas, Offset start, Offset end, Color color, double width,) {
    final dir = end - start;
    final len = dir.distance;
    if (len < 30) return;
    final unit = dir / len;
    final perp = Offset(-unit.dy, unit.dx);
    final size = width * 4;
    final tip = end - unit * 15;
    final path = Path()
      ..moveTo(tip.dx, tip.dy)
      ..lineTo(tip.dx - unit.dx * size + perp.dx * size * 0.5,
          tip.dy - unit.dy * size + perp.dy * size * 0.5,)
      ..lineTo(tip.dx - unit.dx * size - perp.dx * size * 0.5,
          tip.dy - unit.dy * size - perp.dy * size * 0.5,)
      ..close();
    canvas.drawPath(path, Paint()..color = color.withValues(alpha: 0.7));
  }

  void _drawSectorView(Canvas canvas) {
     // L0 Representation
    for (final cluster in clusters.values) {
      final pos = cluster.position;
      final color = SectorConfig.getColor(cluster.sector);
      // Simple Halo
      canvas.drawCircle(
          pos, 40.0, Paint()..color = color.withValues(alpha: 0.2),);
      
      // L0 Labels (Cluster Names)
      _drawClusterLabel(canvas, cluster.name, pos, 40.0, color);
    }
  }

  void _drawClusterLabel(
      Canvas canvas, String name, Offset pos, double r, Color c,) {
    // Only draw if we are REALLY zoomed out
    if (scale > _lod0Limit) return;
    
    _textRenderer.drawText(canvas, name, pos + Offset(0, r + 8),
        TextStyle(color: DS.brandPrimary, fontSize: 12),);
  }

  void _drawNodes(Canvas canvas, {required bool onlyLarge}) {
    final nodePaint = Paint()..style = PaintingStyle.fill;
    final glowPaint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8.0); // Efficient blur

    for (final p in _processedNodes) {
      // Culling
      if (viewport != null) {
        if (!viewport!.inflate(p.radius * 3).contains(p.position - center)) {
          continue;
        }
      }
      
      // LOD Filtering
      if (onlyLarge && p.node.importance < 3) {
          continue;
      }

      final progress = nodeAnimationProgress[p.node.idHash] ?? 1.0;
      final r = p.radius * (0.3 + progress * 0.7);

      if (scale < 0.3 && p.node.importance < 3) {
         canvas.drawCircle(p.position, r * 0.5,
            Paint()..color = p.color.withValues(alpha: 0.5 * progress),);
         continue;
      }

      if (p.node.isUnlocked) {
        // Halo Logic: Luminous Cognition Spec
        // Halo alpha follows alpha = clamp(scale * 2.0 - 0.4)
        final haloAlphaBase = (scale * 2.0 - 0.4).clamp(0.0, 1.0);
        
        if (haloAlphaBase > 0 && 
           (performanceTier == PerformanceTier.ultra || performanceTier == PerformanceTier.high)) {
            final m = p.node.mastery / 100.0;
            // Combined alpha: LOD base * mastery boost * animation progress
            final glowAlpha = haloAlphaBase * (0.3 + m * 0.4) * progress;
            
            glowPaint.color = p.color.withValues(alpha: glowAlpha);
            // Draw Halo
            canvas.drawCircle(p.position, r + 4.0, glowPaint);
        }

        // Core Node: Solid Circle (Spec Requirement)
        nodePaint.color = p.color.withValues(alpha: progress);
        nodePaint.shader = null; // Ensure no gradient
        
        // Draw Core
        canvas.drawCircle(p.position, r, nodePaint);

        // Ring for studied nodes
        if (p.node.studyCount >= 2 && progress > 0.7) {
          canvas.drawCircle(
              p.position,
              r * 1.6,
              Paint()
                ..color = p.color.withValues(alpha: 0.5)
                ..style = PaintingStyle.stroke,);
        }
      } else {
        // Locked Node: Dim solid
        canvas.drawCircle(p.position, r * 0.8,
            Paint()..color = DS.brandPrimary.withValues(alpha: 0.2 * progress),);
      }

      // Labels Logic
      bool showLabel = false;
      if (scale >= _lod3Limit) {
          showLabel = true; 
      } else if (scale >= _lod2Limit) {
          if (p.node.importance >= 2) showLabel = true;
      } else if (scale >= _lod1Limit) {
          if (p.node.importance >= 3) showLabel = true;
      } else if (scale >= _lod0Limit) {
           if (p.node.importance >= 4) showLabel = true;
      }
      
      if (showLabel) {
         _drawNodeLabel(canvas, p.node, p.position, p.color);
      }
    }
  }

  void _drawNodeLabel(
      Canvas canvas, CompactKnowledgeNode node, Offset pos, Color color,) {
    _textRenderer.drawText(
      canvas,
      node.name,
      pos + Offset(0, (3.0 + node.importance * 2.0) + 8),
      TextStyle(
          color: DS.brandPrimary.withValues(alpha: node.isUnlocked ? 0.9 : 0.5),
          fontSize: 10,),
    );
  }

  @override
  bool shouldRepaint(covariant StarMapPainter old) =>
      old.scale != scale ||
      old.performanceTier != performanceTier ||
      old.currentDpr != currentDpr ||
      old.viewport != viewport ||
      !identical(old.nodes, nodes) ||
      old.selectionPulse != selectionPulse ||
      old.beamFlow != beamFlow;
}
