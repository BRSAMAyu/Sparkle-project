import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/assistant_message_metadata_tray.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  Widget buildTestWidget({
    required List<WidgetPayload> actions,
    required bool isLatestMessage,
  }) => testMaterialApp(home: Scaffold(
        body: AssistantMessageMetadataTray(
          actions: actions,
          isLatestMessage: isLatestMessage,
          status: 'IDLE',
        ),
      ),);

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

    // When not latest, next_actions badge should not appear
    expect(find.byIcon(Icons.bookmark_added_rounded), findsNothing);

    await tester.pumpWidget(
      buildTestWidget(actions: actions, isLatestMessage: true),
    );

    // When latest, next_actions badge appears (icon only when collapsed)
    expect(find.byIcon(Icons.bookmark_added_rounded), findsOneWidget);
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

    // Initially collapsed - evidence summary content not visible
    expect(find.text('这里是展开后的来源摘要'), findsNothing);
    expect(find.text('结论来自最近一轮检索'), findsNothing);

    // Source summary badge shows icon (iconOnlyWhenCollapsed=true)
    expect(find.byIcon(Icons.library_books_outlined), findsOneWidget);

    // Tap the badge to expand
    await tester.tap(find.byIcon(Icons.library_books_outlined));
    await tester.pumpAndSettle();

    // Now the headline and citations are visible
    expect(find.text('结论来自最近一轮检索'), findsOneWidget);
    expect(find.text('来源 A'), findsOneWidget);
  });
}
