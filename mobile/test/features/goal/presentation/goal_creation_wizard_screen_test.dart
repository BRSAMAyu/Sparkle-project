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

/// 记录调用次数的意图分析桩（N-7 旁路测试用）。
class _RecordingDisabledIntentService implements GoalIntentService {
  int analyzeCalls = 0;

  @override
  Future<GoalIntentAnalysis> analyze(String text) async {
    analyzeCalls++;
    return GoalIntentAnalysis.disabled();
  }
}

/// 可行动（actionable）意图分析桩：模拟命中考试救援判定。
class _ActionableGoalIntentService implements GoalIntentService {
  @override
  Future<GoalIntentAnalysis> analyze(String text) async =>
      const GoalIntentAnalysis(
        mode: 'exam_rescue',
        confidence: 0.9,
        headline: '高数急救计划',
        nextBestAction: '先做一次真题摸底',
        correctionOptions: [],
        suggestedActions: [
          GoalIntentSuggestedAction(
            key: 'baseline_drill',
            label: '10 分钟摸底练习',
            estimatedMinutes: 10,
          ),
        ],
      );
}

FilledButton? _bottomContinueButton(WidgetTester tester) {
  final finder = find.widgetWithText(FilledButton, '继续');
  final matched = finder.evaluate().isEmpty
      ? null
      : tester.widget<FilledButton>(finder.first);
  return matched;
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

  group('N-7 底部继续键 UX 旁路（Entry Wire 单路径解锁）', () {
    testWidgets('空文本时底部继续键禁用', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            goalIntentServiceProvider.overrideWithValue(
              _RecordingDisabledIntentService(),
            ),
          ],
          child: testMaterialApp(
            home: const GoalCreationWizardScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(_bottomContinueButton(tester)?.onPressed, isNull,
          reason: '空意图文本时底部继续键必须保持禁用',);
    });

    testWidgets('纯空白文本时底部继续键保持禁用', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            goalIntentServiceProvider.overrideWithValue(
              _RecordingDisabledIntentService(),
            ),
          ],
          child: testMaterialApp(
            home: const GoalCreationWizardScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '   ');
      await tester.pump();

      expect(_bottomContinueButton(tester)?.onPressed, isNull,
          reason: '纯空白意图文本视同空文本，继续键保持禁用',);
    });

    testWidgets('文本非空时点亮继续键，点击走与输入卡提交同一分析路径', (tester) async {
      final intentService = _RecordingDisabledIntentService();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            goalIntentServiceProvider.overrideWithValue(intentService),
          ],
          child: testMaterialApp(
            home: const GoalCreationWizardScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '通过高数考试');
      await tester.pump();

      expect(_bottomContinueButton(tester)?.onPressed, isNotNull,
          reason: '意图文本非空时底部继续键必须点亮可点',);

      // 点击底部继续键（不点输入卡内的「让我先看看你的情况」），
      // 必须触发与卡内提交相同的意图分析路径。
      await tester.tap(find.widgetWithText(FilledButton, '继续'));
      await tester.pumpAndSettle();

      expect(intentService.analyzeCalls, 1,
          reason: '底部继续键应复用 Entry Wire 意图分析路径',);
      // 分析返回 disabled → 回退到传统类型选择器。
      expect(find.text('学术'), findsOneWidget);
    });

    testWidgets('分析进行中继续键禁用，确认卡出现后不抢确认卡的路径', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            goalIntentServiceProvider.overrideWithValue(
              _ActionableGoalIntentService(),
            ),
          ],
          child: testMaterialApp(
            home: const GoalCreationWizardScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '三周内通过高数');
      await tester.pump();
      expect(_bottomContinueButton(tester)?.onPressed, isNotNull);

      await tester.tap(find.widgetWithText(FilledButton, '继续'));
      await tester.pumpAndSettle();

      // actionable 分析 → 确认卡出现，底部继续键重新禁用（不与卡内路径抢道）。
      expect(find.text('高数急救计划'), findsOneWidget);
      expect(_bottomContinueButton(tester)?.onPressed, isNull,
          reason: '确认卡展示时底部继续键应保持禁用',);
    });
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
