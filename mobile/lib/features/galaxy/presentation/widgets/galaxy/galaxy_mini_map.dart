import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_camera.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class GalaxyMiniMap extends StatelessWidget {
  const GalaxyMiniMap({
    required this.camera,
    required this.positions,
    required this.nodesById,
    required this.worldBounds,
    required this.isDarkMode,
    required this.onNavigate,
    required this.onViewportDragged,
    super.key,
    this.size = 120,
  });

  final GalaxyCamera camera;
  final Map<String, Offset> positions;
  final Map<String, GalaxyNodeModel> nodesById;
  final Rect worldBounds;
  final bool isDarkMode;
  final double size;
  final ValueChanged<Offset> onNavigate;
  final ValueChanged<Offset> onViewportDragged;

  @override
  Widget build(BuildContext context) {
    final frameColor = isDarkMode
        ? Colors.white.withValues(alpha: 0.14)
        : Colors.black.withValues(alpha: 0.08);

    return SizedBox(
      width: size,
      height: size,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTapDown: (details) => onNavigate(
              _localToWorld(details.localPosition, Size.square(size)),
            ),
            onPanStart: (details) => onViewportDragged(
              _localToWorld(details.localPosition, Size.square(size)),
            ),
            onPanUpdate: (details) => onViewportDragged(
              _localToWorld(details.localPosition, Size.square(size)),
            ),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: isDarkMode
                    ? const Color(0xAA101A2B)
                    : Colors.white.withValues(alpha: 0.8),
                border: Border.all(color: frameColor),
                borderRadius: BorderRadius.circular(18),
                boxShadow: [
                  BoxShadow(
                    color:
                        Colors.black.withValues(alpha: isDarkMode ? 0.22 : 0.1),
                    blurRadius: 16,
                    offset: const Offset(0, 12),
                  ),
                ],
              ),
              child: CustomPaint(
                painter: _GalaxyMiniMapPainter(
                  camera: camera,
                  positions: positions,
                  nodesById: nodesById,
                  worldBounds: worldBounds,
                  isDarkMode: isDarkMode,
                ),
                child: const SizedBox.expand(),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Offset _localToWorld(Offset local, Size size) {
    final normalizedX = (local.dx / size.width).clamp(0.0, 1.0);
    final normalizedY = (local.dy / size.height).clamp(0.0, 1.0);
    return Offset(
      lerpDouble(worldBounds.left, worldBounds.right, normalizedX)!,
      lerpDouble(worldBounds.top, worldBounds.bottom, normalizedY)!,
    );
  }
}

class _GalaxyMiniMapPainter extends CustomPainter {
  const _GalaxyMiniMapPainter({
    required this.camera,
    required this.positions,
    required this.nodesById,
    required this.worldBounds,
    required this.isDarkMode,
  });

  final GalaxyCamera camera;
  final Map<String, Offset> positions;
  final Map<String, GalaxyNodeModel> nodesById;
  final Rect worldBounds;
  final bool isDarkMode;

  @override
  void paint(Canvas canvas, Size size) {
    final paddedBounds = worldBounds.inflate(40);
    final scaleX = size.width / math.max(1, paddedBounds.width);
    final scaleY = size.height / math.max(1, paddedBounds.height);
    final trackColor =
        isDarkMode ? const Color(0xFF152238) : const Color(0xFFEFF3F8);
    final viewportColor =
        isDarkMode ? const Color(0xFF88B4FF) : const Color(0xFF3563DA);

    canvas.drawRect(Offset.zero & size, Paint()..color = trackColor);

    for (final entry in positions.entries) {
      final node = nodesById[entry.key];
      if (node == null) {
        continue;
      }

      final point = _mapToMini(entry.value, paddedBounds, scaleX, scaleY);
      final color = SectorConfig.getColor(node.sector, isDarkMode: isDarkMode);
      canvas.drawCircle(
        point,
        node.importance >= 4 ? 2.1 : 1.4,
        Paint()..color = color.withValues(alpha: node.isUnlocked ? 0.92 : 0.38),
      );
    }

    final viewport = camera.viewportRect;
    final rect = Rect.fromLTRB(
      _mapToMini(
        viewport.topLeft,
        paddedBounds,
        scaleX,
        scaleY,
      ).dx,
      _mapToMini(
        viewport.topLeft,
        paddedBounds,
        scaleX,
        scaleY,
      ).dy,
      _mapToMini(
        viewport.bottomRight,
        paddedBounds,
        scaleX,
        scaleY,
      ).dx,
      _mapToMini(
        viewport.bottomRight,
        paddedBounds,
        scaleX,
        scaleY,
      ).dy,
    );

    canvas
      ..drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(10)),
        Paint()..color = viewportColor.withValues(alpha: 0.12),
      )
      ..drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(10)),
        Paint()
          ..color = viewportColor.withValues(alpha: 0.78)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.6,
      );
  }

  Offset _mapToMini(
    Offset world,
    Rect bounds,
    double scaleX,
    double scaleY,
  ) =>
      Offset(
        (world.dx - bounds.left) * scaleX,
        (world.dy - bounds.top) * scaleY,
      );

  @override
  bool shouldRepaint(covariant _GalaxyMiniMapPainter oldDelegate) =>
      oldDelegate.camera != camera ||
      oldDelegate.positions != positions ||
      oldDelegate.worldBounds != worldBounds ||
      oldDelegate.isDarkMode != isDarkMode;
}
