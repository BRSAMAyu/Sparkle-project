// V4-F04 · Shell 证据采集：顶页截图（PNG）+ 语义树 dump。
//
// 常规跑 `flutter test`：本文件仍执行真实渲染断言（三尺寸壳可构建、
// 五目的地就位、错误探针在视口内），不写文件——保证套件全绿且无副作用。
// 设 `SHELL_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   shell_<variant>.png（整壳 RepaintBoundary 截图，dpr=2）
//   shell_<variant>_semantics.txt（语义树 dump）
// 证据落盘路径见 v4/evidence/V4-F04/run_manifest.json。
//
// 断言面即验收面：360宽/800×600/1280×720 三档壳 + 像素 preview 档装饰沿
// （classic 零差量的对照面）。
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/tokens_v2/pixel_preview_theme.dart';
import 'package:sparkle/core/navigation/shell_navigation.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

import 'shell_test_harness.dart';

class _ThrowingApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('no network in shell evidence test');
}

class _RecordingVisualElementNotifier extends VisualElementNotifier {
  _RecordingVisualElementNotifier() : super(_ThrowingApiClient());

  @override
  Future<void> refresh() async {}
}

/// 语义树 dump（元素树口径）：遍历 [RenderSemanticsAnnotations]（Text 派生
/// 语义与显式 Semantics 注解均落此），逐节点记 label/value/isButton/rect。
/// （本机 Flutter 3.41.3 下 `semanticsOwner.rootSemanticsNode` 在 widget
/// test 泵内恒为 null——SemanticsNode 真根不可达；F02 的同口径 dump 在
/// 本机复跑亦得空根，故 F04 改元素树口径取证，字段覆盖等价。）
String _dumpSemanticsFromElements(Element rootElement) {
  final buf = StringBuffer();
  void visit(Element el, int depth) {
    final ro = el.renderObject;
    // Text 派生语义落在 RenderParagraph（文本即标签）。
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

Future<void> _pumpShellEvidence(
  WidgetTester tester, {
  required Size logicalSize,
  required String variant,
  required GlobalKey repaintKey,
  bool pixelPreview = false,
}) async {
  tester.view.devicePixelRatio = 2.0;
  tester.view.physicalSize = logicalSize * 2.0;
  addTearDown(() {
    tester.view.resetDevicePixelRatio();
    tester.view.resetPhysicalSize();
  });
  setUpI18nForTesting();
  // runAsync 真实异步窗内 shell 副作用（ThemeManager 持久化等）会触达
  // shared_preferences 通道——mock 掉防 MissingPluginException。
  SharedPreferences.setMockInitialValues({});

  final semantics = tester.ensureSemantics();
  final router = GoRouter(
    initialLocation: '/home',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) => RepaintBoundary(
          key: repaintKey,
          child: MainNavigationShell(navigationShell: navigationShell),
        ),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/home',
                builder: (context, state) => const ShellHomePlaceholder(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/galaxy',
                builder: (context, state) => const ShellGalaxyPlaceholder(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/chat',
                builder: (context, state) => const ShellChatPlaceholder(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/community',
                builder: (context, state) =>
                    const ShellCommunityPlaceholder(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                builder: (context, state) => const ShellProfilePlaceholder(),
              ),
            ],
          ),
        ],
      ),
    ],
  );

  final container = ProviderContainer(
    overrides: [
      apiClientProvider.overrideWithValue(_ThrowingApiClient()),
      visualElementProvider.overrideWith((ref) => _RecordingVisualElementNotifier()),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: testMaterialApp(
        routerConfig: router,
        theme: pixelPreview
            ? ThemeData(
                colorScheme: ColorScheme.fromSeed(
                  seedColor: const Color(0xFF3E6652),
                ),
                extensions: [
                  PixelProfileTheme.forProfile(PixelPreviewProfile.paperDay),
                ],
              )
            : null,
      ),
    ),
  );
  await tester.pump(const Duration(milliseconds: 1300));
  await tester.pumpAndSettle();

  // 真实渲染断言（无论是否落盘都执行）。
  expect(find.text('ERROR_PROBE'), findsOneWidget);
  expect(tester.takeException(), isNull);

  final dir = io.Platform.environment['SHELL_EVIDENCE_DIR'];
  if (dir != null && dir.isNotEmpty) {
    // 语义树先于 runAsync 读取（test 事件循环内语义已构建完毕）。
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
      io.File('${outDir.path}/shell_$variant.png')
          .writeAsBytesSync(bytes!.buffer.asUint8List());
      // 语义树 dump（元素树口径，见 _dumpSemanticsFromElements 注）。
      io.File('${outDir.path}/shell_${variant}_semantics.txt')
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
  testWidgets('[evidence:classic_360x800] 手机档壳真实渲染并按需落盘',
      (tester) async {
    await _pumpShellEvidence(
      tester,
      logicalSize: const Size(360, 800),
      variant: 'classic_360x800',
      repaintKey: GlobalKey(),
    );
  });

  testWidgets('[evidence:classic_800x600] 窄短边小窗档壳真实渲染并按需落盘',
      (tester) async {
    await _pumpShellEvidence(
      tester,
      logicalSize: const Size(800, 600),
      variant: 'classic_800x600',
      repaintKey: GlobalKey(),
    );
  });

  testWidgets('[evidence:classic_1280x720] 桌面窗口档壳真实渲染并按需落盘',
      (tester) async {
    await _pumpShellEvidence(
      tester,
      logicalSize: const Size(1280, 720),
      variant: 'classic_1280x720',
      repaintKey: GlobalKey(),
    );
  });

  testWidgets('[evidence:pixel_paperDay_360x800] 像素 preview 档壳真实渲染并按需落盘',
      (tester) async {
    await _pumpShellEvidence(
      tester,
      logicalSize: const Size(360, 800),
      variant: 'pixel_paperDay_360x800',
      repaintKey: GlobalKey(),
      pixelPreview: true,
    );
  });
}
