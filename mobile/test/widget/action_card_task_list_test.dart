import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

void main() {
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

    // 2. Act: Pump the ActionCard
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(
          body: Padding(
            padding: const EdgeInsets.all(16.0),
            child: ActionCard(
              action: taskListPayload,
              onConfirm: () {},
            ),
          ),
        ),
      ),
    );

    // 3. Assert: Check if it renders properly
    // It should NOT render the fallback key-value view (e.g. "tasks: [{id: 1...}]")
    // It SHOULD render specific Task List UI
    
    // Check if the title is correct
    expect(find.text('任务列表'), findsOneWidget);

    // Check if it renders the task titles
    expect(find.text('Task 1'), findsOneWidget, reason: 'Task 1 title should be visible');
    expect(find.text('Task 2'), findsOneWidget, reason: 'Task 2 title should be visible');

    // Check if confirm button is visible
    expect(find.text('确定'), findsOneWidget);
  });
}
