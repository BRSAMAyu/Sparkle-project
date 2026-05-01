import 'package:flutter/material.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/home/presentation/widgets/insight_hub_card.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/presentation/screens/learning_report_screen.dart';
import 'package:sparkle/features/report/presentation/widgets/mastery_radar_chart.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/data/repositories/simulation_repository.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';
import 'package:sparkle/features/theater/data/repositories/theater_repository.dart';
import 'package:sparkle/features/theater/presentation/providers/theater_provider.dart';
import 'package:sparkle/features/theater/presentation/screens/knowledge_theater_screen.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import '../shared/i18n_test_helper.dart';

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
    int? plannedRoundCount,
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
    int? plannedRoundCount,
  }) =>
      const Stream<SimulationStreamEventModel>.empty();

  @override
  Future<SimulationSessionModel> getSession(String sessionId) async =>
      const SimulationSessionModel(
        id: 's-1',
        scenarioKey: 'study_group',
        state: 'COMPLETED',
        topic: '特征值与特征向量',
        participants: <SimulationParticipantModel>[],
        rounds: <SimulationRoundModel>[],
        insightSummary: '已完成模拟',
      );
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
    String? simulationSessionId,
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

  setUp(setUpI18nForTesting);
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{
      // Suppress MirofishMilestone celebration dialogs in LearningReportScreen tests.
      'mirofish_milestone_v1:firstReport': true,
    });
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
          child: MaterialApp.router(
            routerConfig: router,
            locale: const Locale('zh'),
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
          ),
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

    testWidgets('learning report screen renders partial-data report without feature routing',
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
            evidence: <String>['掌握度：58%（来自知识图谱实际数据）', '上次学习此主题：2026-03-24'],
            severity: 'high',
          ),
        ],
        actionCards: <LearningReportActionCard>[
          LearningReportActionCard(
            id: 'attack-weakest',
            title: '专项攻克：行列式',
            summary: '当前掌握度 58%。建议用 25 分钟做一组针对性练习。',
            ctaLabel: '开始练习',
            deepLink: '/galaxy/node/node-1',
            kind: 'immediate_action',
            badge: '优先',
          ),
        ],
        trendOverview: LearningReportTrendOverview(
          headline: '最近一轮掌握度约 72%',
          summary: '当前只覆盖到部分真实学习记录，请先以方向判断为主。',
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
          title: '以下是基于聊天推断的方向，需要你确认',
          summary: '当前报告基于部分真实学习记录与聊天线索整理。',
          dataStatus: 'partial',
        ),
        dataStatus: 'partial',
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            apiClientProvider.overrideWithValue(_FakeApiClient()),
          ],
          child: testMaterialApp(
            home: LearningReportScreen(report: report),
          ),
        ),
      );
      // Pump enough frames for _AnimatedReportSection timers (≤140ms) and
      // TweenAnimationBuilder animations (DS.durationSlow) to complete.
      await tester.pump(const Duration(milliseconds: 150));
      await tester.pump(const Duration(milliseconds: 350));
      await tester.pump(const Duration(milliseconds: 350));

      expect(find.text('学习分析报告'), findsAtLeastNWidgets(1));
      expect(find.text('以下是基于聊天推断的方向，需要你确认'), findsOneWidget);
      expect(find.text('部分数据，仅供参考'), findsWidgets);
      expect(find.text('诊断摘要'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('下一步行动'),
        120,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('下一步行动'), findsOneWidget);
      expect(find.text('专项攻克：行列式'), findsOneWidget);
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
      final analysisTile = find.widgetWithText(ExpansionTile, 'AI 分析报告');
      await tester.ensureVisible(analysisTile);
      await tester.tap(analysisTile, warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });

    testWidgets('learning report screen shows empty state when data is insufficient',
        (tester) async {
      const report = LearningReport(
        reportId: 'report-empty',
        markdown: '# 学习分析报告\n\n当前还没有足够学习记录。',
        sections: <String>['summary'],
        mastery: <LearningMasteryDatum>[],
        diagnosisCards: <LearningReportDiagnosticCard>[
          LearningReportDiagnosticCard(
            id: 'data-collection-guide',
            title: '需要更多学习记录',
            headline: '先开始一次真实学习',
            summary: '完成一个学习任务、练习或复盘后，这里才会出现可信的掌握度分析。',
            evidence: <String>['当前没有可用的掌握度或趋势数据'],
            severity: 'info',
          ),
        ],
        actionCards: <LearningReportActionCard>[
          LearningReportActionCard(
            id: 'start-first-learning-task',
            title: '开始你的第一个学习任务',
            summary: '先完成一次真实学习，再回来查看报告。',
            ctaLabel: '去创建计划',
            deepLink: '/plan',
            kind: 'immediate_action',
          ),
        ],
        trendOverview: LearningReportTrendOverview(
          headline: '',
          summary: '',
          status: 'no_data',
          message: '暂无足够学习记录生成趋势',
        ),
        triggerSummary: LearningReportTriggerSummary(
          mode: 'baseline_ready',
          title: '以下是基于聊天推断的方向，需要你确认',
          summary: '当前缺少真实学习记录。',
          dataStatus: 'insufficient',
        ),
        dataStatus: 'insufficient',
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            apiClientProvider.overrideWithValue(_FakeApiClient()),
          ],
          child: testMaterialApp(
            home: LearningReportScreen(report: report),
          ),
        ),
      );
      // Pump enough frames for _AnimatedReportSection timers and animations.
      await tester.pump(const Duration(milliseconds: 150));
      await tester.pump(const Duration(milliseconds: 350));
      await tester.pump(const Duration(milliseconds: 350));

      expect(find.byType(MasteryRadarChart), findsNothing);
      expect(find.text('需要更多学习记录'), findsOneWidget);
      expect(find.textContaining('推演剧场'), findsNothing);
      expect(find.textContaining('模拟'), findsNothing);
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
          child: testMaterialApp(
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
          child: MaterialApp.router(
            routerConfig: router,
            locale: const Locale('zh'),
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.textContaining('洞察内容暂时没有刷新成功'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('learning report screen remains stable on compact width',
        (tester) async {
      await tester.binding.setSurfaceSize(const Size(320, 760));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      const report = LearningReport(
        reportId: 'report-compact',
        markdown: '# 本周总结\n\n- 这一轮重点先收口行列式\n- 再逐步推进特征值与特征向量',
        sections: <String>['summary'],
        mastery: <LearningMasteryDatum>[
          LearningMasteryDatum(nodeName: '特征值与特征向量', masteryScore: 72),
          LearningMasteryDatum(nodeName: '行列式与矩阵可逆条件', masteryScore: 58),
          LearningMasteryDatum(nodeName: '线性变换的几何直觉', masteryScore: 67),
        ],
        diagnosisCards: <LearningReportDiagnosticCard>[
          LearningReportDiagnosticCard(
            id: 'diagnosis-1',
            title: '优先补强',
            headline: '行列式与矩阵可逆条件 58%',
            summary: '这是当前最值得先收口的环节，建议先回到定义、例题和前置关系。',
            evidence: <String>[
              '最近几轮练习里，这个知识点反复拖慢推进速度。',
              '如果先补稳它，后续特征值部分会更顺。',
            ],
            severity: 'high',
            ctaLabel: '打开推演剧场',
            deepLink:
                '/theater?topic=%E8%A1%8C%E5%88%97%E5%BC%8F%E4%B8%8E%E7%9F%A9%E9%98%B5%E5%8F%AF%E9%80%86%E6%9D%A1%E4%BB%B6',
          ),
        ],
        actionCards: <LearningReportActionCard>[
          LearningReportActionCard(
            id: 'action-1',
            title: '先推演 行列式与矩阵可逆条件',
            summary: '先拆路径、风险和日程投入，再决定今天先补哪一段。',
            ctaLabel: '打开推演剧场',
            deepLink:
                '/theater?topic=%E8%A1%8C%E5%88%97%E5%BC%8F%E4%B8%8E%E7%9F%A9%E9%98%B5%E5%8F%AF%E9%80%86%E6%9D%A1%E4%BB%B6',
            kind: 'theater',
            badge: '优先',
          ),
        ],
        trendOverview: LearningReportTrendOverview(
          headline: '最近两轮掌握度正在回升',
          summary: '先把短板收口，再扩大练习范围会更稳。',
          historyPoints: <LearningTrendPoint>[
            LearningTrendPoint(
                label: '3/10', averageMastery: 61, studyMinutes: 42),
            LearningTrendPoint(
                label: '3/17', averageMastery: 66, studyMinutes: 56),
            LearningTrendPoint(
                label: '3/24', averageMastery: 72, studyMinutes: 63),
          ],
          comparisons: <LearningTrendComparison>[
            LearningTrendComparison(
              label: '本周 vs 上周',
              summary: '掌握度提升了 6 个点，学习时长也更稳定。',
              deltaMastery: 6,
              direction: 'up',
            ),
          ],
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            apiClientProvider.overrideWithValue(_FakeApiClient()),
          ],
          child: testMaterialApp(
            home: LearningReportScreen(report: report),
          ),
        ),
      );
      // Pump enough frames for _AnimatedReportSection timers and animations.
      await tester.pump(const Duration(milliseconds: 150));
      await tester.pump(const Duration(milliseconds: 350));
      await tester.pump(const Duration(milliseconds: 350));

      expect(find.text('学习分析报告'), findsAtLeastNWidgets(1));
      await tester.scrollUntilVisible(
        find.text('诊断摘要'),
        120,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('诊断摘要'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets(
        'knowledge theater screen remains stable with prediction on compact width',
        (tester) async {
      await tester.binding.setSurfaceSize(const Size(320, 760));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      const route = TheaterPathOption(
        id: 'path_foundation',
        title: '先补行列式，再推进特征值与特征向量',
        summary: '先把前置关系补稳，再逐步推进目标部分，整体节奏更平衡。',
        strategyType: 'foundation',
        expertIds: <String>['galaxy_guide'],
        estimatedCompletionRate: 0.84,
        estimatedMastery: 79,
        dailyMinutes: 40,
        risks: <String>['后半程需要稳定复盘'],
        routeScore: 83,
        checkpointDays: <int>[1, 3, 7],
        steps: <TheaterPathStep>[
          TheaterPathStep(
            index: 1,
            nodeId: 'node-1',
            nodeName: '行列式与矩阵可逆条件',
            rationale: '先补前置关系，避免后续推导断层。',
            currentMastery: 40,
            predictedMastery: 62,
            riskLevel: 'high',
            estimatedMinutes: 35,
            dayLabel: 'Day 1',
          ),
          TheaterPathStep(
            index: 2,
            nodeId: 'node-2',
            nodeName: '特征值与特征向量',
            rationale: '在前置稳住后再推进目标内容。',
            currentMastery: 56,
            predictedMastery: 79,
            riskLevel: 'medium',
            estimatedMinutes: 40,
            dayLabel: 'Day 7',
          ),
        ],
      );

      const prediction = TheaterPrediction(
        predictionId: 'prediction-compact',
        topic: '两周内掌握特征值与特征向量',
        targetNodeId: 'node-2',
        targetName: '线性代数',
        horizonDays: 7,
        paths: <TheaterPathOption>[route],
        discussionTurns: <TheaterDiscussionTurn>[
          TheaterDiscussionTurn(
            turnIndex: 0,
            agentId: 'galaxy_guide',
            displayName: '星图导航',
            turnType: 'analysis',
            content: '先补行列式，再推进目标内容会更稳。',
            relatedNodeIds: <String>['node-1'],
          ),
        ],
        graphNodes: <TheaterGraphNode>[
          TheaterGraphNode(
            id: 'node-1',
            name: '行列式与矩阵可逆条件',
            description: '前置节点',
            currentMastery: 40,
            predictedMastery: 62,
            riskLevel: 'high',
          ),
          TheaterGraphNode(
            id: 'node-2',
            name: '特征值与特征向量',
            description: '目标节点',
            currentMastery: 56,
            predictedMastery: 79,
            riskLevel: 'medium',
          ),
        ],
        graphEdges: <TheaterGraphEdge>[
          TheaterGraphEdge(
            id: 'edge-1',
            sourceId: 'node-1',
            targetId: 'node-2',
            relationType: 'prerequisite',
            strength: 0.9,
          ),
        ],
        timeline: <TheaterTimelineFrame>[
          TheaterTimelineFrame(
            index: 0,
            label: 'Day 1',
            dayIndex: 1,
            routeId: 'path_foundation',
            focusNodeIds: <String>['node-1'],
            discussionTurnIndex: 0,
            projectedMastery: 45,
            projectedCompletionRate: 0.12,
            activeStepNodeId: 'node-1',
            activeStepTitle: '行列式与矩阵可逆条件',
            compareLabel: '推荐基线',
            branchType: 'baseline',
          ),
          TheaterTimelineFrame(
            index: 1,
            label: 'Day 7',
            dayIndex: 7,
            routeId: 'path_foundation',
            focusNodeIds: <String>['node-2'],
            discussionTurnIndex: 0,
            projectedMastery: 79,
            projectedCompletionRate: 0.84,
            activeStepNodeId: 'node-2',
            activeStepTitle: '特征值与特征向量',
            compareLabel: '推荐基线',
            branchType: 'baseline',
          ),
        ],
        recommendedRouteId: 'path_foundation',
        targetResolutionMode: 'knowledge_graph',
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            simulationProvider.overrideWith(
              (ref) => _StaticSimulationNotifier(const SimulationState()),
            ),
            theaterProvider.overrideWith(
              (ref) => _StaticTheaterNotifier(
                const TheaterState(
                  prediction: prediction,
                  selectedRouteId: 'path_foundation',
                ),
                ref,
              ),
            ),
          ],
          child: testMaterialApp(
            home: KnowledgeTheaterScreen(),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('知识推演剧场'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('路径对比'),
        120,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('路径对比'), findsWidgets);
      expect(find.textContaining('先补行列式'), findsWidgets);
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump(const Duration(milliseconds: 400));
      expect(tester.takeException(), isNull);
    });

    testWidgets(
        'compact insight hub card remains stable on dashboard-sized layout',
        (tester) async {
      await tester.binding.setSurfaceSize(const Size(320, 196));
      addTearDown(() => tester.binding.setSurfaceSize(null));

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
              (ref) async => <Map<String, dynamic>>[],
            ),
          ],
          child: testMaterialApp(
            home: Scaffold(
              body: SizedBox(
                width: 320,
                height: 196,
                child: InsightHubCard(compact: true, dense: true),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('学习洞察'), findsOneWidget);
      expect(find.text('仿真'), findsOneWidget);
      expect(find.text('推演'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
