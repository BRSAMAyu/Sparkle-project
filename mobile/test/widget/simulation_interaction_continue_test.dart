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

class _StreamingSimulationRepository implements SimulationRepository {
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
      throw UnimplementedError('stream path should build draft session');

  @override
  Stream<SimulationStreamEventModel> streamSimulation({
    required String topic,
    required String scenarioKey,
    int? plannedRoundCount,
    List<String>? participantNames,
    String facilitationStyle = 'balanced',
  }) =>
      Stream<
          SimulationStreamEventModel>.fromIterable(<SimulationStreamEventModel>[
        SimulationStreamEventModel.fromJson('status', <String, dynamic>{
          'session_id': 'sim-stream-1',
          'state': 'PREPARING',
          'progress': 0.1,
          'planned_round_count': 12,
          'facilitation_style': 'practical',
        }),
        SimulationStreamEventModel.fromJson('participants', <String, dynamic>{
          'session_id': 'sim-stream-1',
          'state': 'RUNNING',
          'participants': <Map<String, dynamic>>[
            <String, dynamic>{
              'name': '实践派',
              'role_hint': '先讲怎么落地',
              'persona': <String, dynamic>{},
            },
          ],
          'planned_round_count': 12,
          'facilitation_style': 'practical',
        }),
        SimulationStreamEventModel.fromJson('interaction', <String, dynamic>{
          'session_id': 'sim-stream-1',
          'state': 'WAITING_FOR_USER',
          'rounds': <Map<String, dynamic>>[
            <String, dynamic>{
              'round': 1,
              'speaker': '实践派',
              'message': '我们先落到一个可验证动作上。',
            },
          ],
          'interaction': <String, dynamic>{
            'id': 'interaction-1',
            'interaction_type': 'choice',
            'prompt': '你第一步会怎么验证？',
            'suggested_replies': <String>['我先做一道题验证理解。'],
            'options': <String>['先练题', '先整理框架'],
            'target_round': 1,
          },
          'planned_round_count': 12,
          'facilitation_style': 'practical',
        }),
      ]);

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
  final _fakeAppEventStreamService = _FakeAppEventStreamService();

  @override
  dynamic noSuchMethod(Invocation invocation) {
    if (invocation.memberName == #read) {
      return _fakeAppEventStreamService;
    }
    return null;
  }
}

class _FakeAppEventStreamService {
  Future<void> recordSimulationStarted({
    required String topic,
    required String scenarioKey,
  }) async {}
}

class _RecordingSimulationNotifier extends SimulationNotifier {
  _RecordingSimulationNotifier(SimulationState initialState)
      : super(_FakeSimulationRepository(), _FakeRef()) {
    state = initialState;
  }

  final List<String> replies = <String>[];

  @override
  Future<void> loadRecommendedSeeds({
    String? scenarioKey,
    int limit = 3,
    bool silent = false,
  }) async {}

  @override
  Future<bool> continueSimulation(String userResponse) async {
    replies.add(userResponse);
    state = state.copyWith(
      isLoading: false,
      isContinuing: false,
      engineState: 'RUNNING',
    );
    return true;
  }
}

class _FailingContinueNotifier extends SimulationNotifier {
  _FailingContinueNotifier(SimulationState initialState)
      : super(_FakeSimulationRepository(), _FakeRef()) {
    state = initialState;
  }

  @override
  Future<void> loadRecommendedSeeds({
    String? scenarioKey,
    int limit = 3,
    bool silent = false,
  }) async {}

  @override
  Future<bool> continueSimulation(String userResponse) async {
    state = state.copyWith(
      isLoading: false,
      isContinuing: false,
      error: '模拟继续失败',
    );
    return false;
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  testWidgets('interaction card continues simulation in place', (tester) async {
    final notifier = _RecordingSimulationNotifier(
      const SimulationState(
        session: SimulationSessionModel(
          id: 'sim-1',
          scenarioKey: 'study_group',
          state: 'WAITING_FOR_USER',
          topic: '特征值与特征向量',
          participants: <SimulationParticipantModel>[
            SimulationParticipantModel(
              name: '优等生',
              roleHint: '先搭框架',
              persona: <String, dynamic>{},
            ),
          ],
          rounds: <SimulationRoundModel>[
            SimulationRoundModel(
              round: 1,
              speaker: '优等生',
              message: '我们先把前置依赖画出来。',
            ),
          ],
          insightSummary: '先框架后练题。',
          interactionPrompt: '你会怎么接这一步？',
          suggestedReplies: <String>[
            '我会先画依赖图，再做一道题验证。',
          ],
          interactionType: 'choice',
          interactionOptions: <String>['优等生', '提问者'],
          pendingInteraction: SimulationInteractionModel(
            id: 'i-1',
            interactionType: 'choice',
            prompt: '你会怎么接这一步？',
            suggestedReplies: <String>[
              '我会先画依赖图，再做一道题验证。',
            ],
            options: <String>['优等生', '提问者'],
            targetRound: 1,
          ),
        ),
        sessionId: 'sim-1',
        engineState: 'WAITING_FOR_USER',
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          simulationProvider.overrideWith((ref) => notifier),
        ],
        child: const MaterialApp(
          home: SimulationScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('推荐场景'), findsNothing);
    expect(find.text('模拟设置'), findsOneWidget);
    expect(find.text('提交我的判断'), findsOneWidget);
    final chipFinder = find.byType(ActionChip).first;
    await tester.ensureVisible(chipFinder);
    await tester.pumpAndSettle();
    await tester.tap(chipFinder, warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(notifier.replies, <String>['我会先画依赖图，再做一道题验证。']);
    expect(find.text('继续当前模拟'), findsNothing);
    expect(find.text('提交我的判断'), findsOneWidget);
  });

  test('streamed simulation keeps backend round plan and facilitation style',
      () async {
    final notifier = SimulationNotifier(
      _StreamingSimulationRepository(),
      _FakeRef(),
    );

    await notifier.run(
      topic: '矩阵对角化',
      scenarioKey: 'study_group',
      plannedRoundCount: 5,
      facilitationStyle: 'balanced',
    );

    expect(notifier.state.session?.id, 'sim-stream-1');
    expect(notifier.state.session?.plannedRoundCount, 12);
    expect(notifier.state.session?.facilitationStyle, 'practical');
    expect(notifier.state.livePlannedRoundCount, 12);
    expect(notifier.state.liveFacilitationStyle, 'practical');
  });

  testWidgets('typed reply is preserved when simulation continue fails',
      (tester) async {
    final notifier = _FailingContinueNotifier(
      const SimulationState(
        session: SimulationSessionModel(
          id: 'sim-2',
          scenarioKey: 'study_group',
          state: 'WAITING_FOR_USER',
          topic: '矩阵对角化',
          participants: <SimulationParticipantModel>[
            SimulationParticipantModel(
              name: '实践派',
              roleHint: '先落到动作',
              persona: <String, dynamic>{},
            ),
          ],
          rounds: <SimulationRoundModel>[
            SimulationRoundModel(
              round: 1,
              speaker: '实践派',
              message: '你先选一个最小验证动作。',
            ),
          ],
          insightSummary: '先验证，再抽象。',
          interactionPrompt: '你会先做什么？',
          pendingInteraction: SimulationInteractionModel(
            id: 'interaction-2',
            interactionType: 'choice',
            prompt: '你会先做什么？',
            options: <String>['先练题', '先整理定义'],
            targetRound: 1,
          ),
        ),
        sessionId: 'sim-2',
        engineState: 'WAITING_FOR_USER',
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          simulationProvider.overrideWith((ref) => notifier),
        ],
        child: const MaterialApp(
          home: SimulationScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).last, '我先做一道题试试看');
    await tester.ensureVisible(find.text('提交我的判断'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('提交我的判断'), warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(find.text('我先做一道题试试看'), findsOneWidget);
    expect(notifier.state.error, '模拟继续失败');
  });
}
