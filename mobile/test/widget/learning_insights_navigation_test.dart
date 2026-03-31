import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/home/presentation/widgets/insight_hub_card.dart';
import 'package:sparkle/features/insights/presentation/screens/learning_insights_overview_screen.dart';
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
    int? plannedRoundCount,
    List<String>? participantNames,
    String facilitationStyle = 'balanced',
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
    int? plannedRoundCount,
    List<String>? participantNames,
    String facilitationStyle = 'balanced',
  }) =>
      const Stream<SimulationStreamEventModel>.empty();

  @override
  Future<SimulationSessionModel> continueSimulation({
    required String sessionId,
    required String userResponse,
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
  Stream<SimulationStreamEventModel> continueSimulationStream({
    required String sessionId,
    required String userResponse,
  }) =>
      const Stream<SimulationStreamEventModel>.empty();
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

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  group('learning insights navigation', () {
    testWidgets('insight hub shortcuts open destination pages directly',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/',
        routes: <RouteBase>[
          GoRoute(
            path: '/',
            builder: (context, state) => const Scaffold(body: InsightHubCard()),
          ),
          GoRoute(
            path: '/learning/insights',
            builder: (context, state) => const Text('overview-none'),
          ),
          GoRoute(
            path: '/theater',
            builder: (context, state) => Text(state.uri.toString()),
          ),
          GoRoute(
            path: '/simulation',
            builder: (context, state) => const Text('simulation-direct'),
          ),
          GoRoute(
            path: '/learning-report',
            builder: (context, state) => const Text('report-direct'),
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
                    'title': '稳扎稳打',
                    'deep_link':
                        '/theater?topic=%E7%BA%BF%E6%80%A7%E4%BB%A3%E6%95%B0&target_node_id=node-1',
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

      await tester.tap(find.text('推演剧场'));
      await tester.pumpAndSettle();

      expect(
        find.text(
            '/theater?topic=%E7%BA%BF%E6%80%A7%E4%BB%A3%E6%95%B0&target_node_id=node-1'),
        findsOneWidget,
      );
    });

    testWidgets('overview opens child routes and returns back to overview',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/learning/insights?initialPanel=simulation',
        routes: <RouteBase>[
          GoRoute(
            path: '/learning/insights',
            builder: (context, state) => LearningInsightsOverviewScreen(
              initialPanel: state.uri.queryParameters['initialPanel'],
            ),
          ),
          GoRoute(
            path: '/simulation',
            builder: (context, state) => const Scaffold(
              body: Center(child: Text('simulation-screen')),
            ),
          ),
          GoRoute(
            path: '/theater',
            builder: (context, state) => const Scaffold(
              body: Center(child: Text('theater-screen')),
            ),
          ),
          GoRoute(
            path: '/learning-report',
            builder: (context, state) => const Scaffold(
              body: Center(child: Text('report-screen')),
            ),
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

      expect(find.byType(LearningInsightsOverviewScreen), findsOneWidget);
      expect(find.text('已聚焦：学习仿真'), findsOneWidget);

      await tester.tap(find.text('从推荐开始'));
      await tester.pumpAndSettle();
      expect(find.text('simulation-screen'), findsOneWidget);

      router.pop();
      await tester.pumpAndSettle();

      expect(find.byType(LearningInsightsOverviewScreen), findsOneWidget);
    });
  });
}
