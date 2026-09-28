// V4-F01 一审 C2 · initialize() 越界持久值直接守卫。
//
// 独立测试文件 = 独立 isolate：ThemeManager 单例的 `_initialized` 在本
// isolate 首次 `initialize()` 前恒 false，因此这里的 initialize() 会真实
// 走持久值读取路径（pixel_preview_theme_test.dart 的 setUp 已初始化单例，
// 无法在其内复现该路径；同文件多测试会共享单例，故本文件只含一个场景，
// 合法索引恢复场景在 pixel_preview_prefs_restore_test.dart）。
//
// 必须可失败：若 ThemeManager.initialize() 移除索引边界守卫
// （`pixelIndex >= 0 && < values.length`），越界持久值 99 将触发
// RangeError 或错误档位，本测试红。
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('initialize() 读到越界持久索引 99 回落 classic（preview off）', () async {
    SharedPreferences.setMockInitialValues({
      ThemeManager.pixelPreviewPrefsKey: 99,
    });
    final manager = ThemeManager();
    await manager.initialize();
    expect(manager.pixelPreviewProfile, PixelPreviewProfile.classic);
    expect(manager.pixelPreviewEnabled, isFalse);
  });
}
