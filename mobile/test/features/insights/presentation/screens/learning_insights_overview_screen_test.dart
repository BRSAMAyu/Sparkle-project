import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/insights/presentation/screens/learning_insights_overview_screen.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/data/repositories/simulation_repository.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

void main() {
  testWidgets(
      'insights overview shows empty state guidance when there is no data',
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
        ],
        child: MaterialApp(
          theme: AppThemes.lightTheme,
          home: const LearningInsightsOverviewScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('学习洞察还没有可读数据'), findsOneWidget);
    expect(find.text('去创建学习任务'), findsOneWidget);
  });

  testWidgets('weekly narrative panel opens expanded from deep link',
      (WidgetTester tester) async {
    const narrative = WeeklyGrowthNarrative(
      period: '本周成长故事',
      weekStart: '2026-04-20',
      weekEnd: '2026-04-26',
      body: '这周你学习了 5 天。',
      sentences: <String>['这周你学习了 5 天。'],
      highlights: <String>['错题复盘更稳定了。'],
      biggestImprovement: <String, dynamic>{},
      nextWeekSuggestion: '',
      dataPoints: <String, dynamic>{'study_days': 5},
      sourceCounts: <String, int>{'study_days': 5},
      isPlaceholder: false,
      generatedAt: '2026-04-25T10:00:00',
    );

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
            (ref) async => narrative,
          ),
        ],
        child: MaterialApp(
          theme: AppThemes.lightTheme,
          home: const LearningInsightsOverviewScreen(
            initialPanel: LearningInsightsOverviewScreen.panelWeeklyNarrative,
          ),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byTooltip('收起'), findsOneWidget);
    expect(find.text('错题复盘更稳定了。'), findsOneWidget);
  });
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
