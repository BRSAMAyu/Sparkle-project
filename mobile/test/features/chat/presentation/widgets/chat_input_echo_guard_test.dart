import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import '../../../../shared/i18n_test_helper.dart';

/// N-6（web-round2）红绿测试：聊天输入框发送后必须清空，且 web 端 DOM
/// 回灌（旧文本在 clear() 之后被异步写回）不得导致下一条消息拼接
/// （round-2 实测「…介绍你自己我下周要考…」46/400）。
///
/// 修复：_handleSend 清空后启动 200ms 回声防护 —— 若控制器在窗口内又变回
/// 「刚发送的文本」，再次清空。
///
/// 红（修复前）：发送清空后模拟 web 回灌（controller 又变回已发送文本），
/// 文本滞留 → 第二条输入必然拼接。
/// 绿（修复后）：回灌文本在防护窗口内被清除。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);

  tearDown(tearDownI18n);

  Future<TextEditingController> pumpChatInput(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: ChatInput(
              onSend: (_, {replyToId}) {},
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    return tester
        .widget<TextField>(find.byType(TextField).first)
        .controller!;
  }

  testWidgets('发送清空后 web 回灌旧文本 → 回声防护窗口内被清除', (tester) async {
    final controller = await pumpChatInput(tester);

    // 用户输入第一条消息并点发送。
    await tester.enterText(find.byType(TextField).first, '你好，请用一句话介绍你自己');
    await tester.pump();

    final sendButton = find.bySemanticsLabel('Send message').first;
    expect(sendButton, findsOneWidget);
    // 只推进一帧：回声防护窗口（200ms）必须在注入回灌文本时仍然未到期。
    await tester.tap(sendButton, warnIfMissed: false);
    await tester.pump();

    // 发送即清空（widget 原有语义）。
    expect(controller.text, isEmpty);

    // 模拟 web flt-text-editing-host 异步 DOM 回灌：旧文本被写回控制器
    // （真实时序：clear() 之后数十毫秒内到达）。
    controller.text = '你好，请用一句话介绍你自己';
    await tester.pump();

    // 修复前：回灌文本永久滞留（下一条输入被拼接）。
    // 修复后：200ms 回声防护窗口内被再次清空。
    await tester.pump(const Duration(milliseconds: 300));

    expect(
      controller.text,
      isEmpty,
      reason: '回灌的已发送文本必须在防护窗口内被清除，否则下一条消息会被拼接',
    );
  });

  testWidgets('回声窗口内用户新输入的不同内容不受防护影响', (tester) async {
    final controller = await pumpChatInput(tester);

    await tester.enterText(find.byType(TextField).first, '第一条');
    await tester.pump();
    await tester.tap(find.bySemanticsLabel('Send message').first, warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(controller.text, isEmpty);

    // 用户立即开始输入第二条（与已发送文本不同）。
    controller.text = '第二条：';
    await tester.pump(const Duration(milliseconds: 300));

    expect(controller.text, '第二条：');
  });
}
