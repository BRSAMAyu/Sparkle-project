import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/user_state_models.dart';
import 'package:sparkle/features/user/presentation/widgets/working_memory_card.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('WorkingMemoryCard renders top working-memory items', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: WorkingMemoryCard(
            snapshot: UserStateFieldEnvelope(
              value: Stage35WorkingMemorySnapshot(
                activeSessionId: 'session-1',
                items: [
                  Stage35WorkingMemoryItem(
                    summary: '先把英语阅读第 3 段的逻辑链补完。',
                    subjectType: 'study_focus',
                    mentionCount: 3,
                    consolidated: false,
                    lastSeenAt: DateTime(2026, 4, 22, 9, 30),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    expect(find.text('工作记忆快照'), findsOneWidget);
    expect(find.text('先把英语阅读第 3 段的逻辑链补完。'), findsOneWidget);
    expect(find.textContaining('提及 3 次'), findsOneWidget);
  });
}
