import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';
import 'package:sparkle/features/insights/presentation/providers/evidence_insight_provider.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/insights/presentation/screens/learning_insights_overview_screen.dart';
import 'package:sparkle/features/insights/presentation/widgets/evidence_insight_card.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/data/repositories/simulation_repository.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

import '../../../../shared/i18n_test_helper.dart';

/// D-07 证据洞察卡：fact→interpretation→uncertainty→evidence→implication
/// 五要素结构 + 证据深链 + 假精确黑话清除断言。
///
/// 「Simulator 能理解 3 条 insight」的 headless 口径：三类洞察（摩擦模式/
/// 有帮助的应对/目标进展）在真实渲染管线中各出一张卡，每张卡五要素标签
/// 与内容齐备、不确定性有诚实措辞、证据可点——结构断言，不引真模型。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  final frictionCard = EvidenceInsightCardData.fromJson(<String, dynamic>{
    'id': 'friction_pattern:execution_friction',
    'kind': 'friction_pattern',
    'fact': <String, dynamic>{
      'friction_tag': 'execution_friction',
      'exposures': 3,
      'accepted': 1,
      'edited': 0,
      'rejected': 1,
    },
    'interpretation': <String, dynamic>{
      'friction_tag': 'execution_friction',
      'role': 'most_frequent',
    },
    'uncertainty': <String, dynamic>{
      'qualifiers': <String>['counts_only_from_lifecycle_events', 'small_sample'],
      'samples': 3,
    },
    'evidence': <Map<String, dynamic>>[
      <String, dynamic>{
        'label_key': 'evidence_directive_log',
        'deep_link': '/learning/insights/directives',
        'refs': <String>['aurora_abc'],
      },
    ],
    'implication': <String, dynamic>{
      'action_key': 'review_directives',
      'deep_link': '/learning/insights/directives',
    },
  });

  final helpedCard = EvidenceInsightCardData.fromJson(<String, dynamic>{
    'id': 'interventions_that_helped:rescope:recall_gap',
    'kind': 'interventions_that_helped',
    'fact': <String, dynamic>{
      'intervention_type': 'rescope',
      'friction_tag': 'recall_gap',
      'n_exposed': 2,
      'n_accepted': 2,
      'n_observed': 2,
      'n_positive': 2,
      'n_negative': 0,
    },
    'interpretation': <String, dynamic>{
      'evidence_strength': 'repeated',
      'direction': 'positive_association',
      'causal': false,
    },
    'uncertainty': <String, dynamic>{
      'qualifiers': <String>['correlation_not_causation'],
      'samples': 2,
      'not_yet_observed': 1,
    },
    'evidence': <Map<String, dynamic>>[
      <String, dynamic>{
        'label_key': 'evidence_directive_log',
        'deep_link': '/learning/insights/directives',
        'refs': <String>['aurora_def'],
      },
    ],
    'implication': <String, dynamic>{
      'action_key': 'review_directives',
      'deep_link': '/learning/insights/directives',
    },
  });

  final goalCard = EvidenceInsightCardData.fromJson(<String, dynamic>{
    'id': 'goal_progress:abc',
    'kind': 'goal_progress',
    'fact': <String, dynamic>{
      'goal_id': 'abc',
      'title': '两周内完成线代一轮复习',
      'status': 'active',
      'ledger': <String, dynamic>{'completed': 3, 'total': 10},
      'progress_column': 0.0,
    },
    'interpretation': <String, dynamic>{'band': 'in_progress'},
    'uncertainty': <String, dynamic>{
      'qualifiers': <String>[
        'task_ledger_is_honest_progress',
        'progress_column_may_lag_ledger',
      ],
      'samples': 10,
    },
    'evidence': <Map<String, dynamic>>[
      <String, dynamic>{
        'label_key': 'evidence_goal_ledger',
        'deep_link': '/goals/abc',
        'refs': <String>['abc'],
      },
    ],
    'implication': <String, dynamic>{
      'action_key': 'open_goal',
      'deep_link': '/goals/abc',
    },
  });

  testWidgets(
    'three insight kinds each render the five evidence elements '
    '(headless simulator comprehension)',
    (WidgetTester tester) async {
      String? openedLink;
      await tester.pumpWidget(
        testMaterialApp(
          theme: AppThemes.lightTheme,
          home: Scaffold(
            body: SingleChildScrollView(
              child: Column(
                children: [
                  EvidenceInsightCardWidget(
                    card: frictionCard,
                    onOpenDeepLink: (link) => openedLink = link,
                  ),
                  EvidenceInsightCardWidget(
                    card: helpedCard,
                    onOpenDeepLink: (link) => openedLink = link,
                  ),
                  EvidenceInsightCardWidget(
                    card: goalCard,
                    onOpenDeepLink: (link) => openedLink = link,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      // 五要素标签在每张卡上齐备（3 卡 × 5 标签）。
      for (final label in const ['事实', '解读', '不确定性', '证据', '行动含义']) {
        expect(find.text(label), findsNWidgets(3), reason: '每张卡必须渲染「$label」要素');
      }

      // Simulator 可读的事实内容：真实计数/标题，而不是分数。
      expect(find.textContaining('任务执行阻力'), findsOneWidget);
      expect(find.textContaining('3 次'), findsOneWidget);
      expect(find.textContaining('观察到的 2 次记录中'), findsOneWidget);
      expect(find.textContaining('两周内完成线代一轮复习'), findsOneWidget);
      expect(find.textContaining('3 / 共 10 项'), findsOneWidget);

      // 定性解读（无分数）：最常见模式 / 重复观察方向 / 进行中。
      expect(find.text('这是最近最常出现的阻力模式'), findsOneWidget);
      expect(find.text('多次观察都呈现同样方向'), findsOneWidget);
      expect(find.text('进行中'), findsOneWidget);

      // 不确定性诚实措辞：相关非因果 + 小样本 + 账本口径。
      expect(find.text('只是相关观察，不能证明因果'), findsOneWidget);
      expect(find.text('样本较少，仅供参考'), findsOneWidget);
      expect(find.text('目标进度列可能与账本不一致，两个口径都如实呈现'), findsOneWidget);

      // 假精确黑话清除：百分比与置信度措辞不得出现。
      expect(find.textContaining('%'), findsNothing);
      expect(find.textContaining('置信度'), findsNothing);
      expect(find.textContaining('风险指数'), findsNothing);

      // 证据深链可点（第三卡在视口外，先滚动到位再点）。
      await tester.ensureVisible(find.text('查看目标与任务账本'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('查看目标与任务账本'));
      await tester.pump();
      expect(openedLink, '/goals/abc');
    },
  );

  testWidgets(
    'insights overview renders the evidence section with three cards',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            simulationProvider.overrideWith(
              (ref) => _StaticSimulationNotifier(const SimulationState()),
            ),
            systemUpdatesProvider.overrideWith(
              (ref) async => const <Map<String, dynamic>>[],
            ),
            weeklyGrowthNarrativeProvider.overrideWith(
              (ref) async => WeeklyGrowthNarrative.placeholder(),
            ),
            evidenceInsightCardsProvider.overrideWith(
              (ref) async => <EvidenceInsightCardData>[
                frictionCard,
                helpedCard,
                goalCard,
              ],
            ),
          ],
          child: testMaterialApp(
            theme: AppThemes.lightTheme,
            home: const LearningInsightsOverviewScreen(),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('证据洞察'), findsOneWidget);
      expect(find.text('阻力模式'), findsOneWidget);
      expect(find.text('有帮助的应对'), findsOneWidget);
      expect(find.text('目标进展'), findsOneWidget);
    },
  );

  testWidgets(
    'insights overview hides the evidence section when there is no data '
    '(no persona conclusions without evidence)',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            simulationProvider.overrideWith(
              (ref) => _StaticSimulationNotifier(const SimulationState()),
            ),
            systemUpdatesProvider.overrideWith(
              (ref) async => const <Map<String, dynamic>>[],
            ),
            weeklyGrowthNarrativeProvider.overrideWith(
              (ref) async => WeeklyGrowthNarrative.placeholder(),
            ),
            evidenceInsightCardsProvider
                .overrideWith((ref) async => const <EvidenceInsightCardData>[]),
          ],
          child: testMaterialApp(
            theme: AppThemes.lightTheme,
            home: const LearningInsightsOverviewScreen(),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('证据洞察'), findsNothing);
    },
  );
}

class _FakeSimulationRepository implements SimulationRepository {
  @override
  Future<List<SimulationSeedModel>> getRecommendedSeeds({
    String? scenarioKey,
    int limit = 3,
  }) async =>
      const <SimulationSeedModel>[];

  @override
  Future<SimulationSessionModel> runSimulation({
    required String topic,
    required String scenarioKey,
    int? plannedRoundCount,
    List<String>? participantNames,
    String facilitationStyle = 'balanced',
  }) async =>
      throw UnimplementedError();

  @override
  Stream<SimulationStreamEventModel> streamSimulation({
    required String topic,
    required String scenarioKey,
    int? plannedRoundCount,
    List<String>? participantNames,
    String facilitationStyle = 'balanced',
  }) =>
      const Stream<SimulationStreamEventModel>.empty();

  @override
  Future<SimulationSessionModel> continueSimulation({
    required String sessionId,
    required String userResponse,
    int? plannedRoundCount,
  }) async =>
      throw UnimplementedError();

  @override
  Stream<SimulationStreamEventModel> continueSimulationStream({
    required String sessionId,
    required String userResponse,
    int? plannedRoundCount,
  }) =>
      const Stream<SimulationStreamEventModel>.empty();

  @override
  Future<SimulationSessionModel> getSession(String sessionId) async =>
      throw UnimplementedError();
}

class _StaticSimulationNotifier extends SimulationNotifier {
  _StaticSimulationNotifier(SimulationState initialState)
      : super(_FakeSimulationRepository(), _FakeRef()) {
    state = initialState;
  }

  @override
  Future<void> loadRecommendedSeeds({
    String? scenarioKey,
    int limit = 3,
    bool silent = false,
  }) async {}
}

class _FakeRef implements Ref {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}
