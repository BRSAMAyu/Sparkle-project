import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/data/repositories/simulation_repository.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/presentation/screens/simulation_screen.dart';

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
  }) async =>
      const SimulationSessionModel(
        id: 's-overflow',
        scenarioKey: 'study_group',
        state: 'COMPLETED',
        topic: '特征值与特征向量',
        participants: <SimulationParticipantModel>[],
        rounds: <SimulationRoundModel>[],
        insightSummary: '已完成',
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
        id: 's-overflow',
        scenarioKey: 'study_group',
        state: 'COMPLETED',
        topic: '特征值与特征向量',
        participants: <SimulationParticipantModel>[],
        rounds: <SimulationRoundModel>[],
        insightSummary: '已完成',
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

  testWidgets('simulation screen stays stable on compact height',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 560));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          simulationProvider.overrideWith(
            (ref) => _StaticSimulationNotifier(
              const SimulationState(
                session: SimulationSessionModel(
                  id: 's-1',
                  scenarioKey: 'study_group',
                  state: 'COMPLETED',
                  topic: '一个非常长非常长的学习主题，用来验证窄屏与较低高度下的布局稳定性',
                  participants: <SimulationParticipantModel>[
                    SimulationParticipantModel(
                      name: '数学专家',
                      roleHint: 'analyst',
                      persona: <String, dynamic>{},
                    ),
                    SimulationParticipantModel(
                      name: '反方辩手',
                      roleHint: 'challenger',
                      stance: 'opposing',
                      persona: <String, dynamic>{},
                    ),
                    SimulationParticipantModel(
                      name: '学习伙伴',
                      roleHint: 'questioner',
                      persona: <String, dynamic>{},
                    ),
                  ],
                  rounds: <SimulationRoundModel>[
                    SimulationRoundModel(
                      round: 1,
                      speaker: '数学专家',
                      message: '先从定义出发，说明特征值与线性变换之间的联系。',
                      turnGoal: 'open',
                    ),
                    SimulationRoundModel(
                      round: 2,
                      speaker: '反方辩手',
                      message: '如果只会代公式但不理解几何意义，后面仍然会卡住。',
                      replyToSpeaker: '数学专家',
                      turnGoal: 'challenge',
                    ),
                    SimulationRoundModel(
                      round: 3,
                      speaker: '学习伙伴',
                      message: '可以先把矩阵看成对空间的拉伸，再理解不变方向。',
                      replyToSpeaker: '反方辩手',
                      turnGoal: 'synthesize',
                    ),
                  ],
                  insightSummary: '这轮讨论的关键在于先建立直觉，再回到代数表达，避免只停留在机械运算。',
                  interactionPrompt: '如果是你，现在会先补几何直觉还是先练一道题？',
                  suggestedReplies: <String>[
                    '我会先补几何直觉，再回到代数表达。',
                    '我想先找一道典型题验证理解。',
                  ],
                ),
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
        ],
        child: const MaterialApp(
          home: SimulationScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('学习场景模拟'), findsWidgets);
    expect(find.text('沉浸讨论流'), findsOneWidget);
    expect(find.text('推荐场景'), findsNothing);
    expect(find.text('展开模拟设置'), findsOneWidget);
    expect(find.text('数学专家'), findsWidgets);
    expect(find.text('反方辩手'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
