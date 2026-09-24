import 'dart:ui';

/// G-03「焦点随相机」：视口锚点解析（纯函数，零状态）。
///
/// 挂账差额清理：视口被移动时，spotlight 锚此前要么钉在屏外旧节点
/// （误导），要么全空（tech demo 感——不知道该看哪）。本解析器把
/// 「当前该看哪个节点」收敛为视口几何的纯函数，供屏幕在既有相机
/// 变更路径（pan/zoom/fling）内消费——不新增状态机、不新增字段。
class GalaxyCameraFocus {
  const GalaxyCameraFocus._();

  /// 返回视口内距视口中心最近的节点 id。
  ///
  /// - [preferredId]（显式选中/既有锚）仍在视口内时直接沿用——用户
  ///   点选的焦点不被平移冲掉，只有当它被移出视口才交还给几何；
  /// - 视口内无任何节点时返回 null（诚实退回无锚态，不造默认值）；
  /// - 平局（距离相等）保持 [positions] 插入序中先到者，结果确定。
  static String? resolveNearestNodeId({
    required Rect viewportRect,
    required Map<String, Offset> positions,
    String? preferredId,
  }) {
    if (positions.isEmpty) {
      return null;
    }
    if (preferredId != null) {
      final preferredPosition = positions[preferredId];
      if (preferredPosition != null &&
          viewportRect.contains(preferredPosition)) {
        return preferredId;
      }
    }
    final center = viewportRect.center;
    String? nearestId;
    var nearestDistance = double.infinity;
    positions.forEach((nodeId, position) {
      if (!viewportRect.contains(position)) {
        return;
      }
      final distance = (position - center).distanceSquared;
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestId = nodeId;
      }
    });
    return nearestId;
  }
}

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
