import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/goal/data/models/goal_creation_models.dart';
import 'package:sparkle/features/goal/data/models/goal_intent_models.dart';
import 'package:sparkle/features/goal/data/repositories/goal_repository.dart';
import 'package:sparkle/features/goal/data/services/goal_intent_service.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_creation_wizard_screen.dart';

import '../../../shared/i18n_test_helper.dart';

/// 意图分析桩：始终返回 kill-switch-off（mode=disabled），模拟 FME 端点
/// 关闭/不可达时文档化的回退路径——wizard 落回传统 5 步流程。
class _DisabledGoalIntentService implements GoalIntentService {
  @override
  Future<GoalIntentAnalysis> analyze(String text) async =>
      GoalIntentAnalysis.disabled();
}

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('goal creation wizard previews milestones and creates a goal', (
    tester,
  ) async {
    final repository = _FakeGoalRepository();
    CreatedGoal? created;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          goalRepositoryProvider.overrideWithValue(repository),
          goalIntentServiceProvider.overrideWithValue(
            _DisabledGoalIntentService(),
          ),
        ],
        child: testMaterialApp(
          home: GoalCreationWizardScreen(onCreated: (goal) => created = goal),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Phase-1 Entry Wire：第 0 步是自然语言意图输入。提交意图文本后，
    // 意图服务返回 disabled，wizard 回退到传统类型选择器（「学术」等）。
    await tester.enterText(find.byType(TextField), '通过高数考试');
    await tester.tap(find.widgetWithText(FilledButton, '让我先看看你的情况'));
    await tester.pumpAndSettle();

    expect(find.text('学术'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();
    expect(find.text('目标标题'), findsOneWidget);
    await tester.enterText(find.byType(TextField).at(0), '通过高数考试');
    await tester.pump();
    await tester.enterText(find.byType(TextField).at(1), '奖学金需要这门成绩');
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();
    expect(find.text('短期 7-30 天'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();

    expect(repository.previewCalls, 1);
    expect(find.text('Map the baseline'), findsOneWidget);

    await tester.tap(find.text('继续'));
    await tester.pumpAndSettle();
    expect(find.text('里程碑'), findsOneWidget);

    await tester.tap(find.text('创建'));
    await tester.pump(const Duration(milliseconds: 250));

    expect(repository.createCalls, 1);
    expect(created?.id, 'goal-1');
  });
}

class _FakeGoalRepository implements GoalRepository {
  int previewCalls = 0;
  int createCalls = 0;

  @override
  Future<GoalDecompositionPreview> decomposePreview({
    required String goalType,
    required String title,
    required String motivation,
    required String timeHorizon,
  }) async {
    previewCalls++;
    return const GoalDecompositionPreview(
      goalType: 'academic',
      timeHorizon: 'short',
      suggestedTargetDate: '2026-05-23',
      rationale: 'Visible checkpoints keep the goal editable.',
      milestones: [
        GoalMilestoneDraft(
          id: 'm1',
          title: 'Map the baseline',
          description: 'Confirm weak topics.',
          estimatedDays: 7,
          acceptanceCriteria: ['Baseline exists'],
        ),
        GoalMilestoneDraft(
          id: 'm2',
          title: 'Timed practice loop',
          description: 'Run drills.',
          estimatedDays: 14,
          acceptanceCriteria: ['Two drills complete'],
        ),
      ],
    );
  }

  @override
  Future<CreatedGoal> createGoal({
    required String goalType,
    required String title,
    required String motivation,
    required String timeHorizon,
    required List<GoalMilestoneDraft> milestones,
    String? description,
  }) async {
    createCalls++;
    expect(title, '通过高数考试');
    expect(milestones, isNotEmpty);
    return const CreatedGoal(
      id: 'goal-1',
      title: '通过高数考试',
      goalType: 'academic',
      status: 'active',
    );
  }

  @override
  Future<void> updateGoal({
    required String goalId,
    String? title,
    String? description,
  }) async {}
}
