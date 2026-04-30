import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/working_memory_badge.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('shows consolidated label when archived', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: WorkingMemoryBadge(consolidated: true),
        ),
      ),
    );

    expect(find.text('已归档到长期记忆'), findsOneWidget);
  });

  testWidgets('shows session label when not archived', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: WorkingMemoryBadge(consolidated: false),
        ),
      ),
    );

    expect(find.text('当前 session'), findsOneWidget);
  });
}
