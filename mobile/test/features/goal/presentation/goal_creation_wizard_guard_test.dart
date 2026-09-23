import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/goal/data/models/goal_creation_models.dart';
import 'package:sparkle/features/goal/data/models/goal_intent_models.dart';
import 'package:sparkle/features/goal/data/repositories/goal_repository.dart';
import 'package:sparkle/features/goal/data/services/goal_intent_service.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_creation_wizard_screen.dart';

import '../../../shared/i18n_test_helper.dart';

class _DisabledGoalIntentService implements GoalIntentService {
  @override
  Future<GoalIntentAnalysis> analyze(String text) async =>
      GoalIntentAnalysis.disabled();
}

class _StubGoalRepository implements GoalRepository {
  @override
  Future<GoalDecompositionPreview> decomposePreview({
    required String goalType,
    required String title,
    required String motivation,
    required String timeHorizon,
  }) async => throw UnimplementedError();

  @override
  Future<CreatedGoal> createGoal({
    required String goalType,
    required String title,
    required String motivation,
    required String timeHorizon,
    required List<GoalMilestoneDraft> milestones,
    String? description,
  }) async => throw UnimplementedError();

  @override
  Future<void> updateGoal({
    required String goalId,
    String? title,
    String? description,
  }) async {}
}

/// N27（A-SPEC5 v1.5）脏态保护回归（goal_creation_wizard 屏）：
/// 报告点名「goal 向导退出丢掉已跑的意图分析结果」——补 guard 后
/// 有输入返回必确认；无输入返回直接放行。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> pumpWizard(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          goalRepositoryProvider.overrideWithValue(_StubGoalRepository()),
          goalIntentServiceProvider.overrideWithValue(
            _DisabledGoalIntentService(),
          ),
        ],
        child: testMaterialApp(
          home: Navigator(
            pages: [
              const MaterialPage<void>(child: Scaffold(body: Text('起点'))),
              const MaterialPage<void>(
                key: ValueKey('wizard-page'),
                child: GoalCreationWizardScreen(),
              ),
            ],
            onPopPage: (route, result) => route.didPop(result),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('无输入返回不弹确认，直接放行', (tester) async {
    await pumpWizard(tester);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.byType(GoalCreationWizardScreen), findsNothing);
    expect(find.text('起点'), findsOneWidget);
    expect(find.text('放弃更改？'), findsNothing);
  });

  testWidgets('已输入意图文本后返回必确认，「继续编辑」留下、「放弃更改」放行',
      (tester) async {
    await pumpWizard(tester);

    await tester.enterText(find.byType(TextField), '三周内通过高数');
    await tester.pump();

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.text('放弃更改？'), findsOneWidget,
        reason: '向导退出丢意图输入必须被拦截确认',);

    await tester.tap(find.text('继续编辑'));
    await tester.pumpAndSettle();
    expect(find.byType(GoalCreationWizardScreen), findsOneWidget);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    await tester.tap(find.text('放弃更改'));
    await tester.pumpAndSettle();

    expect(find.byType(GoalCreationWizardScreen), findsNothing);
    expect(find.text('起点'), findsOneWidget);
  });
}
