// V4-F05 · 证据采集：五面 × 四档（classic + paperDay/dusk/quiet）截图与
// 语义 dump（「五面状态截图附相同 build 与数据 seed」）。
//
// 常规跑 `flutter test`：仍执行真实渲染断言（页面/面可构建、真实组件就位），
// 不写文件——套件全绿无副作用。
// 设 `STYLE_PREVIEW_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   preview_page_<profile>.png（整页截图，含切换器 + 状态流，dpr=2）
//   preview_face_<face>_<profile>.png（单面截图，面 canonical 流步）
//   preview_sheet_<profile>.png（卡住 sheet 真实 bottomSheet 顶层形态）
//   *_semantics.txt（元素树口径语义 dump，F04 同口径）
//
// 同 build 同 seed：全部截图出自同一 worktree/同一 Flutter 版本/同一冻结
// seed（kStylePreviewSeedVersion）与同一组面构建器（style_preview_faces），
// 采集映射见 v4/evidence/V4-F05/run_manifest.json。
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/design/style_preview/style_preview_faces.dart';
import 'package:sparkle/core/design/style_preview/style_preview_page.dart';
import 'package:sparkle/core/design/style_preview/style_preview_seed.dart';
import 'package:sparkle/core/design/tokens_v2/pixel_preview_theme.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/features/chat/presentation/widgets/task_stuck_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';

import 'style_preview_test_harness.dart';

/// 面canonical 流步（同一状态流的确定性取点；manifest 逐面登记）。
const Map<StylePreviewFace, StylePreviewFlowStep> _faceStep =
    <StylePreviewFace, StylePreviewFlowStep>{
  StylePreviewFace.home: StylePreviewFlowStep.committed,
  StylePreviewFace.stuckSheet: StylePreviewFlowStep.versionConflict,
  StylePreviewFace.memory: StylePreviewFlowStep.memorySaved,
  StylePreviewFace.longAnswer: StylePreviewFlowStep.runActive,
  StylePreviewFace.starMap: StylePreviewFlowStep.committed,
};

const List<PixelPreviewProfile> _profiles = <PixelPreviewProfile>[
  PixelPreviewProfile.classic,
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

/// 语义树 dump（元素树口径，F04 同款；本机 widget-test 泵内
/// SemanticsOwner.rootSemanticsNode 恒 null，元素树字段覆盖等价）。
String _dumpSemanticsFromElements(Element rootElement) {
  final buf = StringBuffer();
  void visit(Element el, int depth) {
    final ro = el.renderObject;
    if (ro is RenderParagraph) {
      final text = ro.text.toPlainText();
      if (text.trim().isNotEmpty) {
        final rect = ro.localToGlobal(Offset.zero) & ro.size;
        buf.writeln('${'  ' * depth}- label="$text" isText=true rect=$rect');
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
      buf.writeln('${'  ' * depth}- label="${ro.properties.label}" '
          'value="${ro.properties.value}" '
          'isButton=$isButton rect=$rect');
      depth += 1;
    }
    el.visitChildElements((child) => visit(child, depth));
  }

  visit(rootElement, 0);
  return buf.toString();
}

Future<void> _capture(
  WidgetTester tester,
  GlobalKey boundaryKey,
  String outPath,
  String semanticsPath,
) async {
  await tester.runAsync(() async {
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(boundaryKey),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final bytes = await image.toByteData(format: ImageByteFormat.png);
    io.File(outPath).writeAsBytesSync(bytes!.buffer.asUint8List());
    final rootElement = tester.element(find.byType(MaterialApp));
    io.File(semanticsPath).writeAsStringSync(
      _dumpSemanticsFromElements(rootElement),
    );
  });
}

Widget _faceWidget(StylePreviewFace face, StylePreviewFlowStep step) {
  switch (face) {
    case StylePreviewFace.home:
      return StylePreviewHomeFace(step: step);
    case StylePreviewFace.stuckSheet:
      return const StylePreviewStuckSheetFace();
    case StylePreviewFace.memory:
      return StylePreviewMemoryFace(step: step);
    case StylePreviewFace.longAnswer:
      return StylePreviewLongAnswerFace(step: step);
    case StylePreviewFace.starMap:
      return StylePreviewStarMapFace(step: step);
  }
}

void main() {
  for (final profile in _profiles) {
    testWidgets('[evidence:$profile] 整页（切换器+状态流+五面头）真实渲染并按需落盘',
        (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(720, 1600);
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      await freshThemeManager();
      await ThemeManager().setPixelPreviewProfile(profile);
      final boundaryKey = GlobalKey();
      await tester.pumpWidget(
        buildPreviewHost(
          repaintKey: boundaryKey,
          body: const StylePreviewPage(),
        ),
      );
      await settlePreview(tester);

      // 真实渲染断言（无论是否落盘都执行）：360x800 视口下断言首屏
      // 内容（懒构建 ListView 首卡片），五面逐面由单面采集用例断言。
      expect(find.byType(StylePreviewPage), findsOneWidget);
      expect(find.byType(TodayCockpitCard), findsOneWidget);
      expect(
        find.byKey(const ValueKey('style-preview-profile-switcher')),
        findsOneWidget,
      );
      expect(mountedPixelProfile(tester),
          profile == PixelPreviewProfile.classic ? isNull : profile,);

      final dir = io.Platform.environment['STYLE_PREVIEW_EVIDENCE_DIR'];
      if (dir != null && dir.isNotEmpty) {
        await _capture(
          tester,
          boundaryKey,
          '$dir/preview_page_${profile.name}.png',
          '$dir/preview_page_${profile.name}_semantics.txt',
        );
      }
    });

    for (final face in StylePreviewFace.values) {
      final step = _faceStep[face]!;
      testWidgets('[evidence:$profile:${face.name}] 单面 canonical 流步渲染'
          '并按需落盘', (tester) async {
        tester.view.devicePixelRatio = 2.0;
        tester.view.physicalSize = const Size(720, 1600);
        addTearDown(() {
          tester.view.resetDevicePixelRatio();
          tester.view.resetPhysicalSize();
        });
        await freshThemeManager();
        await ThemeManager().setPixelPreviewProfile(profile);
        final boundaryKey = GlobalKey();
        await tester.pumpWidget(
          buildPreviewHost(
            repaintKey: boundaryKey,
            body: Scaffold(
              body: SafeArea(
                child: ListView(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  children: [
                    StylePreviewFaceCard(
                      key: ValueKey('evidence-face-${face.name}'),
                      face: face,
                      frame: StylePreviewFlowFrame.of(step),
                      child: _faceWidget(face, step),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
        await settlePreview(tester);

        // 每面真实组件断言（同源面构建器）。
        switch (face) {
          case StylePreviewFace.home:
            expect(find.byType(TodayCockpitCard), findsOneWidget);
          case StylePreviewFace.stuckSheet:
            expect(find.byType(TaskStuckCard), findsOneWidget);
          case StylePreviewFace.memory:
            expect(find.byType(MemoryEvidenceBadge), findsOneWidget);
          case StylePreviewFace.longAnswer:
            expect(find.byType(PixelSuccessBadge), findsNothing);
          case StylePreviewFace.starMap:
            expect(find.byType(GalaxyNodePreviewCard), findsOneWidget);
        }
        expect(tester.takeException(), isNull);

        final dir = io.Platform.environment['STYLE_PREVIEW_EVIDENCE_DIR'];
        if (dir != null && dir.isNotEmpty) {
          await _capture(
            tester,
            boundaryKey,
            '$dir/preview_face_${face.name}_${profile.name}.png',
            '$dir/preview_face_${face.name}_${profile.name}_semantics.txt',
          );
        }
      });
    }

    // 卡住 sheet 顶层形态（真实 showModalBottomSheet 打开后整屏）。
    testWidgets('[evidence:$profile:stuckSheetOpen] sheet 顶层真实形态落盘',
        (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(720, 1600);
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      await freshThemeManager();
      await ThemeManager().setPixelPreviewProfile(profile);
      final boundaryKey = GlobalKey();
      await tester.pumpWidget(
        buildPreviewHost(
          repaintKey: boundaryKey,
          body: const Scaffold(
            body: SafeArea(child: StylePreviewStuckSheetFace()),
          ),
        ),
      );
      await settlePreview(tester);
      await tester.tap(find.text('以真实 bottomSheet 打开'));
      await settlePreview(tester);
      expect(find.byType(TaskStuckCard), findsNWidgets(2));

      final dir = io.Platform.environment['STYLE_PREVIEW_EVIDENCE_DIR'];
      if (dir != null && dir.isNotEmpty) {
        await _capture(
          tester,
          boundaryKey,
          '$dir/preview_sheet_${profile.name}.png',
          '$dir/preview_sheet_${profile.name}_semantics.txt',
        );
      }
    });
  }
}
