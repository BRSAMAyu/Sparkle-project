import 'dart:ui';

/// Pure camera model for world/screen coordinate conversion.
class GalaxyCamera {
  const GalaxyCamera({
    required this.offset,
    required this.scale,
    required this.viewportSize,
    this.minScale = 0.08,
    this.maxScale = 2.5,
  });

  final Offset offset;
  final double scale;
  final Size viewportSize;
  final double minScale;
  final double maxScale;

  Rect get viewportRect => Rect.fromLTWH(
        -offset.dx / scale,
        -offset.dy / scale,
        viewportSize.width / scale,
        viewportSize.height / scale,
      );

  Offset screenToWorld(Offset screenPoint) => Offset(
        (screenPoint.dx - offset.dx) / scale,
        (screenPoint.dy - offset.dy) / scale,
      );

  Offset worldToScreen(Offset worldPoint) => Offset(
        worldPoint.dx * scale + offset.dx,
        worldPoint.dy * scale + offset.dy,
      );

  GalaxyCamera copyWith({
    Offset? offset,
    double? scale,
    Size? viewportSize,
    double? minScale,
    double? maxScale,
  }) =>
      GalaxyCamera(
        offset: offset ?? this.offset,
        scale: scale ?? this.scale,
        viewportSize: viewportSize ?? this.viewportSize,
        minScale: minScale ?? this.minScale,
        maxScale: maxScale ?? this.maxScale,
      );

  GalaxyCamera applyPan(Offset delta) => copyWith(offset: offset + delta);

  GalaxyCamera applyZoom(double scaleDelta, Offset focalPoint) {
    if (scaleDelta == 0) {
      return this;
    }

    final nextScale = (scale * scaleDelta).clamp(minScale, maxScale);
    if ((nextScale - scale).abs() < 0.000001) {
      return this;
    }

    final scaleRatio = nextScale / scale;
    final nextOffset = Offset(
      focalPoint.dx - (focalPoint.dx - offset.dx) * scaleRatio,
      focalPoint.dy - (focalPoint.dy - offset.dy) * scaleRatio,
    );

    return copyWith(offset: nextOffset, scale: nextScale);
  }

  GalaxyCamera withViewportSize(Size nextViewportSize) {
    if (nextViewportSize == viewportSize) {
      return this;
    }

    final currentWorldCenter = screenToWorld(
      Offset(viewportSize.width / 2, viewportSize.height / 2),
    );

    return centerOnWorldPoint(
      worldPoint: currentWorldCenter,
      nextViewportSize: nextViewportSize,
    );
  }

  GalaxyCamera centerOnWorldPoint({
    required Offset worldPoint,
    Size? nextViewportSize,
  }) {
    final targetViewport = nextViewportSize ?? viewportSize;
    final nextOffset = Offset(
      targetViewport.width / 2 - worldPoint.dx * scale,
      targetViewport.height / 2 - worldPoint.dy * scale,
    );

    return copyWith(offset: nextOffset, viewportSize: targetViewport);
  }

  static GalaxyCamera fitRect({
    required Rect worldBounds,
    required Size viewportSize,
    double minScale = 0.08,
    double maxScale = 2.5,
    double padding = 120,
  }) {
    final paddedBounds = worldBounds.inflate(padding);
    final safeWidth = paddedBounds.width <= 0 ? 1.0 : paddedBounds.width;
    final safeHeight = paddedBounds.height <= 0 ? 1.0 : paddedBounds.height;
    final scaleX = viewportSize.width / safeWidth;
    final scaleY = viewportSize.height / safeHeight;
    final fittedScale = scaleX < scaleY ? scaleX : scaleY;
    final initialScale = fittedScale.clamp(minScale, maxScale);
    final worldCenter = paddedBounds.center;

    return GalaxyCamera(
      offset: Offset(
        viewportSize.width / 2 - worldCenter.dx * initialScale,
        viewportSize.height / 2 - worldCenter.dy * initialScale,
      ),
      scale: initialScale,
      viewportSize: viewportSize,
      minScale: minScale,
      maxScale: maxScale,
    );
  }
}
