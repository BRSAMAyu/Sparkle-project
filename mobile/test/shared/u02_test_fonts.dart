import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// U-02 验收截图用真实字体装载（macOS 宿主）。
///
/// 背景：flutter test 默认只有 FlutterTest 元数据字体（色块渲染），既有
/// golden 基线全部是色块图，无法承担"真实渲染体验证据"。本 helper 在
/// `tester.runAsync` 内把宿主系统真实字体注册进测试引擎：
/// - `.AppleSystemUIFont` / `Roboto` ← Hiragino Sans GB.ttc（中日韩一体，
///   含拉丁字形；PingFang.ttc 为系统保护路径，取 Hiragino 同源替代）；
/// - `MaterialIcons` ← Flutter SDK cache 图标字体。
/// 必须在 `tester.runAsync` 内调用：引擎字体注册需要真异步完成，假异步
/// zone 内 load() 完成但渲染拾取不到（探针实证，见 U-02 证据记录）。
class U02TestFonts {
  U02TestFonts._();

  static bool _loaded = false;

  static Future<void> _register(String family, String path) async {
    final file = File(path);
    if (!file.existsSync()) {
      debugPrint('U02TestFonts FONT MISS: $path');
      return;
    }
    final Uint8List bytes = file.readAsBytesSync();
    final loader = FontLoader(family)
      ..addFont(Future.value(bytes.buffer.asByteData()));
    await loader.load();
  }

  /// 幂等装载；在 testWidgets 内 `await tester.runAsync(U02TestFonts.load)`。
  static Future<void> load() async {
    if (_loaded) return;
    TestWidgetsFlutterBinding.ensureInitialized();
    await _register(
      '.AppleSystemUIFont',
      '/System/Library/Fonts/Hiragino Sans GB.ttc',
    );
    await _register('Roboto', '/System/Library/Fonts/Hiragino Sans GB.ttc');
    await _register('Heiti SC', '/System/Library/Fonts/STHeiti Medium.ttc');
    final flutterBin = Platform.environment['FLUTTER_ROOT'] ?? '';
    if (flutterBin.isNotEmpty) {
      await _register(
        'MaterialIcons',
        '$flutterBin/bin/cache/artifacts/material_fonts/'
        'MaterialIcons-Regular.otf',
      );
    }
    _loaded = true;
  }
}
