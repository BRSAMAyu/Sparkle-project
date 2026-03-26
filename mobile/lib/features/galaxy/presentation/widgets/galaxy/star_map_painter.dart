import 'dart:collection';
import 'dart:developer' as developer;
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_build_playback_plan.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_display_settings_provider.dart';
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

/// Edge picture caching has been intentionally removed.
///
/// Drawing ≤800 simple paths per frame is trivially fast on modern GPUs.
/// The previous Picture-based cache introduced visual artefacts (arc flicker
/// during zoom/pan) because Bezier control points are computed in screen-space
/// and cannot be correctly replayed after a camera transform change.

class GalaxyBackdropPictureCache {
  ui.Picture? _picture;
  Size? _size;
  bool? _isDarkMode;
  bool? _performanceDegraded;

  void clear() {
    _picture?.dispose();
    _picture = null;
    _size = null;
    _isDarkMode = null;
    _performanceDegraded = null;
  }

  bool canReuse({
    required Size size,
    required bool isDarkMode,
    required bool performanceDegraded,
  }) =>
      _picture != null &&
      _size == size &&
      _isDarkMode == isDarkMode &&
      _performanceDegraded == performanceDegraded;

  void draw(Canvas canvas) {
    final picture = _picture;
    if (picture == null) {
      return;
    }
    canvas.drawPicture(picture);
  }

  void store({
    required ui.Picture picture,
    required Size size,
    required bool isDarkMode,
    required bool performanceDegraded,
  }) {
    clear();
    _picture = picture;
    _size = size;
    _isDarkMode = isDarkMode;
    _performanceDegraded = performanceDegraded;
  }
}

class GalaxyParallaxStarLayerCache {
  GalaxyParallaxStarLayerCache({this.panThresholdPx = 90});

  final double panThresholdPx;

  ui.Picture? _picture;
  Size? _size;
  bool? _isDarkMode;
  bool? _performanceDegraded;
  Offset? _cameraOffset;
  double? _parallaxFactor;

  void clear() {
    _picture?.dispose();
    _picture = null;
    _size = null;
    _isDarkMode = null;
    _performanceDegraded = null;
    _cameraOffset = null;
    _parallaxFactor = null;
  }

  bool canReuse({
    required Size size,
    required bool isDarkMode,
    required bool performanceDegraded,
    required Offset cameraOffset,
    required double parallaxFactor,
  }) {
    if (_picture == null ||
        _size != size ||
        _isDarkMode != isDarkMode ||
        _performanceDegraded != performanceDegraded ||
        _cameraOffset == null ||
        _parallaxFactor != parallaxFactor) {
      return false;
    }

    final translatedPan =
        (cameraOffset - _cameraOffset!).distance * parallaxFactor;
    return translatedPan <= panThresholdPx;
  }

  void draw(Canvas canvas, Offset cameraOffset) {
    final picture = _picture;
    final cachedCameraOffset = _cameraOffset;
    final parallaxFactor = _parallaxFactor;
    if (picture == null ||
        cachedCameraOffset == null ||
        parallaxFactor == null) {
      return;
    }

    final delta = cameraOffset - cachedCameraOffset;
    canvas
      ..save()
      ..translate(-delta.dx * parallaxFactor, -delta.dy * parallaxFactor)
      ..drawPicture(picture)
      ..restore();
  }

  void store({
    required ui.Picture picture,
    required Size size,
    required bool isDarkMode,
    required bool performanceDegraded,
    required Offset cameraOffset,
    required double parallaxFactor,
  }) {
    clear();
    _picture = picture;
    _size = size;
    _isDarkMode = isDarkMode;
    _performanceDegraded = performanceDegraded;
    _cameraOffset = cameraOffset;
    _parallaxFactor = parallaxFactor;
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
    required this.backdropPictureCache,
    required this.parallaxStarLayerCache,
    required this.sceneVersion,
    required this.isDarkMode,
    required this.worldBounds,
    required this.blendedColors,
    required this.displaySettings,
    required this.playbackPlan,
    required this.playbackElapsedMs,
    required this.preRevealedNodeIds,
    required this.preRevealedEdgeIds,
    required this.nodeConnectionCounts,
    this.spotlightNodeIds = const <String>{},
    this.spotlightAnchorId,
    this.searchMatchedNodeIds = const <String>{},
    this.driftOffsets = const <String, Offset>{},
    this.edgeParticles = const <GalaxyEdgeParticle>[],
    this.celebrationNodeIds = const <String>{},
    this.performanceDegraded = false,
    this.selectedNodeId,
    this.previewNodeId,
    this.draggingNodeId,
    this.tapFeedbackNodeId,
    this.tapFeedbackProgress = 0,
    this.tapFeedbackPhase = 0,
    this.ambientPhase = 0,
    this.isBuildAnimating = false,
  });

  final GalaxyCamera camera;
  final Map<String, GalaxyNodeModel> nodesById;
  final List<GalaxyEdgeModel> edges;
  final Map<String, Offset> positions;
  final GalaxySpatialIndex spatialIndex;
  final GalaxyLabelCache labelCache;
  final GalaxyBackdropPictureCache backdropPictureCache;
  final GalaxyParallaxStarLayerCache parallaxStarLayerCache;
  final int sceneVersion;
  final bool isDarkMode;
  final Rect worldBounds;
  final Map<String, Color> blendedColors;
  final GalaxyDisplaySettings displaySettings;
  final GalaxyBuildPlaybackPlan? playbackPlan;
  final int playbackElapsedMs;
  final Set<String> preRevealedNodeIds;
  final Set<String> preRevealedEdgeIds;
  final Map<String, int> nodeConnectionCounts;
  final Set<String> spotlightNodeIds;
  final String? spotlightAnchorId;
  final Set<String> searchMatchedNodeIds;
  final Map<String, Offset> driftOffsets;
  final List<GalaxyEdgeParticle> edgeParticles;
  final Set<String> celebrationNodeIds;
  final bool performanceDegraded;
  final String? selectedNodeId;
  final String? previewNodeId;
  final String? draggingNodeId;
  final String? tapFeedbackNodeId;
  final double tapFeedbackProgress;
  final double tapFeedbackPhase;
  final double ambientPhase;
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
      oldDelegate.previewNodeId != previewNodeId ||
      oldDelegate.draggingNodeId != draggingNodeId ||
      oldDelegate.tapFeedbackNodeId != tapFeedbackNodeId ||
      oldDelegate.tapFeedbackProgress != tapFeedbackProgress ||
      oldDelegate.tapFeedbackPhase != tapFeedbackPhase ||
      oldDelegate.isDarkMode != isDarkMode ||
      oldDelegate.worldBounds != worldBounds ||
      oldDelegate.blendedColors != blendedColors ||
      oldDelegate.displaySettings != displaySettings ||
      oldDelegate.playbackPlan != playbackPlan ||
      oldDelegate.playbackElapsedMs != playbackElapsedMs ||
      oldDelegate.preRevealedNodeIds != preRevealedNodeIds ||
      oldDelegate.preRevealedEdgeIds != preRevealedEdgeIds ||
      oldDelegate.nodeConnectionCounts != nodeConnectionCounts ||
      oldDelegate.spotlightNodeIds != spotlightNodeIds ||
      oldDelegate.spotlightAnchorId != spotlightAnchorId ||
      oldDelegate.searchMatchedNodeIds != searchMatchedNodeIds ||
      oldDelegate.driftOffsets != driftOffsets ||
      oldDelegate.edgeParticles != edgeParticles ||
      oldDelegate.celebrationNodeIds != celebrationNodeIds ||
      oldDelegate.performanceDegraded != performanceDegraded ||
      oldDelegate.ambientPhase != ambientPhase ||
      oldDelegate.isBuildAnimating != isBuildAnimating;

  void _drawBackground(Canvas canvas, Size size) {
    if (backdropPictureCache.canReuse(
      size: size,
      isDarkMode: isDarkMode,
      performanceDegraded: performanceDegraded,
    )) {
      backdropPictureCache.draw(canvas);
    } else {
      final recorder = ui.PictureRecorder();
      final pictureCanvas = Canvas(recorder);
      _drawBackdropContents(pictureCanvas, size);
      backdropPictureCache
        ..store(
          picture: recorder.endRecording(),
          size: size,
          isDarkMode: isDarkMode,
          performanceDegraded: performanceDegraded,
        )
        ..draw(canvas);
    }

    const farLayerParallax = 0.10;
    if (parallaxStarLayerCache.canReuse(
      size: size,
      isDarkMode: isDarkMode,
      performanceDegraded: performanceDegraded,
      cameraOffset: camera.offset,
      parallaxFactor: farLayerParallax,
    )) {
      parallaxStarLayerCache.draw(canvas, camera.offset);
    } else {
      final recorder = ui.PictureRecorder();
      final pictureCanvas = Canvas(recorder);
      _drawStarLayer(
        pictureCanvas,
        size,
        seed: 17,
        count: isDarkMode ? 180 : 120,
        parallaxFactor: farLayerParallax,
        minRadius: 0.45,
        maxRadius: 1.2,
        minAlpha: isDarkMode ? 0.05 : 0.025,
        maxAlpha: isDarkMode ? 0.14 : 0.055,
      );
      parallaxStarLayerCache
        ..store(
          picture: recorder.endRecording(),
          size: size,
          isDarkMode: isDarkMode,
          performanceDegraded: performanceDegraded,
          cameraOffset: camera.offset,
          parallaxFactor: farLayerParallax,
        )
        ..draw(canvas, camera.offset);
    }

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

  void _drawBackdropContents(Canvas canvas, Size size) {
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
    final vignettePaint = Paint()
      ..shader = ui.Gradient.radial(
        center,
        size.longestSide * 0.82,
        [
          Colors.transparent,
          Colors.transparent,
          (isDarkMode ? Colors.black : const Color(0xFFCBD2DD)).withValues(
            alpha: isDarkMode ? 0.12 : 0.06,
          ),
        ],
        const [0.0, 0.72, 1.0],
      );
    canvas.drawRect(Offset.zero & size, vignettePaint);
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
    final labelAlpha = visibility * (isDarkMode ? 0.88 : 0.66);

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
      final pulse = math.sin(ambientPhase * 0.3 + style.baseAngle / 72) * 0.015;
      final atmosphereAlpha = visibility * (isDarkMode ? 0.12 : 0.07) + pulse;
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
      final blendBandPaint = Paint()
        ..color = SectorConfig.lerpInHsl(
          glow,
          primary,
          0.5,
        ).withValues(alpha: atmosphereAlpha * 0.16)
        ..strokeWidth = isDarkMode ? 10 : 8
        ..style = PaintingStyle.stroke
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10);
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
          blendBandPaint,
        )
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
            fontSize: lod == GalaxyLod.l0 ? (isDarkMode ? 16 : 15) : 13,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
            shadows: [
              Shadow(
                color: glow.withValues(alpha: labelAlpha * 0.58),
                blurRadius: 4,
              ),
              Shadow(
                color: glow.withValues(alpha: labelAlpha * 0.22),
                blurRadius: 16,
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
    final anchors = <(double, double, SectorEnum, double, double)>[
      (0.18, 0.16, SectorEnum.tech, 0.34, 0.045),
      (0.74, 0.22, SectorEnum.art, 0.3, 0.042),
      (0.3, 0.72, SectorEnum.life, 0.28, 0.04),
      (0.62, 0.66, SectorEnum.civilization, 0.15, 0.095),
      (0.46, 0.34, SectorEnum.wisdom, 0.12, 0.088),
      (0.84, 0.78, SectorEnum.cosmos, 0.11, 0.082),
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
          color.withValues(alpha: isDarkMode ? anchor.$5 : anchor.$5 * 0.48),
          color.withValues(
            alpha: isDarkMode ? anchor.$5 * 0.42 : anchor.$5 * 0.2,
          ),
          Colors.transparent,
        ],
        const [0.0, 0.52, 1.0],
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
    final warmBase =
        isDarkMode ? const Color(0xFFFFF4E6) : const Color(0xFF6E6354);
    final coolBase =
        isDarkMode ? const Color(0xFFE6F0FF) : const Color(0xFF526173);

    for (var index = 0; index < effectiveCount; index++) {
      final rawX = random.nextDouble() * width;
      final rawY = random.nextDouble() * height;
      final dx = ((rawX + shift.dx) % width + width) % width - overscan;
      final dy = ((rawY + shift.dy) % height + height) % height - overscan;
      final phase = random.nextDouble() * math.pi * 2;
      final frequencyJitter = 0.82 + random.nextDouble() * 0.46;
      final twinkle = twinkleStrength == 0
          ? 0.0
          : math.sin(
                ambientPhase * (0.6 + parallaxFactor * 3) * frequencyJitter +
                    phase,
              ) *
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
      final colorMix = ((dx + overscan) / width).clamp(0.0, 1.0);
      final starColor = Color.lerp(warmBase, coolBase, colorMix)!;

      starPaint.color = starColor.withValues(alpha: alpha);
      canvas.drawCircle(position, radius, starPaint);

      final drawGlint =
          !performanceDegraded && allowGlints && random.nextDouble() > 0.78;
      if (drawGlint) {
        _drawGlintStar(
          canvas,
          position,
          radius: radius * 1.7,
          color: starColor.withValues(alpha: alpha * 0.8),
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
          _spotlightNodeVisibility(nodeId);
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

  double _spotlightNodeVisibility(String nodeId) =>
      galaxySpotlightNodeOpacity(nodeId, spotlightNodeIds);

  double _spotlightLabelVisibility(String nodeId) =>
      galaxySpotlightLabelOpacity(
        nodeId: nodeId,
        spotlightAnchorId: spotlightAnchorId,
        spotlightNodeIds: spotlightNodeIds,
      );

  void _drawEdges({
    required Canvas canvas,
    required GalaxyLod lod,
    required Rect viewport,
    required Offset viewportCenter,
    required Set<String> visibleNodeIds,
  }) {
    if (lod == GalaxyLod.l0) {
      return;
    }

    final edgesToDraw = _selectVisibleEdges(
      lod: lod,
      viewport: viewport,
      viewportCenter: viewportCenter,
      visibleNodeIds: visibleNodeIds,
    );
    if (edgesToDraw.isNotEmpty) {
      _drawEdgeList(canvas, edgesToDraw);
    }
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
      final reveal = _edgeRevealFor(
        edge,
        sourceReveal: _buildRevealFor(edge.sourceId),
        targetReveal: _buildRevealFor(edge.targetId),
      );
      final searchMultiplier = searchMatchedNodeIds.isEmpty
          ? 1.0
          : (searchMatchedNodeIds.contains(edge.sourceId) ||
                  searchMatchedNodeIds.contains(edge.targetId))
              ? 1.0
              : 0.1;
      final spotlightMultiplier = galaxySpotlightEdgeOpacity(
        sourceId: edge.sourceId,
        targetId: edge.targetId,
        spotlightAnchorId: spotlightAnchorId,
        spotlightNodeIds: spotlightNodeIds,
      );
      final selectionFocusMultiplier = selectedNodeId == null
          ? 1.0
          : (edge.sourceId == selectedNodeId || edge.targetId == selectedNodeId)
              ? 1.25
              : 1.0;
      final alpha = edgeStyle.alpha *
          _edgeAlpha(edge, lod) *
          reveal *
          spotlightMultiplier *
          searchMultiplier *
          selectionFocusMultiplier;
      if (alpha <= 0) {
        continue;
      }

      final midX = (source.dx + target.dx) / 2;
      final midY = (source.dy + target.dy) / 2;
      final paintEdge = _PaintEdge(
        sourceId: edge.sourceId,
        targetId: edge.targetId,
        start: source,
        end: target,
        distanceToViewportCenter:
            (midX - viewportCenter.dx) * (midX - viewportCenter.dx) +
                (midY - viewportCenter.dy) * (midY - viewportCenter.dy),
        color: edgeStyle.color.withValues(alpha: alpha),
        sourceColor: sourceColor.withValues(alpha: alpha),
        targetColor: targetColor.withValues(alpha: alpha),
        strokeWidth: edgeStyle.strokeWidth *
            ((edge.sourceId == spotlightAnchorId ||
                    edge.targetId == spotlightAnchorId)
                ? 1.18
                : 1.0),
        dashLength: edgeStyle.dashLength,
        gapLength: edgeStyle.gapLength,
        relationType: edge.relationType,
        strength: edge.strength,
        reveal: reveal,
        curveDirection: _stableCurveDirection(edge.sourceId, edge.targetId),
        sourceConnections: nodeConnectionCounts[edge.sourceId] ?? 0,
        targetConnections: nodeConnectionCounts[edge.targetId] ?? 0,
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
    final syntheticEdges = _buildSyntheticPlaybackEdges(
      lod: lod,
      viewport: viewport,
      viewportCenter: viewportCenter,
      visibleNodeIds: visibleNodeIds,
    );
    result.addAll(syntheticEdges);
    final budget = _edgeBudgetFor(lod);
    if (result.length > budget) {
      result.removeRange(budget, result.length);
    }

    return result;
  }

  double _edgeRevealFor(
    GalaxyEdgeModel edge, {
    required double sourceReveal,
    required double targetReveal,
  }) {
    if (preRevealedEdgeIds.contains(edge.id)) {
      return 1;
    }
    if (!isBuildAnimating || playbackPlan == null) {
      return 1;
    }
    final step = playbackPlan!.edgeSteps[edge.id];
    if (step != null) {
      return playbackPlan!.edgeRevealAt(edge.id, playbackElapsedMs);
    }
    if (sourceReveal >= 0.999 && targetReveal >= 0.999) {
      return 1;
    }
    return 0;
  }

  List<_PaintEdge> _buildSyntheticPlaybackEdges({
    required GalaxyLod lod,
    required Rect viewport,
    required Offset viewportCenter,
    required Set<String> visibleNodeIds,
  }) {
    final playbackPlan = this.playbackPlan;
    if (!isBuildAnimating ||
        playbackPlan == null ||
        playbackPlan.edgeSteps.isEmpty) {
      return const <_PaintEdge>[];
    }

    final edgesToDraw = <_PaintEdge>[];
    for (final step in playbackPlan.edgeSteps.values) {
      if (!step.isSynthetic) {
        continue;
      }
      final reveal = playbackPlan.edgeRevealAt(step.id, playbackElapsedMs);
      if (reveal <= 0) {
        continue;
      }
      final source = _renderWorldPosition(step.sourceId);
      final target = _renderWorldPosition(step.targetId);
      final sourceNode = nodesById[step.sourceId];
      final targetNode = nodesById[step.targetId];
      if (source == null ||
          target == null ||
          sourceNode == null ||
          targetNode == null) {
        continue;
      }

      final sourceVisible = visibleNodeIds.contains(step.sourceId);
      final targetVisible = visibleNodeIds.contains(step.targetId);
      final intersectsViewport =
          _segmentIntersectsRect(source, target, viewport);
      if (!sourceVisible && !targetVisible && !intersectsViewport) {
        continue;
      }

      final sourceColor =
          _nodeCanvasColor(sourceNode).withValues(alpha: 0.42 * reveal);
      final targetColor =
          _nodeCanvasColor(targetNode).withValues(alpha: 0.42 * reveal);
      final midX = (source.dx + target.dx) / 2;
      final midY = (source.dy + target.dy) / 2;
      edgesToDraw.add(
        _PaintEdge(
          sourceId: step.sourceId,
          targetId: step.targetId,
          start: source,
          end: target,
          distanceToViewportCenter:
              (midX - viewportCenter.dx) * (midX - viewportCenter.dx) +
                  (midY - viewportCenter.dy) * (midY - viewportCenter.dy),
          color: Color.lerp(sourceColor, targetColor, 0.5)!,
          sourceColor: sourceColor,
          targetColor: targetColor,
          strokeWidth: (lod.index >= GalaxyLod.l3.index ? 1.2 : 1.0) *
              displaySettings.linkThicknessScale,
          dashLength: 0,
          gapLength: 0,
          relationType: step.relationType,
          strength: step.strength,
          reveal: reveal,
          curveDirection: _stableCurveDirection(step.sourceId, step.targetId),
          sourceConnections: nodeConnectionCounts[step.sourceId] ?? 0,
          targetConnections: nodeConnectionCounts[step.targetId] ?? 0,
        ),
      );
    }

    edgesToDraw.sort(
      (left, right) => left.distanceToViewportCenter
          .compareTo(right.distanceToViewportCenter),
    );
    return edgesToDraw;
  }

  void _drawEdgeList(Canvas canvas, List<_PaintEdge> edgesToDraw) {
    final paintCache = <int, Paint>{};
    final glowPaintCache = <int, Paint>{};

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
        screenStart: start,
        screenEnd: end,
        worldStart: edge.start,
        worldEnd: edge.end,
        relationType: edge.relationType,
        strength: edge.strength,
        curveDirection: edge.curveDirection,
      );
      final renderedPath = isBuildAnimating && edge.reveal < 0.999
          ? _extractPathReveal(path, edge.reveal)
          : path;
      final hasHubGlow =
          edge.sourceConnections >= 5 || edge.targetConnections >= 5;
      paint.shader = ui.Gradient.linear(
        start,
        end,
        [edge.sourceColor, edge.targetColor],
      );
      if (hasHubGlow && !performanceDegraded) {
        final glowKey = Object.hash(
          edge.color.toARGB32(),
          edge.strokeWidth,
        );
        final glowPaint = glowPaintCache[glowKey] ??
            (glowPaintCache[glowKey] = Paint()
              ..strokeWidth = edge.strokeWidth + 0.6
              ..style = PaintingStyle.stroke
              ..strokeCap = StrokeCap.round
              ..color = edge.color.withValues(alpha: edge.color.a * 0.32)
              ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2));
        canvas.drawPath(renderedPath, glowPaint);
      }
      if (edge.isDashed) {
        _drawDashedPath(
          canvas: canvas,
          path: renderedPath,
          paint: paint,
          dashLength: edge.dashLength,
          gapLength: edge.gapLength,
        );
      } else if (edge.relationType == EdgeRelationType.parentChild ||
          edge.relationType == EdgeRelationType.prerequisite) {
        _drawTaperedEdge(
          canvas: canvas,
          path: renderedPath,
          startColor: edge.sourceColor,
          endColor: edge.targetColor,
          startWidth: edge.strokeWidth,
          endWidth: edge.strokeWidth * 0.6,
        );
      } else {
        canvas.drawPath(renderedPath, paint);
      }

      if (displaySettings.showsArrowFor(edge.relationType) &&
          edge.reveal >= 0.999) {
        _drawArrowHead(
          canvas,
          renderedPath,
          edge.targetColor,
          edge.strokeWidth,
        );
        _drawPathTailDashes(
          canvas: canvas,
          path: renderedPath,
          color: edge.targetColor,
          strokeWidth: edge.strokeWidth * 0.86,
        );
      }
    }
  }

  Path _extractPathReveal(Path path, double reveal) {
    final clamped = reveal.clamp(0.0, 1.0);
    if (clamped <= 0) {
      return Path();
    }
    if (clamped >= 1) {
      return path;
    }
    final revealed = Path();
    for (final metric in path.computeMetrics()) {
      revealed.addPath(
        metric.extractPath(0, metric.length * clamped),
        Offset.zero,
      );
    }
    return revealed;
  }

  void _drawEdgeParticles(Canvas canvas) {
    for (final particle in edgeParticles) {
      final source = _renderWorldPosition(particle.sourceId);
      final target = _renderWorldPosition(particle.targetId);
      if (source == null || target == null) {
        continue;
      }

      final path = _edgePath(
        screenStart: camera.worldToScreen(source),
        screenEnd: camera.worldToScreen(target),
        worldStart: source,
        worldEnd: target,
        relationType: particle.relationType,
        strength: particle.strength,
        curveDirection: _stableCurveDirection(
          particle.sourceId,
          particle.targetId,
        ),
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
      final isPreviewed = previewNodeId == node.id;
      final isSpotlighted = spotlightNodeIds.contains(node.id);
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
      final previewLift = isPreviewed ? -2.0 : 0.0;
      final nodeCenter = item.screenPosition.translate(0, previewLift);

      if (isPreviewed) {
        canvas.drawCircle(
          nodeCenter.translate(0, 1.5),
          radius * 1.12,
          Paint()
            ..color = style.baseColor.withValues(alpha: 0.14 * nodeAlpha)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
        );
      }

      if (!performanceDegraded &&
          style.glowAlpha > 0 &&
          nodeAlpha > 0 &&
          lod.index >= GalaxyLod.l2.index &&
          (isSpotlighted || camera.scale >= 0.8 || node.masteryScore >= 85)) {
        canvas
          ..drawCircle(
            nodeCenter,
            radius * 1.62,
            Paint()
              ..color = style.baseColor.withValues(
                alpha: style.glowAlpha * nodeAlpha * 0.78,
              )
              ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12),
          )
          ..drawCircle(
            nodeCenter,
            radius * 2.08,
            Paint()
              ..color = style.baseColor.withValues(
                alpha: style.glowAlpha * nodeAlpha * 0.34,
              )
              ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 20),
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
          nodeCenter,
          radius,
          Paint()
            ..shader = ui.Gradient.radial(
              nodeCenter,
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
          nodeCenter,
          math.max(1.1, radius * 0.28),
          Paint()
            ..color =
                Colors.white.withValues(alpha: style.coreAlpha * nodeAlpha),
        );
      }

      if (style.masteryRingAlpha > 0 && nodeAlpha > 0) {
        canvas.drawCircle(
          nodeCenter,
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
        _drawDashedCircle(
          canvas: canvas,
          center: nodeCenter,
          radius: radius + 1,
          color: style.baseColor.withValues(alpha: 0.28 * nodeAlpha),
        );
        final questionPainter = TextPainter(
          text: TextSpan(
            text: '?',
            style: TextStyle(
              color: style.baseColor.withValues(alpha: 0.42 * nodeAlpha),
              fontSize: math.max(10, radius * 1.05),
              fontWeight: FontWeight.w700,
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        questionPainter.paint(
          canvas,
          Offset(
            nodeCenter.dx - questionPainter.width / 2,
            nodeCenter.dy - questionPainter.height / 2,
          ),
        );
      }

      if (!performanceDegraded &&
          node.masteryScore >= 85 &&
          lod.index >= GalaxyLod.l2.index) {
        canvas.drawCircle(
          nodeCenter,
          radius * 2.2,
          Paint()
            ..color = style.baseColor.withValues(alpha: 0.08 * nodeAlpha)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 22),
        );
      }

      if (node.importance >= 4 &&
          lod.index >= GalaxyLod.l3.index &&
          (isSpotlighted || camera.scale >= 0.9)) {
        _drawOrbitRing(
          canvas: canvas,
          center: nodeCenter,
          radius: radius * 1.42,
          color: style.baseColor.withValues(alpha: 0.18 * nodeAlpha),
          dashed: node.importance < 5,
        );
      }

      if (!performanceDegraded &&
          node.importance >= 5 &&
          lod.index >= GalaxyLod.l3.index &&
          (selectedNodeId == node.id || camera.scale >= 1.0)) {
        _drawNodeRays(
          canvas,
          nodeCenter,
          radius: radius,
          color: style.baseColor.withValues(alpha: 0.08 * nodeAlpha),
          seed: _nodeSeed(node.id),
          rotation: ambientPhase * (math.pi / 360),
        );
      }

      if (tapFeedbackNodeId == node.id) {
        _drawTapRipples(
          canvas: canvas,
          center: nodeCenter,
          radius: radius,
          color: style.baseColor.withValues(alpha: nodeAlpha),
          phase: tapFeedbackPhase,
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
            nodeCenter,
            radius * (1.45 + selectionPulse * 0.14),
            Paint()
              ..color = selectedColor.withValues(
                alpha: 0.13 + selectionPulse * 0.08,
              )
              ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 16),
          )
          ..drawCircle(
            nodeCenter,
            radius + 4 + selectionPulse * 1.4,
            Paint()
              ..color = selectedColor.withValues(alpha: 0.85 * nodeAlpha)
              ..strokeWidth = 1.6
              ..style = PaintingStyle.stroke,
          )
          ..drawCircle(
            nodeCenter,
            ui.lerpDouble(radius * 1.0, radius * 3.0, selectionPulse)!,
            Paint()
              ..color = selectedColor.withValues(
                alpha: (0.4 * (1 - selectionPulse)).clamp(0.0, 0.4),
              )
              ..strokeWidth = 1.1
              ..style = PaintingStyle.stroke,
          );
      }

      if (celebrationNodeIds.contains(node.id)) {
        canvas
          ..drawCircle(
            nodeCenter,
            radius * 3.4,
            Paint()
              ..color = style.baseColor.withValues(alpha: 0.22 * nodeAlpha)
              ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 28),
          )
          ..drawCircle(
            nodeCenter,
            radius * 1.9,
            Paint()
              ..color = DS.brandPrimary.withValues(alpha: 0.14 * nodeAlpha)
              ..style = PaintingStyle.stroke
              ..strokeWidth = 1.6,
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
          _labelRevealFor(node.id) *
          _searchNodeVisibility(node.id) *
          _spotlightLabelVisibility(node.id);
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

  GalaxyLod _currentLod(double scale) => resolveGalaxyLod(scale);

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
    final emphasized = spotlightNodeIds.contains(node.id);
    final densityAlpha = displaySettings.labelDensityForScale(
      camera.scale,
      importance: node.importance,
      emphasized: emphasized,
    );
    switch (lod) {
      case GalaxyLod.l0:
        return emphasized ? densityAlpha : 0;
      case GalaxyLod.l1:
        return emphasized || node.importance >= 5 ? densityAlpha : 0;
      case GalaxyLod.l2:
        return emphasized || node.importance >= 3 ? densityAlpha : 0;
      case GalaxyLod.l3:
      case GalaxyLod.l4:
        return densityAlpha;
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
          strokeWidth: 1.25 * displaySettings.linkThicknessScale,
          alpha: 0.54,
        );
      case EdgeRelationType.prerequisite:
        return _PaintEdgeStyle(
          color: _toneColor(
            bridgeColor,
            lightnessDelta: isDarkMode ? 0.08 : -0.04,
          ),
          strokeWidth: 1.0 * displaySettings.linkThicknessScale,
          alpha: 0.48,
        );
      case EdgeRelationType.derived:
        return _PaintEdgeStyle(
          color: _toneColor(bridgeColor, saturationMultiplier: 0.92),
          strokeWidth: 0.9 * displaySettings.linkThicknessScale,
          alpha: 0.34,
          dashLength: 6,
          gapLength: 4,
        );
      case EdgeRelationType.related:
        return _PaintEdgeStyle(
          color: bridgeColor,
          strokeWidth: 0.6 * displaySettings.linkThicknessScale,
          alpha: 0.32,
        );
      case EdgeRelationType.similar:
        return _PaintEdgeStyle(
          color: _toneColor(bridgeColor, saturationMultiplier: 0.82),
          strokeWidth: 0.78 * displaySettings.linkThicknessScale,
          alpha: 0.28,
          dashLength: 2,
          gapLength: 3,
        );
      case EdgeRelationType.contrast:
        return _PaintEdgeStyle(
          color: _toneColor(
            bridgeColor,
            lightnessDelta: isDarkMode ? 0.04 : -0.03,
          ),
          strokeWidth: 0.5 * displaySettings.linkThicknessScale,
          alpha: 0.21,
          dashLength: 4,
          gapLength: 6,
        );
      case EdgeRelationType.application:
        return _PaintEdgeStyle(
          color: _toneColor(bridgeColor, saturationMultiplier: 0.95),
          strokeWidth: 0.5 * displaySettings.linkThicknessScale,
          alpha: 0.21,
          dashLength: 4,
          gapLength: 6,
        );
      case EdgeRelationType.example:
        return _PaintEdgeStyle(
          color: _toneColor(bridgeColor, saturationMultiplier: 0.78),
          strokeWidth: 0.78 * displaySettings.linkThicknessScale,
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
    final baseColor = _masteryTemperatureColor(
      _nodeCanvasColor(node),
      masteryScore: node.masteryScore,
    );
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
    final base = math.max(
      4.0,
      node.radius *
          displaySettings.nodeSizeScale *
          camera.scale.clamp(0.75, 1.5),
    );
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

  Path _edgePath({
    required Offset screenStart,
    required Offset screenEnd,
    required Offset worldStart,
    required Offset worldEnd,
    required EdgeRelationType relationType,
    required double strength,
    required double curveDirection,
  }) {
    final screenDelta = screenEnd - screenStart;
    final length = screenDelta.distance;
    if (length < 18) {
      return Path()
        ..moveTo(screenStart.dx, screenStart.dy)
        ..lineTo(screenEnd.dx, screenEnd.dy);
    }

    if (relationType != EdgeRelationType.parentChild &&
        relationType != EdgeRelationType.prerequisite &&
        relationType != EdgeRelationType.derived) {
      return Path()
        ..moveTo(screenStart.dx, screenStart.dy)
        ..lineTo(screenEnd.dx, screenEnd.dy);
    }

    final normal = Offset(-screenDelta.dy / length, screenDelta.dx / length);
    final midpoint = Offset(
      (screenStart.dx + screenEnd.dx) / 2,
      (screenStart.dy + screenEnd.dy) / 2,
    );
    final worldLength = (worldEnd - worldStart).distance;
    final bendScale =
        relationType == EdgeRelationType.parentChild ? 0.12 : 0.08;
    final bend =
        (worldLength * camera.scale * bendScale * (0.85 + strength * 0.35))
            .clamp(10.0, 34.0);
    final control = midpoint + normal * bend * curveDirection;
    return Path()
      ..moveTo(screenStart.dx, screenStart.dy)
      ..quadraticBezierTo(control.dx, control.dy, screenEnd.dx, screenEnd.dy);
  }

  void _drawTaperedEdge({
    required Canvas canvas,
    required Path path,
    required Color startColor,
    required Color endColor,
    required double startWidth,
    required double endWidth,
    int segments = 10,
  }) {
    final metrics = path.computeMetrics().toList(growable: false);
    if (metrics.isEmpty) {
      return;
    }
    final metric = metrics.first;
    if (metric.length <= 0) {
      return;
    }
    final segmentLength = metric.length / segments;
    for (var index = 0; index < segments; index++) {
      final t0 = index / segments;
      final t1 = (index + 1) / segments;
      final extract = metric.extractPath(
        segmentLength * index,
        math.min(metric.length, segmentLength * (index + 1)),
      );
      final color = Color.lerp(startColor, endColor, (t0 + t1) / 2)!;
      final width = ui.lerpDouble(startWidth, endWidth, (t0 + t1) / 2)!;
      canvas.drawPath(
        extract,
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = width,
      );
    }
  }

  void _drawPathTailDashes({
    required Canvas canvas,
    required Path path,
    required Color color,
    required double strokeWidth,
  }) {
    final metrics = path.computeMetrics().toList(growable: false);
    if (metrics.isEmpty) {
      return;
    }
    final metric = metrics.first;
    final tailStart = metric.length * 0.8;
    final tailPath = metric.extractPath(tailStart, metric.length);
    _drawDashedPath(
      canvas: canvas,
      path: tailPath,
      paint: Paint()
        ..color = color.withValues(alpha: color.a * 0.78)
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeWidth = strokeWidth,
      dashLength: 5,
      gapLength: 4,
    );
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
    required double rotation,
  }) {
    final rayPaint = Paint()
      ..color = color
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 1.0;
    final rayCount = 4 + (seed * 10).round() % 3;
    for (var index = 0; index < rayCount; index++) {
      final angle = seed + rotation + (math.pi * 2 * index / rayCount);
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

  void _drawOrbitRing({
    required Canvas canvas,
    required Offset center,
    required double radius,
    required Color color,
    required bool dashed,
  }) {
    if (dashed) {
      _drawDashedCircle(
        canvas: canvas,
        center: center,
        radius: radius,
        color: color,
      );
      return;
    }
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..color = color
        ..strokeWidth = 1
        ..style = PaintingStyle.stroke,
    );
  }

  void _drawTapRipples({
    required Canvas canvas,
    required Offset center,
    required double radius,
    required Color color,
    required double phase,
  }) {
    final ripples = <(double, double, double, double, double)>[
      (0.0, 1.2, 2.0, 0.35, 1.8),
      (0.33, 1.5, 2.5, 0.22, 1.4),
      (0.66, 1.8, 3.0, 0.12, 1.1),
    ];
    for (final ripple in ripples) {
      final progress = ((phase - ripple.$1) / (1 - ripple.$1)).clamp(0.0, 1.0);
      if (progress <= 0) {
        continue;
      }
      canvas.drawCircle(
        center,
        ui.lerpDouble(radius * ripple.$2, radius * ripple.$3, progress)!,
        Paint()
          ..color = color.withValues(alpha: ripple.$4 * (1 - progress))
          ..strokeWidth = ripple.$5
          ..style = PaintingStyle.stroke,
      );
    }
  }

  double _fade(double value, double start, double end) =>
      galaxyLodFade(value, start, end);

  bool _segmentIntersectsRect(Offset a, Offset b, Rect rect) {
    if (rect.contains(a) || rect.contains(b)) {
      return true;
    }

    return Rect.fromPoints(a, b).overlaps(rect);
  }

  Color _nodeCanvasColor(GalaxyNodeModel node) {
    final blended = blendedColors[node.id] ??
        SectorConfig.resolveNodeBaseColor(node: node, isDarkMode: isDarkMode);
    return SectorConfig.applyImportanceRamp(
      blended,
      importance: node.importance,
      isDarkMode: isDarkMode,
    );
  }

  double _buildRevealFor(String nodeId) {
    if (preRevealedNodeIds.contains(nodeId)) {
      return 1;
    }
    final playbackPlan = this.playbackPlan;
    if (!isBuildAnimating || playbackPlan == null) {
      return 1;
    }
    return playbackPlan.nodeRevealAt(nodeId, playbackElapsedMs);
  }

  double _labelRevealFor(String nodeId) {
    if (preRevealedNodeIds.contains(nodeId)) {
      return 1;
    }
    final playbackPlan = this.playbackPlan;
    if (!isBuildAnimating || playbackPlan == null) {
      return 1;
    }
    return playbackPlan.labelRevealAt(nodeId, playbackElapsedMs);
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

  Color _masteryTemperatureColor(Color color, {required int masteryScore}) {
    if (masteryScore >= 85) {
      return Color.lerp(color, const Color(0xFFFFD700), 0.05)!;
    }
    if (masteryScore < 30) {
      return Color.lerp(color, const Color(0xFF88B4FF), 0.05)!;
    }
    return color;
  }

  double _stableCurveDirection(String sourceId, String targetId) =>
      ((sourceId.hashCode ^ targetId.hashCode) & 1) == 0 ? 1.0 : -1.0;

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
    required this.sourceId,
    required this.targetId,
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
    required this.reveal,
    required this.curveDirection,
    required this.sourceConnections,
    required this.targetConnections,
  });

  final String sourceId;
  final String targetId;
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
  final double reveal;
  final double curveDirection;
  final int sourceConnections;
  final int targetConnections;

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
