import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/assistant_message_metadata_tray.dart';

void main() {
  Widget buildTestWidget({
    required List<WidgetPayload> actions,
    required bool isLatestMessage,
  }) {
    return MaterialApp(
      home: Scaffold(
        body: AssistantMessageMetadataTray(
          actions: actions,
          isLatestMessage: isLatestMessage,
          status: 'IDLE',
        ),
      ),
    );
  }

  testWidgets('next actions only renders for latest assistant message',
      (tester) async {
    final actions = [
      WidgetPayload(
        type: 'next_actions',
        data: {
          'actions': [
            {'label': '继续拆解', 'type': 'prompt', 'prompt': '继续拆解'},
          ],
        },
      ),
    ];

    await tester.pumpWidget(
      buildTestWidget(actions: actions, isLatestMessage: false),
    );

    expect(find.text('下一步'), findsNothing);

    await tester.pumpWidget(
      buildTestWidget(actions: actions, isLatestMessage: true),
    );

    expect(find.text('下一步'), findsOneWidget);
  });

  testWidgets('source summary stays collapsed until explicitly opened',
      (tester) async {
    await tester.pumpWidget(
      buildTestWidget(
        isLatestMessage: true,
        actions: [
          WidgetPayload(
            type: 'source_summary',
            data: {
              'headline': '结论来自最近一轮检索',
              'evidence_summary': '这里是展开后的来源摘要',
              'citations': [
                {'title': '来源 A'},
              ],
            },
          ),
        ],
      ),
    );

    expect(find.text('这里是展开后的来源摘要'), findsNothing);

    await tester.tap(find.text('来源'));
    await tester.pumpAndSettle();

    expect(find.text('这里是展开后的来源摘要'), findsOneWidget);
    expect(find.text('来源 A'), findsOneWidget);
  });
}
