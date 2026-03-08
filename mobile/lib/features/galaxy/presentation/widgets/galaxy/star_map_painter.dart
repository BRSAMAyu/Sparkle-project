import 'dart:collection';
import 'dart:developer' as developer;
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_camera.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

GalaxyLod resolveGalaxyLod(double scale) {
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

double galaxyLodFade(double value, double start, double end) {
  if (value <= start) {
    return 0;
  }
  if (value >= end) {
    return 1;
  }
  return ((value - start) / (end - start)).clamp(0, 1);
}

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
          letterSpacing: 0.1,
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
    this.panThresholdPx = 100,
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
    required this.worldBounds,
    required this.blendedColors,
    required this.revealRanks,
    this.focusNodeIds = const <String>{},
    this.searchMatchedNodeIds = const <String>{},
    this.driftOffsets = const <String, Offset>{},
    this.edgeParticles = const <GalaxyEdgeParticle>[],
    this.celebrationNodeIds = const <String>{},
    this.performanceDegraded = false,
    this.selectedNodeId,
    this.draggingNodeId,
    this.tapFeedbackNodeId,
    this.tapFeedbackProgress = 0,
    this.ambientPhase = 0,
    this.buildRevealProgress = 1,
    this.isBuildAnimating = false,
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
  final Rect worldBounds;
  final Map<String, Color> blendedColors;
  final Map<String, int> revealRanks;
  final Set<String> focusNodeIds;
  final Set<String> searchMatchedNodeIds;
  final Map<String, Offset> driftOffsets;
  final List<GalaxyEdgeParticle> edgeParticles;
  final Set<String> celebrationNodeIds;
  final bool performanceDegraded;
  final String? selectedNodeId;
  final String? draggingNodeId;
  final String? tapFeedbackNodeId;
  final double tapFeedbackProgress;
  final double ambientPhase;
  final double buildRevealProgress;
  final bool isBuildAnimating;

  static const int _nodeBudget = 500;
  static const int _edgeBudget = 800;
  static const Color _darkBackground = Color(0xFF0A0E17);
  static const Color _darkRadial = Color(0xFF0D1525);
  static const Color _lightBackground = Color(0xFFF5F6F8);
  static const Color _lightRadial = Color(0xFFEBEDF2);

  @override
  void paint(Canvas canvas, Size size) {
    developer.Timeline.startSync(
      'GalaxyPaint',
      arguments: {
        'scale': camera.scale,
        'sceneVersion': sceneVersion,
        'searchMatches': searchMatchedNodeIds.length,
        'particles': edgeParticles.length,
      },
    );
    try {
      final lod = _currentLod(camera.scale);
      _drawBackground(canvas, size);
      _drawSectorAtmosphere(canvas, size, lod);

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

      developer.Timeline.startSync(
        'GalaxyPaintEdges',
        arguments: {
          'lod': lod.name,
          'candidateNodes': candidateNodeIds.length,
          'visibleNodes': visibleNodes.length,
        },
      );
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

      if (edgeParticles.isNotEmpty) {
        _drawEdgeParticles(canvas);
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
      oldDelegate.isDarkMode != isDarkMode ||
      oldDelegate.worldBounds != worldBounds ||
      oldDelegate.blendedColors != blendedColors ||
      oldDelegate.revealRanks != revealRanks ||
      oldDelegate.focusNodeIds != focusNodeIds ||
      oldDelegate.searchMatchedNodeIds != searchMatchedNodeIds ||
      oldDelegate.driftOffsets != driftOffsets ||
      oldDelegate.edgeParticles != edgeParticles ||
      oldDelegate.celebrationNodeIds != celebrationNodeIds ||
      oldDelegate.performanceDegraded != performanceDegraded ||
      oldDelegate.ambientPhase != ambientPhase ||
      oldDelegate.buildRevealProgress != buildRevealProgress ||
      oldDelegate.isBuildAnimating != isBuildAnimating;

  void _drawBackground(Canvas canvas, Size size) {
    final baseColor = isDarkMode ? _darkBackground : _lightBackground;
    final radialColor = isDarkMode ? _darkRadial : _lightRadial;
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.shortestSide * 0.74;
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
    _drawNebulaClouds(canvas, size);
    _drawStarLayer(
      canvas,
      size,
      seed: 17,
      count: isDarkMode ? 180 : 120,
      parallaxFactor: 0.10,
      minRadius: 0.45,
      maxRadius: 1.2,
      minAlpha: isDarkMode ? 0.05 : 0.025,
      maxAlpha: isDarkMode ? 0.14 : 0.055,
    );
    _drawStarLayer(
      canvas,
      size,
      seed: 29,
      count: isDarkMode ? 84 : 56,
      parallaxFactor: 0.18,
      minRadius: 0.8,
      maxRadius: 1.8,
      minAlpha: isDarkMode ? 0.12 : 0.04,
      maxAlpha: isDarkMode ? 0.28 : 0.09,
      twinkleStrength: 0.2,
    );
    _drawStarLayer(
      canvas,
      size,
      seed: 43,
      count: isDarkMode ? 28 : 18,
      parallaxFactor: 0.28,
      minRadius: 1.1,
      maxRadius: 2.4,
      minAlpha: isDarkMode ? 0.18 : 0.06,
      maxAlpha: isDarkMode ? 0.34 : 0.12,
      twinkleStrength: 0.3,
      allowGlints: true,
    );
  }

  void _drawSectorAtmosphere(Canvas canvas, Size size, GalaxyLod lod) {
    if (lod.index > GalaxyLod.l1.index) {
      return;
    }

    final visibility = 1 - _fade(camera.scale, 0.22, 0.45);
    if (visibility <= 0) {
      return;
    }

    final origin = camera.worldToScreen(Offset.zero);
    final outerRadiusWorld = _worldRadius + 260;
    final innerRadiusPx = math.max(20.0, 120 * camera.scale);
    final outerRadiusPx =
        math.max(innerRadiusPx + 24, outerRadiusWorld * camera.scale);
    final labelAlpha = visibility * (isDarkMode ? 0.82 : 0.6);

    for (final entry in SectorConfig.styles.entries) {
      final style = entry.value;
      final primary = style.primaryColorFor(isDarkMode: isDarkMode);
      final glow = style.glowColorFor(isDarkMode: isDarkMode);
      final wedge = _sectorPath(
        center: origin,
        startAngleDegrees: style.baseAngle - 90,
        sweepAngleDegrees: style.sweepAngle,
        innerRadius: innerRadiusPx,
        outerRadius: outerRadiusPx,
      );
      final startRadians = (style.baseAngle - 90) * math.pi / 180;
      final endRadians =
          (style.baseAngle + style.sweepAngle - 90) * math.pi / 180;
      final atmosphereAlpha = visibility * (isDarkMode ? 0.12 : 0.07);
      final boundaryAlpha = visibility * (isDarkMode ? 0.09 : 0.055);
      final outerRect = Rect.fromCircle(center: origin, radius: outerRadiusPx);
      final innerStart = Offset(
        origin.dx + math.cos(startRadians) * innerRadiusPx,
        origin.dy + math.sin(startRadians) * innerRadiusPx,
      );
      final innerEnd = Offset(
        origin.dx + math.cos(endRadians) * innerRadiusPx,
        origin.dy + math.sin(endRadians) * innerRadiusPx,
      );
      final outerStart = Offset(
        origin.dx + math.cos(startRadians) * outerRadiusPx,
        origin.dy + math.sin(startRadians) * outerRadiusPx,
      );
      final outerEnd = Offset(
        origin.dx + math.cos(endRadians) * outerRadiusPx,
        origin.dy + math.sin(endRadians) * outerRadiusPx,
      );

      canvas.drawPath(
        wedge,
        Paint()
          ..shader = ui.Gradient.radial(
            origin,
            outerRadiusPx,
            [
              glow.withValues(alpha: atmosphereAlpha * 1.05),
              primary.withValues(alpha: atmosphereAlpha * 0.92),
              primary.withValues(alpha: atmosphereAlpha * 0.48),
              Colors.transparent,
            ],
            const [0.0, 0.34, 0.76, 1.0],
          )
          ..maskFilter = MaskFilter.blur(
            BlurStyle.normal,
            isDarkMode ? 46 : 36,
          ),
      );

      final atmosphereLiftPaint = Paint()
        ..color = glow.withValues(alpha: atmosphereAlpha * 0.22)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 18);
      final boundaryPaint = Paint()
        ..color = glow.withValues(alpha: boundaryAlpha)
        ..strokeWidth = isDarkMode ? 1.1 : 0.9
        ..style = PaintingStyle.stroke
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.5);
      canvas
        ..drawPath(wedge, atmosphereLiftPaint)
        ..drawArc(
          outerRect,
          startRadians,
          style.sweepAngle * math.pi / 180,
          false,
          boundaryPaint,
        )
        ..drawLine(innerStart, outerStart, boundaryPaint)
        ..drawLine(innerEnd, outerEnd, boundaryPaint);

      final labelAngleRadians =
          (style.baseAngle + style.sweepAngle / 2 - 90) * math.pi / 180;
      final labelRadius =
          innerRadiusPx + (outerRadiusPx - innerRadiusPx) * 0.54;
      final labelPosition = Offset(
        origin.dx + math.cos(labelAngleRadians) * labelRadius,
        origin.dy + math.sin(labelAngleRadians) * labelRadius,
      );

      final textPainter = TextPainter(
        text: TextSpan(
          text: style.name,
          style: TextStyle(
            color: glow.withValues(alpha: labelAlpha * 0.8),
            fontSize: isDarkMode ? 13 : 12,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
            shadows: [
              Shadow(
                color: glow.withValues(alpha: labelAlpha * 0.35),
                blurRadius: 12,
              ),
            ],
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      textPainter.paint(
        canvas,
        Offset(
          labelPosition.dx - textPainter.width / 2,
          labelPosition.dy - textPainter.height / 2,
        ),
      );
    }
  }

  void _drawNebulaClouds(Canvas canvas, Size size) {
    final nebulaPaint = Paint();
    final anchors = <(double, double, SectorEnum, double)>[
      (0.22, 0.18, SectorEnum.tech, 0.18),
      (0.78, 0.28, SectorEnum.art, 0.16),
      (0.34, 0.72, SectorEnum.life, 0.14),
    ];

    for (final anchor in anchors) {
      final color = SectorConfig.getGlowColor(
        anchor.$3,
        isDarkMode: isDarkMode,
      );
      final radius = size.shortestSide * anchor.$4;
      final center = Offset(size.width * anchor.$1, size.height * anchor.$2);
      nebulaPaint.shader = ui.Gradient.radial(
        center,
        radius,
        [
          color.withValues(alpha: isDarkMode ? 0.08 : 0.035),
          color.withValues(alpha: isDarkMode ? 0.03 : 0.014),
          Colors.transparent,
        ],
        const [0.0, 0.58, 1.0],
      );
      canvas.drawCircle(center, radius, nebulaPaint);
    }
  }

  void _drawStarLayer(
    Canvas canvas,
    Size size, {
    required int seed,
    required int count,
    required double parallaxFactor,
    required double minRadius,
    required double maxRadius,
    required double minAlpha,
    required double maxAlpha,
    double twinkleStrength = 0,
    bool allowGlints = false,
  }) {
    final random = math.Random(seed);
    final effectiveCount = performanceDegraded ? (count * 0.65).round() : count;
    const overscan = 120.0;
    final width = size.width + overscan * 2;
    final height = size.height + overscan * 2;
    final shift = Offset(
      -camera.offset.dx * parallaxFactor,
      -camera.offset.dy * parallaxFactor,
    );
    final starPaint = Paint()..style = PaintingStyle.fill;
    final baseColor =
        isDarkMode ? const Color(0xFFF5F7FF) : const Color(0xFF526173);

    for (var index = 0; index < effectiveCount; index++) {
      final rawX = random.nextDouble() * width;
      final rawY = random.nextDouble() * height;
      final dx = ((rawX + shift.dx) % width + width) % width - overscan;
      final dy = ((rawY + shift.dy) % height + height) % height - overscan;
      final phase = random.nextDouble() * math.pi * 2;
      final twinkle = twinkleStrength == 0
          ? 0.0
          : math.sin(ambientPhase * (0.6 + parallaxFactor * 3) + phase) *
              twinkleStrength;
      final radius = ui.lerpDouble(
            minRadius,
            maxRadius,
            random.nextDouble(),
          )! *
          (1 + twinkle * 0.18);
      final alpha = (ui.lerpDouble(
                minAlpha,
                maxAlpha,
                random.nextDouble(),
              )! +
              twinkle * 0.06)
          .clamp(0.01, isDarkMode ? 0.42 : 0.16);
      final position = Offset(dx, dy);

      starPaint.color = baseColor.withValues(alpha: alpha);
      canvas.drawCircle(position, radius, starPaint);

      final drawGlint =
          !performanceDegraded && allowGlints && random.nextDouble() > 0.78;
      if (drawGlint) {
        _drawGlintStar(
          canvas,
          position,
          radius: radius * 1.7,
          color: baseColor.withValues(alpha: alpha * 0.8),
        );
      }
    }
  }

  void _drawGlintStar(
    Canvas canvas,
    Offset center, {
    required double radius,
    required Color color,
  }) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 0.8
      ..strokeCap = StrokeCap.round;
    canvas
      ..drawLine(
        Offset(center.dx - radius, center.dy),
        Offset(center.dx + radius, center.dy),
        paint,
      )
      ..drawLine(
        Offset(center.dx, center.dy - radius),
        Offset(center.dx, center.dy + radius),
        paint,
      );
  }

  List<_PaintNode> _selectVisibleNodes({
    required List<String> candidateNodeIds,
    required GalaxyLod lod,
    required Offset viewportCenter,
  }) {
    final nodes = <_PaintNode>[];

    for (final nodeId in candidateNodeIds) {
      final node = nodesById[nodeId];
      final position = _renderWorldPosition(nodeId);
      if (node == null || position == null) {
        continue;
      }

      final reveal = _buildRevealFor(nodeId);
      final alpha = _nodeAlpha(node, lod) *
          reveal *
          _searchNodeVisibility(nodeId) *
          _focusNodeVisibility(nodeId) *
          buildRevealProgress;
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
          reveal: reveal,
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

  Offset? _renderWorldPosition(String nodeId) {
    final base = positions[nodeId];
    if (base == null) {
      return null;
    }
    return base + (driftOffsets[nodeId] ?? Offset.zero);
  }

  double _searchNodeVisibility(String nodeId) {
    if (searchMatchedNodeIds.isEmpty) {
      return 1;
    }
    return searchMatchedNodeIds.contains(nodeId) ? 1 : 0.14;
  }

  double _focusNodeVisibility(String nodeId) {
    if (focusNodeIds.isEmpty) {
      return 1;
    }
    return focusNodeIds.contains(nodeId) ? 1 : 0.22;
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

    if (draggingNodeId != null || isBuildAnimating) {
      edgePictureCache.clear();
      _drawEdgeList(canvas, edgesToDraw);
      return;
    }

    final sceneSignature = Object.hash(
      sceneVersion,
      selectedNodeId,
      lod,
      isDarkMode,
      visibleNodeIds.length,
      Object.hashAll(focusNodeIds),
      Object.hashAll(searchMatchedNodeIds),
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

      final source = _renderWorldPosition(edge.sourceId);
      final target = _renderWorldPosition(edge.targetId);
      final sourceNode = nodesById[edge.sourceId];
      final targetNode = nodesById[edge.targetId];
      if (source == null ||
          target == null ||
          sourceNode == null ||
          targetNode == null) {
        continue;
      }

      final sourceVisible = visibleNodeIds.contains(edge.sourceId);
      final targetVisible = visibleNodeIds.contains(edge.targetId);
      final intersectsViewport =
          _segmentIntersectsRect(source, target, viewport);
      if (!sourceVisible && !targetVisible && !intersectsViewport) {
        continue;
      }

      final sourceColor = _nodeCanvasColor(sourceNode);
      final targetColor = _nodeCanvasColor(targetNode);
      final edgeStyle = _edgeStyle(
        edge,
        sourceColor: sourceColor,
        targetColor: targetColor,
      );
      final reveal = math.min(
        _buildRevealFor(edge.sourceId),
        _buildRevealFor(edge.targetId),
      );
      final searchMultiplier = searchMatchedNodeIds.isEmpty
          ? 1.0
          : (searchMatchedNodeIds.contains(edge.sourceId) ||
                  searchMatchedNodeIds.contains(edge.targetId))
              ? 1.0
              : 0.1;
      final networkFocusMultiplier = focusNodeIds.isEmpty
          ? 1.0
          : (focusNodeIds.contains(edge.sourceId) ||
                  focusNodeIds.contains(edge.targetId))
              ? 1.0
              : 0.16;
      final selectionFocusMultiplier = selectedNodeId == null
          ? 1.0
          : (edge.sourceId == selectedNodeId || edge.targetId == selectedNodeId)
              ? 1.55
              : 0.18;
      final alpha = edgeStyle.alpha *
          _edgeAlpha(edge, lod) *
          reveal *
          networkFocusMultiplier *
          searchMultiplier *
          selectionFocusMultiplier *
          buildRevealProgress;
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
        sourceColor: sourceColor.withValues(alpha: alpha),
        targetColor: targetColor.withValues(alpha: alpha),
        strokeWidth: edgeStyle.strokeWidth,
        dashLength: edgeStyle.dashLength,
        gapLength: edgeStyle.gapLength,
        relationType: edge.relationType,
        strength: edge.strength,
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
      final paintKey = Object.hash(
        edge.sourceColor.toARGB32(),
        edge.targetColor.toARGB32(),
        edge.strokeWidth,
      );
      final paint = paintCache[paintKey] ??
          (paintCache[paintKey] = Paint()
            ..strokeWidth = edge.strokeWidth
            ..style = PaintingStyle.stroke
            ..strokeCap = StrokeCap.round);

      final start = camera.worldToScreen(edge.start);
      final end = camera.worldToScreen(edge.end);
      final path = _edgePath(
        start,
        end,
        relationType: edge.relationType,
        strength: edge.strength,
      );
      paint.shader = ui.Gradient.linear(
        start,
        end,
        [edge.sourceColor, edge.targetColor],
      );
      if (edge.isDashed) {
        _drawDashedPath(
          canvas: canvas,
          path: path,
          paint: paint,
          dashLength: edge.dashLength,
          gapLength: edge.gapLength,
        );
      } else {
        canvas.drawPath(path, paint);
      }

      if (edge.relationType == EdgeRelationType.prerequisite) {
        _drawArrowHead(
          canvas,
          path,
          edge.targetColor,
          edge.strokeWidth,
        );
      }
    }
  }

  void _drawEdgeParticles(Canvas canvas) {
    for (final particle in edgeParticles) {
      final source = _renderWorldPosition(particle.sourceId);
      final target = _renderWorldPosition(particle.targetId);
      if (source == null || target == null) {
        continue;
      }

      final path = _edgePath(
        camera.worldToScreen(source),
        camera.worldToScreen(target),
        relationType: particle.relationType,
        strength: particle.strength,
      );
      final metrics = path.computeMetrics().toList(growable: false);
      if (metrics.isEmpty) {
        continue;
      }

      final metric = metrics.first;
      final tangent =
          metric.getTangentForOffset(metric.length * particle.progress);
      if (tangent == null) {
        continue;
      }

      final glowColor = particle.color.withValues(alpha: particle.alpha * 0.32);
      canvas
        ..drawCircle(
          tangent.position,
          particle.radius * 2.4,
          Paint()
            ..color = glowColor
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
        )
        ..drawCircle(
          tangent.position,
          particle.radius,
          Paint()..color = particle.color.withValues(alpha: particle.alpha),
        );
    }
  }

  void _drawNodes(Canvas canvas, GalaxyLod lod, List<_PaintNode> nodes) {
    final allowPulse = lod.index >= GalaxyLod.l3.index &&
        nodes.length < 100 &&
        !isBuildAnimating;

    for (final item in nodes) {
      final node = item.node;
      final isDragging = draggingNodeId == node.id;
      final revealCurve =
          isBuildAnimating ? Curves.easeOutBack.transform(item.reveal) : 1.0;
      final radius = _effectiveNodeRadius(
            node,
            lod,
            isDragging,
            allowPulse: allowPulse,
          ) *
          (isBuildAnimating ? (0.6 + 0.4 * revealCurve) : 1.0);
      final style = _nodeStyle(node, lod, isDragging);
      final nodeAlpha = item.alpha.clamp(0.0, 1.0);
      final selectionPulse = selectedNodeId == node.id
          ? 0.5 + 0.5 * math.sin(ambientPhase * 3.2 + _nodeSeed(node.id))
          : 0.0;

      if (!performanceDegraded &&
          style.glowAlpha > 0 &&
          nodeAlpha > 0 &&
          lod.index >= GalaxyLod.l2.index) {
        canvas
          ..drawCircle(
            item.screenPosition,
            radius * 1.45,
            Paint()
              ..color = style.baseColor.withValues(
                alpha: style.glowAlpha * nodeAlpha * 0.78,
              )
              ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10),
          )
          ..drawCircle(
            item.screenPosition,
            radius * 1.8,
            Paint()
              ..color = style.baseColor.withValues(
                alpha: style.glowAlpha * nodeAlpha * 0.34,
              )
              ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
          );
      }

      if (style.fillAlpha > 0 && nodeAlpha > 0) {
        final innerColor = _toneColor(
          style.baseColor,
          saturationMultiplier: 1.08,
          lightnessDelta: isDarkMode ? 0.1 : 0.06,
        );
        final outerColor = _toneColor(
          style.baseColor,
          saturationMultiplier: 0.92,
          lightnessDelta: isDarkMode ? -0.12 : -0.08,
        );
        canvas.drawCircle(
          item.screenPosition,
          radius,
          Paint()
            ..shader = ui.Gradient.radial(
              item.screenPosition,
              radius,
              [
                Colors.white.withValues(alpha: nodeAlpha * 0.2),
                innerColor.withValues(
                  alpha: style.fillAlpha * nodeAlpha * 0.92,
                ),
                style.baseColor.withValues(
                  alpha: style.fillAlpha * nodeAlpha,
                ),
                outerColor.withValues(
                  alpha: style.fillAlpha * nodeAlpha * 0.86,
                ),
                outerColor.withValues(alpha: 0),
              ],
              const [0.0, 0.14, 0.38, 0.82, 1.0],
            ),
        );
      }

      if (style.coreAlpha > 0 && nodeAlpha > 0) {
        canvas.drawCircle(
          item.screenPosition,
          math.max(1.1, radius * 0.28),
          Paint()
            ..color =
                Colors.white.withValues(alpha: style.coreAlpha * nodeAlpha),
        );
      }

      if (style.masteryRingAlpha > 0 && nodeAlpha > 0) {
        canvas.drawCircle(
          item.screenPosition,
          radius + 1.6,
          Paint()
            ..color = style.baseColor.withValues(
              alpha: style.masteryRingAlpha * nodeAlpha,
            )
            ..strokeWidth = 1.5
            ..style = PaintingStyle.stroke,
        );
      }

      if (!node.isUnlocked) {
        final pulseAlpha =
            (0.08 + 0.04 * math.sin(ambientPhase * 1.6 + _nodeSeed(node.id)))
                .clamp(0.04, 0.14);
        canvas.drawCircle(
          item.screenPosition,
          radius * 1.08,
          Paint()
            ..color = style.baseColor.withValues(alpha: pulseAlpha * nodeAlpha),
        );
        _drawDashedCircle(
          canvas: canvas,
          center: item.screenPosition,
          radius: radius + 1,
          color: style.baseColor.withValues(alpha: 0.36 * nodeAlpha),
        );
      }

      if (!performanceDegraded &&
          node.masteryScore >= 85 &&
          lod.index >= GalaxyLod.l2.index) {
        canvas.drawCircle(
          item.screenPosition,
          radius * 1.85,
          Paint()
            ..color = style.baseColor.withValues(alpha: 0.08 * nodeAlpha)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 18),
        );
      }

      if (!performanceDegraded &&
          node.importance >= 5 &&
          lod.index >= GalaxyLod.l3.index) {
        _drawNodeRays(
          canvas,
          item.screenPosition,
          radius: radius,
          color: style.baseColor.withValues(alpha: 0.08 * nodeAlpha),
          seed: _nodeSeed(node.id),
        );
      }

      if (tapFeedbackNodeId == node.id) {
        final rippleRadius = radius * (1.1 + tapFeedbackProgress * 1.5);
        final rippleAlpha = (1 - tapFeedbackProgress).clamp(0.0, 1.0) * 0.42;
        canvas.drawCircle(
          item.screenPosition,
          rippleRadius,
          Paint()
            ..color = style.baseColor.withValues(alpha: rippleAlpha)
            ..strokeWidth = 1.8
            ..style = PaintingStyle.stroke,
        );
      }

      if (selectedNodeId == node.id) {
        final selectedColor = Color.lerp(
          style.baseColor,
          isDarkMode ? Colors.white : Colors.black,
          isDarkMode ? 0.42 : 0.28,
        )!;
        canvas
          ..drawCircle(
            item.screenPosition,
            radius * (1.45 + selectionPulse * 0.14),
            Paint()
              ..color = selectedColor.withValues(
                alpha: 0.13 + selectionPulse * 0.08,
              )
              ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 16),
          )
          ..drawCircle(
            item.screenPosition,
            radius + 4 + selectionPulse * 1.4,
            Paint()
              ..color = selectedColor.withValues(alpha: 0.85 * nodeAlpha)
              ..strokeWidth = 1.6
              ..style = PaintingStyle.stroke,
          );
      }

      if (celebrationNodeIds.contains(node.id)) {
        canvas.drawCircle(
          item.screenPosition,
          radius * 2.1,
          Paint()
            ..color = style.baseColor.withValues(alpha: 0.12 * nodeAlpha)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 20),
        );
      }
    }
  }

  void _drawLabels(Canvas canvas, GalaxyLod lod, List<_PaintNode> nodes) {
    final allowPulse = lod.index >= GalaxyLod.l3.index &&
        nodes.length < 100 &&
        !isBuildAnimating;

    for (final item in nodes) {
      final node = item.node;
      final labelAlpha = _labelAlpha(node, lod) *
          item.reveal *
          _searchNodeVisibility(node.id) *
          _focusNodeVisibility(node.id) *
          buildRevealProgress;
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
      final radius = _effectiveNodeRadius(
        node,
        lod,
        draggingNodeId == node.id,
        allowPulse: allowPulse,
      );
      final labelOffset = Offset(
        item.screenPosition.dx + radius + 7,
        item.screenPosition.dy - labelPainter.height / 2,
      );

      if (isSelected) {
        final baseColor = _nodeCanvasColor(node);
        final backgroundRect = RRect.fromRectAndRadius(
          Rect.fromLTWH(
            labelOffset.dx - 7,
            labelOffset.dy - 4,
            labelPainter.width + 14,
            labelPainter.height + 8,
          ),
          const Radius.circular(7),
        );
        canvas.drawRRect(
          backgroundRect,
          Paint()
            ..color = Color.lerp(
              isDarkMode ? _darkBackground : Colors.white,
              baseColor,
              0.18,
            )!
                .withValues(alpha: 0.84 * labelAlpha),
        );
      }

      labelPainter.paint(canvas, labelOffset);

      if (lod == GalaxyLod.l4) {
        final barColor = _nodeCanvasColor(node).withValues(alpha: 0.92);
        final barTrackColor = (isDarkMode ? Colors.white24 : Colors.black12);
        final barOffset = Offset(
          labelOffset.dx,
          labelOffset.dy + labelPainter.height + 5,
        );
        const barWidth = 42.0;
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
    return resolveGalaxyLod(scale);
  }

  int _nodeBudgetFor(GalaxyLod lod) {
    if (performanceDegraded) {
      switch (lod) {
        case GalaxyLod.l0:
          return 20;
        case GalaxyLod.l1:
          return 36;
        case GalaxyLod.l2:
          return 260;
        case GalaxyLod.l3:
        case GalaxyLod.l4:
          return 360;
      }
    }
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
    if (performanceDegraded) {
      switch (lod) {
        case GalaxyLod.l0:
          return 0;
        case GalaxyLod.l1:
          return 140;
        case GalaxyLod.l2:
          return 280;
        case GalaxyLod.l3:
        case GalaxyLod.l4:
          return 520;
      }
    }
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

  _PaintEdgeStyle _edgeStyle(
    GalaxyEdgeModel edge, {
    required Color sourceColor,
    required Color targetColor,
  }) {
    final bridgeColor = SectorConfig.lerpInHsl(sourceColor, targetColor, 0.4);
    switch (edge.relationType) {
      case EdgeRelationType.parentChild:
        return _PaintEdgeStyle(
          color: sourceColor,
          strokeWidth: 1.25,
          alpha: 0.54,
        );
      case EdgeRelationType.prerequisite:
        return _PaintEdgeStyle(
          color: _toneColor(
            bridgeColor,
            lightnessDelta: isDarkMode ? 0.08 : -0.04,
          ),
          strokeWidth: 1.0,
          alpha: 0.44,
        );
      case EdgeRelationType.derived:
        return _PaintEdgeStyle(
          color: _toneColor(bridgeColor, saturationMultiplier: 0.92),
          strokeWidth: 0.95,
          alpha: 0.36,
        );
      case EdgeRelationType.related:
        return _PaintEdgeStyle(
          color: bridgeColor,
          strokeWidth: 0.9,
          alpha: 0.32,
          dashLength: 10,
          gapLength: 4,
        );
      case EdgeRelationType.similar:
        return _PaintEdgeStyle(
          color: _toneColor(bridgeColor, saturationMultiplier: 0.82),
          strokeWidth: 0.85,
          alpha: 0.28,
          dashLength: 4,
          gapLength: 4,
        );
      case EdgeRelationType.contrast:
        return _PaintEdgeStyle(
          color: _toneColor(
            bridgeColor,
            lightnessDelta: isDarkMode ? 0.04 : -0.03,
          ),
          strokeWidth: 0.8,
          alpha: 0.24,
          dashLength: 12,
          gapLength: 6,
        );
      case EdgeRelationType.application:
        return _PaintEdgeStyle(
          color: _toneColor(bridgeColor, saturationMultiplier: 0.95),
          strokeWidth: 0.82,
          alpha: 0.24,
          dashLength: 2,
          gapLength: 6,
        );
      case EdgeRelationType.example:
        return _PaintEdgeStyle(
          color: _toneColor(bridgeColor, saturationMultiplier: 0.78),
          strokeWidth: 0.78,
          alpha: 0.22,
          dashLength: 3,
          gapLength: 5,
        );
    }
  }

  _PaintNodeStyle _nodeStyle(
    GalaxyNodeModel node,
    GalaxyLod lod,
    bool isDragging,
  ) {
    final baseColor = _nodeCanvasColor(node);
    final mastery = node.masteryScore;
    if (!node.isUnlocked) {
      return _PaintNodeStyle(
        baseColor: baseColor,
        fillAlpha: 0,
        masteryRingAlpha: 0,
        glowAlpha: 0,
        coreAlpha: 0,
      );
    }

    double fillAlpha;
    double masteryRingAlpha;
    double glowAlpha = 0;
    var coreAlpha = 0.18;

    if (mastery < 30) {
      fillAlpha = 0.32;
      masteryRingAlpha = 0;
    } else if (mastery < 60) {
      fillAlpha = 0.58;
      masteryRingAlpha = 0;
      coreAlpha = 0.24;
    } else if (mastery < 85) {
      fillAlpha = 0.82;
      masteryRingAlpha = 0.38;
      coreAlpha = 0.28;
    } else {
      fillAlpha = 0.94;
      masteryRingAlpha = 0.72;
      glowAlpha = lod.index >= GalaxyLod.l2.index ? 0.18 : 0;
      coreAlpha = 0.34;
    }

    if (isDragging) {
      fillAlpha = 0.88;
      masteryRingAlpha = math.max(masteryRingAlpha, 0.46);
      glowAlpha = math.max(glowAlpha, 0.14);
      coreAlpha = math.max(coreAlpha, 0.28);
    }

    return _PaintNodeStyle(
      baseColor: baseColor,
      fillAlpha: fillAlpha,
      masteryRingAlpha: masteryRingAlpha,
      glowAlpha: glowAlpha,
      coreAlpha: coreAlpha,
    );
  }

  double _effectiveNodeRadius(
    GalaxyNodeModel node,
    GalaxyLod lod,
    bool isDragging, {
    required bool allowPulse,
  }) {
    var radius = _nodeRadius(node, lod);
    if (tapFeedbackNodeId == node.id) {
      radius *= 1 + 0.3 * tapFeedbackProgress;
    }
    if (isDragging) {
      radius *= 1.2;
    }
    if (allowPulse && node.masteryScore >= 85) {
      radius *= 1 + 0.06 * math.sin(ambientPhase * 2.1 + _nodeSeed(node.id));
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

  void _drawDashedPath({
    required Canvas canvas,
    required Path path,
    required Paint paint,
    required double dashLength,
    required double gapLength,
  }) {
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

  Path _edgePath(
    Offset start,
    Offset end, {
    required EdgeRelationType relationType,
    required double strength,
  }) {
    final delta = end - start;
    final length = delta.distance;
    if (length < 18) {
      return Path()
        ..moveTo(start.dx, start.dy)
        ..lineTo(end.dx, end.dy);
    }

    if (relationType != EdgeRelationType.parentChild &&
        relationType != EdgeRelationType.prerequisite &&
        relationType != EdgeRelationType.derived) {
      return Path()
        ..moveTo(start.dx, start.dy)
        ..lineTo(end.dx, end.dy);
    }

    final normal = Offset(-delta.dy / length, delta.dx / length);
    final midpoint = Offset((start.dx + end.dx) / 2, (start.dy + end.dy) / 2);
    final direction = math
            .sin(
              start.dx + end.dx + start.dy * 0.5 + end.dy * 0.25,
            )
            .isNegative
        ? -1.0
        : 1.0;
    final bendScale =
        relationType == EdgeRelationType.parentChild ? 0.12 : 0.08;
    final bend =
        (length * bendScale * (0.85 + strength * 0.35)).clamp(10.0, 34.0);
    final control = midpoint + normal * bend * direction;
    return Path()
      ..moveTo(start.dx, start.dy)
      ..quadraticBezierTo(control.dx, control.dy, end.dx, end.dy);
  }

  void _drawArrowHead(
    Canvas canvas,
    Path path,
    Color color,
    double strokeWidth,
  ) {
    final metrics = path.computeMetrics().toList(growable: false);
    if (metrics.isEmpty) {
      return;
    }

    final metric = metrics.first;
    final tangent = metric.getTangentForOffset(
      math.max(0, metric.length - 8),
    );
    if (tangent == null) {
      return;
    }

    final direction = tangent.vector / tangent.vector.distance;
    final normal = Offset(-direction.dy, direction.dx);
    final tip = tangent.position;
    final size = math.max(5.0, strokeWidth * 4.8);
    final pathArrow = Path()
      ..moveTo(tip.dx, tip.dy)
      ..lineTo(
        tip.dx - direction.dx * size + normal.dx * size * 0.45,
        tip.dy - direction.dy * size + normal.dy * size * 0.45,
      )
      ..lineTo(
        tip.dx - direction.dx * size - normal.dx * size * 0.45,
        tip.dy - direction.dy * size - normal.dy * size * 0.45,
      )
      ..close();
    canvas.drawPath(pathArrow, Paint()..color = color.withValues(alpha: 0.88));
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

  void _drawNodeRays(
    Canvas canvas,
    Offset center, {
    required double radius,
    required Color color,
    required double seed,
  }) {
    final rayPaint = Paint()
      ..color = color
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 1.0;
    final rayCount = 4 + (seed * 10).round() % 3;
    for (var index = 0; index < rayCount; index++) {
      final angle = seed + (math.pi * 2 * index / rayCount);
      final inner = radius * 1.15;
      final outer = radius * (1.65 + 0.12 * math.sin(seed + index));
      canvas.drawLine(
        Offset(
          center.dx + math.cos(angle) * inner,
          center.dy + math.sin(angle) * inner,
        ),
        Offset(
          center.dx + math.cos(angle) * outer,
          center.dy + math.sin(angle) * outer,
        ),
        rayPaint,
      );
    }
  }

  double _fade(double value, double start, double end) {
    return galaxyLodFade(value, start, end);
  }

  bool _segmentIntersectsRect(Offset a, Offset b, Rect rect) {
    if (rect.contains(a) || rect.contains(b)) {
      return true;
    }

    return Rect.fromPoints(a, b).overlaps(rect);
  }

  Color _nodeCanvasColor(GalaxyNodeModel node) {
    final blended = blendedColors[node.id] ??
        SectorConfig.getColor(node.sector, isDarkMode: isDarkMode);
    return SectorConfig.applyImportanceRamp(
      blended,
      importance: node.importance,
      isDarkMode: isDarkMode,
    );
  }

  double _buildRevealFor(String nodeId) {
    if (!isBuildAnimating) {
      return 1;
    }

    final rank = revealRanks[nodeId];
    if (rank == null || revealRanks.isEmpty) {
      return buildRevealProgress.clamp(0.0, 1.0);
    }

    final count = revealRanks.length;
    final staggerSpan = count <= 1 ? 0.0 : 0.72;
    const revealSpan = 0.18;
    final start = count <= 1 ? 0.0 : (rank / (count - 1)) * staggerSpan;
    final end = (start + revealSpan).clamp(0.0, 1.0);
    if (buildRevealProgress <= start) {
      return 0;
    }
    if (buildRevealProgress >= end) {
      return 1;
    }
    return Curves.easeOutCubic.transform(
      ((buildRevealProgress - start) / (end - start)).clamp(0.0, 1.0),
    );
  }

  double get _worldRadius {
    final maxX = math.max(worldBounds.left.abs(), worldBounds.right.abs());
    final maxY = math.max(worldBounds.top.abs(), worldBounds.bottom.abs());
    return math.max(maxX, maxY);
  }

  Path _sectorPath({
    required Offset center,
    required double startAngleDegrees,
    required double sweepAngleDegrees,
    required double innerRadius,
    required double outerRadius,
  }) {
    final startRad = startAngleDegrees * math.pi / 180;
    final sweepRad = sweepAngleDegrees * math.pi / 180;
    final innerRect = Rect.fromCircle(center: center, radius: innerRadius);
    final outerRect = Rect.fromCircle(center: center, radius: outerRadius);
    final path = Path();
    final innerStart = Offset(
      center.dx + innerRadius * math.cos(startRad),
      center.dy + innerRadius * math.sin(startRad),
    );

    path
      ..moveTo(innerStart.dx, innerStart.dy)
      ..arcTo(innerRect, startRad, sweepRad, false)
      ..lineTo(
        center.dx + outerRadius * math.cos(startRad + sweepRad),
        center.dy + outerRadius * math.sin(startRad + sweepRad),
      )
      ..arcTo(outerRect, startRad + sweepRad, -sweepRad, false)
      ..close();
    return path;
  }

  Color _toneColor(
    Color color, {
    double saturationMultiplier = 1,
    double lightnessDelta = 0,
  }) {
    final hsl = HSLColor.fromColor(color);
    return hsl
        .withSaturation(
          (hsl.saturation * saturationMultiplier).clamp(0.2, 0.86),
        )
        .withLightness((hsl.lightness + lightnessDelta).clamp(0.18, 0.84))
        .toColor();
  }

  double _nodeSeed(String value) {
    var hash = 0;
    for (final codeUnit in value.codeUnits) {
      hash = ((hash * 31) + codeUnit) & 0x7fffffff;
    }
    return (hash % 1000) / 100.0;
  }
}

enum GalaxyLod {
  l0,
  l1,
  l2,
  l3,
  l4,
}

class GalaxyEdgeParticle {
  const GalaxyEdgeParticle({
    required this.sourceId,
    required this.targetId,
    required this.relationType,
    required this.strength,
    required this.progress,
    required this.radius,
    required this.alpha,
    required this.color,
  });

  final String sourceId;
  final String targetId;
  final EdgeRelationType relationType;
  final double strength;
  final double progress;
  final double radius;
  final double alpha;
  final Color color;
}

class _PaintNode {
  const _PaintNode({
    required this.node,
    required this.worldPosition,
    required this.screenPosition,
    required this.distanceToViewportCenter,
    required this.alpha,
    required this.reveal,
  });

  final GalaxyNodeModel node;
  final Offset worldPosition;
  final Offset screenPosition;
  final double distanceToViewportCenter;
  final double alpha;
  final double reveal;
}

class _PaintEdge {
  const _PaintEdge({
    required this.start,
    required this.end,
    required this.distanceToViewportCenter,
    required this.color,
    required this.sourceColor,
    required this.targetColor,
    required this.strokeWidth,
    required this.dashLength,
    required this.gapLength,
    required this.relationType,
    required this.strength,
  });

  final Offset start;
  final Offset end;
  final double distanceToViewportCenter;
  final Color color;
  final Color sourceColor;
  final Color targetColor;
  final double strokeWidth;
  final double dashLength;
  final double gapLength;
  final EdgeRelationType relationType;
  final double strength;

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
    required this.coreAlpha,
  });

  final Color baseColor;
  final double fillAlpha;
  final double masteryRingAlpha;
  final double glowAlpha;
  final double coreAlpha;
}
