import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('task stuck intervention renders chat choices', (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ActionCard(action: _taskStuckPayload()),
        ),
      ),
    );

    expect(find.textContaining('连续 3 张任务'), findsWidgets);
    expect(find.text('高数作业'), findsOneWidget);
    expect(find.text('线代习题'), findsOneWidget);
    expect(find.text('和Sparkle聊聊这个问题'), findsOneWidget);
    expect(find.text('稍后'), findsOneWidget);
    expect(find.text('不需要'), findsOneWidget);
  });

  testWidgets('task stuck later action sends snooze feedback', (tester) async {
    String? actionType;
    Map<String, dynamic>? actionPayload;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ActionCard(
            action: _taskStuckPayload(),
            onWidgetAction: (type, payload) async {
              actionType = type;
              actionPayload = payload;
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('稍后'));
    await tester.pump();

    expect(actionType, 'intervention_feedback');
    expect(actionPayload?['intervention_id'], 'intervention-1');
    expect(actionPayload?['feedback_action'], 'snoozed');
    expect(actionPayload?['snooze_hours'], 24);
  });
}

WidgetPayload _taskStuckPayload() => WidgetPayload(
      type: 'task_stuck_card',
      data: {
        'intervention_id': 'intervention-1',
        'message': '我注意到最近连续 3 张任务都卡住了。要不要聊一下？大概 2 分钟。',
        'observed_pattern': '连续 3 张任务都卡住了',
        'task_titles': ['高数作业', '线代习题', '概率论复习'],
        'micro_session': {
          'entry_reason': {
            'trigger_source': 'task_stuck_card',
            'observed_signals': ['连续 3 张任务都卡住了'],
            'suggested_agenda_preview': ['确认卡点原因', '调小下一张任务卡'],
            'why_now': '连续任务卡点会影响下一步。',
            'estimated_minutes': 2,
          },
        },
      },
    );
