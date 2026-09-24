import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';

import '../shared/i18n_test_helper.dart';

UserBrief _guestUser() => UserBrief(
      id: 'guest-user',
      username: 'guest',
      nickname: 'Guest',
    );

/// 发送失败的 AI 代写私信：失败徽标与重试入口可见，且绝不渲染
/// "已读"（done_all）等伪造成功信号（wt276 诚实性红线）。
UserBrief _failedAgentSender() => UserBrief(
      id: kCommunityAgentUserId,
      username: 'sparkle_ai',
      nickname: kCommunityAgentDisplayName,
    );

PrivateMessageInfo _failedAgentMessage() => PrivateMessageInfo(
      id: 'local-failed-1',
      sender: _failedAgentSender(),
      receiver: _guestUser(),
      messageType: MessageType.text,
      content: 'AI 起草的回复',
      contentData: {kAgentMetadataKey: true},
      isRead: false,
      hasError: true,
      createdAt: DateTime(2026, 3, 25, 10),
      updatedAt: DateTime(2026, 3, 25, 10),
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    setUpI18nForTesting();
  });

  testWidgets(
      'failed agent private message exposes failed badge with retry entry',
      (tester) async {
    var retryTaps = 0;

    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: ListView(
              children: [
                ChatBubble(
                  message: _failedAgentMessage(),
                  onRetryDelivery: () => retryTaps++,
                ),
              ],
            ),
          ),
        ),
      ),
    );

    // ChatBubble 持有循环动画控制器，禁用 pumpAndSettle（会超时）。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 失败态可见：失败徽标 + 重试入口（与群聊侧失败徽标同形制）。
    expect(find.text(S.chatDeliveryFailed), findsOneWidget);
    expect(find.text(S.chatDeliveryRetry), findsOneWidget);
    expect(find.byIcon(Icons.error_outline_rounded), findsOneWidget);

    // 绝不伪造成功：无 done_all 已读信号。
    expect(find.byIcon(Icons.done_all_rounded), findsNothing);
    expect(find.byIcon(Icons.done_rounded), findsNothing);

    await tester.tap(find.text(S.chatDeliveryRetry));
    await tester.pump();
    expect(retryTaps, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('failed agent message without retry callback keeps error icon',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: ListView(
              children: [
                ChatBubble(message: _failedAgentMessage()),
              ],
            ),
          ),
        ),
      ),
    );
    // 循环动画：同前，不使用 pumpAndSettle。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byIcon(Icons.error_outline), findsOneWidget);
    expect(find.byIcon(Icons.done_all_rounded), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('settled agent message never shows fake read receipt when unread',
      (tester) async {
    final message = PrivateMessageInfo(
      id: 'local-pending-1',
      sender: _failedAgentSender(),
      receiver: _guestUser(),
      messageType: MessageType.text,
      content: 'AI 起草的回复',
      contentData: {kAgentMetadataKey: true},
      isRead: false,
      isSending: true,
      createdAt: DateTime(2026, 3, 25, 10),
      updatedAt: DateTime(2026, 3, 25, 10),
    );

    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: ListView(
              children: [
                ChatBubble(message: message),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    // pending 态：发送中指示器，而非已读回执。
    expect(find.byIcon(Icons.done_all_rounded), findsNothing);
    expect(find.text(S.chatDeliveryFailed), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
