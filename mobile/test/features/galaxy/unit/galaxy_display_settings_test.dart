import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_force_engine.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_display_settings_provider.dart';

void main() {
  group('GalaxyDisplaySettings', () {
    test('serializes and restores with clamped values', () {
      final settings = GalaxyDisplaySettings.fromJson({
        'textFadeThreshold': 2.0,
        'nodeSizeScale': 0.5,
        'linkThicknessScale': 1.2,
        'centerForce': 0.0022,
        'repelForce': 15000,
        'linkForce': 0.051,
        'linkDistance': 140,
        'replaySpeed': 1.6,
      })!;

      expect(settings.textFadeThreshold, kGalaxyTextFadeThresholdMax);
      expect(settings.nodeSizeScale, kGalaxyNodeSizeScaleMin);
      expect(settings.linkThicknessScale, 1.2);
      expect(settings.centerForce, 0.0022);
      expect(settings.repelForce, 15000);
      expect(settings.linkForce, 0.051);
      expect(settings.linkDistance, 140);
      expect(settings.replaySpeed, 1.6);
      expect(
        GalaxyDisplaySettings.fromJson(settings.toJson()),
        equals(settings),
      );
    });

    test('label density responds to scale and emphasis', () {
      const settings = GalaxyDisplaySettings(textFadeThreshold: 0.6);

      expect(
        settings.labelDensityForScale(
          0.4,
          importance: 2,
          emphasized: false,
        ),
        0,
      );
      expect(
        settings.labelDensityForScale(
          0.72,
          importance: 2,
          emphasized: false,
        ),
        greaterThan(0),
      );
      expect(
        settings.labelDensityForScale(
          0.25,
          importance: 2,
          emphasized: true,
        ),
        1,
      );
    });

    test('spotlight fades outer graph but keeps anchor and neighbors strong',
        () {
      const spotlight = {'root', 'child'};

      expect(galaxySpotlightNodeOpacity('root', spotlight), 1);
      expect(galaxySpotlightNodeOpacity('other', spotlight), 0.2);

      expect(
        galaxySpotlightLabelOpacity(
          nodeId: 'root',
          spotlightAnchorId: 'root',
          spotlightNodeIds: spotlight,
        ),
        1,
      );
      expect(
        galaxySpotlightLabelOpacity(
          nodeId: 'child',
          spotlightAnchorId: 'root',
          spotlightNodeIds: spotlight,
        ),
        0.94,
      );
      expect(
        galaxySpotlightEdgeOpacity(
          sourceId: 'root',
          targetId: 'child',
          spotlightAnchorId: 'root',
          spotlightNodeIds: spotlight,
        ),
        1,
      );
      expect(
        galaxySpotlightEdgeOpacity(
          sourceId: 'root',
          targetId: 'other',
          spotlightAnchorId: 'root',
          spotlightNodeIds: spotlight,
        ),
        0.24,
      );
    });

    test('link distance maps to force engine spring rest length', () {
      final engine = GalaxyForceEngine();
      engine.updateParameters(springRestLength: 144);

      expect(engine.springRestLength, 144);
    });
  });
}
