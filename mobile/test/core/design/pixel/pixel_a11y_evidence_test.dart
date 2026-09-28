// V4-F06 · 证据采集：像素故事页 200% 文本 + 减弱动效（PNG + 语义 dump）。
//
// 常规跑 `flutter test`：本文件仍执行真实渲染断言（200%/100% 故事页可
// 构建、五态语义在树、无异常），不写文件——保证套件全绿且无副作用。
// 设 `PIXEL_A11Y_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   pixel_story_<variant>.png（整页 RepaintBoundary 截图，dpr=2）
//   pixel_story_<variant>_semantics.txt（语义树 dump，元素树口径）
// 证据落盘路径见 v4/evidence/V4-F06/run_manifest.json。
//
// 语义 dump 口径与 F04 shell_evidence_test 同源（元素树：
// RenderParagraph + RenderSemanticsAnnotations；3.41.3 widget-test 泵内
// rootSemanticsNode 恒 null，F02/F04 同口径）。
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel.dart';

String _dumpSemanticsFromElements(Element rootElement) {
  final buf = StringBuffer();
  void visit(Element el, int depth) {
    final ro = el.renderObject;
    if (ro is RenderParagraph) {
      final text = ro.text.toPlainText();
      if (text.trim().isNotEmpty) {
        final rect = ro.localToGlobal(Offset.zero) & ro.size;
        buf.writeln(
          '${'  ' * depth}- label="$text" isText=true rect=$rect',
        );
      }
    }
    if (ro is RenderSemanticsAnnotations) {
      var isButton = false;
      try {
        isButton = (ro as dynamic).button as bool? ?? false;
      } on NoSuchMethodError {
        isButton = false;
      }
      final rect = ro.localToGlobal(Offset.zero) & ro.size;
      buf.writeln(
        '${'  ' * depth}- label="${ro.properties.label}" '
        'value="${ro.properties.value}" '
        'isButton=$isButton rect=$rect',
      );
      depth += 1;
    }
    el.visitChildElements((child) => visit(child, depth));
  }

  visit(rootElement, 0);
  return buf.toString();
}

Future<void> _pumpStoryEvidence(
  WidgetTester tester, {
  required String variant,
  required GlobalKey repaintKey,
  required double textScale,
  required bool disableAnimations,
}) async {
  tester.view.devicePixelRatio = 2.0;
  tester.view.physicalSize = const Size(720, 1600);
  addTearDown(() {
    tester.view.resetDevicePixelRatio();
    tester.view.resetPhysicalSize();
  });
  SharedPreferences.setMockInitialValues({});
  final manager = ThemeManager();
  if (!manager.initialized) await manager.initialize();
  await manager.setPixelPreviewProfile(PixelPreviewProfile.paperDay);

  final semantics = tester.ensureSemantics();
  await tester.pumpWidget(
    RepaintBoundary(
      key: repaintKey,
      child: MaterialApp(
        theme: AppThemes.lightTheme,
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context).copyWith(
            textScaler: TextScaler.linear(textScale),
            disableAnimations: disableAnimations,
          ),
          child: child ?? const SizedBox.shrink(),
        ),
        home: const PixelStateStoryPage(),
      ),
    ),
  );
  await tester.pumpAndSettle();

  // 真实渲染断言（无论是否落盘都执行）。
  for (final s in PixelRunState.values) {
    expect(
      find.bySemanticsLabel(PixelStateSpec.forState(s).label),
      findsWidgets,
      reason: '[$variant] ${s.name} 语义缺失',
    );
  }
  expect(find.byType(PixelPrimaryAction), findsWidgets);
  expect(
    tester.takeException(),
    isNull,
    reason: '[$variant] 不得产生布局异常',
  );

  final dir = io.Platform.environment['PIXEL_A11Y_EVIDENCE_DIR'];
  if (dir != null && dir.isNotEmpty) {
    await tester.pump();
    final rootElement = tester.binding.rootElement;
    await tester.runAsync(() async {
      final outDir = io.Directory(dir);
      if (!outDir.existsSync()) outDir.createSync(recursive: true);
      final boundary = tester.renderObject<RenderRepaintBoundary>(
        find.byKey(repaintKey),
      );
      final image = await boundary.toImage(pixelRatio: 2.0);
      final bytes = await image.toByteData(format: ImageByteFormat.png);
      io.File('$dir/pixel_story_$variant.png')
          .writeAsBytesSync(bytes!.buffer.asUint8List());
      io.File('$dir/pixel_story_${variant}_semantics.txt')
          .writeAsStringSync(
        rootElement == null
            ? '(无元素根)'
            : _dumpSemanticsFromElements(rootElement),
      );
    });
  }
  semantics.dispose();
}

void main() {
  testWidgets('[evidence:200pct_reduceMotion] 200% 文本+减弱动效故事页',
      (tester) async {
    await _pumpStoryEvidence(
      tester,
      variant: '200pct_reduceMotion',
      repaintKey: GlobalKey(),
      textScale: 2.0,
      disableAnimations: true,
    );
  });

  testWidgets('[evidence:100pct_baseline] 100% 基线故事页（对照）',
      (tester) async {
    await _pumpStoryEvidence(
      tester,
      variant: '100pct_baseline',
      repaintKey: GlobalKey(),
      textScale: 1.0,
      disableAnimations: false,
    );
  });
}
