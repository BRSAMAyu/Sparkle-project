// V4-F02 · 故事页证据采集：顶页截图（PNG）+ 语义树 dump。
//
// 常规跑 `flutter test`：本文件仍执行真实渲染断言（页面可构建、
// 全组件就位），不写文件——保证套件全绿且无副作用。
// 设 `PIXEL_STORY_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   pixel_story_<profile>.png（整页 RepaintBoundary 截图，dpr=2）
//   pixel_story_<profile>_semantics.txt（语义树 dump）
// 证据落盘路径见 v4/evidence/V4-F02/run_manifest.json。
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel.dart';

const List<PixelPreviewProfile> _evidenceProfiles = [
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

String _dumpSemantics(SemanticsNode node, int depth) {
  final data = node.getSemanticsData();
  final buf = StringBuffer(
    '${'  ' * depth}- label="${node.label}" '
    'isButton=${data.flagsCollection.isButton} '
    'rect=${node.rect}\n',
  );
  node.visitChildren((child) {
    buf.write(_dumpSemantics(child, depth + 1));
    return true;
  });
  return buf.toString();
}

void main() {
  for (final profile in _evidenceProfiles) {
    testWidgets('[evidence:$profile] 故事页真实渲染并按需落盘', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(800, 1600);
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      SharedPreferences.setMockInitialValues({});
      final manager = ThemeManager();
      if (!manager.initialized) await manager.initialize();
      await manager.setPixelPreviewProfile(profile);
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(
        MaterialApp(
          theme: AppThemes.lightTheme,
          home: const RepaintBoundary(
            key: Key('pixel-story-root'),
            child: PixelStateStoryPage(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      // 真实渲染断言（无论是否落盘都执行）。
      expect(find.byType(PixelStateStoryPage), findsOneWidget);
      expect(find.byType(PixelReceiptCard), findsOneWidget);
      expect(find.byType(PixelRunCard), findsOneWidget);
      expect(tester.takeException(), isNull);

      final dir = io.Platform.environment['PIXEL_STORY_EVIDENCE_DIR'];
      if (dir != null && dir.isNotEmpty) {
        await tester.runAsync(() async {
          final outDir = io.Directory(dir);
          if (!outDir.existsSync()) outDir.createSync(recursive: true);
          final outPath = outDir.path;
          final name = profile.name;
          final boundary = tester.renderObject<RenderRepaintBoundary>(
            find.byKey(const Key('pixel-story-root')),
          );
          final image = await boundary.toImage(pixelRatio: 2.0);
          final bytes = await image.toByteData(format: ImageByteFormat.png);
          io.File('$outPath/pixel_story_$name.png')
              .writeAsBytesSync(bytes!.buffer.asUint8List());
          // 语义树真根：rootPipelineOwner 的 SemanticsOwner 持有整棵
          // 节点树（页面 render object 自身不拥有语义节点）。
          final root = RendererBinding
              .instance.rootPipelineOwner.semanticsOwner?.rootSemanticsNode;
          io.File('$outPath/pixel_story_${name}_semantics.txt')
              .writeAsStringSync(
            root == null ? '(无语义根)' : _dumpSemantics(root, 0),
          );
        });
      }
      semantics.dispose();
    });
  }
}
