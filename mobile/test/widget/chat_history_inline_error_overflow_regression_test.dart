import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_design_language_widgets.dart';

import '../shared/i18n_test_helper.dart';

/// V3-FIX-344 回归护栏：ChatHistoryInlineError 在窄约束（受约束 sheet 的
/// Expanded 错误槽，如 260px 上界）内渲染超长错误文案时不得抛 RenderFlex
/// overflow。真机小屏/分屏下此前 384px 内容 vs 260px 约束会裁切并报异常。
void main() {
  setUp(setUpI18nForTesting);

  Future<void> pumpInlineErrorInBoundedSlot(
    WidgetTester tester, {
    required String message,
  }) async {
    tester.view.physicalSize = const Size(400, 600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: Center(
            // 模拟 history sheet 中 FutureBuilder 错误槽的受约束空间。
            child: SizedBox(
              width: 360,
              height: 260,
              child: ChatHistoryInlineError(
                message: message,
                onRetry: () {},
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets(
      'ChatHistoryInlineError renders without RenderFlex overflow '
      'in a 260px bounded slot at 400x600', (tester) async {
    await pumpInlineErrorInBoundedSlot(
      tester,
      message:
          '网络连接失败：gRPC 通道连接 chat.orchestrator 超时（ETIMEDOUT），'
          '已自动重试 3 次仍未恢复，请检查网络代理设置后点击重试；'
          '若持续失败可稍后在设置中切换接入点或联系支持。',
    );

    expect(
      tester.takeException(),
      isNull,
      reason: 'ChatHistoryInlineError 在 260px 受约束槽内渲染超长文案'
          '不得抛 RenderFlex overflow（V3-FIX-344）',
    );
    // 错误语义与重试入口仍存在于树中。
    expect(find.textContaining('网络连接失败'), findsOneWidget);
    expect(find.text('重试'), findsOneWidget);
  });

  testWidgets(
      'oversized content stays reachable by scrolling in the bounded slot',
      (tester) async {
    await pumpInlineErrorInBoundedSlot(
      tester,
      message:
          '网络连接失败：gRPC 通道连接 chat.orchestrator 超时（ETIMEDOUT），'
          '已自动重试 3 次仍未恢复，请检查网络代理设置后点击重试；'
          '若持续失败可稍后在设置中切换接入点或联系支持。',
    );

    // 内容超出 260px 约束时应可滚动到重试按钮，而非被裁切丢弃。
    await tester.scrollUntilVisible(
      find.text('重试'),
      50,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('重试'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
