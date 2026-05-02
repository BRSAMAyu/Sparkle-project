import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('runtime follow-up renders as a natural continuation card',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ActionCard(
            action: _followUpPayload(),
          ),
        ),
      ),
    );

    expect(find.text('继续上次聊的：TCP 拥塞控制'), findsOneWidget);
    expect(find.textContaining('继续接上次那条线'), findsOneWidget);
    expect(find.text('Day 4 晚：检查传输层'), findsOneWidget);
    expect(find.text('Day 5 · TCP 补强'), findsOneWidget);
    expect(find.text('wake-1'), findsNothing);
  });

  testWidgets('runtime follow-up cta sends continuation action',
      (tester) async {
    String? actionType;
    Map<String, dynamic>? actionPayload;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ActionCard(
            action: _followUpPayload(),
            onWidgetAction: (type, payload) async {
              actionType = type;
              actionPayload = payload;
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('接着聊'));
    await tester.pump();

    expect(actionType, 'checkpoint_follow_up_continue');
    expect(actionPayload?['wake_id'], 'wake-1');
    expect(actionPayload?['conversation_id'], 'cp:plan:4');
    expect(actionPayload?['prompt'], contains('继续接上次那条线'));
  });
}

WidgetPayload _followUpPayload() => WidgetPayload(
      type: 'aurora_runtime_follow_up',
      data: {
        'wake_id': 'wake-1',
        'conversation_id': 'cp:plan:4',
        'message': '继续接上次那条线：你说「TCP 拥塞控制」还没完全闭合。',
        'render_action': {
          'type': 'checkpoint_follow_up',
          'style': 'conversation_continuation',
          'title': '继续上次聊的：TCP 拥塞控制',
          'summary': '继续接上次那条线：你说「TCP 拥塞控制」还没完全闭合。',
          'checkpoint_description': 'Day 4 晚：检查传输层',
          'blocker_summary': 'TCP 拥塞控制',
          'next_task_title': 'Day 5 · TCP 补强',
          'cta_label': '接着聊',
          'wake_id': 'wake-1',
          'conversation_id': 'cp:plan:4',
        },
      },
    );
