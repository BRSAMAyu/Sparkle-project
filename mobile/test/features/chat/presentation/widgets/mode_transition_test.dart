import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_mode_transition_banner.dart';

void main() {
  group('ModeTransitionRecord', () {
    test('isDirectToWorkflow detects direct→workflow', () {
      final record = ModeTransitionRecord(
        fromMode: ChatModeStandard(),
        toMode: ChatModeDeepAnalysis(),
        timestamp: DateTime.now(),
      );
      expect(record.isDirectToWorkflow, true);
      expect(record.isWorkflowToDirect, false);
    });

    test('isWorkflowToDirect detects workflow→direct', () {
      final record = ModeTransitionRecord(
        fromMode: ChatModeDeepAnalysis(),
        toMode: ChatModeStandard(),
        timestamp: DateTime.now(),
      );
      expect(record.isWorkflowToDirect, true);
      expect(record.isDirectToWorkflow, false);
    });

    test('neither flag for workflow→workflow', () {
      final record = ModeTransitionRecord(
        fromMode: ChatModeDeepAnalysis(),
        toMode: ChatModeStudyPlan(),
        timestamp: DateTime.now(),
      );
      expect(record.isDirectToWorkflow, false);
      expect(record.isWorkflowToDirect, false);
    });
  });

  group('ChatModeTransitionBanner', () {
    Widget buildWidget(ModeTransitionRecord transition) => MaterialApp(
          home: Scaffold(
            body: ProviderScope(
              child: ChatModeTransitionBanner(transition: transition),
            ),
          ),
        );

    testWidgets('renders direct→workflow transition', (tester) async {
      final transition = ModeTransitionRecord(
        fromMode: ChatModeStandard(),
        toMode: ChatModeDeepAnalysis(),
        timestamp: DateTime.now(),
      );

      await tester.pumpWidget(buildWidget(transition));
      await tester.pump();

      expect(find.byType(ChatModeTransitionBanner), findsOneWidget);
      expect(find.byIcon(Icons.trending_up_rounded), findsOneWidget);

      // Exhaust the auto-dismiss timer
      await tester.pump(const Duration(seconds: 6));
      await tester.pumpAndSettle();
    });

    testWidgets('renders workflow→direct transition', (tester) async {
      final transition = ModeTransitionRecord(
        fromMode: ChatModeDeepAnalysis(),
        toMode: ChatModeStandard(),
        timestamp: DateTime.now(),
      );

      await tester.pumpWidget(buildWidget(transition));
      await tester.pump();

      expect(find.byType(ChatModeTransitionBanner), findsOneWidget);
      expect(find.byIcon(Icons.chat_bubble_outline), findsOneWidget);

      // Exhaust the auto-dismiss timer
      await tester.pump(const Duration(seconds: 6));
      await tester.pumpAndSettle();
    });

    testWidgets('renders workflow→workflow transition', (tester) async {
      final transition = ModeTransitionRecord(
        fromMode: ChatModeDeepAnalysis(),
        toMode: ChatModeStudyPlan(),
        timestamp: DateTime.now(),
      );

      await tester.pumpWidget(buildWidget(transition));
      await tester.pump();

      expect(find.byType(ChatModeTransitionBanner), findsOneWidget);

      // Exhaust the auto-dismiss timer
      await tester.pump(const Duration(seconds: 6));
      await tester.pumpAndSettle();
    });
  });
}
