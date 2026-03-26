import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/home/presentation/widgets/insight_hub_card.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/presentation/screens/learning_report_screen.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/data/repositories/simulation_repository.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

class _FakeSimulationRepository implements SimulationRepository {
  @override
  Future<List<SimulationSeedModel>> getRecommendedSeeds({
    String? scenarioKey,
    int limit = 3,
  }) async =>
      <SimulationSeedModel>[
        const SimulationSeedModel(
          topic: '特征值与特征向量',
          context: '来自 Galaxy 的推荐种子',
          tensionPoint: '前置知识存在断层',
          sourceType: 'galaxy',
          sourceIds: <String>['n1'],
          relevanceScore: 0.91,
          suggestedScenario: 'study_group',
          suggestedExperts: <String>['数学专家', '星图导航'],
        ),
      ];

  @override
  Future<SimulationSessionModel> runSimulation({
    required String topic,
    required String scenarioKey,
  }) async =>
      const SimulationSessionModel(
        id: 's-1',
        scenarioKey: 'study_group',
        state: 'COMPLETED',
        topic: '特征值与特征向量',
        participants: <SimulationParticipantModel>[],
        rounds: <SimulationRoundModel>[],
        insightSummary: '已完成模拟',
      );

  @override
  Stream<SimulationStreamEventModel> streamSimulation({
    required String topic,
    required String scenarioKey,
  }) =>
      const Stream<SimulationStreamEventModel>.empty();
}

class _StaticSimulationNotifier extends SimulationNotifier {
  _StaticSimulationNotifier(SimulationState initialState)
      : super(_FakeSimulationRepository()) {
    state = initialState;
  }

  @override
  Future<void> loadRecommendedSeeds({
    String? scenarioKey,
    int limit = 3,
    bool silent = false,
  }) async {}
}

void main() {
  group('Insights frontend smoke', () {
    testWidgets('insight hub card renders unified entry and navigates to theater', (tester) async {
      final router = GoRouter(
        initialLocation: '/',
        routes: <RouteBase>[
          GoRoute(
            path: '/',
            builder: (context, state) => const Scaffold(body: InsightHubCard()),
          ),
          GoRoute(
            path: '/theater',
            builder: (context, state) => const Text('open-theater'),
          ),
          GoRoute(
            path: '/simulation',
            builder: (context, state) => const Text('open-simulation'),
          ),
          GoRoute(
            path: '/learning-report',
            builder: (context, state) => const Text('open-report'),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            simulationProvider.overrideWith(
              (ref) => _StaticSimulationNotifier(
                const SimulationState(
                  recommendedSeeds: <SimulationSeedModel>[
                    SimulationSeedModel(
                      topic: '特征值与特征向量',
                      context: '来自 Galaxy 的推荐种子',
                      tensionPoint: '前置知识存在断层',
                      sourceType: 'galaxy',
                      sourceIds: <String>['n1'],
                      relevanceScore: 0.91,
                      suggestedScenario: 'study_group',
                      suggestedExperts: <String>['数学专家', '星图导航'],
                    ),
                  ],
                ),
              ),
            ),
            systemUpdatesProvider.overrideWith(
              (ref) async => <Map<String, dynamic>>[
                <String, dynamic>{
                  'type': 'theater_route_adopted',
                  'description': '已根据推演创建计划',
                  'metadata': <String, dynamic>{
                    'title': '线性代数',
                  },
                },
                <String, dynamic>{
                  'type': 'learning_report_ready',
                  'metadata': <String, dynamic>{
                    'report_payload': <String, dynamic>{
                      'report_id': 'r-1',
                      'markdown': '# 报告',
                      'sections': <String>['summary'],
                      'mastery': <Map<String, dynamic>>[
                        <String, dynamic>{
                          'node_name': '特征值',
                          'mastery_score': 72,
                        },
                      ],
                    },
                  },
                },
              ],
            ),
          ],
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('学习洞察'), findsOneWidget);
      expect(find.text('推演剧场'), findsOneWidget);
      expect(find.text('学习仿真'), findsOneWidget);
      expect(find.text('学习报告'), findsOneWidget);
      expect(find.textContaining('上次推演：线性代数'), findsOneWidget);
      expect(find.textContaining('1 个推荐场景待探索'), findsOneWidget);
      expect(find.textContaining('掌握度 72%'), findsOneWidget);

      await tester.tap(find.text('推演剧场'));
      await tester.pumpAndSettle();
      expect(find.text('open-theater'), findsOneWidget);
    });

    testWidgets('learning report screen renders animated dashboard sections', (tester) async {
      const report = LearningReport(
        reportId: 'report-1',
        markdown: '# 本周总结\n\n- 特征值掌握提升\n- 仍需补强行列式',
        sections: <String>['summary'],
        mastery: <LearningMasteryDatum>[
          LearningMasteryDatum(nodeName: '特征值', masteryScore: 82),
          LearningMasteryDatum(nodeName: '特征向量', masteryScore: 76),
          LearningMasteryDatum(nodeName: '行列式', masteryScore: 58),
          LearningMasteryDatum(nodeName: '线性变换', masteryScore: 71),
        ],
      );

      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: LearningReportScreen(report: report),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('学习分析报告'), findsOneWidget);
      expect(find.text('掌握度雷达图'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('关键指标'),
        240,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('关键指标'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('AI 分析报告'),
        240,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('AI 分析报告'), findsOneWidget);
      expect(find.textContaining('本周总结'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
