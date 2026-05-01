import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/predicted_intent_card.dart';

import '../../dashboard_test_harness.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    await initializeDashboardTestEnvironment();
  });

  testWidgets('dashboard predicted intent card shows bounded claim with caveat when payload exists', (
    tester,
  ) async {
    await tester.pumpWidget(
      buildDashboardWidgetHarness(
        child: const PredictedIntentCard(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Recent same-category signal'), findsOneWidget);
    expect(
      find.textContaining(
        'Based only on recent results inside this request category.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('dashboard predicted intent card hides bounded claim when payload is absent', (
    tester,
  ) async {
    final base = _dashboardStateWithoutWithinCategoryHint();
    await tester.pumpWidget(
      buildDashboardWidgetHarness(
        child: const PredictedIntentCard(),
        dashboardState: base,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Recent same-category signal'), findsNothing);
    expect(
      find.textContaining(
        'Based only on recent results inside this request category.',
      ),
      findsNothing,
    );
  });
}

DashboardState _dashboardStateWithoutWithinCategoryHint() => DashboardState(
      weather: WeatherData(type: 'sunny', condition: 'clear'),
      flame: FlameData(
        level: 4,
        brightness: 0.8,
        todayFocusMinutes: 95,
        tasksCompleted: 2,
      ),
      sprint: null,
      growth: GrowthData(
        id: 'growth-1',
        name: 'Growth',
        progress: 0.42,
        masteryLevel: 0.56,
      ),
      nextActions: [
        TaskData(
          id: 'action-1',
          title: 'Draft launch outline',
          estimatedMinutes: 25,
          priority: 1,
          type: 'planning',
        ),
      ],
      cognitive: CognitiveData(status: 'stable'),
      nextIntentForecast: PredictionInsightData(
        predictionId: 'prediction-1',
        horizon: 'today',
        title: 'Best next move',
        summary: 'Refine the dashboard shell before tuning secondary cards.',
        confidence: 0.82,
        predictedActionType: 'continue_plan',
        predictedWindow: 'next 2 hours',
        reasons: const [
          'The dashboard shell is already in place.',
        ],
        suggestedPrompt: 'Polish the dashboard visuals.',
        predictionSource: 'test',
        predictionTier: 'harness',
        fallbackUsed: false,
        explanations: const {
          'recent_24h': [
            'You already consolidated the top narrative area.',
          ],
        },
        recommendedActions: const [],
        trackingCandidateId: 'prediction-1',
        trackingActionType: 'continue_plan',
      ),
      growthStatus: GrowthStatusData(
        headline: 'You are moving with more clarity this week.',
        subtitle: 'Focus sessions and task completion are trending upward.',
        userName: 'Sparkle Test',
        streakDays: 5,
        focusHoursWeek: 6.5,
        tasksCompletedWeek: 8,
      ),
      mostImportantTask: PriorityTaskData(
        id: 'task-1',
        title: 'Finalize dashboard narrative',
        estimatedMinutes: 30,
        priority: 1,
        type: 'planning',
        reason: 'It unlocks the rest of the polish work.',
        planName: 'Dashboard Polish',
        daysToDeadline: 3,
      ),
      growthSignal: GrowthSignalData(
        headline: 'Execution quality is stabilizing.',
        summary:
            'You are shifting from scattered updates to deliberate progress.',
        source: 'Recent task rhythm',
      ),
      activePlanProgress: ActivePlanProgressData(
        id: 'plan-1',
        name: 'Dashboard Polish',
        type: 'design',
        phase: 'Refinement',
        progress: 0.64,
        masteryLevel: 0.5,
        daysToDeadline: 3,
      ),
      whatChangedCard: WhatChangedCardData(
        headline: 'The dashboard story is becoming clearer.',
        summary:
            'Redundant surfaces are gone and the top zone is easier to scan.',
        highlights: const [
          'The hero now compresses the main message into one place.',
        ],
        timeframeLabel: 'This week',
      ),
      nextMoveCard: NextMoveCardData(
        headline: 'Polish the remaining dashboard surfaces',
        summary:
            'Bring insights, task board, and module sections into one visual family.',
        whyNow: 'These are still the main coherence gaps.',
        reassurance:
            'The structure is already in place; this pass is about consistency.',
        taskId: 'task-1',
        estimatedMinutes: 30,
        planName: 'Dashboard Polish',
        daysToDeadline: 3,
      ),
    );
