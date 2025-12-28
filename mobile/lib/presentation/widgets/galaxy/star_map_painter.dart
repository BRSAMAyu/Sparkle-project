import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/core/services/text_cache.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

/// Pre-processed node data for efficient painting
class ProcessedNode {

  ProcessedNode({
    required this.node,
    required this.color,
    required this.radius,
    required this.position,
  });
  final GalaxyNodeModel node;
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

/// 关系类型颜色配置
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
        return const _RelationStyle(
          color: Color(0xFF4FC3F7),  // 浅蓝色 - 前置知识
          baseWidth: 2.0,
        );
      case EdgeRelationType.derived:
        return const _RelationStyle(
          color: Color(0xFF81C784),  // 浅绿色 - 衍生知识
          baseWidth: 1.8,
        );
      case EdgeRelationType.related:
        return const _RelationStyle(
          color: Color(0xFFFFB74D),  // 橙色 - 相关知识
          isDashed: true,
          dashLength: 8,
          baseWidth: 1.2,
        );
      case EdgeRelationType.similar:
        return const _RelationStyle(
          color: Color(0xFFBA68C8),  // 紫色 - 相似概念
          isDashed: true,
          dashLength: 4,
          baseWidth: 1.0,
        );
      case EdgeRelationType.contrast:
        return const _RelationStyle(
          color: Color(0xFFE57373),  // 红色 - 对比概念
          isDashed: true,
          dashLength: 12,
        );
      case EdgeRelationType.application:
        return const _RelationStyle(
          color: Color(0xFF4DB6AC),  // 青色 - 应用场景
        );
      case EdgeRelationType.example:
        return const _RelationStyle(
          color: Color(0xFF90A4AE),  // 灰色 - 具体示例
          isDashed: true,
          dashLength: 6,
          baseWidth: 1.0,
        );
      case EdgeRelationType.parentChild:
        return const _RelationStyle(
          color: Color(0xFFFF6B35), // DS.brandPrimary
          baseWidth: 1.8,
        );
    }
  }
}

class StarMapPainter extends CustomPainter {

  StarMapPainter({
    required this.nodes,
    required this.positions, this.edges = const [],
    this.scale = 1.0,
    this.aggregationLevel = AggregationLevel.full,
    this.clusters = const {},
    this.viewport,
    this.center = Offset.zero,
    this.selectedNodeId,
    this.expandedEdgeNodeIds = const {},
    this.nodeAnimationProgress = const {},
    this.selectionPulse = 0.0,
  }) {
    _preprocessData();
  }
  final List<GalaxyNodeModel> nodes;
  final List<GalaxyEdgeModel> edges;
  final Map<String, Offset> positions;
  final double scale;
  final AggregationLevel aggregationLevel;
  final Map<String, ClusterInfo> clusters;
  final Rect? viewport;  // 可选视口用于裁剪
  final Offset center;   // 宇宙中心点
  final String? selectedNodeId;
  final Set<String> expandedEdgeNodeIds;
  final Map<String, double> nodeAnimationProgress; // 0.0 to 1.0
  final double selectionPulse; // 0.0 to 1.0 for selection animation

  // Cache storage - 使用智能缓存替代简单Map
  static final SmartCache<int, List<ProcessedNode>> _nodeCache = SmartCache(
    maxSize: 10,
  );
  static final SmartCache<int, List<ProcessedEdge>> _edgeCache = SmartCache(
    maxSize: 10,
  );
  static final SmartCache<int, Map<String, Color>> _colorCacheStorage = SmartCache(
    maxSize: 10,
  );
  static final SmartCache<int, Map<String, Offset>> _positionCacheStorage = SmartCache(
    maxSize: 10,
  );

  // 文本渲染器
  static final BatchTextRenderer _textRenderer = BatchTextRenderer();

  // Instance data
  late final List<ProcessedNode> _processedNodes;
  late final List<ProcessedEdge> _processedEdges;
  late final Map<String, Color> _colorCache;
  late final Map<String, Offset> _positionCache;

  int _generateCacheKey() {
    // Generate a unique key based on the data that affects the processed output
    // Note: 'nodes' and 'edges' lists usually change reference when filtered
    // 'positions' map reference also likely changes on layout updates
    return Object.hash(
      identityHashCode(nodes),
      identityHashCode(edges),
      identityHashCode(positions),
    );
  }

  /// Pre-process all data in the constructor to avoid repeated work in paint()
  void _preprocessData() {
    final cacheKey = _generateCacheKey();

    // 使用智能缓存获取
    final cachedNodes = _nodeCache.get(cacheKey);
    final cachedEdges = _edgeCache.get(cacheKey);
    final cachedColors = _colorCacheStorage.get(cacheKey);
    final cachedPositions = _positionCacheStorage.get(cacheKey);

    if (cachedNodes != null && cachedEdges != null && cachedColors != null && cachedPositions != null) {
      _processedNodes = cachedNodes;
      _processedEdges = cachedEdges;
      _colorCache = cachedColors;
      _positionCache = cachedPositions;
      return;
    }

    // Build caches
    _colorCache = {};
    _positionCache = {};

    for (final node in nodes) {
      // 使用星域色系：基于节点的星域、重要程度和掌握度生成颜色
      _colorCache[node.id] = SectorConfig.getNodeColor(
        sector: node.sector,
        importance: node.importance,
        masteryScore: node.masteryScore,
      );
      final pos = positions[node.id];
      if (pos != null) {
        _positionCache[node.id] = pos;
      }
    }

    // Build processed nodes
    // Note: 'nodes' passed here are already filtered by Provider for Visibility & LOD
    _processedNodes = [];
    for (final node in nodes) {
      final pos = _positionCache[node.id];
      if (pos == null) continue;

      final color = _colorCache[node.id] ?? DS.brandPrimary;
      final radius = node.radius;
      _processedNodes.add(ProcessedNode(
        node: node,
        color: color,
        radius: radius,
        position: pos,
      ),);
    }

    // Build processed edges
    // Note: 'edges' passed here are already filtered by Provider
    _processedEdges = [];

    // First, add edges from the edges list
    for (final edge in edges) {
      final start = _positionCache[edge.sourceId];
      final end = _positionCache[edge.targetId];

      if (start == null || end == null) continue;

      final sourceColor = _colorCache[edge.sourceId] ?? DS.brandPrimary;
      final targetColor = _colorCache[edge.targetId] ?? DS.brandPrimary;
      final distance = (end - start).distance;
      final style = _RelationStyle.forType(edge.relationType);
      final strokeWidth = style.baseWidth * (0.5 + edge.strength * 0.5);

      _processedEdges.add(ProcessedEdge(
        edge: edge,
        start: start,
        end: end,
        startColor: sourceColor,
        endColor: targetColor,
        distance: distance,
        strokeWidth: strokeWidth,
      ),);
    }

    // Also add parent-child connections if not already in edges
    final edgeKeys = edges.map((e) => '${e.sourceId}-${e.targetId}').toSet();
    for (final node in nodes) {
      if (node.parentId != null) {
        final key = '${node.parentId}-${node.id}';
        if (edgeKeys.contains(key)) continue;

        final start = _positionCache[node.parentId];
        final end = _positionCache[node.id];

        if (start == null || end == null) continue;
        
        // Skip if parent is not in visible positions (might be culled)
        final parentColor = _colorCache[node.parentId] ?? DS.brandPrimary;
        final childColor = _colorCache[node.id] ?? DS.brandPrimary;
        final distance = (end - start).distance;

        _processedEdges.add(ProcessedEdge(
          edge: GalaxyEdgeModel(
            id: 'parent_$key',
            sourceId: node.parentId!,
            targetId: node.id,
            relationType: EdgeRelationType.parentChild,
            strength: 0.7,
          ),
          start: start,
          end: end,
          startColor: parentColor,
          endColor: childColor,
          distance: distance,
          strokeWidth: 1.5,
        ),);
      }
    }

    // Store in cache - 智能缓存会自动管理大小和过期
    _nodeCache.set(cacheKey, _processedNodes);
    _edgeCache.set(cacheKey, _processedEdges);
    _colorCacheStorage.set(cacheKey, _colorCache);
    _positionCacheStorage.set(cacheKey, _positionCache);
  }

  /// 清理静态缓存（供外部调用）
  static void clearCaches() {
    _nodeCache.clear();
    _edgeCache.clear();
    _colorCacheStorage.clear();
    _positionCacheStorage.clear();
    _textRenderer.clear();
  }

  @override
  void paint(Canvas canvas, Size size) {
    // Base layer: Connections
    _drawRootConnections(canvas);
    _drawEdges(canvas);

    // Nodes and overlays based on level
    switch (aggregationLevel) {
      case AggregationLevel.universe:
        _drawSectorView(canvas);
        
      case AggregationLevel.galaxy:
        _drawSectorView(canvas); // Still show sectors in background/context
        _drawNodes(canvas); // Draw only roots (filtered by provider)
        
      case AggregationLevel.cluster:
        _drawClusteredView(canvas);
        _drawNodes(canvas); // Draw importance >= 3
        
      case AggregationLevel.nebula:
        _drawClusteredView(canvas); // Faint clusters
        _drawNodes(canvas); // Draw importance >= 2
        
      case AggregationLevel.full:
        _drawNodes(canvas); // All nodes
    }
    
    // Draw selected node highlight if any
    if (selectedNodeId != null && _positionCache.containsKey(selectedNodeId)) {
      _drawSelectionHighlight(canvas, _positionCache[selectedNodeId]!);
    }
  }

  void _drawSelectionHighlight(Canvas canvas, Offset pos) {
    // Pulse effect driven by selectionPulse value (0.0 to 1.0)
    final radius = 40.0 + (selectionPulse * 8.0); // 40 to 48
    final opacity = 0.3 + (selectionPulse * 0.2); // 0.3 to 0.5
    
    final paint = Paint()
      ..color = DS.brandPrimary.withValues(alpha: opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0 + (selectionPulse * 1.0);
      
    canvas.drawCircle(pos, radius, paint);
    
    // Inner fill
    paint.color = DS.brandPrimary.withValues(alpha: 0.1 + (selectionPulse * 0.05));
    paint.style = PaintingStyle.fill;
    canvas.drawCircle(pos, 40, paint);
  }

  /// Draw connections from Universe Center to Sector Roots
  void _drawRootConnections(Canvas canvas) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    for (final node in nodes) {
      if (node.parentId == null) {
        final pos = _positionCache[node.id];
        if (pos == null) continue;

        final sectorColor = SectorConfig.getColor(node.sector);
        
        // Gradient from invisible center to colored node
        final gradient = ui.Gradient.linear(
          center,
          pos,
          [
            sectorColor.withValues(alpha: 0.0),
            sectorColor.withValues(alpha: 0.3),
          ],
        );
        
        paint.shader = gradient;
        canvas.drawLine(center, pos, paint);
      }
    }
  }

  /// Draw all edges with relationship-specific styling
  void _drawEdges(Canvas canvas) {
    for (final processedEdge in _processedEdges) {
      _drawEdge(canvas, processedEdge);
    }
  }

  /// Draw a single edge with relationship-aware styling
  void _drawEdge(Canvas canvas, ProcessedEdge edge) {
    final style = _RelationStyle.forType(edge.edge.relationType);

    if (style.isDashed) {
      _drawDashedEdge(canvas, edge, style);
    } else {
      _drawSolidEdge(canvas, edge, style);
    }

    // Draw arrow for directed relationships
    if (edge.edge.relationType == EdgeRelationType.prerequisite ||
        edge.edge.relationType == EdgeRelationType.derived) {
      _drawArrow(canvas, edge.start, edge.end, style.color, edge.strokeWidth);
    }
  }

  /// Draw a solid edge with gradient
  void _drawSolidEdge(Canvas canvas, ProcessedEdge edge, _RelationStyle style) {
    // Gradient from source to target
    final gradient = ui.Gradient.linear(
      edge.start,
      edge.end,
      [
        Color.lerp(edge.startColor, style.color, 0.5)!.withValues(alpha: 0.6 * edge.edge.strength),
        Color.lerp(edge.endColor, style.color, 0.5)!.withValues(alpha: 0.3 * edge.edge.strength),
      ],
    );

    final paint = Paint()
      ..shader = gradient
      ..strokeWidth = edge.strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawLine(edge.start, edge.end, paint);

    // Subtle glow effect
    final glowPaint = Paint()
      ..shader = ui.Gradient.linear(
        edge.start,
        edge.end,
        [
          style.color.withValues(alpha: 0.15 * edge.edge.strength),
          style.color.withValues(alpha: 0.05 * edge.edge.strength),
        ],
      )
      ..strokeWidth = edge.strokeWidth * 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);

    canvas.drawLine(edge.start, edge.end, glowPaint);
  }

  /// Draw a dashed edge
  void _drawDashedEdge(Canvas canvas, ProcessedEdge edge, _RelationStyle style) {
    final paint = Paint()
      ..color = Color.lerp(edge.startColor, style.color, 0.5)!.withValues(alpha: 0.5 * edge.edge.strength)
      ..strokeWidth = edge.strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final path = Path();
    final direction = edge.end - edge.start;
    final length = direction.distance;
    final unitDir = Offset(direction.dx / length, direction.dy / length);

    double currentLength = 0;
    var drawing = true;
    final dashLength = style.dashLength;
    final gapLength = style.dashLength * 0.6;

    while (currentLength < length) {
      final segmentLength = drawing
          ? math.min(dashLength, length - currentLength)
          : math.min(gapLength, length - currentLength);

      if (drawing) {
        final startPoint = edge.start + unitDir * currentLength;
        final endPoint = edge.start + unitDir * (currentLength + segmentLength);
        path.moveTo(startPoint.dx, startPoint.dy);
        path.lineTo(endPoint.dx, endPoint.dy);
      }

      currentLength += segmentLength;
      drawing = !drawing;
    }

    canvas.drawPath(path, paint);
  }

  /// Draw an arrow at the end of an edge
  void _drawArrow(Canvas canvas, Offset start, Offset end, Color color, double strokeWidth) {
    final direction = end - start;
    final length = direction.distance;
    if (length < 30) return;

    final unitDir = Offset(direction.dx / length, direction.dy / length);
    final perpDir = Offset(-unitDir.dy, unitDir.dx);

    final arrowSize = strokeWidth * 4;
    final arrowPoint = end - unitDir * 15;  // Offset from node

    final arrowPath = Path()
      ..moveTo(arrowPoint.dx, arrowPoint.dy)
      ..lineTo(
        arrowPoint.dx - unitDir.dx * arrowSize + perpDir.dx * arrowSize * 0.5,
        arrowPoint.dy - unitDir.dy * arrowSize + perpDir.dy * arrowSize * 0.5,
      )
      ..lineTo(
        arrowPoint.dx - unitDir.dx * arrowSize - perpDir.dx * arrowSize * 0.5,
        arrowPoint.dy - unitDir.dy * arrowSize - perpDir.dy * arrowSize * 0.5,
      )
      ..close();

    final paint = Paint()
      ..color = color.withValues(alpha: 0.7)
      ..style = PaintingStyle.fill;

    canvas.drawPath(arrowPath, paint);
  }

  /// Draw clustered view - parent nodes as larger circles with child count
  void _drawClusteredView(Canvas canvas) {
    final nodePaint = Paint()..style = PaintingStyle.fill;
    final glowPaint = Paint()..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12.0);
    final strokePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    for (final cluster in clusters.values) {
      final pos = cluster.position;
      final style = SectorConfig.getStyle(cluster.sector);
      final color = style.primaryColor;

      // Cluster size based on node count (logarithmic scaling)
      final baseRadius = 15.0 + (cluster.nodeCount.clamp(1, 50) * 0.8);
      final masteryFactor = cluster.totalMastery / 100.0;

      // Outer glow
      glowPaint.color = color.withAlpha((masteryFactor * 80).toInt());
      canvas.drawCircle(pos, baseRadius * 2.5, glowPaint);

      // Inner glow
      glowPaint.color = color.withAlpha((masteryFactor * 120).toInt());
      glowPaint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 6.0);
      canvas.drawCircle(pos, baseRadius * 1.5, glowPaint);
      glowPaint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 12.0);

      // Main circle with gradient fill
      final gradient = ui.Gradient.radial(
        pos,
        baseRadius,
        [
          color.withAlpha(200),
          color.withAlpha(100),
        ],
      );
      nodePaint.shader = gradient;
      canvas.drawCircle(pos, baseRadius, nodePaint);
      nodePaint.shader = null;

      // Border ring
      strokePaint.color = color.withAlpha(180);
      canvas.drawCircle(pos, baseRadius, strokePaint);

      // Node count badge
      _drawClusterBadge(canvas, pos, baseRadius, cluster.nodeCount, color);

      // Cluster name
      _drawClusterLabel(canvas, cluster.name, pos, baseRadius, color);
    }
  }

  /// Draw node count badge on cluster
  void _drawClusterBadge(Canvas canvas, Offset pos, double radius, int count, Color color) {
    final badgePos = pos + Offset(radius * 0.7, -radius * 0.7);
    const badgeRadius = 10.0;

    // Badge background
    final badgePaint = Paint()
      ..color = DS.brandPrimary
      ..style = PaintingStyle.fill;
    canvas.drawCircle(badgePos, badgeRadius, badgePaint);

    // Badge border
    badgePaint
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawCircle(badgePos, badgeRadius, badgePaint);

    // Count text
    final textSpan = TextSpan(
      text: count > 99 ? '99+' : '$count',
      style: TextStyle(
        color: color,
        fontSize: count > 99 ? 7 : 9,
        fontWeight: FontWeight.bold,
      ),
    );
    final textPainter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();
    textPainter.paint(
      canvas,
      badgePos - Offset(textPainter.width / 2, textPainter.height / 2),
    );
  }

  /// Draw cluster label using cached text renderer
  void _drawClusterLabel(Canvas canvas, String name, Offset pos, double radius, Color color) {
    final style = TextStyle(
      color: DS.brandPrimary.withAlpha(220),
      fontSize: 12,
      fontWeight: FontWeight.w600,
      shadows: [
        Shadow(
          color: color.withAlpha(150),
          blurRadius: 6,
        ),
      ],
    );

    _textRenderer.drawText(
      canvas,
      name,
      pos + Offset(0, radius + 8),
      style,
      align: TextAlign.center,
    );
  }

  /// Draw sector-level view - only sector centroids
  void _drawSectorView(Canvas canvas) {
    final nodePaint = Paint()..style = PaintingStyle.fill;
    final glowPaint = Paint()..maskFilter = const MaskFilter.blur(BlurStyle.normal, 20.0);

    for (final cluster in clusters.values) {
      final pos = cluster.position;
      final style = SectorConfig.getStyle(cluster.sector);
      final color = style.primaryColor;

      // Large sector centroid
      final baseRadius = 30.0 + (cluster.nodeCount.clamp(1, 100) * 0.3);
      final masteryFactor = cluster.totalMastery / 100.0;

      // Large outer glow
      glowPaint.color = color.withAlpha((masteryFactor * 60).toInt());
      canvas.drawCircle(pos, baseRadius * 3.5, glowPaint);

      // Mid glow
      glowPaint.color = color.withAlpha((masteryFactor * 100).toInt());
      glowPaint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 12.0);
      canvas.drawCircle(pos, baseRadius * 2.0, glowPaint);
      glowPaint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 20.0);

      // Core with radial gradient
      final gradient = ui.Gradient.radial(
        pos,
        baseRadius,
        [
          DS.brandPrimary.withAlpha(200),
          color.withAlpha(200),
          color.withAlpha(100),
        ],
        [0.0, 0.3, 1.0],
      );
      nodePaint.shader = gradient;
      canvas.drawCircle(pos, baseRadius, nodePaint);
      nodePaint.shader = null;

      // Sector name (larger)
      final textSpan = TextSpan(
        text: style.name,
        style: TextStyle(
          color: DS.brandPrimaryConst,
          fontSize: 16,
          fontWeight: FontWeight.bold,
          shadows: [
            Shadow(
              color: color,
              blurRadius: 8,
            ),
            Shadow(
              color: DS.brandPrimary.withAlpha(150),
              blurRadius: 4,
            ),
          ],
        ),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(canvas, pos + Offset(-textPainter.width / 2, baseRadius + 12));

      // Node count subtitle
      final countSpan = TextSpan(
        text: '${cluster.nodeCount} 个知识点',
        style: TextStyle(
          color: DS.brandPrimary.withAlpha(180),
          fontSize: 11,
        ),
      );
      final countPainter = TextPainter(
        text: countSpan,
        textDirection: TextDirection.ltr,
      );
      countPainter.layout();
      countPainter.paint(canvas, pos + Offset(-countPainter.width / 2, baseRadius + 30));
    }
  }

  /// Draw all nodes using preprocessed data
  void _drawNodes(Canvas canvas) {
    final nodePaint = Paint()..style = PaintingStyle.fill;
    final glowPaint = Paint()..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8.0);
    final ringPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    for (final processedNode in _processedNodes) {
      final node = processedNode.node;
      final pos = processedNode.position;
      final color = processedNode.color;
      final radius = processedNode.radius;

      // Get animation progress (0.0 to 1.0)
      final animationProgress = nodeAnimationProgress[node.id] ?? 1.0;

      // Apply bloom animation: scale and opacity
      final animatedRadius = radius * (0.3 + animationProgress * 0.7); // 0.3x to 1.0x
      final animatedOpacity = animationProgress;

      // LOD: Skip small nodes when zoomed out significantly
      if (scale < 0.3 && node.importance < 3) {
        nodePaint.color = color.withValues(alpha: 0.5 * animatedOpacity);
        canvas.drawCircle(pos, animatedRadius * 0.5, nodePaint);
        continue;
      }

      if (node.isUnlocked) {
        // Calculate mastery-based glow intensity
        final masteryFactor = node.masteryScore / 100.0;
        final glowIntensity = 0.3 + masteryFactor * 0.5;

        // Outer glow (soft, large) - scaled with animation
        if (scale > 0.5) { // Only draw glow if not too zoomed out
          glowPaint.color = color.withValues(alpha: glowIntensity * 0.4 * animatedOpacity);
          canvas.drawCircle(pos, animatedRadius * 3.0, glowPaint);
        }

        // Inner glow (brighter, smaller)
        glowPaint.color = color.withValues(alpha: glowIntensity * 0.7 * animatedOpacity);
        glowPaint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 4.0);
        canvas.drawCircle(pos, animatedRadius * 1.8, glowPaint);
        glowPaint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 8.0);

        // Core fill with gradient
        final nodeGradient = ui.Gradient.radial(
          pos,
          animatedRadius,
          [
            DS.brandPrimary.withValues(alpha: 0.9 * animatedOpacity),
            color.withValues(alpha: animatedOpacity),
            color.withValues(alpha: 0.8 * animatedOpacity),
          ],
          [0.0, 0.3, 1.0],
        );
        nodePaint.shader = nodeGradient;
        canvas.drawCircle(pos, animatedRadius, nodePaint);
        nodePaint.shader = null;

        // Progress Ring Logic (Study Count)
        // Only draw rings when animation is mostly complete (>= 0.7)
        if (scale > 0.4 && animationProgress > 0.7) {
          final ringRadius = animatedRadius * 1.6;

          if (node.studyCount >= 2) {
             // Full Energy Ring
             ringPaint
              ..color = color.withValues(alpha: 0.8 * animatedOpacity)
              ..strokeWidth = 2.0
              ..maskFilter = const MaskFilter.blur(BlurStyle.solid, 2.0);

             canvas.drawCircle(pos, ringRadius, ringPaint);

             // Extra "Pulse" ring for expansion ready
             ringPaint
              ..color = DS.brandPrimary.withValues(alpha: 0.5 * animatedOpacity)
              ..strokeWidth = 1.0
              ..maskFilter = null;
             canvas.drawCircle(pos, ringRadius * 1.1, ringPaint);

          } else if (node.studyCount == 1) {
             // Half Energy Ring
             ringPaint
              ..color = color.withValues(alpha: 0.6 * animatedOpacity)
              ..strokeWidth = 1.5
              ..maskFilter = null;

             canvas.drawArc(
               Rect.fromCircle(center: pos, radius: ringRadius),
               -math.pi / 2,
               math.pi,
               false,
               ringPaint,
             );
          }
        }

        // Bright center highlight (mastery indicator)
        if (masteryFactor > 0.5 && animationProgress > 0.5) {
          final highlightRadius = animatedRadius * 0.4 * masteryFactor;
          nodePaint.color = DS.brandPrimary.withValues(alpha: (0.6 + masteryFactor * 0.3) * animatedOpacity);
          canvas.drawCircle(pos, highlightRadius, nodePaint);
        }

      } else {
        // Locked: Grey dim with subtle indication
        nodePaint.color = DS.brandPrimary.withValues(alpha: 0.25 * animatedOpacity);
        canvas.drawCircle(pos, animatedRadius * 0.8, nodePaint);

        // Very subtle glow for locked nodes
        if (scale > 0.6) {
          glowPaint.color = DS.brandPrimary.withValues(alpha: 0.1 * animatedOpacity);
          canvas.drawCircle(pos, animatedRadius * 1.5, glowPaint);
        }
      }

      // Text Label (LOD)
      // Zoom > 0.8: Show all labels
      // Zoom > 0.5: Show importance >= 3
      // Zoom <= 0.5: Show importance >= 4 only
      var shouldDrawLabel = false;
      if (scale > 0.8) {
        shouldDrawLabel = true;
      } else if (scale > 0.5) {
        shouldDrawLabel = node.importance >= 3;
      } else {
        shouldDrawLabel = node.importance >= 4;
      }

      if (shouldDrawLabel) {
        _drawNodeLabel(canvas, node, pos, color);
      }
    }
  }

  /// Draw node label with sector-aware styling using cached text renderer
  void _drawNodeLabel(Canvas canvas, GalaxyNodeModel node, Offset pos, Color color) {
    final sectorStyle = SectorConfig.getStyle(node.sector);
    final textColor = node.isUnlocked
        ? DS.brandPrimary.withValues(alpha: 0.9)
        : DS.brandPrimary.withValues(alpha: 0.5);

    final style = TextStyle(
      color: textColor,
      fontSize: node.importance >= 4 ? 12 : 10,
      fontWeight: node.isUnlocked ? FontWeight.w600 : FontWeight.w400,
      shadows: node.isUnlocked
          ? [
              Shadow(
                color: sectorStyle.primaryColor.withValues(alpha: 0.6),
                blurRadius: 6,
              ),
              Shadow(
                color: DS.brandPrimary.withValues(alpha: 0.54),
                blurRadius: 2,
              ),
            ]
          : null,
    );

    // Use cached text renderer for better performance
    _textRenderer.drawText(
      canvas,
      node.name,
      pos + Offset(0, node.radius + 8),
      style,
      align: TextAlign.center,
    );
  }

  @override
  bool shouldRepaint(covariant StarMapPainter oldDelegate) {
    // 1. 视口变化检查（最频繁的变化）- 使用近似比较
    final viewportChanged = !_approxEqualRect(oldDelegate.viewport, viewport);
    if (viewportChanged) return true;

    // 2. 数据变化检查（次频繁）- 使用引用比较
    final dataChanged = !identical(oldDelegate.nodes, nodes) ||
        !identical(oldDelegate.edges, edges) ||
        !identical(oldDelegate.positions, positions);
    if (dataChanged) return true;

    // 3. 动画变化检查（特定动画）- 使用阈值比较
    final animationChanged = (selectionPulse - oldDelegate.selectionPulse).abs() > 0.01 ||
        !_mapsEqual(oldDelegate.nodeAnimationProgress, nodeAnimationProgress);
    if (animationChanged) return true;

    // 4. 聚合级别变化（较少发生）
    if (oldDelegate.aggregationLevel != aggregationLevel) return true;

    // 5. 选择状态变化
    if (oldDelegate.selectedNodeId != selectedNodeId) return true;

    // 6. 缩放变化 - 使用阈值
    if ((oldDelegate.scale - scale).abs() > 0.01) return true;

    // 7. 集群数据变化
    if (!identical(oldDelegate.clusters, clusters)) return true;

    return false;
  }

  /// 近似比较两个Rect
  static bool _approxEqualRect(Rect? a, Rect? b) {
    if (a == null && b == null) return true;
    if (a == null || b == null) return false;
    return (a.center.dx - b.center.dx).abs() < 1.0 &&
        (a.center.dy - b.center.dy).abs() < 1.0 &&
        (a.width - b.width).abs() < 1.0 &&
        (a.height - b.height).abs() < 1.0;
  }

  /// 比较两个Map是否相等
  static bool _mapsEqual<K, V>(Map<K, V> a, Map<K, V> b) {
    if (identical(a, b)) return true;
    if (a.length != b.length) return false;
    for (final key in a.keys) {
      if (!b.containsKey(key) || a[key] != b[key]) return false;
    }
    return true;
  }
}
