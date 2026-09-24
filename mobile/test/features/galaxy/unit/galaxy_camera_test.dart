import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_camera.dart';

void main() {
  group('GalaxyCamera', () {
    test('applyZoom keeps the focal world point anchored', () {
      const camera = GalaxyCamera(
        offset: Offset(120, 80),
        scale: 0.6,
        viewportSize: Size(400, 300),
      );
      const focalPoint = Offset(240, 160);
      final anchoredWorldPoint = camera.screenToWorld(focalPoint);

      final zoomed = camera.applyZoom(1.8, focalPoint);

      expect(
        (zoomed.worldToScreen(anchoredWorldPoint) - focalPoint).distance,
        lessThan(0.000001),
      );
    });

    test('centerOnWorldPoint moves the requested node to screen center', () {
      const camera = GalaxyCamera(
        offset: Offset.zero,
        scale: 0.75,
        viewportSize: Size(360, 640),
      );
      const worldPoint = Offset(180, -90);

      final centered = camera.centerOnWorldPoint(worldPoint: worldPoint);

      expect(
        centered.worldToScreen(worldPoint),
        const Offset(180, 320),
      );
    });
  });

  // G-03「焦点随相机」：视口锚点解析（纯函数）——平移/缩放后锚应落在
  // 视口内距中心最近的节点；显式选中在视口内不被冲掉；视口空则诚实无锚。
  group('GalaxyCameraFocus.resolveNearestNodeId', () {
    const viewport = Rect.fromLTWH(0, 0, 400, 300);
    final positions = <String, Offset>{
      'left': const Offset(-100, 150), // 视口外
      'edge': const Offset(190, 150), // 视口内，离中心较远
      'near': const Offset(201, 150), // 视口内，距中心最近
      'far': const Offset(390, 290), // 视口内，角落
    };

    test('returns the in-viewport node nearest to the viewport center', () {
      final anchor = GalaxyCameraFocus.resolveNearestNodeId(
        viewportRect: viewport,
        positions: positions,
      );
      expect(anchor, 'near');
    });

    test('keeps the preferred anchor while it stays inside the viewport', () {
      final anchor = GalaxyCameraFocus.resolveNearestNodeId(
        viewportRect: viewport,
        positions: positions,
        preferredId: 'far',
      );
      expect(anchor, 'far');
    });

    test('re-anchors when the preferred node has left the viewport', () {
      final anchor = GalaxyCameraFocus.resolveNearestNodeId(
        viewportRect: viewport,
        positions: positions,
        preferredId: 'left',
      );
      expect(anchor, 'near');
    });

    test('returns null when the viewport contains no nodes (honest empty)', () {
      final anchor = GalaxyCameraFocus.resolveNearestNodeId(
        viewportRect: viewport,
        positions: const {
          'outside-left': Offset(-50, 150),
          'outside-right': Offset(450, 150),
        },
      );
      expect(anchor, isNull);
    });

    test('returns null for empty positions', () {
      final anchor = GalaxyCameraFocus.resolveNearestNodeId(
        viewportRect: viewport,
        positions: const {},
      );
      expect(anchor, isNull);
    });
  });
}
