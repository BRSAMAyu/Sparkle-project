import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';

void main() {
  group('Galaxy LOD helpers', () {
    test('resolves scale boundaries to the correct lod band', () {
      expect(resolveGalaxyLod(0.11), GalaxyLod.l0);
      expect(resolveGalaxyLod(0.12), GalaxyLod.l1);
      expect(resolveGalaxyLod(0.25), GalaxyLod.l2);
      expect(resolveGalaxyLod(0.5), GalaxyLod.l3);
      expect(resolveGalaxyLod(1.01), GalaxyLod.l4);
    });

    test('fade helper clamps below and above range', () {
      expect(galaxyLodFade(0.1, 0.25, 0.5), 0);
      expect(galaxyLodFade(0.5, 0.25, 0.5), 1);
      expect(galaxyLodFade(0.375, 0.25, 0.5), closeTo(0.5, 0.0001));
    });
  });
}
