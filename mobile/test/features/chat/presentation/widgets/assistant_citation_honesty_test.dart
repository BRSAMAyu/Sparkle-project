import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/assistant_citation_strip.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U07「reference点击真来源，未知引用不造超链接」的可失败钉。
///
/// 每面一正一反：
/// - 正：引用携带可解析的真来源（sparkle 深链/合法路由）→ 引用 chip 打开
///   定位 sheet、「前往文档」可点并真实导航；
/// - 反：只有外部 url / 无目标 / 伪造 sparkle 类型 → 「前往文档」禁用态，
///   不渲染可点超链接（摘录仍如实展示，不装死也不造链接）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    setUpI18nForTesting();
    // 引用 chip 点击会发感官反馈（fire-and-forget）——测试环境关声/震，
    // 不触碰音频平台通道。
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await SensoryFeedbackService.setSoundEnabled(false);
    await SensoryFeedbackService.setHapticEnabled(false);
  });

  ChatMessageModel messageWithCitation(Map<String, dynamic> citation) =>
      ChatMessageModel(
        conversationId: 'c-1',
        role: MessageRole.assistant,
        content: '回答正文',
        rawMetadata: {
          'citations': [citation],
        },
      );

  Future<GoRouter> routerWithTaskDetail(ChatMessageModel message) async {
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (_, __) =>
              Scaffold(body: AssistantCitationStrip(message: message)),
        ),
        GoRoute(
          path: '/tasks/:id',
          builder: (_, state) =>
              Scaffold(body: Text('TASK-DETAIL:${state.pathParameters['id']}')),
        ),
      ],
    );
    return router;
  }

  testWidgets('正：真来源引用可点，前往文档真实导航到深链目标', (tester) async {
    final message = messageWithCitation(const {
      'id': 'cite-1',
      'title': '线性代数讲义',
      'excerpt': '特征值的定义：Ax = λx',
      'section_title': '第 3 章 特征值',
      'document_deep_link': '/tasks/task-123',
    });
    final router = await routerWithTaskDetail(message);
    await tester.pumpWidget(testMaterialApp(routerConfig: router));
    await tester.pumpAndSettle();

    // 引用 chip 呈现真实来源标题与定位。
    expect(find.text('线性代数讲义 · 第 3 章 特征值'), findsOneWidget);
    await tester.tap(find.text('线性代数讲义 · 第 3 章 特征值'));
    await tester.pumpAndSettle();

    // sheet 内展示摘录与可点的「前往文档」。
    expect(find.text('特征值的定义：Ax = λx'), findsOneWidget);
    final openButton = tester.widget<OutlinedButton>(
      find.ancestor(
        of: find.text('前往文档'),
        matching: find.byType(OutlinedButton),
      ),
    );
    expect(openButton.onPressed, isNotNull, reason: '真来源必须可点');

    await tester.tap(find.text('前往文档'));
    await tester.pumpAndSettle();
    expect(
      find.text('TASK-DETAIL:task-123'),
      findsOneWidget,
      reason: 'reference 点击进入真来源（深链目标真实存在）',
    );
  });

  testWidgets('反：外部 url 引用不造超链接（不可解析目标禁用前往文档）', (tester) async {
    final message = messageWithCitation(const {
      'id': 'cite-2',
      'title': '外部资料',
      'excerpt': '某个只有 url 的引用',
      'url': 'https://example.com/not-a-sparkle-source',
    });
    final router = await routerWithTaskDetail(message);
    await tester.pumpWidget(testMaterialApp(routerConfig: router));
    await tester.pumpAndSettle();

    await tester.tap(find.text('外部资料'));
    await tester.pumpAndSettle();

    final openButton = tester.widget<OutlinedButton>(
      find.ancestor(
        of: find.text('前往文档'),
        matching: find.byType(OutlinedButton),
      ),
    );
    expect(openButton.onPressed, isNull, reason: '目标无法解析为站内来源时不得渲染可用链接');
    // 摘录仍如实展示（不装死：内容在，链接不在）。
    expect(find.text('某个只有 url 的引用'), findsOneWidget);
  });

  testWidgets('反：无目标与伪造 sparkle 类型引用都不造超链接', (tester) async {
    final doubleCited = ChatMessageModel(
      conversationId: 'c-1',
      role: MessageRole.assistant,
      content: '回答正文',
      rawMetadata: const {
        'citations': [
          {'id': 'cite-3', 'title': '无定位引用', 'excerpt': '没有提供任何定位目标'},
          {
            'id': 'cite-4',
            'title': '伪造类型引用',
            'excerpt': '未知资源类型',
            'deep_link': 'sparkle://not-a-real-type/xyz',
          },
        ],
      },
    );
    final router = await routerWithTaskDetail(doubleCited);
    await tester.pumpWidget(testMaterialApp(routerConfig: router));
    await tester.pumpAndSettle();

    for (final title in ['无定位引用', '伪造类型引用']) {
      await tester.tap(find.text(title));
      await tester.pumpAndSettle();
      final openButton = tester.widget<OutlinedButton>(
        find.ancestor(
          of: find.text('前往文档'),
          matching: find.byType(OutlinedButton),
        ),
      );
      expect(openButton.onPressed, isNull, reason: '$title 不得渲染可用链接');
      // 点 sheet 外屏障关闭，再验下一个引用。
      await tester.tapAt(const Offset(10, 20));
      await tester.pumpAndSettle();
    }
  });
}
