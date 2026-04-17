import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/providers/home_close_to_unlock_provider.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/expert_catalog_model.dart';
import 'package:sparkle/features/chat/presentation/providers/expert_catalog_provider.dart';
import 'package:sparkle/features/home/data/models/notification_model.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/data/repositories/notification_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

Directory? _dashboardHiveDir;
late SharedPreferences _dashboardPrefs;

Future<void> initializeDashboardTestEnvironment() async {
  SharedPreferences.setMockInitialValues({});
  _dashboardHiveDir ??=
      Directory.systemTemp.createTempSync('sparkle_dashboard_hive_');
  Hive.init(_dashboardHiveDir!.path);
  _dashboardPrefs = await SharedPreferences.getInstance();
  await ViewStorageService.ensureInitialized();
  await ViewStorageService.instance.clearAllViewState();
  await ViewStorageService.instance.setJson(
    'dashboard_cards',
    'config',
    const DashboardCardConfigState(
      visibleCardIds: [
        DashboardCardIds.streak,
        DashboardCardIds.nextActions,
        DashboardCardIds.longTermPlan,
        DashboardCardIds.focus,
      ],
      cardOrder: [
        DashboardCardIds.streak,
        DashboardCardIds.nextActions,
        DashboardCardIds.longTermPlan,
        DashboardCardIds.focus,
        DashboardCardIds.insights,
        DashboardCardIds.calendar,
        DashboardCardIds.tools,
        DashboardCardIds.openClaw,
        DashboardCardIds.curiosity,
        DashboardCardIds.seedLibrary,
      ],
      layoutMode: DashboardCardLayoutMode.grid,
    ).toJson(),
    debounce: Duration.zero,
  );
}

Widget buildDashboardTestHarness({
  ThemeData? theme,
  Size size = const Size(390, 844),
  Locale? locale = const Locale('en'),
}) {
  final dashboardState = _sampleDashboardState();
  final tasks = _sampleTasks();

  return ProviderScope(
    overrides: [
      flutterSecureStorageProvider.overrideWithValue(_MemorySecureStorage()),
      sharedPreferencesProvider.overrideWithValue(_dashboardPrefs),
      authProvider.overrideWith((ref) => _StaticAuthNotifier()),
      currentUserProvider.overrideWith((ref) => _buildUser()),
      notificationServiceProvider.overrideWith(
        (ref) => _SilentNotificationService(),
      ),
      homeCloseToUnlockProvider.overrideWith(
        (ref) => _StaticHomeCloseToUnlockNotifier(),
      ),
      dashboardProvider.overrideWith(
        (ref) => _StaticDashboardNotifier(dashboardState),
      ),
      dashboardCardConfigProvider
          .overrideWith(_StaticDashboardCardConfigNotifier.new),
      streakStatsProvider.overrideWithValue(
        StreakStats(
          currentStreak: 5,
          maxStreak: 5,
          longestStreak: 8,
          freezeCharges: 1,
          maxFreezeCharges: 3,
          totalCheckinDays: 18,
          lastActivityDate: DateTime(2026, 4, 8),
        ),
      ),
      visiblePredictionsProvider.overrideWith((ref) => const []),
      multiAgentCatalogProvider.overrideWith(
        (ref) async => MultiAgentCatalog(
          modes: const [],
          experts: const [],
          customExperts: const [],
          customTeams: const [],
          modelOptions: const [],
        ),
      ),
      taskListProvider.overrideWith((ref) => _StaticTaskListNotifier(tasks)),
      planListProvider.overrideWith((ref) => _StaticPlanListNotifier()),
      taskBoardTodaySummaryProvider.overrideWith(
        (ref) => const TaskBoardTodaySummary(totalCount: 1, completedCount: 0),
      ),
      notificationRepositoryProvider.overrideWithValue(
        _FakeNotificationRepository(),
      ),
      notificationCenterProvider.overrideWith(
        () => _StaticNotificationCenter(const NotificationCenterState()),
      ),
      systemUpdatesProvider.overrideWith((ref) async => _sampleSystemUpdates()),
      nightlyReviewProvider.overrideWith((ref) async => null),
    ],
    child: MaterialApp(
      locale: locale,
      theme: theme ?? ThemeData.light(),
      localizationsDelegates: const [
        ...AppLocalizations.localizationsDelegates,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: MediaQuery(
        data: MediaQueryData(size: size),
        child: const TickerMode(
          enabled: false,
          child: DashboardScreen(),
        ),
      ),
    ),
  );
}

class _StaticDashboardNotifier extends DashboardNotifier {
  _StaticDashboardNotifier(DashboardState initialState)
      : super(_UnusedDashboardRepository()) {
    state = initialState;
  }

  @override
  Future<void> fetchData() async {}

  @override
  Future<void> refresh() async {}
}

class _StaticAuthNotifier extends AuthNotifier {
  _StaticAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: _buildUser(),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _StaticHomeCloseToUnlockNotifier extends HomeCloseToUnlockNotifier {
  _StaticHomeCloseToUnlockNotifier() : super(_UnusedRef()) {
    state = const HomeCloseToUnlockState();
  }

  @override
  Future<void> fetch({bool forceRefresh = false}) async {}
}

class _StaticDashboardCardConfigNotifier extends DashboardCardConfigNotifier {
  _StaticDashboardCardConfigNotifier(super.ref) {
    state = const DashboardCardConfigState(
      visibleCardIds: [
        DashboardCardIds.streak,
        DashboardCardIds.nextActions,
        DashboardCardIds.longTermPlan,
        DashboardCardIds.focus,
      ],
      cardOrder: [
        DashboardCardIds.streak,
        DashboardCardIds.nextActions,
        DashboardCardIds.longTermPlan,
        DashboardCardIds.focus,
        DashboardCardIds.insights,
        DashboardCardIds.calendar,
        DashboardCardIds.tools,
        DashboardCardIds.openClaw,
        DashboardCardIds.curiosity,
        DashboardCardIds.seedLibrary,
      ],
      layoutMode: DashboardCardLayoutMode.grid,
    );
  }
}

class _StaticTaskListNotifier extends TaskNotifier {
  _StaticTaskListNotifier(List<TaskModel> tasks)
      : super(
          _UnusedTaskRepository(),
          _UnusedTaskNotificationScheduler(),
          _UnusedRef(),
        ) {
    state = TaskListState(tasks: tasks, todayTasks: tasks);
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

class _StaticPlanListNotifier extends PlanNotifier {
  _StaticPlanListNotifier() : super(_UnusedPlanRepository(), _UnusedRef());

  @override
  Future<void> loadPlans({PlanType? type}) async {}

  @override
  Future<void> loadActivePlans() async {}

  @override
  Future<void> refresh() async {}
}

class _StaticNotificationCenter extends NotificationCenter {
  _StaticNotificationCenter(this._initialState);

  final NotificationCenterState _initialState;

  @override
  NotificationCenterState build() => _initialState;

  @override
  Future<void> loadNotifications({
    bool unreadOnly = false,
    String? sourceType,
  }) async {}
}

class _FakeNotificationRepository extends NotificationRepository {
  _FakeNotificationRepository() : super(_NoopApiClient());

  @override
  Future<List<NotificationModel>> getNotifications({
    int skip = 0,
    int limit = 50,
    bool unreadOnly = false,
  }) async =>
      const [];
}

class _SilentNotificationService extends NotificationService {
  _SilentNotificationService() : super(_UnusedRef(), autoInitialize: false);

  @override
  Future<bool> requestPermission() async => false;

  @override
  Future<NotificationPermissionStatus> checkPermissionStatus() async =>
      NotificationPermissionStatus.denied(reason: 'test harness');
}

class _UnusedDashboardRepository extends DashboardRepository {
  _UnusedDashboardRepository() : super(_NoopApiClient());

  @override
  Future<Map<String, dynamic>> getDashboardStatus() async => {};

  @override
  Future<Map<String, dynamic>> getPredictiveDashboard() async => {};

  @override
  Future<Map<String, dynamic>> getGrowthDashboard() async => {};
}

class _UnusedTaskRepository extends TaskRepository {
  _UnusedTaskRepository() : super(_NoopApiClient());
}

class _UnusedPlanRepository extends PlanRepository {
  _UnusedPlanRepository() : super(_NoopApiClient());
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_NoopApiClient(), _MemorySecureStorage());

  @override
  Future<bool> isLoggedIn() async => true;

  @override
  Future<UserModel> getCurrentUser() async => _buildUser();

  @override
  Future<String?> getToken() async => null;

  @override
  Future<String?> getRefreshToken() async => null;

  @override
  Future<void> clearTokens() async {}

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedTaskNotificationScheduler extends TaskNotificationScheduler {
  _UnusedTaskNotificationScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) => InterceptorsWrapper() as T;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MemorySecureStorage implements FlutterSecureStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<bool> containsKey({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _values.containsKey(key);

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _values.remove(key);
  }

  @override
  Future<void> deleteAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _values.clear();
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _values[key];

  @override
  Future<Map<String, String>> readAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      Map<String, String>.from(_values);

  @override
  Future<void> write({
    required String key,
    String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value == null) {
      _values.remove(key);
    } else {
      _values[key] = value;
    }
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

DashboardState _sampleDashboardState() => DashboardState(
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
        TaskData(
          id: 'action-2',
          title: 'Review task flow',
          estimatedMinutes: 20,
          priority: 2,
          type: 'learning',
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
          'A consistency pass will unlock the biggest visual gain.',
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
          'Updates are folded under a single summary section.',
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

List<TaskModel> _sampleTasks() {
  final now = DateTime(2026, 4, 8, 9);
  return [
    TaskModel(
      id: 'task-1',
      userId: 'user-1',
      title: 'Finalize dashboard narrative',
      type: TaskType.planning,
      tags: const ['dashboard'],
      estimatedMinutes: 30,
      difficulty: 2,
      energyCost: 2,
      status: TaskStatus.pending,
      priority: 1,
      createdAt: now,
      updatedAt: now,
      dueDate: now,
    ),
  ];
}

List<Map<String, dynamic>> _sampleSystemUpdates() => [
      {
        'type': 'theater_route_adopted',
        'title': 'A new scenario route is ready',
        'description': 'You have one fresh insight path to review.',
        'metadata': {
          'deep_link': '/theater',
        },
        'created_at': DateTime(2026, 4, 8, 8).toIso8601String(),
      },
      {
        'type': 'learning_report_ready',
        'title': 'Weekly learning report',
        'description': 'Your latest report is ready to open.',
        'metadata': {
          'report_payload': {
            'report_id': 'report-1',
            'markdown': '# Dashboard Report',
            'sections': <String>[],
            'mastery': <Map<String, dynamic>>[],
          },
        },
        'created_at': DateTime(2026, 4, 8, 7).toIso8601String(),
      },
    ];

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000001',
      username: 'dashboard_test_user',
      email: 'dashboard@example.com',
      nickname: 'Dashboard Test',
      flameLevel: 4,
      flameBrightness: 0.8,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );
