import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/tools/data/repositories/tool_history_repository.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_context_effect_feedback.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('context effect feedback can undo a saved tool event',
      (tester) async {
    final repository = _FakeToolHistoryRepository();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          toolHistoryRepositoryProvider.overrideWithValue(repository),
        ],
        child: testMaterialApp(
          home: Scaffold(
            body: Consumer(
              builder: (context, ref, _) => TextButton(
                onPressed: () => ToolContextEffectFeedback.show(
                  context: context,
                  ref: ref,
                  toolLabel: '计算器',
                  eventId: 7,
                ),
                child: const Text('show'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('show'));
    await tester.pump();

    expect(find.text('已让 Aurora 知道这次计算器'), findsOneWidget);
    expect(find.text('不让 Aurora 知道'), findsOneWidget);

    tester.widget<SnackBarAction>(find.byType(SnackBarAction)).onPressed();
    await tester.pumpAndSettle();

    expect(repository.forgotIds, [7]);
    expect(find.text('已撤回这次工具上下文'), findsOneWidget);
  });
}

class _FakeToolHistoryRepository implements ToolHistoryRepository {
  final List<int> forgotIds = [];

  @override
  Future<bool> forgetToolEvent(int id) async {
    forgotIds.add(id);
    return true;
  }

  @override
  Future<int?> recordBreathingCompleted({
    required String pattern,
    required int durationMinutes,
    required int roundsCompleted,
    required String surface,
    required bool completedFromBackground,
  }) =>
      throw UnimplementedError();

  @override
  Future<int?> recordCalculatorEvaluated({
    required String complexity,
    required String surface,
  }) =>
      throw UnimplementedError();

  @override
  Future<int?> recordFlashCapsuleSaved({
    required String subject,
    required String errorType,
    required String surface,
    String? taskId,
  }) =>
      throw UnimplementedError();

  @override
  Future<int?> recordNotesSynced({
    required int charCount,
    required int lineCount,
    required String surface,
    String? taskId,
  }) =>
      throw UnimplementedError();

  @override
  Future<int?> recordTranslatorCompleted({
    required String sourceLanguage,
    required String targetLanguage,
    required int textLength,
    required String surface,
  }) =>
      throw UnimplementedError();

  @override
  Future<int?> recordVocabularyLookupCompleted({
    required String lookupTerm,
    required String surface,
  }) =>
      throw UnimplementedError();
}
