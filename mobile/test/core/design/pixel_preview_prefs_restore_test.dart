// V4-F01 一审 C2 · initialize() 合法持久索引恢复（守卫不误伤面）。
//
// 与 pixel_preview_prefs_guard_test.dart 同理：独立 isolate 单场景，
// 首次 initialize() 真实读取持久值。若边界守卫误写成
// `pixelIndex < values.length - 1` 之类的过紧条件，dusk（合法档）会被
// 误回落 classic，本测试红。
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('initialize() 读到合法持久索引 dusk 恢复对应档', () async {
    SharedPreferences.setMockInitialValues({
      ThemeManager.pixelPreviewPrefsKey: PixelPreviewProfile.dusk.index,
    });
    final manager = ThemeManager();
    await manager.initialize();
    expect(manager.pixelPreviewProfile, PixelPreviewProfile.dusk);
    expect(manager.pixelPreviewEnabled, isTrue);
  });
}
