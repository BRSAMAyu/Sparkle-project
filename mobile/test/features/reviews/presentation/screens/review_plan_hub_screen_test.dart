import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/reviews/data/models/nightly_review_payload.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/reviews/presentation/screens/review_plan_hub_screen.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('renders reachable empty review hub state', (tester) async {
    await _pumpHub(
      tester,
      todayReviewOverride: (ref) async => const [],
      nightlyReviewOverride: (ref) async => null,
    );

    await tester.pump();

    expect(find.byType(ReviewPlanHubScreen), findsOneWidget);
    expect(find.text(S.reviewPlanHubTitle), findsOneWidget);
    expect(find.text(S.reviewPlanHubNoDueErrors), findsOneWidget);
    expect(find.text(S.reviewPlanHubNoNightlyReview), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text(S.reviewPlanHubNoActivePlan),
      300,
    );
    expect(find.text(S.reviewPlanHubNoActivePlan), findsOneWidget);
  });

  testWidgets('surfaces provider failures without crashing the hub',
      (tester) async {
    await _pumpHub(
      tester,
      todayReviewOverride: (ref) async => throw Exception('today unavailable'),
      nightlyReviewOverride: (ref) async =>
          throw Exception('nightly unavailable'),
    );

    await tester.pump();

    expect(find.byType(ReviewPlanHubScreen), findsOneWidget);
    expect(find.textContaining('today unavailable'), findsOneWidget);
    expect(find.text(S.reviewPlanHubNightlyUnavailable), findsOneWidget);
  });
}

Future<void> _pumpHub(
  WidgetTester tester, {
  required Future<List<ErrorRecord>> Function(Ref ref) todayReviewOverride,
  required Future<NightlyReviewPayload?> Function(Ref ref)
      nightlyReviewOverride,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        todayReviewListProvider.overrideWith(todayReviewOverride),
        nightlyReviewProvider.overrideWith(nightlyReviewOverride),
        dashboardProvider.overrideWith((ref) => _StaticDashboardNotifier()),
        planListProvider.overrideWith((ref) => _StaticPlanNotifier()),
        taskListProvider.overrideWith((ref) => _StaticTaskNotifier()),
      ],
      child: testMaterialApp(
        home: const ReviewPlanHubScreen(),
      ),
    ),
  );
}

class _StaticDashboardNotifier extends DashboardNotifier {
  _StaticDashboardNotifier() : super(_UnusedDashboardRepository(), _UnusedRef()) {
    state = DashboardState(
      weather: WeatherData(type: 'sunny', condition: 'clear'),
      flame: FlameData(level: 1, brightness: 0.5, todayFocusMinutes: 0),
      sprint: null,
      nextActions: const [],
      cognitive: CognitiveData(status: 'empty'),
    );
  }

  @override
  Future<void> fetchData() async {}
}

class _StaticPlanNotifier extends PlanNotifier {
  _StaticPlanNotifier() : super(_UnusedPlanRepository(), _UnusedRef());

  @override
  Future<void> loadPlans({PlanType? type}) async {}

  @override
  Future<void> loadActivePlans() async {}

  @override
  Future<void> refresh() async {}
}

class _StaticTaskNotifier extends TaskNotifier {
  _StaticTaskNotifier()
      : super(
          _UnusedTaskRepository(),
          _UnusedTaskNotificationScheduler(),
          _UnusedRef(),
        ) {
    state = TaskListState();
  }

  @override
  Future<void> loadTasks({TaskFilter? filter}) async {}

  @override
  Future<void> loadTodayTasks() async {}

  @override
  Future<void> loadRecommendedTasks() async {}

  @override
  Future<void> refreshTasks() async {}
}

class _UnusedDashboardRepository extends DashboardRepository {
  _UnusedDashboardRepository() : super(_UnusedApiClient());
}

class _UnusedPlanRepository extends Fake implements PlanRepository {}

class _UnusedTaskRepository extends Fake implements TaskRepository {}

class _UnusedTaskNotificationScheduler extends Fake
    implements TaskNotificationScheduler {}

class _UnusedApiClient extends Fake implements ApiClient {}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
