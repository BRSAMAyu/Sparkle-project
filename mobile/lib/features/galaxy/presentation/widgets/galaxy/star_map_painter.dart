import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/core/services/text_cache.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';
import 'package:sparkle/shared/models/compact_knowledge_node.dart';

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
          color: DS.warning,
          isDashed: true,
          dashLength: 8,
          baseWidth: 1.2,
        );
      case EdgeRelationType.similar:
        return _RelationStyle(
          color: DS.taskReflection,
          isDashed: true,
          dashLength: 4,
          baseWidth: 1.0,
        );
      case EdgeRelationType.contrast:
        return _RelationStyle(color: DS.error, isDashed: true, dashLength: 12);
      case EdgeRelationType.application:
        return _RelationStyle(color: DS.taskPlanning);
      case EdgeRelationType.example:
        return _RelationStyle(
          color: DS.textSecondary,
          isDashed: true,
          dashLength: 6,
          baseWidth: 1.0,
        );
      case EdgeRelationType.parentChild:
        return _RelationStyle(color: DS.brandPrimaryConst, baseWidth: 1.8);
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
    this.highlightedNodeIdHashes = const {},
    this.highlightRevision = 0,
    this.expandedEdgeNodeIdHashes = const {},
    this.nodeAnimationProgress = const {},
    this.selectionPulse = 0.0,
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
  final Set<int> highlightedNodeIdHashes;
  final int highlightRevision;
  final Set<int> expandedEdgeNodeIdHashes;
  final Map<int, double> nodeAnimationProgress;
  final double selectionPulse;

  // LOD Thresholds - Clear scale boundaries
  // L0: <0.2 - Sector view (centroids only)
  // L1: 0.2-0.4 - Large nodes + key labels (imp>=4)
  // L2: 0.4-0.6 - All nodes + parent-child edges + standard labels (imp>=3)
  // L3: 0.6-0.8 - All edges + more labels (imp>=2) + glow
  // L4: >=0.8 - Full detail + all labels (imp>=1)
  static const double _lod0Limit = GalaxyLodThresholds.universeMax;
  static const double _lod1Limit = GalaxyLodThresholds.galaxyMax;
  static const double _lod2Limit = GalaxyLodThresholds.clusterMax;
  static const double _lod3Limit = GalaxyLodThresholds.nebulaMax;

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
        nodes.length,
        edges.length,
        Object.hashAll(
          nodes.take(12).map(
                (node) =>
                    Object.hash(node.idHash, node.x.round(), node.y.round()),
              ),
        ),
        Object.hashAll(
          edges.take(12).map(
                (edge) => Object.hash(
                    edge.sourceId, edge.targetId, edge.relationType),
              ),
        ),
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
      final pos = _positionCache[node.idHash]!; // 安全使用!，因为已经在第187行添加
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
    // L0 (<0.2): Sector view - centroids only, no nodes/edges
    if (scale < _lod0Limit) {
      _drawSectorView(canvas);
      return;
    }

    // L1+ (>=0.2): Draw nodes
    // L1 (0.2-0.4): Large nodes only (imp>=4)
    // L2+ (>=0.4): All nodes
    _drawNodes(canvas, onlyLarge: scale < _lod1Limit);

    // L2+ (>=0.4): Draw edges
    // L2 (0.4-0.6): Parent-child edges only
    // L3+ (>=0.6): All edges
    if (scale >= _lod1Limit) {
      _drawEdges(canvas, parentChildOnly: scale < _lod2Limit);
    }

    // Selection Highlight (always visible if selected)
    if (selectionPulse > 0 &&
        selectedNodeIdHash != null &&
        _positionCache.containsKey(selectedNodeIdHash)) {
      _drawSelectionHighlight(canvas, _positionCache[selectedNodeIdHash]!);
    }

    if (selectionPulse > 0 && highlightedNodeIdHashes.isNotEmpty) {
      _drawEvidenceHighlights(canvas);
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
    if (performanceTier == PerformanceTier.ultra ||
        performanceTier == PerformanceTier.high) {
      paint.color =
          DS.brandPrimary.withValues(alpha: 0.1 + (selectionPulse * 0.05));
      paint.style = PaintingStyle.fill;
      canvas.drawCircle(pos, 40, paint);
    }
  }

  void _drawEvidenceHighlights(Canvas canvas) {
    const baseRadius = 24.0;
    final pulseRadius = baseRadius + (selectionPulse * 4.0);
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5
      ..color = DS.info.withValues(alpha: 0.55);

    for (final nodeHash in highlightedNodeIdHashes) {
      if (nodeHash == selectedNodeIdHash) {
        continue;
      }
      final pos = _positionCache[nodeHash];
      if (pos == null) {
        continue;
      }
      canvas.drawCircle(pos, pulseRadius, paint);
    }
  }

  void _drawEdges(Canvas canvas, {required bool parentChildOnly}) {
    // Optimization: If DPR is very low, skip thin lines or use simpler drawing
    final lowRes = currentDpr < 1.5;
    final selectedHash = selectedNodeIdHash;

    for (final edge in _processedEdges) {
      // Culling
      if (viewport != null) {
        final cRect = viewport!.inflate(50);
        if (!cRect.contains(edge.start) && !cRect.contains(edge.end)) {
          continue;
        }
      }

      if (parentChildOnly &&
          edge.edge.relationType != EdgeRelationType.parentChild) {
        continue;
      }

      // Skip weak non-structural edges on low res
      if (lowRes &&
          edge.edge.strength < 0.5 &&
          edge.edge.relationType != EdgeRelationType.parentChild) {
        continue;
      }

      final style = _RelationStyle.forType(edge.edge.relationType);
      final edgeAlpha = _edgeAlphaMultiplier(edge, selectedHash);

      // Tier Check: Low tier = no dashed lines, simple lines
      if (performanceTier == PerformanceTier.low || lowRes) {
        final paint = Paint()
          ..color = style.color.withValues(alpha: 0.28 * edgeAlpha)
          ..strokeWidth = edge.strokeWidth * (0.9 + edgeAlpha * 0.35);
        canvas.drawLine(edge.start, edge.end, paint);
        continue;
      }

      if (style.isDashed) {
        _drawDashedEdge(canvas, edge, style, edgeAlpha);
      } else {
        _drawSolidEdge(canvas, edge, style, edgeAlpha);
      }

      // Arrows only on L4+ (>=0.8)
      if (scale >= _lod3Limit &&
          (edge.edge.relationType == EdgeRelationType.prerequisite ||
              edge.edge.relationType == EdgeRelationType.derived)) {
        _drawArrow(canvas, edge.start, edge.end, style.color, edge.strokeWidth);
      }
    }
  }

  double _edgeAlphaMultiplier(ProcessedEdge edge, int? selectedHash) {
    if (selectedHash == null) {
      return edge.edge.relationType == EdgeRelationType.parentChild
          ? 0.92
          : 0.72;
    }

    final sourceHash = edge.edge.sourceId.hashCode;
    final targetHash = edge.edge.targetId.hashCode;
    final touchesSelection =
        sourceHash == selectedHash || targetHash == selectedHash;
    final touchesEvidence = highlightedNodeIdHashes.contains(sourceHash) ||
        highlightedNodeIdHashes.contains(targetHash);

    if (touchesSelection) {
      return 1.15;
    }
    if (touchesEvidence) {
      return 0.96;
    }
    return edge.edge.relationType == EdgeRelationType.parentChild ? 0.52 : 0.34;
  }

  void _drawSolidEdge(
    Canvas canvas,
    ProcessedEdge edge,
    _RelationStyle style,
    double edgeAlpha,
  ) {
    final paint = Paint()
      ..strokeWidth = edge.strokeWidth * (0.9 + edgeAlpha * 0.3)
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    // Gradient only on Medium+
    if (performanceTier != PerformanceTier.low) {
      paint.shader = ui.Gradient.linear(edge.start, edge.end, [
        Color.lerp(edge.startColor, style.color, 0.5)!
            .withValues(alpha: 0.52 * edge.edge.strength * edgeAlpha),
        Color.lerp(edge.endColor, style.color, 0.5)!
            .withValues(alpha: 0.22 * edge.edge.strength * edgeAlpha),
      ]);
    } else {
      paint.color = style.color.withValues(alpha: 0.35 * edgeAlpha);
    }

    canvas.drawLine(edge.start, edge.end, paint);
  }

  void _drawDashedEdge(
    Canvas canvas,
    ProcessedEdge edge,
    _RelationStyle style,
    double edgeAlpha,
  ) {
    final paint = Paint()
      ..color = Color.lerp(edge.startColor, style.color, 0.5)!
          .withValues(alpha: 0.4 * edge.edge.strength * edgeAlpha)
      ..strokeWidth = edge.strokeWidth * (0.85 + edgeAlpha * 0.2)
      ..style = PaintingStyle.stroke;

    final length = (edge.end - edge.start).distance;
    final unit = (edge.end - edge.start) / length;
    final dash = style.dashLength;
    final gap = dash * 0.6;

    double curr = 0;
    while (curr < length) {
      final seg = math.min(dash, length - curr);
      canvas.drawLine(
        edge.start + unit * curr,
        edge.start + unit * (curr + seg),
        paint,
      );
      curr += dash + gap;
    }
  }

  void _drawArrow(
    Canvas canvas,
    Offset start,
    Offset end,
    Color color,
    double width,
  ) {
    final dir = end - start;
    final len = dir.distance;
    if (len < 30) return;
    final unit = dir / len;
    final perp = Offset(-unit.dy, unit.dx);
    final size = width * 4;
    final tip = end - unit * 15;
    final path = Path()
      ..moveTo(tip.dx, tip.dy)
      ..lineTo(
        tip.dx - unit.dx * size + perp.dx * size * 0.5,
        tip.dy - unit.dy * size + perp.dy * size * 0.5,
      )
      ..lineTo(
        tip.dx - unit.dx * size - perp.dx * size * 0.5,
        tip.dy - unit.dy * size - perp.dy * size * 0.5,
      )
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
        pos,
        40.0,
        Paint()..color = color.withValues(alpha: 0.2),
      );

      // L0 Labels (Cluster Names)
      _drawClusterLabel(canvas, cluster.name, pos, 40.0, color);
    }
  }

  void _drawClusterLabel(
    Canvas canvas,
    String name,
    Offset pos,
    double r,
    Color c,
  ) {
    // Only draw in L0 (<0.2)
    if (scale >= _lod0Limit) return;

    _textRenderer.drawText(
      canvas,
      name,
      pos + Offset(0, r + 8),
      TextStyle(color: DS.brandPrimaryConst, fontSize: 12),
    );
  }

  void _drawNodes(Canvas canvas, {required bool onlyLarge}) {
    final nodePaint = Paint()..style = PaintingStyle.fill;
    final glowPaint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8.0);

    for (final p in _processedNodes) {
      // Culling
      if (viewport != null) {
        if (!viewport!.inflate(p.radius * 3).contains(p.position)) {
          continue;
        }
      }

      // LOD Filtering is now handled by the provider's _computeVisibleNodes()
      // This painter receives already-filtered nodes, so we only do minimal filtering here
      // to handle edge cases during scale transitions

      final progress = nodeAnimationProgress[p.node.idHash] ?? 1.0;
      final r = p.radius * (0.3 + progress * 0.7);

      // For very zoomed out views, render smaller/dimmer nodes
      final isLowDetailView = scale < 0.3;
      final effectiveRadius =
          isLowDetailView && p.node.importance < 3 ? r * 0.6 : r;
      final effectiveAlpha =
          isLowDetailView && p.node.importance < 3 ? 0.6 * progress : progress;

      if (p.node.isUnlocked) {
        // Glow: L3+ (>=0.6) AND (Ultra or High Tier)
        if (scale >= _lod2Limit &&
            (performanceTier == PerformanceTier.ultra ||
                performanceTier == PerformanceTier.high)) {
          final m = p.node.mastery / 100.0;
          glowPaint.color =
              p.color.withValues(alpha: (0.3 + m * 0.5) * 0.4 * effectiveAlpha);
          canvas.drawCircle(p.position, effectiveRadius * 3.0, glowPaint);
        }

        // Main Node
        // Disable fancy shader gradient on low tier OR low DPR
        if (performanceTier != PerformanceTier.low && currentDpr >= 1.5) {
          nodePaint.shader = ui.Gradient.radial(p.position, effectiveRadius, [
            DS.brandPrimary.withValues(alpha: 0.9 * effectiveAlpha),
            p.color.withValues(alpha: effectiveAlpha),
          ]);
        } else {
          nodePaint.color = p.color.withValues(alpha: effectiveAlpha);
          nodePaint.shader = null;
        }

        canvas.drawCircle(p.position, effectiveRadius, nodePaint);
        nodePaint.shader = null;

        if (p.node.studyCount >= 2 && effectiveAlpha > 0.7) {
          canvas.drawCircle(
            p.position,
            effectiveRadius * 1.6,
            Paint()
              ..color = p.color.withValues(alpha: 0.5)
              ..style = PaintingStyle.stroke,
          );
        }
      } else {
        canvas.drawCircle(
          p.position,
          effectiveRadius * 0.8,
          Paint()
            ..color = DS.brandPrimary.withValues(alpha: 0.2 * effectiveAlpha),
        );
      }

      // Labels Logic - aligned with LOD levels
      // L1 (0.2-0.4): Key labels (imp >= 4)
      // L2 (0.4-0.6): Standard labels (imp >= 3)
      // L3 (0.6-0.8): More labels (imp >= 2)
      // L4 (>=0.8): All labels (imp >= 1)

      var showLabel = false;
      if (scale >= _lod3Limit) {
        // L4+: All labels
        showLabel = true;
      } else if (scale >= _lod2Limit) {
        // L3: imp >= 2
        if (p.node.importance >= 2) showLabel = true;
      } else if (scale >= _lod1Limit) {
        // L2: imp >= 3
        if (p.node.importance >= 3) showLabel = true;
      } else if (scale >= _lod0Limit) {
        // L1: imp >= 4
        if (p.node.importance >= 4) showLabel = true;
      }

      if (showLabel) {
        _drawNodeLabel(canvas, p.node, p.position, p.color);
        _drawNodeTag(canvas, p.node, p.position, p.color);
      }
    }
  }

  void _drawNodeLabel(
    Canvas canvas,
    CompactKnowledgeNode node,
    Offset pos,
    Color color,
  ) {
    final fontSize = scale >= _lod3Limit ? 11.0 : 10.0;
    _textRenderer.drawText(
      canvas,
      node.name,
      pos + Offset(0, (3.0 + node.importance * 2.0) + 8),
      TextStyle(
        color: DS.brandPrimary.withValues(alpha: node.isUnlocked ? 0.9 : 0.5),
        fontSize: fontSize,
        fontWeight: node.importance >= 4 ? FontWeight.w700 : FontWeight.w600,
      ),
    );
  }

  void _drawNodeTag(
    Canvas canvas,
    CompactKnowledgeNode node,
    Offset pos,
    Color color,
  ) {
    final tag = node.primaryTag;
    if (tag == null ||
        tag.isEmpty ||
        scale < _lod2Limit ||
        node.importance < 2) {
      return;
    }

    _textRenderer.drawText(
      canvas,
      '#$tag',
      pos + Offset(0, (3.0 + node.importance * 2.0) + 24),
      TextStyle(
        color: color.withValues(alpha: node.isUnlocked ? 0.74 : 0.38),
        fontSize: scale >= _lod3Limit ? 9 : 8,
        fontWeight: FontWeight.w600,
      ),
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
      old.selectedNodeIdHash != selectedNodeIdHash ||
      old.highlightRevision != highlightRevision;
}
