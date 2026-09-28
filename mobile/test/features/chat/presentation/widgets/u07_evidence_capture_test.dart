// V4-U07 · 快慢反馈与引用诚实 证据采集：顶页截图（PNG）+ 语义树 dump。
//
// 常规跑 `flutter test`：本文件仍执行真实渲染断言（组件就位、语义在场），
// 不写文件——保证套件全绿且无副作用。
// 设 `U07_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   u07_lane_marker.png / u07_lane_marker_semantics.txt
//     —— 助手气泡尾部「即时回复」诚实标记（I09 快路轮呈现语义）
//   u07_citation_unresolved.png / u07_citation_unresolved_semantics.txt
//     —— 未知引用定位 sheet：摘录在场、「前往文档」禁用（不造超链接）
// 证据落盘路径见 v4/evidence/V4-U07/run_manifest.json。
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/assistant_citation_strip.dart';
import 'package:sparkle/features/chat/presentation/widgets/assistant_lane_marker.dart';

import '../../../../shared/i18n_test_helper.dart';

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

Future<void> _dumpEvidence(
  WidgetTester tester, {
  required String dir,
  required Key boundaryKey,
  required String fileStem,
}) async {
  // 语义树在帧边界后即在场（fake-async 区同步取串）；文件 IO 走 runAsync。
  // tester.binding.pipelineOwner 在本 Flutter 版本标 deprecated（建议改道
  // SemanticsBinding），但 rootPipelineOwner 路径实测取不到 root 节点，
  // 故沿用 F02 pixel_story_evidence 同款取径并显式忽略弃用提示。
  // ignore: deprecated_member_use
  final owner = tester.binding.pipelineOwner.semanticsOwner;
  final root = owner?.rootSemanticsNode;
  final semanticsText = root == null ? null : _dumpSemantics(root, 0);
  await tester.runAsync(() async {
    final outDir = io.Directory(dir);
    if (!outDir.existsSync()) outDir.createSync(recursive: true);
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(boundaryKey),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final bytes = await image.toByteData(format: ImageByteFormat.png);
    io.File('$dir/$fileStem.png')
        .writeAsBytesSync(bytes!.buffer.asUint8List());
    if (semanticsText != null) {
      io.File('$dir/${fileStem}_semantics.txt')
          .writeAsStringSync(semanticsText);
    }
  });
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await SensoryFeedbackService.setSoundEnabled(false);
    await SensoryFeedbackService.setHapticEnabled(false);
  });

  testWidgets('[evidence] 快路「即时回复」标记真实渲染并按需落盘', (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(800, 1200);
    final semantics = tester.ensureSemantics();
    addTearDown(() {
      tester.view.resetDevicePixelRatio();
      tester.view.resetPhysicalSize();
    });

    await tester.pumpWidget(
      testMaterialApp(
        home: RepaintBoundary(
          key: const Key('u07-lane-root'),
          child: Scaffold(
            backgroundColor: DS.surfacePrimary,
            body: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 助手气泡形制（chat_bubble 同款容器语义）：
                    // 快路模板应答 + 尾部诚实标记。
                    Container(
                      constraints: const BoxConstraints(maxWidth: 288),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        color: DS.chatBubbleOther,
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(20),
                          topRight: Radius.circular(20),
                          bottomRight: Radius.circular(20),
                          bottomLeft: Radius.circular(4),
                        ),
                        border: Border.all(color: DS.borderSubtle),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SparkleMarkdown(
                            content: '你好！我是 Sparkle，很高兴见到你。'
                                '可以随时告诉我你现在想推进什么。',
                            textColor: DS.chatBubbleOtherText,
                            codeBackgroundColor: DS.surfaceTertiary,
                            linkColor: DS.brandPrimary,
                            contentRole: SparkleMarkdownRole.chatBubble,
                          ),
                          const AssistantLaneMarker(kind: 'greeting'),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 真实渲染断言（无论是否落盘都执行）。
    expect(find.text('即时回复 · 问候'), findsOneWidget);
    expect(find.byType(AssistantLaneMarker), findsOneWidget);
    expect(tester.takeException(), isNull);

    final dir = io.Platform.environment['U07_EVIDENCE_DIR'];
    if (dir != null && dir.isNotEmpty) {
      await _dumpEvidence(
        tester,
        dir: dir,
        boundaryKey: const Key('u07-lane-root'),
        fileStem: 'u07_lane_marker',
      );
    }
    semantics.dispose();
  });

  testWidgets('[evidence] 未知引用定位 sheet 禁用「前往文档」并按需落盘', (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(800, 1200);
    final semantics = tester.ensureSemantics();
    addTearDown(() {
      tester.view.resetDevicePixelRatio();
      tester.view.resetPhysicalSize();
    });

    final message = ChatMessageModel(
      conversationId: 'c-1',
      role: MessageRole.assistant,
      content: '回答正文',
      rawMetadata: const {
        'citations': [
          {
            'id': 'cite-9',
            'title': '未定位来源',
            'excerpt': '模型给出了参考，但上游未提供可解析的来源定位目标。',
          },
        ],
      },
    );
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (_, __) => Scaffold(
            body: AssistantCitationStrip(message: message),
          ),
        ),
        GoRoute(
          path: '/tasks/:id',
          builder: (_, state) =>
              Scaffold(body: Text('TASK-DETAIL:${state.pathParameters['id']}')),
        ),
      ],
    );
    await tester.pumpWidget(
      RepaintBoundary(
        key: const Key('u07-citation-root'),
        child: testMaterialApp(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    // 真实操作：点引用 chip 打开定位 sheet。
    await tester.tap(find.text('未定位来源'));
    await tester.pumpAndSettle();

    expect(find.text('模型给出了参考，但上游未提供可解析的来源定位目标。'), findsOneWidget);
    final openButton = tester.widget<OutlinedButton>(
      find.ancestor(
        of: find.text('前往文档'),
        matching: find.byType(OutlinedButton),
      ),
    );
    expect(openButton.onPressed, isNull, reason: '未知引用不造超链接');
    expect(tester.takeException(), isNull);

    final dir = io.Platform.environment['U07_EVIDENCE_DIR'];
    if (dir != null && dir.isNotEmpty) {
      // sheet 挂在根 navigator 上，根 RepaintBoundary 截当前顶层画面。
      await _dumpEvidence(
        tester,
        dir: dir,
        boundaryKey: const Key('u07-citation-root'),
        fileStem: 'u07_citation_unresolved',
      );
    }
    semantics.dispose();
  });
}
