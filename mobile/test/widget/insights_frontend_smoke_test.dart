import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/home/presentation/widgets/insight_hub_card.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/presentation/screens/learning_report_screen.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/data/repositories/simulation_repository.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/theater/data/repositories/theater_repository.dart';
import 'package:sparkle/features/theater/presentation/providers/theater_provider.dart';
import 'package:sparkle/features/theater/presentation/screens/knowledge_theater_screen.dart';
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

class _FakeApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class _FakeTheaterRepository extends TheaterRepository {
  _FakeTheaterRepository() : super(_FakeApiClient());
}

class _StaticTheaterNotifier extends TheaterNotifier {
  _StaticTheaterNotifier(this._initialState, Ref ref)
      : super(_FakeTheaterRepository(), ref) {
    state = _initialState;
  }

  final TheaterState _initialState;

  @override
  Future<void> generatePrediction({
    required String topic,
    String? targetNodeId,
    int horizonDays = 14,
  }) async {}

  @override
  Future<void> adoptSelectedRouteWithSource({
    String? sourceChatSessionId,
  }) async {}

  @override
  Future<void> runWhatIfForStep(String stepNodeId) async {}

  @override
  Future<void> saveSnapshot({String? note}) async {}

  @override
  Future<void> refreshAccuracy() async {}
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  group('Insights frontend smoke', () {
    testWidgets(
        'insight hub card renders unified entry and supports direct jump',
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
            builder: (context, state) => const Text('open-theater'),
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
      expect(find.textContaining('线性代数'), findsOneWidget);
      expect(find.textContaining('1 个推荐场景'), findsWidgets);
      expect(find.textContaining('掌握度 72%'), findsOneWidget);

      await tester.tap(find.text('推演剧场'));
      await tester.pumpAndSettle();
      expect(find.text('open-theater'), findsOneWidget);
    });

    testWidgets('learning report screen renders animated dashboard sections',
        (tester) async {
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
        diagnosisCards: <LearningReportDiagnosticCard>[
          LearningReportDiagnosticCard(
            id: 'weak-spot',
            title: '优先补强',
            headline: '行列式 58%',
            summary: '这是当前最值得先收口的薄弱点。',
            evidence: <String>['当前掌握度偏低', '建议先回到定义和例题'],
            severity: 'high',
          ),
        ],
        actionCards: <LearningReportActionCard>[
          LearningReportActionCard(
            id: 'open-theater',
            title: '先推演 行列式',
            summary: '先拆路径再决定练习顺序。',
            ctaLabel: '打开推演剧场',
            deepLink: '/theater?topic=%E8%A1%8C%E5%88%97%E5%BC%8F',
            kind: 'theater',
            badge: '优先',
          ),
        ],
        trendOverview: LearningReportTrendOverview(
          headline: '最近一轮掌握度约 72%',
          summary: '掌握度整体稳中有升。',
          historyPoints: <LearningTrendPoint>[
            LearningTrendPoint(label: '上周', averageMastery: 66),
            LearningTrendPoint(label: '本周', averageMastery: 72),
          ],
          comparisons: <LearningTrendComparison>[
            LearningTrendComparison(
              label: '本周 vs 上周',
              summary: '掌握度提升了 6 个点。',
              deltaMastery: 6,
              direction: 'up',
            ),
          ],
        ),
        triggerSummary: LearningReportTriggerSummary(
          mode: 'baseline_ready',
          title: '已建立第一版学习基线',
          summary: '系统已经整理出一版可执行的诊断仪表盘。',
        ),
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
      expect(find.text('已建立第一版学习基线'), findsOneWidget);
      expect(find.text('诊断摘要'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('掌握度趋势'),
        120,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('掌握度趋势'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('掌握度雷达图'),
        120,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('掌握度雷达图'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('下一步行动'),
        180,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('下一步行动'), findsOneWidget);
      expect(find.text('先推演 行列式'), findsOneWidget);
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
      await tester.tap(find.text('AI 分析报告'));
      await tester.pumpAndSettle();
      expect(find.textContaining('本周总结'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('knowledge theater screen shows friendly timeout guidance',
        (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            simulationProvider.overrideWith(
              (ref) => _StaticSimulationNotifier(const SimulationState()),
            ),
            theaterProvider.overrideWith(
              (ref) => _StaticTheaterNotifier(
                const TheaterState(
                  error: '这次推演花的时间有点长。你可以把目标说得更具体一点，或者稍后再试。',
                ),
                ref,
              ),
            ),
          ],
          child: const MaterialApp(
            home: KnowledgeTheaterScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.textContaining('这次推演花的时间有点长'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
      expect(find.text('换个目标'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('insight hub card shows retry banner when refresh fails',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/',
        routes: <RouteBase>[
          GoRoute(
            path: '/',
            builder: (context, state) => const Scaffold(body: InsightHubCard()),
          ),
          GoRoute(
            path: '/theater',
            builder: (context, state) => const SizedBox.shrink(),
          ),
          GoRoute(
            path: '/simulation',
            builder: (context, state) => const SizedBox.shrink(),
          ),
          GoRoute(
            path: '/learning-report',
            builder: (context, state) => const SizedBox.shrink(),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            simulationProvider.overrideWith(
              (ref) => _StaticSimulationNotifier(
                const SimulationState(
                  error: 'network failed',
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
              (ref) async => <Map<String, dynamic>>[],
            ),
          ],
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.textContaining('洞察内容暂时没有刷新成功'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
