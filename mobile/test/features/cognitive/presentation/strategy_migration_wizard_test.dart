import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/cognitive/data/models/strategy_migration_models.dart';
import 'package:sparkle/features/cognitive/data/repositories/strategy_migration_repository.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/strategy_migration_wizard.dart';

import '../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('strategy migration wizard renders evidence and migrates', (
    tester,
  ) async {
    final repository = _FakeStrategyMigrationRepository();
    StrategyMigrationResult? migrated;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          strategyMigrationRepositoryProvider.overrideWithValue(repository),
        ],
        child: testMaterialApp(
          home: Scaffold(
            body: StrategyMigrationWizard(
              goalId: 'goal-1',
              belief: const StrategyBeliefView(
                strategyId: 'recover_execution_rhythm',
                title: 'Recover execution rhythm',
                confidence: 0.25,
                counterEvidence: [
                  StrategyEvidenceModel(
                    reason: '连续三次任务仍然超时',
                    weight: 1,
                    source: 'task_history',
                  ),
                ],
              ),
              onMigrated: (result) => migrated = result,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('策略需要迁移'), findsOneWidget);
    expect(find.text('连续三次任务仍然超时'), findsOneWidget);

    await tester.tap(find.text('查看替代策略'));
    await tester.pumpAndSettle();
    expect(find.text('Repair the blocking gap'), findsOneWidget);
    await tester.tap(find.text('Repair the blocking gap'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('继续'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('确认迁移'));
    await tester.pumpAndSettle();

    expect(repository.migratedTo, 'repair_knowledge_bottleneck');
    expect(migrated?.newStrategyId, 'repair_knowledge_bottleneck');
    expect(find.textContaining('已切换到'), findsOneWidget);
  });
}

class _FakeStrategyMigrationRepository implements StrategyMigrationRepository {
  String? migratedTo;

  @override
  Future<StrategySuggestionBundle> fetchAlternatives({
    required String goalId,
  }) async =>
      const StrategySuggestionBundle(
        goalId: 'goal-1',
        currentStrategyId: 'recover_execution_rhythm',
        currentStrategyTitle: 'Recover execution rhythm',
        confidence: 0.25,
        counterEvidence: [
          StrategyEvidenceModel(
            reason: '连续三次任务仍然超时',
            weight: 1,
            source: 'task_history',
          ),
        ],
        alternatives: [
          AlternativeStrategyModel(
            strategyId: 'repair_knowledge_bottleneck',
            title: 'Repair the blocking gap',
            description: 'Practice the weak prerequisite first.',
            confidence: 0.82,
            estimatedLift: 0.5,
            why: 'This goal needs prerequisite repair.',
          ),
          AlternativeStrategyModel(
            strategyId: 'task_granularity_fit',
            title: 'Resize the task',
            description: 'Split work into smaller pieces.',
            confidence: 0.76,
            estimatedLift: 0.4,
            why: 'This reduces daily overload.',
          ),
        ],
      );

  @override
  Future<StrategyMigrationResult> migrateStrategy({
    required String goalId,
    required String newStrategyId,
  }) async {
    migratedTo = newStrategyId;
    return StrategyMigrationResult(
      goalId: goalId,
      previousStrategyId: 'recover_execution_rhythm',
      newStrategyId: newStrategyId,
      newStrategyTitle: 'Repair the blocking gap',
      migratedAt: '2026-05-02T00:00:00Z',
    );
  }
}
