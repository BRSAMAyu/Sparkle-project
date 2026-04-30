import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('ActionCard handles task_list correctly', (WidgetTester tester) async {
    // 1. Arrange: Create a task_list payload
    final taskListPayload = WidgetPayload(
      type: 'task_list',
      data: {
        'tasks': [
          {
            'id': '1',
            'title': 'Task 1',
            'status': 'PENDING',
            'estimated_minutes': 30,
          },
          {
            'id': '2',
            'title': 'Task 2',
            'status': 'COMPLETED',
            'estimated_minutes': 15,
          },
        ],
        'task_count': 2,
        'tool_result_id': 'mock_tool_id',
      },
    );

    // 2. Act: Pump the ActionCard with Sparkle theme extension
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.light().copyWith(
          extensions: [SparkleThemeExtension.light()],
        ),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(
          body: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: ActionCard(
                action: taskListPayload,
                onConfirm: () {},
              ),
            ),
          ),
        ),
      ),
    );
    // Use pump instead of pumpAndSettle — card has repeating shimmer animation
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    // 3. Assert: task_list starts collapsed — title visible, preview shown
    expect(find.text('任务列表'), findsWidgets);

    // 4. Expand the card by tapping the expand button
    final expandButton = find.text('展开');
    expect(expandButton, findsOneWidget);
    await tester.tap(expandButton);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    // 5. After expanding, task titles should be visible
    expect(find.text('Task 1'), findsOneWidget, reason: 'Task 1 title should be visible');
    expect(find.text('Task 2'), findsOneWidget, reason: 'Task 2 title should be visible');
  });
}
