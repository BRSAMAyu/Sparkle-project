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
}
