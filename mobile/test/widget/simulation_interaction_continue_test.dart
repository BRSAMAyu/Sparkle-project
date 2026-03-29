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
      throw UnimplementedError();

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
  Future<void> continueSimulation(String userResponse) async {
    replies.add(userResponse);
    state = state.copyWith(
      isLoading: false,
      isContinuing: false,
      engineState: 'RUNNING',
    );
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
    expect(find.text('展开模拟设置'), findsOneWidget);
    expect(find.text('提交我的判断'), findsOneWidget);
    final chipFinder = find.byType(ActionChip).first;
    await tester.ensureVisible(chipFinder);
    await tester.tap(chipFinder);
    await tester.pump();

    expect(notifier.replies, <String>['我会先画依赖图，再做一道题验证。']);
    expect(find.text('继续当前模拟'), findsNothing);
    expect(find.text('提交我的判断'), findsOneWidget);
  });
}
