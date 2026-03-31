import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/data/repositories/simulation_repository.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';
import 'package:sparkle/features/theater/data/repositories/theater_repository.dart';
import 'package:sparkle/features/theater/presentation/providers/theater_provider.dart';
import 'package:sparkle/features/theater/presentation/screens/knowledge_theater_screen.dart';

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
  }) async =>
      throw UnimplementedError();

  @override
  Stream<SimulationStreamEventModel> continueSimulationStream({
    required String sessionId,
    required String userResponse,
  }) =>
      const Stream<SimulationStreamEventModel>.empty();
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

class _StaticTheaterNotifier extends TheaterNotifier {
  _StaticTheaterNotifier(TheaterState initialState, Ref ref)
      : super(_FakeTheaterRepository(), ref) {
    state = initialState;
  }

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
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  testWidgets('knowledge theater prediction uses workbench layout',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(360, 720));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const route = TheaterPathOption(
      id: 'path-foundation',
      title: '稳扎稳打',
      summary: '先补前置，再推进目标。',
      strategyType: 'foundation',
      expertIds: <String>['galaxy-guide'],
      estimatedCompletionRate: 0.84,
      estimatedMastery: 79,
      dailyMinutes: 40,
      risks: <String>['后半程需要稳定性'],
      routeScore: 83,
      steps: <TheaterPathStep>[
        TheaterPathStep(
          index: 1,
          nodeId: 'node-1',
          nodeName: '行列式',
          rationale: '补前置',
          currentMastery: 40,
          predictedMastery: 62,
          riskLevel: 'high',
          estimatedMinutes: 35,
          dayLabel: '第 1 天',
          mappedGalaxyNodeId: 'galaxy-node-1',
        ),
        TheaterPathStep(
          index: 2,
          nodeId: 'node-2',
          nodeName: '特征值',
          rationale: '推进目标',
          currentMastery: 56,
          predictedMastery: 79,
          riskLevel: 'medium',
          estimatedMinutes: 40,
          dayLabel: '第 7 天',
          mappedGalaxyNodeId: 'galaxy-node-2',
        ),
      ],
    );

    const prediction = TheaterPrediction(
      predictionId: 'prediction-1',
      topic: '特征值与特征向量',
      targetNodeId: 'node-2',
      targetName: '线性代数',
      horizonDays: 7,
      paths: <TheaterPathOption>[route],
      discussionTurns: <TheaterDiscussionTurn>[
        TheaterDiscussionTurn(
          turnIndex: 0,
          agentId: 'galaxy-guide',
          displayName: '星图导航',
          turnType: 'analysis',
          content: '先补前置，再推进目标会更稳。',
          relatedNodeIds: <String>['node-1'],
        ),
      ],
      graphNodes: <TheaterGraphNode>[
        TheaterGraphNode(
          id: 'node-1',
          name: '行列式',
          description: '前置节点',
          currentMastery: 40,
          predictedMastery: 62,
          riskLevel: 'high',
          candidateStatus: 'pending_review',
        ),
        TheaterGraphNode(
          id: 'node-2',
          name: '特征值',
          description: '目标节点',
          currentMastery: 56,
          predictedMastery: 79,
          riskLevel: 'medium',
          sourceType: 'hybrid_reference',
          mappedGalaxyNodeId: 'galaxy-node-2',
          isTarget: true,
        ),
      ],
      graphEdges: <TheaterGraphEdge>[
        TheaterGraphEdge(
          id: 'edge-1',
          sourceId: 'node-1',
          targetId: 'node-2',
          relationType: 'prerequisite',
          strength: 0.9,
          sourceType: 'hybrid_reference',
        ),
      ],
      timeline: <TheaterTimelineFrame>[
        TheaterTimelineFrame(
          index: 0,
          label: '第 1 天',
          dayIndex: 1,
          routeId: 'path-foundation',
          focusNodeIds: <String>['node-1'],
          discussionTurnIndex: 0,
          projectedMastery: 45,
          projectedCompletionRate: 0.12,
          activeStepNodeId: 'node-1',
          activeStepTitle: '行列式',
          compareLabel: '推荐基线',
          branchType: 'baseline',
        ),
        TheaterTimelineFrame(
          index: 1,
          label: '第 7 天',
          dayIndex: 7,
          routeId: 'path-foundation',
          focusNodeIds: <String>['node-2'],
          discussionTurnIndex: 0,
          projectedMastery: 79,
          projectedCompletionRate: 0.84,
          activeStepNodeId: 'node-2',
          activeStepTitle: '特征值',
          compareLabel: '推荐基线',
          branchType: 'baseline',
        ),
      ],
      recommendedRouteId: 'path-foundation',
      targetResolutionMode: 'hybrid_semantic',
      semanticMatches: <TheaterSemanticMatch>[
        TheaterSemanticMatch(
          freeformNodeId: 'node-1',
          freeformNodeName: '行列式',
          galaxyNodeId: 'galaxy-node-1',
          galaxyNodeName: '行列式',
          confidence: 0.82,
          evidence: '语义接近，可作为参考映射。',
        ),
      ],
      accuracyTracking: TheaterAccuracyTracking(
        predictionId: 'prediction-1',
        status: 'pending_feedback',
        dueOn: '2026-04-03',
        summaryHint: '建议在 7 天后回填真实完成率和掌握度。',
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          simulationProvider.overrideWith(
            (ref) => _StaticSimulationNotifier(
              const SimulationState(
                recommendedSeeds: <SimulationSeedModel>[
                  SimulationSeedModel(
                    topic: '矩阵的几何意义',
                    context: '从当前主题延伸出来的推荐场景',
                    tensionPoint: '概念直觉不足',
                    sourceType: 'galaxy',
                    sourceIds: <String>['n1'],
                    relevanceScore: 0.88,
                    suggestedScenario: 'study_group',
                    suggestedExperts: <String>['数学专家'],
                  ),
                ],
              ),
            ),
          ),
          theaterProvider.overrideWith(
            (ref) => _StaticTheaterNotifier(
              const TheaterState(
                prediction: prediction,
                selectedRouteId: 'path-foundation',
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

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    expect(find.text('先定目标，再看清多条路径'), findsNothing);
    expect(find.text('调整目标'), findsOneWidget);
    expect(find.text('关系图谱主舞台'), findsOneWidget);
    expect(find.text('模式 · 智能混合'), findsWidgets);
    expect(find.textContaining('自由节点与星图参考'), findsOneWidget);

    await tester.tap(
      find.byKey(const ValueKey<String>('theater-workbench-tab-paths')),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('路径对比'), findsOneWidget);

    await tester.tap(
      find.byKey(
        const ValueKey<String>('theater-workbench-tab-discussion'),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('推演时间轴'), findsOneWidget);

    await tester.tap(
      find.byKey(
        const ValueKey<String>('theater-workbench-tab-calibration'),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('校准与落地'), findsOneWidget);

    await tester.tap(find.text('调整目标'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('调整推演目标'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
