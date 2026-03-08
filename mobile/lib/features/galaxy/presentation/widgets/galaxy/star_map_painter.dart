import 'dart:collection';
import 'dart:developer' as developer;
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_camera.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class GalaxyLabelCache {
  GalaxyLabelCache({this.maxEntries = 600});

  final int maxEntries;
  final LinkedHashMap<String, TextPainter> _cache =
      LinkedHashMap<String, TextPainter>();

  void clear() => _cache.clear();

  TextPainter obtain({
    required String cacheKey,
    required String text,
    required double fontSize,
    required FontWeight fontWeight,
    required Color color,
    double maxWidth = 160,
  }) {
    final cached = _cache.remove(cacheKey);
    if (cached != null) {
      _cache[cacheKey] = cached;
      return cached;
    }

    final painter = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          color: color,
          fontSize: fontSize,
          fontWeight: fontWeight,
        ),
      ),
      maxLines: 1,
      ellipsis: '…',
      textDirection: TextDirection.ltr,
    )..layout(maxWidth: maxWidth);

    _cache[cacheKey] = painter;
    while (_cache.length > maxEntries) {
      _cache.remove(_cache.keys.first);
    }

    return painter;
  }
}

class GalaxyEdgePictureCache {
  GalaxyEdgePictureCache({
    this.panThresholdPx = 50,
    this.scaleThreshold = 0.05,
  });

  final double panThresholdPx;
  final double scaleThreshold;

  ui.Picture? _picture;
  Offset? _offset;
  double? _scale;
  int? _sceneSignature;
  GalaxyLod? _lod;

  void clear() {
    _picture?.dispose();
    _picture = null;
    _offset = null;
    _scale = null;
    _sceneSignature = null;
    _lod = null;
  }

  bool canReuse({
    required GalaxyCamera camera,
    required int sceneSignature,
    required GalaxyLod lod,
  }) {
    if (_picture == null ||
        _offset == null ||
        _scale == null ||
        _sceneSignature != sceneSignature ||
        _lod != lod) {
      return false;
    }

    final panDelta = (camera.offset - _offset!).distance;
    final scaleDelta = ((camera.scale - _scale!) / _scale!).abs();
    return panDelta <= panThresholdPx && scaleDelta <= scaleThreshold;
  }

  void draw(Canvas canvas, GalaxyCamera camera) {
    final picture = _picture;
    final offset = _offset;
    final scale = _scale;
    if (picture == null || offset == null || scale == null) {
      return;
    }

    final scaleRatio = camera.scale / scale;
    final translatedOffset = Offset(
      camera.offset.dx - offset.dx * scaleRatio,
      camera.offset.dy - offset.dy * scaleRatio,
    );

    canvas
      ..save()
      ..translate(translatedOffset.dx, translatedOffset.dy)
      ..scale(scaleRatio)
      ..drawPicture(picture)
      ..restore();
  }

  void store({
    required ui.Picture picture,
    required GalaxyCamera camera,
    required int sceneSignature,
    required GalaxyLod lod,
  }) {
    clear();
    _picture = picture;
    _offset = camera.offset;
    _scale = camera.scale;
    _sceneSignature = sceneSignature;
    _lod = lod;
  }
}

class StarMapPainter extends CustomPainter {
  StarMapPainter({
    required this.camera,
    required this.nodesById,
    required this.edges,
    required this.positions,
    required this.spatialIndex,
    required this.labelCache,
    required this.edgePictureCache,
    required this.sceneVersion,
    required this.isDarkMode,
    this.selectedNodeId,
    this.draggingNodeId,
    this.tapFeedbackNodeId,
    this.tapFeedbackProgress = 0,
  });

  final GalaxyCamera camera;
  final Map<String, GalaxyNodeModel> nodesById;
  final List<GalaxyEdgeModel> edges;
  final Map<String, Offset> positions;
  final GalaxySpatialIndex spatialIndex;
  final GalaxyLabelCache labelCache;
  final GalaxyEdgePictureCache edgePictureCache;
  final int sceneVersion;
  final bool isDarkMode;
  final String? selectedNodeId;
  final String? draggingNodeId;
  final String? tapFeedbackNodeId;
  final double tapFeedbackProgress;

  static const int _nodeBudget = 500;
  static const int _edgeBudget = 800;
  static const Color _darkBackground = Color(0xFF0A0E17);
  static const Color _darkRadial = Color(0xFF0D1525);
  static const Color _lightBackground = Color(0xFFF5F6F8);
  static const Color _lightRadial = Color(0xFFEBEDF2);

  @override
  void paint(Canvas canvas, Size size) {
    developer.Timeline.startSync('GalaxyPaint');
    try {
      _drawBackground(canvas, size);

      final lod = _currentLod(camera.scale);
      final viewport = camera.viewportRect.inflate(_viewportPaddingFor(lod));
      final viewportCenter = viewport.center;
      final candidateNodeIds = spatialIndex.queryRect(viewport);
      final visibleNodes = _selectVisibleNodes(
        candidateNodeIds: candidateNodeIds,
        lod: lod,
        viewportCenter: viewportCenter,
      );
      final visibleNodeIds = {
        for (final node in visibleNodes) node.node.id,
      };

      developer.Timeline.startSync('GalaxyPaintEdges');
      try {
        _drawEdges(
          canvas: canvas,
          lod: lod,
          viewport: viewport,
          viewportCenter: viewportCenter,
          visibleNodeIds: visibleNodeIds,
        );
      } finally {
        developer.Timeline.finishSync();
      }

      developer.Timeline.startSync('GalaxyPaintNodes');
      try {
        _drawNodes(canvas, lod, visibleNodes);
      } finally {
        developer.Timeline.finishSync();
      }

      developer.Timeline.startSync('GalaxyPaintLabels');
      try {
        _drawLabels(canvas, lod, visibleNodes);
      } finally {
        developer.Timeline.finishSync();
      }
    } finally {
      developer.Timeline.finishSync();
    }
  }

  @override
  bool shouldRepaint(covariant StarMapPainter oldDelegate) =>
      oldDelegate.camera.offset != camera.offset ||
      oldDelegate.camera.scale != camera.scale ||
      oldDelegate.camera.viewportSize != camera.viewportSize ||
      oldDelegate.positions != positions ||
      oldDelegate.sceneVersion != sceneVersion ||
      oldDelegate.selectedNodeId != selectedNodeId ||
      oldDelegate.draggingNodeId != draggingNodeId ||
      oldDelegate.tapFeedbackNodeId != tapFeedbackNodeId ||
      oldDelegate.tapFeedbackProgress != tapFeedbackProgress ||
      oldDelegate.isDarkMode != isDarkMode;

  void _drawBackground(Canvas canvas, Size size) {
    final baseColor = isDarkMode ? _darkBackground : _lightBackground;
    final radialColor = isDarkMode ? _darkRadial : _lightRadial;
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.shortestSide * 0.72;
    final radialPaint = Paint()
      ..shader = ui.Gradient.radial(
        center,
        radius,
        [
          radialColor.withValues(alpha: isDarkMode ? 0.34 : 0.26),
          radialColor.withValues(alpha: isDarkMode ? 0.08 : 0.05),
          Colors.transparent,
        ],
        const [0.0, 0.68, 1.0],
      );

    canvas
      ..drawRect(Offset.zero & size, Paint()..color = baseColor)
      ..drawCircle(center, radius, radialPaint);
  }

  List<_PaintNode> _selectVisibleNodes({
    required List<String> candidateNodeIds,
    required GalaxyLod lod,
    required Offset viewportCenter,
  }) {
    final nodes = <_PaintNode>[];

    for (final nodeId in candidateNodeIds) {
      final node = nodesById[nodeId];
      final position = positions[nodeId];
      if (node == null || position == null) {
        continue;
      }

      final alpha = _nodeAlpha(node, lod);
      if (alpha <= 0) {
        continue;
      }

      nodes.add(
        _PaintNode(
          node: node,
          worldPosition: position,
          screenPosition: camera.worldToScreen(position),
          distanceToViewportCenter: (position - viewportCenter).distanceSquared,
          alpha: alpha,
        ),
      );
    }

    nodes.sort(
      (a, b) =>
          a.distanceToViewportCenter.compareTo(b.distanceToViewportCenter),
    );

    final budget = _nodeBudgetFor(lod);
    if (nodes.length > budget) {
      nodes.removeRange(budget, nodes.length);
    }

    return nodes;
  }

  void _drawEdges({
    required Canvas canvas,
    required GalaxyLod lod,
    required Rect viewport,
    required Offset viewportCenter,
    required Set<String> visibleNodeIds,
  }) {
    if (lod == GalaxyLod.l0 || edges.isEmpty) {
      return;
    }

    final edgesToDraw = _selectVisibleEdges(
      lod: lod,
      viewport: viewport,
      viewportCenter: viewportCenter,
      visibleNodeIds: visibleNodeIds,
    );
    if (edgesToDraw.isEmpty) {
      edgePictureCache.clear();
      return;
    }

    if (draggingNodeId != null) {
      _drawEdgeList(canvas, edgesToDraw);
      return;
    }

    final sceneSignature = Object.hash(
      sceneVersion,
      selectedNodeId,
      lod,
      isDarkMode,
      visibleNodeIds.length,
    );

    if (edgePictureCache.canReuse(
      camera: camera,
      sceneSignature: sceneSignature,
      lod: lod,
    )) {
      edgePictureCache.draw(canvas, camera);
      return;
    }

    final recorder = ui.PictureRecorder();
    final pictureCanvas = Canvas(recorder);
    _drawEdgeList(pictureCanvas, edgesToDraw);
    edgePictureCache
      ..store(
        picture: recorder.endRecording(),
        camera: camera,
        sceneSignature: sceneSignature,
        lod: lod,
      )
      ..draw(canvas, camera);
  }

  List<_PaintEdge> _selectVisibleEdges({
    required GalaxyLod lod,
    required Rect viewport,
    required Offset viewportCenter,
    required Set<String> visibleNodeIds,
  }) {
    final bothVisible = <_PaintEdge>[];
    final partiallyVisible = <_PaintEdge>[];

    for (final edge in edges) {
      if (!_edgeVisibleAtLod(edge, lod)) {
        continue;
      }

      final source = positions[edge.sourceId];
      final target = positions[edge.targetId];
      final sourceNode = nodesById[edge.sourceId];
      if (source == null || target == null || sourceNode == null) {
        continue;
      }

      final sourceVisible = visibleNodeIds.contains(edge.sourceId);
      final targetVisible = visibleNodeIds.contains(edge.targetId);
      final intersectsViewport =
          _segmentIntersectsRect(source, target, viewport);
      if (!sourceVisible && !targetVisible && !intersectsViewport) {
        continue;
      }

      final edgeStyle = _edgeStyle(edge, sourceNode.sector);
      final alpha = edgeStyle.alpha * _edgeAlpha(edge, lod);
      if (alpha <= 0) {
        continue;
      }

      final midX = (source.dx + target.dx) / 2;
      final midY = (source.dy + target.dy) / 2;
      final paintEdge = _PaintEdge(
        start: source,
        end: target,
        distanceToViewportCenter:
            (midX - viewportCenter.dx) * (midX - viewportCenter.dx) +
                (midY - viewportCenter.dy) * (midY - viewportCenter.dy),
        color: edgeStyle.color.withValues(alpha: alpha),
        strokeWidth: edgeStyle.strokeWidth,
        dashLength: edgeStyle.dashLength,
        gapLength: edgeStyle.gapLength,
      );

      if (sourceVisible && targetVisible) {
        bothVisible.add(paintEdge);
      } else {
        partiallyVisible.add(paintEdge);
      }
    }

    bothVisible.sort(
      (a, b) =>
          a.distanceToViewportCenter.compareTo(b.distanceToViewportCenter),
    );
    partiallyVisible.sort(
      (a, b) =>
          a.distanceToViewportCenter.compareTo(b.distanceToViewportCenter),
    );

    final result = <_PaintEdge>[...bothVisible, ...partiallyVisible];
    final budget = _edgeBudgetFor(lod);
    if (result.length > budget) {
      result.removeRange(budget, result.length);
    }

    return result;
  }

  void _drawEdgeList(Canvas canvas, List<_PaintEdge> edgesToDraw) {
    final paintCache = <int, Paint>{};

    for (final edge in edgesToDraw) {
      final paintKey = Object.hash(edge.color.toARGB32(), edge.strokeWidth);
      final paint = paintCache[paintKey] ??
          (paintCache[paintKey] = Paint()
            ..color = edge.color
            ..strokeWidth = edge.strokeWidth
            ..style = PaintingStyle.stroke
            ..strokeCap = StrokeCap.round);

      final start = camera.worldToScreen(edge.start);
      final end = camera.worldToScreen(edge.end);
      if (edge.isDashed) {
        _drawDashedLine(
          canvas: canvas,
          start: start,
          end: end,
          paint: paint,
          dashLength: edge.dashLength,
          gapLength: edge.gapLength,
        );
      } else {
        canvas.drawLine(start, end, paint);
      }
    }
  }

  void _drawNodes(Canvas canvas, GalaxyLod lod, List<_PaintNode> nodes) {
    for (final item in nodes) {
      final node = item.node;
      final isDragging = draggingNodeId == node.id;
      final radius = _effectiveNodeRadius(node, lod, isDragging);
      final style = _nodeStyle(node, lod, isDragging);
      final nodeAlpha = item.alpha.clamp(0.0, 1.0);

      if (style.glowAlpha > 0 &&
          nodeAlpha > 0 &&
          lod.index >= GalaxyLod.l2.index) {
        canvas.drawCircle(
          item.screenPosition,
          radius + 3,
          Paint()
            ..color = style.baseColor.withValues(
              alpha: style.glowAlpha * nodeAlpha,
            )
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4),
        );
      }

      if (style.fillAlpha > 0 && nodeAlpha > 0) {
        canvas.drawCircle(
          item.screenPosition,
          radius,
          Paint()
            ..color = style.baseColor.withValues(
              alpha: style.fillAlpha * nodeAlpha,
            ),
        );
      }

      if (style.masteryRingAlpha > 0 && nodeAlpha > 0) {
        canvas.drawCircle(
          item.screenPosition,
          radius + 1.5,
          Paint()
            ..color = style.baseColor.withValues(
              alpha: style.masteryRingAlpha * nodeAlpha,
            )
            ..strokeWidth = 1.5
            ..style = PaintingStyle.stroke,
        );
      }

      if (!node.isUnlocked) {
        _drawDashedCircle(
          canvas: canvas,
          center: item.screenPosition,
          radius: radius + 1,
          color: style.baseColor.withValues(alpha: 0.25 * nodeAlpha),
        );
      }

      if (selectedNodeId == node.id) {
        final selectedPaint = Paint()
          ..color = (isDarkMode ? Colors.white : Colors.black).withValues(
            alpha: nodeAlpha,
          )
          ..strokeWidth = 2
          ..style = PaintingStyle.stroke;
        canvas.drawCircle(
          item.screenPosition,
          radius + 4,
          selectedPaint,
        );
      }
    }
  }

  void _drawLabels(Canvas canvas, GalaxyLod lod, List<_PaintNode> nodes) {
    for (final item in nodes) {
      final node = item.node;
      final labelAlpha = _labelAlpha(node, lod);
      if (labelAlpha <= 0) {
        continue;
      }

      final isSelected = selectedNodeId == node.id;
      final fontSize = lod.index >= GalaxyLod.l3.index && node.importance >= 4
          ? 13.0
          : camera.scale > 1.0
              ? 12.0
              : 10.0;
      final fontWeight = isSelected ? FontWeight.w700 : FontWeight.w600;
      final labelColor = (isDarkMode ? Colors.white : Colors.black87)
          .withValues(alpha: labelAlpha);
      final cacheKey =
          '${node.id}:$fontSize:${fontWeight.value}:${labelColor.toARGB32()}';
      final labelPainter = labelCache.obtain(
        cacheKey: cacheKey,
        text: node.name,
        fontSize: fontSize,
        fontWeight: fontWeight,
        color: labelColor,
      );
      final radius = _effectiveNodeRadius(node, lod, draggingNodeId == node.id);
      final labelOffset = Offset(
        item.screenPosition.dx + radius + 6,
        item.screenPosition.dy - labelPainter.height / 2,
      );

      if (isSelected) {
        final backgroundRect = RRect.fromRectAndRadius(
          Rect.fromLTWH(
            labelOffset.dx - 6,
            labelOffset.dy - 3,
            labelPainter.width + 12,
            labelPainter.height + 6,
          ),
          const Radius.circular(6),
        );
        canvas.drawRRect(
          backgroundRect,
          Paint()
            ..color = (isDarkMode ? _darkBackground : Colors.white)
                .withValues(alpha: 0.72 * labelAlpha),
        );
      }

      labelPainter.paint(canvas, labelOffset);

      if (lod == GalaxyLod.l4) {
        final barColor =
            SectorConfig.getColor(node.sector).withValues(alpha: 0.9);
        final barTrackColor = (isDarkMode ? Colors.white24 : Colors.black12);
        final barOffset = Offset(
          labelOffset.dx,
          labelOffset.dy + labelPainter.height + 4,
        );
        const barWidth = 40.0;
        final progressRatio = (node.masteryScore / 100).clamp(0.0, 1.0);
        final progressWidth = barWidth * progressRatio;

        canvas
          ..drawRRect(
            RRect.fromRectAndRadius(
              Rect.fromLTWH(barOffset.dx, barOffset.dy, barWidth, 3),
              const Radius.circular(999),
            ),
            Paint()..color = barTrackColor,
          )
          ..drawRRect(
            RRect.fromRectAndRadius(
              Rect.fromLTWH(barOffset.dx, barOffset.dy, progressWidth, 3),
              const Radius.circular(999),
            ),
            Paint()..color = barColor,
          );
      }
    }
  }

  GalaxyLod _currentLod(double scale) {
    if (scale < 0.12) {
      return GalaxyLod.l0;
    }
    if (scale < 0.25) {
      return GalaxyLod.l1;
    }
    if (scale < 0.5) {
      return GalaxyLod.l2;
    }
    if (scale <= 1.0) {
      return GalaxyLod.l3;
    }
    return GalaxyLod.l4;
  }

  int _nodeBudgetFor(GalaxyLod lod) {
    switch (lod) {
      case GalaxyLod.l0:
        return 24;
      case GalaxyLod.l1:
        return 48;
      case GalaxyLod.l2:
      case GalaxyLod.l3:
      case GalaxyLod.l4:
        return _nodeBudget;
    }
  }

  int _edgeBudgetFor(GalaxyLod lod) {
    switch (lod) {
      case GalaxyLod.l0:
        return 0;
      case GalaxyLod.l1:
        return 180;
      case GalaxyLod.l2:
        return 420;
      case GalaxyLod.l3:
      case GalaxyLod.l4:
        return _edgeBudget;
    }
  }

  double _viewportPaddingFor(GalaxyLod lod) {
    switch (lod) {
      case GalaxyLod.l0:
      case GalaxyLod.l1:
        return 240 / camera.scale;
      case GalaxyLod.l2:
      case GalaxyLod.l3:
      case GalaxyLod.l4:
        return 180 / camera.scale;
    }
  }

  double _nodeAlpha(GalaxyNodeModel node, GalaxyLod lod) {
    switch (lod) {
      case GalaxyLod.l0:
        return node.importance >= 5 ? 1 : 0;
      case GalaxyLod.l1:
        if (node.importance >= 5) {
          return 1;
        }
        if (node.importance >= 3) {
          return _fade(camera.scale, 0.12, 0.25);
        }
        return 0;
      case GalaxyLod.l2:
        if (node.importance >= 3) {
          return 1;
        }
        return _fade(camera.scale, 0.25, 0.5);
      case GalaxyLod.l3:
      case GalaxyLod.l4:
        return 1;
    }
  }

  double _labelAlpha(GalaxyNodeModel node, GalaxyLod lod) {
    switch (lod) {
      case GalaxyLod.l0:
        return 0;
      case GalaxyLod.l1:
        return node.importance >= 5 ? _fade(camera.scale, 0.12, 0.2) : 0;
      case GalaxyLod.l2:
        if (node.importance >= 5) {
          return 1;
        }
        if (node.importance >= 3) {
          return _fade(camera.scale, 0.25, 0.5);
        }
        return 0;
      case GalaxyLod.l3:
      case GalaxyLod.l4:
        return 1;
    }
  }

  double _edgeAlpha(GalaxyEdgeModel edge, GalaxyLod lod) {
    switch (lod) {
      case GalaxyLod.l0:
        return 0;
      case GalaxyLod.l1:
        return edge.relationType == EdgeRelationType.parentChild
            ? _fade(camera.scale, 0.12, 0.25)
            : 0;
      case GalaxyLod.l2:
        if (edge.relationType == EdgeRelationType.parentChild) {
          return 1;
        }
        if (edge.relationType == EdgeRelationType.prerequisite) {
          return _fade(camera.scale, 0.25, 0.5);
        }
        return 0;
      case GalaxyLod.l3:
      case GalaxyLod.l4:
        return 1;
    }
  }

  bool _edgeVisibleAtLod(GalaxyEdgeModel edge, GalaxyLod lod) {
    switch (lod) {
      case GalaxyLod.l0:
        return false;
      case GalaxyLod.l1:
        return edge.relationType == EdgeRelationType.parentChild;
      case GalaxyLod.l2:
        return edge.relationType == EdgeRelationType.parentChild ||
            edge.relationType == EdgeRelationType.prerequisite;
      case GalaxyLod.l3:
      case GalaxyLod.l4:
        return true;
    }
  }

  _PaintEdgeStyle _edgeStyle(GalaxyEdgeModel edge, SectorEnum sourceSector) {
    switch (edge.relationType) {
      case EdgeRelationType.parentChild:
        return _PaintEdgeStyle(
          color: SectorConfig.getColor(sourceSector),
          strokeWidth: 1.2,
          alpha: 0.45,
        );
      case EdgeRelationType.prerequisite:
        return _PaintEdgeStyle(
          color: isDarkMode ? const Color(0xFF64B5F6) : const Color(0xFF1565C0),
          strokeWidth: 1.0,
          alpha: 0.4,
        );
      case EdgeRelationType.derived:
        return _PaintEdgeStyle(
          color: isDarkMode ? const Color(0xFF81C784) : const Color(0xFF2E7D32),
          strokeWidth: 1.0,
          alpha: 0.35,
        );
      case EdgeRelationType.related:
        return _PaintEdgeStyle(
          color: isDarkMode ? const Color(0xFFFFB74D) : const Color(0xFFE65100),
          strokeWidth: 0.8,
          alpha: 0.3,
          dashLength: 8,
          gapLength: 4,
        );
      case EdgeRelationType.similar:
        return _PaintEdgeStyle(
          color: isDarkMode ? const Color(0xFFCE93D8) : const Color(0xFF6A1B9A),
          strokeWidth: 0.8,
          alpha: 0.25,
          dashLength: 4,
          gapLength: 4,
        );
      default:
        return _PaintEdgeStyle(
          color: isDarkMode ? Colors.white38 : Colors.black26,
          strokeWidth: 0.6,
          alpha: 0.2,
          dashLength: 4,
          gapLength: 6,
        );
    }
  }

  _PaintNodeStyle _nodeStyle(
    GalaxyNodeModel node,
    GalaxyLod lod,
    bool isDragging,
  ) {
    final baseColor = SectorConfig.getColor(node.sector);
    final mastery = node.masteryScore;
    if (!node.isUnlocked) {
      return _PaintNodeStyle(
        baseColor: baseColor,
        fillAlpha: 0,
        masteryRingAlpha: 0,
        glowAlpha: 0,
      );
    }

    double fillAlpha;
    double masteryRingAlpha;
    double glowAlpha = 0;

    if (mastery < 30) {
      fillAlpha = 0.35;
      masteryRingAlpha = 0;
    } else if (mastery < 60) {
      fillAlpha = 0.6;
      masteryRingAlpha = 0;
    } else if (mastery < 85) {
      fillAlpha = 0.85;
      masteryRingAlpha = 0.4;
    } else {
      fillAlpha = 0.95;
      masteryRingAlpha = 0.7;
      glowAlpha = lod.index >= GalaxyLod.l2.index ? 0.15 : 0;
    }

    if (isDragging) {
      fillAlpha = 0.85;
      masteryRingAlpha = math.max(masteryRingAlpha, 0.45);
    }

    return _PaintNodeStyle(
      baseColor: baseColor,
      fillAlpha: fillAlpha,
      masteryRingAlpha: masteryRingAlpha,
      glowAlpha: glowAlpha,
    );
  }

  double _effectiveNodeRadius(
    GalaxyNodeModel node,
    GalaxyLod lod,
    bool isDragging,
  ) {
    var radius = _nodeRadius(node, lod);
    if (tapFeedbackNodeId == node.id) {
      radius *= 1 + 0.3 * tapFeedbackProgress;
    }
    if (isDragging) {
      radius *= 1.2;
    }
    return radius;
  }

  double _nodeRadius(GalaxyNodeModel node, GalaxyLod lod) {
    final base = math.max(4.0, node.radius * camera.scale.clamp(0.75, 1.5));
    switch (lod) {
      case GalaxyLod.l0:
        return base + node.importance;
      case GalaxyLod.l1:
      case GalaxyLod.l2:
      case GalaxyLod.l3:
      case GalaxyLod.l4:
        return base;
    }
  }

  void _drawDashedLine({
    required Canvas canvas,
    required Offset start,
    required Offset end,
    required Paint paint,
    required double dashLength,
    required double gapLength,
  }) {
    final path = Path()
      ..moveTo(start.dx, start.dy)
      ..lineTo(end.dx, end.dy);

    for (final metric in path.computeMetrics()) {
      double distance = 0;
      while (distance < metric.length) {
        final next = math.min(distance + dashLength, metric.length);
        final extract = metric.extractPath(distance, next);
        canvas.drawPath(extract, paint);
        distance += dashLength + gapLength;
      }
    }
  }

  void _drawDashedCircle({
    required Canvas canvas,
    required Offset center,
    required double radius,
    required Color color,
  }) {
    final path = Path()
      ..addOval(Rect.fromCircle(center: center, radius: radius));
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;

    for (final metric in path.computeMetrics()) {
      double distance = 0;
      while (distance < metric.length) {
        final next = math.min(distance + 5, metric.length);
        canvas.drawPath(metric.extractPath(distance, next), paint);
        distance += 8;
      }
    }
  }

  double _fade(double value, double start, double end) {
    if (value <= start) {
      return 0;
    }
    if (value >= end) {
      return 1;
    }
    return ((value - start) / (end - start)).clamp(0, 1);
  }

  bool _segmentIntersectsRect(Offset a, Offset b, Rect rect) {
    if (rect.contains(a) || rect.contains(b)) {
      return true;
    }

    return Rect.fromPoints(a, b).overlaps(rect);
  }
}

enum GalaxyLod {
  l0,
  l1,
  l2,
  l3,
  l4,
}

class _PaintNode {
  const _PaintNode({
    required this.node,
    required this.worldPosition,
    required this.screenPosition,
    required this.distanceToViewportCenter,
    required this.alpha,
  });

  final GalaxyNodeModel node;
  final Offset worldPosition;
  final Offset screenPosition;
  final double distanceToViewportCenter;
  final double alpha;
}

class _PaintEdge {
  const _PaintEdge({
    required this.start,
    required this.end,
    required this.distanceToViewportCenter,
    required this.color,
    required this.strokeWidth,
    required this.dashLength,
    required this.gapLength,
  });

  final Offset start;
  final Offset end;
  final double distanceToViewportCenter;
  final Color color;
  final double strokeWidth;
  final double dashLength;
  final double gapLength;

  bool get isDashed => dashLength > 0;
}

class _PaintEdgeStyle {
  const _PaintEdgeStyle({
    required this.color,
    required this.strokeWidth,
    required this.alpha,
    this.dashLength = 0,
    this.gapLength = 0,
  });

  final Color color;
  final double strokeWidth;
  final double alpha;
  final double dashLength;
  final double gapLength;
}

class _PaintNodeStyle {
  const _PaintNodeStyle({
    required this.baseColor,
    required this.fillAlpha,
    required this.masteryRingAlpha,
    required this.glowAlpha,
  });

  final Color baseColor;
  final double fillAlpha;
  final double masteryRingAlpha;
  final double glowAlpha;
}
