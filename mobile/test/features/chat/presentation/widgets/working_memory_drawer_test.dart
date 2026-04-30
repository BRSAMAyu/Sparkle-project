import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/features/chat/presentation/widgets/working_memory_drawer.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('drawer expands and renders working memory item', (tester) async {
    final payload = WorkingMemorySessionModel(
      sessionId: 'session-1',
      items: [
        WorkingMemoryItem(
          id: 'entry-1',
          summary: '准备周末补完高数真题',
          subjectType: 'commitment',
          mentionCount: 3,
          salienceScore: 0.9,
          sourceTurnIds: const ['turn-1'],
          evidenceToken: 'turn-1',
          confirmationStatus: 'none',
          consolidatedToL1Id: 'memory-1',
          rejected: false,
          lastSeenAt: DateTime(2026, 4, 21, 10, 0, 0),
        ),
      ],
    );
    String? sourceToken;

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: ChatWorkingMemoryPanel(
              sessionId: 'session-1',
              onViewSource: (token) => sourceToken = token,
              loader: (_) async => payload,
              onForgetEntry: (_, __) async {},
              onMarkCorrectEntry: (_, __) async => payload.items.first,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('AI 当前记住'), findsOneWidget);
    await tester.tap(find.text('AI 当前记住'));
    await tester.pumpAndSettle();

    expect(find.text('准备周末补完高数真题'), findsOneWidget);
    expect(find.text('已归档到长期记忆'), findsOneWidget);

    await tester.tap(find.text('原 turn'));
    await tester.pump();
    expect(sourceToken, 'turn-1');
  });

  testWidgets('drawer stays hidden without session id', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: ChatWorkingMemoryPanel(
              sessionId: null,
              onViewSource: _noopViewSource,
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();
    expect(find.text('AI 当前记住'), findsNothing);
  });

  testWidgets('drawer renders empty state when no items', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: ChatWorkingMemoryPanel(
              sessionId: 'session-empty',
              onViewSource: _noopViewSource,
              loader: (_) async => WorkingMemorySessionModel(
                sessionId: 'session-empty',
                items: const [],
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('AI 当前记住'));
    await tester.pumpAndSettle();
    expect(find.text('当前 session 里还没有可见的工作记忆。'), findsOneWidget);
  });

  testWidgets('drawer calls forget action', (tester) async {
    var forgetCount = 0;
    final payload = WorkingMemorySessionModel(
      sessionId: 'session-1',
      items: [
        WorkingMemoryItem(
          id: 'entry-1',
          summary: '准备周末补完高数真题',
          subjectType: 'commitment',
          mentionCount: 3,
          salienceScore: 0.9,
          sourceTurnIds: const ['turn-1'],
          evidenceToken: 'turn-1',
          confirmationStatus: 'none',
          consolidatedToL1Id: null,
          rejected: false,
          lastSeenAt: DateTime(2026, 4, 21, 10, 0, 0),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: ChatWorkingMemoryPanel(
              sessionId: 'session-1',
              onViewSource: _noopViewSource,
              loader: (_) async => payload,
              onForgetEntry: (_, __) async => forgetCount += 1,
              onMarkCorrectEntry: (_, __) async => payload.items.first,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('AI 当前记住'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('手动忘记'));
    await tester.pumpAndSettle();

    expect(forgetCount, 1);
  });
}

void _noopViewSource(String _) {}
