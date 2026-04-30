import 'dart:async';
import 'dart:ui';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/core/services/retry_strategy.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/galaxy/data/models/user_galaxy_contribution.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_performance_monitor.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';
import 'package:sparkle/features/insights/data/repositories/growth_narrative_repository.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/weekly_growth_narrative_card.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/models/plan_phase_model.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/learning_portfolio_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_completion_screen.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets('A. task completion updates galaxy UI without manual refresh',
      (tester) async {
    final galaxyRepository = _FakeEnhancedGalaxyRepository(
      graphResult: NetworkResult.success(
        GalaxyGraphResponse(
          nodes: <GalaxyNodeModel>[_node('node-1', 20)],
          edges: const <GalaxyEdgeModel>[],
          userFlameIntensity: 0.4,
        ),
      ),
    );
    final portfolioRepository =
        _MutableExamSprintRepository(_portfolio(status: 'active'));
    final achievementRepository = _MutableAchievementRepository();
    final taskRepository = _FakeTaskRepository(
      initialTask: _task('task-1'),
      onComplete: () {
        galaxyRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: <GalaxyNodeModel>[_node('node-1', 80)],
            edges: const <GalaxyEdgeModel>[],
            userFlameIntensity: 0.7,
          ),
        );
        portfolioRepository.portfolio = _portfolio(status: 'completed');
        achievementRepository.unlock();
      },
    );

    await tester.pumpWidget(
      _buildApp(
        overrides: <Override>[
          enhancedGalaxyRepositoryProvider.overrideWithValue(galaxyRepository),
          examSprintRepositoryProvider.overrideWithValue(portfolioRepository),
          achievementRepositoryProvider
              .overrideWithValue(achievementRepository),
          currentUserProvider.overrideWithValue(_user()),
          taskRepositoryProvider.overrideWithValue(taskRepository),
          taskNotificationSchedulerProvider
              .overrideWithValue(_NoopTaskNotificationScheduler()),
          predictionAttributionServiceProvider.overrideWithValue(
            _FakePredictionAttributionService(),
          ),
          appEventStreamServiceProvider.overrideWithValue(
            _FakeAppEventStreamService(),
          ),
        ],
        child: const _TaskGalaxyHarness(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('mastery:20'), findsOneWidget);
    expect(find.text('portfolio:1/0'), findsOneWidget);
    expect(find.text('achievement:locked'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('complete-task')));
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('mastery:80'), findsOneWidget);
    expect(find.text('portfolio:0/1'), findsOneWidget);
    expect(find.text('achievement:unlocked'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
    GalaxyPerformanceMonitor.instance.stopMonitoring();
    PerformanceService.instance.stopMonitoring();
  });

  testWidgets('B. repair task insertion refreshes plan detail automatically',
      (tester) async {
    final planRepository = _MutablePlanRepository(_plan(taskCount: 1));
    final errorRepository = _FakeErrorBookRepository(
      onSubmitReview: () {
        planRepository.plan = _plan(taskCount: 2);
      },
    );

    await tester.pumpWidget(
      _buildApp(
        overrides: <Override>[
          planRepositoryProvider.overrideWithValue(planRepository),
          errorBookRepositoryProvider.overrideWithValue(errorRepository),
        ],
        child: const _PlanRepairHarness(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('tasks:1'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('submit-review-plan')));
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('tasks:2'), findsOneWidget);
  });

  testWidgets('B2. error review bumps galaxy refresh trigger', (tester) async {
    final errorRepository = _FakeErrorBookRepository(onSubmitReview: () {});

    await tester.pumpWidget(
      _buildApp(
        overrides: <Override>[
          errorBookRepositoryProvider.overrideWithValue(errorRepository),
        ],
        child: const _ErrorReviewGalaxyHarness(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('galaxy-trigger:0'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('submit-review-galaxy')));
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('galaxy-trigger:1'), findsOneWidget);
  });

  testWidgets('C. sprint completion pop refreshes learning portfolio',
      (tester) async {
    final repository =
        _MutableExamSprintRepository(_portfolio(status: 'active'));

    await tester.pumpWidget(
      _buildApp(
        overrides: <Override>[
          examSprintRepositoryProvider.overrideWithValue(repository),
          currentUserProvider.overrideWithValue(_user()),
        ],
        child: _PortfolioSyncHarness(
          onOpenCompletion: () {
            repository.portfolio = _portfolio(status: 'completed');
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('active:1 completed:0'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('open-sprint-completion')));
    await tester.pumpAndSettle();

    Navigator.of(
      tester.element(find.byType(SprintCompletionScreen)),
    ).pop();
    await tester.pumpAndSettle();

    expect(find.text('active:0 completed:1'), findsOneWidget);
  });

  testWidgets('D. achievement unlock event refreshes achievement UI',
      (tester) async {
    final events = StreamController<dynamic>.broadcast();
    addTearDown(events.close);
    final repository = _MutableAchievementRepository();

    await tester.pumpWidget(
      _buildApp(
        overrides: <Override>[
          achievementRepositoryProvider.overrideWithValue(repository),
          communityEventsStreamProvider.overrideWithValue(events.stream),
        ],
        child: const _AchievementEventHarness(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('locked'), findsOneWidget);

    repository.unlock();
    events.add(<String, dynamic>{
      'type': 'achievement_unlock',
      'achievement_data': <String, dynamic>{
        'achievement_id': 'ach-1',
      },
    });
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('unlocked'), findsOneWidget);
  });

  testWidgets('E. weekly narrative card refreshes after learning action',
      (tester) async {
    final narrativeRepository = _MutableGrowthNarrativeRepository(
      _narrative('上周故事', '2026-04-14', '2026-04-20'),
    );
    final errorRepository = _FakeErrorBookRepository(
      onSubmitReview: () {
        narrativeRepository.current =
            _narrative('本周故事', '2026-04-21', '2026-04-27');
      },
    );

    await tester.pumpWidget(
      _buildApp(
        overrides: <Override>[
          growthNarrativeRepositoryProvider
              .overrideWithValue(narrativeRepository),
          errorBookRepositoryProvider.overrideWithValue(errorRepository),
        ],
        child: const _WeeklyNarrativeHarness(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('上周故事'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('submit-review-narrative')));
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('本周故事'), findsOneWidget);
  });
}

Widget _buildApp({
  required List<Override> overrides,
  required Widget child,
}) {
  return ProviderScope(
    overrides: overrides,
    child: MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: child,
    ),
  );
}

class _TaskGalaxyHarness extends ConsumerStatefulWidget {
  const _TaskGalaxyHarness();

  @override
  ConsumerState<_TaskGalaxyHarness> createState() => _TaskGalaxyHarnessState();
}

class _TaskGalaxyHarnessState extends ConsumerState<_TaskGalaxyHarness> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(ref.read(galaxyProvider.notifier).loadGalaxy());
    });
  }

  @override
  Widget build(BuildContext context) {
    final galaxy = ref.watch(galaxyProvider);
    final portfolio = ref.watch(learningPortfolioProvider);
    final achievement = ref.watch(achievementProvider);
    final mastery =
        galaxy.nodes.isEmpty ? 'loading' : '${galaxy.nodes.first.masteryScore}';
    final portfolioLabel = portfolio.maybeWhen(
      data: (data) => '${data.activeCount}/${data.completedCount}',
      orElse: () => 'loading',
    );
    final achievementLabel = achievement.achievements.isNotEmpty &&
            achievement.achievements.first.isUnlocked
        ? 'unlocked'
        : 'locked';
    return Scaffold(
      body: Column(
        children: <Widget>[
          Text('mastery:$mastery'),
          Text('portfolio:$portfolioLabel'),
          Text('achievement:$achievementLabel'),
          ElevatedButton(
            key: const ValueKey('complete-task'),
            onPressed: () {
              unawaited(
                ref.read(taskListProvider.notifier).completeTask(
                      'task-1',
                      25,
                      'done',
                    ),
              );
            },
            child: const Text('complete'),
          ),
        ],
      ),
    );
  }
}

class _PlanRepairHarness extends ConsumerWidget {
  const _PlanRepairHarness();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planAsync = ref.watch(planDetailProvider('plan-1'));
    return Scaffold(
      body: Column(
        children: <Widget>[
          planAsync.when(
            data: (plan) => Text('tasks:${plan.tasks?.length ?? 0}'),
            loading: () => const Text('loading'),
            error: (error, stackTrace) => Text('error:$error'),
          ),
          ElevatedButton(
            key: const ValueKey('submit-review-plan'),
            onPressed: () {
              unawaited(
                ref.read(errorOperationsProvider.notifier).submitReview(
                      errorId: 'error-1',
                      performance: 'remembered',
                    ),
              );
            },
            child: const Text('submit'),
          ),
        ],
      ),
    );
  }
}

class _ErrorReviewGalaxyHarness extends ConsumerWidget {
  const _ErrorReviewGalaxyHarness();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final trigger = ref.watch(galaxyRefreshTriggerProvider);
    return Scaffold(
      body: Column(
        children: <Widget>[
          Text('galaxy-trigger:$trigger'),
          ElevatedButton(
            key: const ValueKey('submit-review-galaxy'),
            onPressed: () {
              unawaited(
                ref.read(errorOperationsProvider.notifier).submitReview(
                      errorId: 'error-galaxy',
                      performance: 'remembered',
                    ),
              );
            },
            child: const Text('submit'),
          ),
        ],
      ),
    );
  }
}

class _PortfolioSyncHarness extends ConsumerWidget {
  const _PortfolioSyncHarness({required this.onOpenCompletion});

  final VoidCallback onOpenCompletion;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final portfolioAsync = ref.watch(learningPortfolioProvider);
    return Scaffold(
      body: Column(
        children: <Widget>[
          portfolioAsync.when(
            data: (portfolio) => Text(
              'active:${portfolio.activeCount} completed:${portfolio.completedCount}',
            ),
            loading: () => const Text('loading'),
            error: (error, stackTrace) => Text('error:$error'),
          ),
          ElevatedButton(
            key: const ValueKey('open-sprint-completion'),
            onPressed: () async {
              onOpenCompletion();
              await Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const SprintCompletionScreen(
                    planId: 'plan-1',
                    initialSummary: SprintCompletionSummary(
                      masteredNodesCount: 12,
                      repairedErrorsCount: 3,
                      completedTasksCount: 7,
                      strongestArea: 'TCP',
                      growthArea: 'IP',
                    ),
                  ),
                ),
              );
            },
            child: const Text('open'),
          ),
        ],
      ),
    );
  }
}

class _WeeklyNarrativeHarness extends ConsumerWidget {
  const _WeeklyNarrativeHarness();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      body: Column(
        children: <Widget>[
          const Expanded(child: WeeklyGrowthNarrativeCard()),
          ElevatedButton(
            key: const ValueKey('submit-review-narrative'),
            onPressed: () {
              unawaited(
                ref.read(errorOperationsProvider.notifier).submitReview(
                      errorId: 'error-2',
                      performance: 'fuzzy',
                    ),
              );
            },
            child: const Text('submit'),
          ),
        ],
      ),
    );
  }
}

class _AchievementEventHarness extends ConsumerWidget {
  const _AchievementEventHarness();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(achievementEventConsumerProvider);
    final state = ref.watch(achievementProvider);
    final label = state.isLoading || state.achievements.isEmpty
        ? 'loading'
        : (state.achievements.first.isUnlocked ? 'unlocked' : 'locked');
    return Scaffold(
      body: Center(child: Text(label)),
    );
  }
}

TaskModel _task(String id) {
  final now = DateTime.utc(2026, 4, 25, 9);
  return TaskModel(
    id: id,
    userId: 'user-1',
    title: '任务',
    type: TaskType.learning,
    tags: const <String>['day:1'],
    estimatedMinutes: 25,
    difficulty: 2,
    energyCost: 1,
    status: TaskStatus.pending,
    priority: 1,
    createdAt: now,
    updatedAt: now,
  );
}

GalaxyNodeModel _node(String id, int mastery) => GalaxyNodeModel(
      id: id,
      name: '节点$id',
      importance: 3,
      sector: SectorEnum.tech,
      isUnlocked: true,
      masteryScore: mastery,
      description: '描述',
      positionX: 100,
      positionY: 100,
    );

PlanModel _plan({required int taskCount}) {
  final now = DateTime.utc(2026, 4, 25, 9);
  final tasks = List<TaskModel>.generate(
    taskCount,
    (int index) => TaskModel(
      id: 'task-$index',
      userId: 'user-1',
      planId: 'plan-1',
      title: index == taskCount - 1 && taskCount > 1 ? '错题补强' : '常规任务$index',
      type: index == taskCount - 1 && taskCount > 1
          ? TaskType.errorFix
          : TaskType.learning,
      tags: index == taskCount - 1 && taskCount > 1
          ? const <String>['targeted_repair']
          : const <String>['day:1'],
      estimatedMinutes: 20,
      difficulty: 2,
      energyCost: 1,
      guideJson: index == taskCount - 1 && taskCount > 1
          ? const <String, dynamic>{'task_kind': 'targeted_repair'}
          : const <String, dynamic>{},
      status: TaskStatus.pending,
      priority: 1,
      createdAt: now,
      updatedAt: now,
    ),
  );

  return PlanModel(
    id: 'plan-1',
    userId: 'user-1',
    name: '计划',
    type: PlanType.sprint,
    dailyAvailableMinutes: 45,
    masteryLevel: 0.3,
    progress: 0.2,
    isActive: true,
    createdAt: now,
    updatedAt: now,
    tasks: tasks,
    dayHighlights: PlanDayHighlights(
      day: 1,
      recommendation: '先做关键任务',
      tasks: tasks,
    ),
  );
}

LearningPortfolioResult _portfolio({required String status}) {
  final entry = LearningPortfolioEntry(
    planId: 'plan-1',
    planName: '7天冲刺',
    subject: '计算机网络',
    sprintMode: 'seven_day_survival',
    status: status,
    masteredNodesCount: 12,
    startedAt: DateTime.utc(2026, 4, 20),
    completedAt: status == 'completed' ? DateTime.utc(2026, 4, 26, 20) : null,
    targetDate: DateTime.utc(2026, 4, 26),
    progress: status == 'completed' ? 1.0 : 0.7,
    strongestArea: 'TCP',
    growthArea: 'IP',
  );
  return LearningPortfolioResult(
    entries: <LearningPortfolioEntry>[entry],
    totalMasteredNodes: 12,
    activeCount: status == 'active' ? 1 : 0,
    completedCount: status == 'completed' ? 1 : 0,
    plannedCount: 0,
  );
}

UserModel _user() {
  final now = DateTime.utc(2026, 4, 25, 9);
  return UserModel(
    id: 'user-1',
    username: 'tester',
    email: 'tester@example.com',
    flameLevel: 1,
    flameBrightness: 0.5,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    createdAt: now,
    updatedAt: now,
  );
}

WeeklyGrowthNarrative _narrative(
  String period,
  String weekStart,
  String weekEnd,
) {
  return WeeklyGrowthNarrative(
    period: period,
    weekStart: weekStart,
    weekEnd: weekEnd,
    body: '$period 的总结',
    sentences: <String>['$period 的总结'],
    highlights: <String>['$period 的总结'],
    biggestImprovement: const <String, dynamic>{},
    nextWeekSuggestion: '',
    dataPoints: const <String, dynamic>{'study_days': 3},
    sourceCounts: const <String, int>{'study_days': 3},
    isPlaceholder: false,
    generatedAt: '2026-04-25T10:00:00',
  );
}

class _FakeTaskRepository extends TaskRepository {
  _FakeTaskRepository({
    required this.initialTask,
    required this.onComplete,
  }) : super(_NoopApiClient());

  final TaskModel initialTask;
  final VoidCallback onComplete;

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 10,
  }) async =>
      PaginatedResponse<TaskModel>(
        items: <TaskModel>[initialTask],
        total: 1,
        page: page,
        pageSize: pageSize,
      );

  @override
  Future<List<TaskModel>> getTodayTasks() async => <TaskModel>[initialTask];

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      <TaskModel>[];

  @override
  Future<TaskCompletionResult> completeTask(
    String id,
    int minutes,
    String? note,
  ) async {
    onComplete();
    final now = DateTime.utc(2026, 4, 25, 10);
    final updated = initialTask.copyWith(
      status: TaskStatus.completed,
      actualMinutes: minutes,
      completedAt: now,
      updatedAt: now,
    );
    return TaskCompletionResult(
      task: updated.toJson(),
      galaxyUpdate: const <String, dynamic>{
        'node_id': 'node-1',
        'new_mastery': 80,
      },
    );
  }
}

class _FakeEnhancedGalaxyRepository implements EnhancedGalaxyRepository {
  _FakeEnhancedGalaxyRepository({
    required this.graphResult,
  });

  NetworkResult<GalaxyGraphResponse> graphResult;

  @override
  Future<NetworkResult<GalaxyGraphResponse>> getGraph({
    double zoomLevel = 1.0,
    bool forceRefresh = false,
  }) async =>
      graphResult;

  @override
  Future<NetworkResult<GalaxyGraphResponse>> getGraphForViewport({
    required Rect viewport,
  }) async =>
      graphResult;

  @override
  Future<NetworkResult<UserGalaxyContribution>> getContributionStats() async =>
      NetworkResult.failure(GalaxyError.unknown('unused'));

  @override
  Future<NetworkResult<void>> updateNodePositions(
    Map<String, Offset> positions,
  ) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<void>> updateNodePosition(
    String nodeId,
    Offset position,
  ) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<Map<String, dynamic>>> updateNodeMastery(
    String nodeId, {
    required int mastery,
    String reason = 'manual_update',
  }) async =>
      NetworkResult.success(<String, dynamic>{
        'node_id': nodeId,
        'new_mastery': mastery,
      });

  @override
  Stream<SSEEvent> getGalaxyEventsStream({String? lastEventId}) =>
      const Stream<SSEEvent>.empty();

  @override
  Future<NetworkResult<void>> sparkNode(String id) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<void>> toggleFavorite(String nodeId) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<void>> pauseDecay(String nodeId, bool pause) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<KnowledgeDetailResponse>> getNodeDetail(
    String nodeId,
  ) async =>
      NetworkResult.failure(GalaxyError.unknown('unused'));

  @override
  Future<NetworkResult<GalaxyNodeHistory>> getNodeHistory(
    String nodeId, {
    String? packId,
  }) async =>
      NetworkResult.failure(GalaxyError.unknown('unused'));

  @override
  Future<NetworkResult<KnowledgeDetailResponse?>> predictNextNode() async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<List<GalaxySearchResult>>> searchNodes(
    String query,
  ) async =>
      NetworkResult.success(const <GalaxySearchResult>[]);

  @override
  Future<NetworkResult<NodeChunksResponse>> getNodeSourceChunks(
    String nodeId, {
    int page = 1,
    int pageSize = 100,
  }) async =>
      NetworkResult.failure(GalaxyError.unknown('Not implemented'));

  @override
  void clearCache() {}

  @override
  CircuitState get circuitBreakerState => CircuitState.closed;

  @override
  void resetCircuitBreaker() {}

  @override
  Map<String, CacheStats> get cacheStats => const <String, CacheStats>{};
}

class _MutablePlanRepository extends PlanRepository {
  _MutablePlanRepository(this.plan) : super(_NoopApiClient());

  PlanModel plan;

  @override
  Future<PlanModel> getPlan(String id) async => plan;

  @override
  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) async =>
      <PlanModel>[plan];

  @override
  Future<List<PlanModel>> getActivePlans() async => <PlanModel>[plan];

  @override
  Future<PlanPhaseBundle> getPlanPhases(String planId) async => PlanPhaseBundle(
        planCardId: null,
        currentPhaseCardId: null,
        progressMode: 'legacy',
        weightedProgress: null,
        phases: const <PlanPhaseModel>[],
      );
}

class _FakeErrorBookRepository extends ErrorBookRepository {
  _FakeErrorBookRepository({required this.onSubmitReview}) : super(Dio());

  final VoidCallback onSubmitReview;

  @override
  Future<ErrorRecord> submitReview({
    required String errorId,
    required String performance,
    int? timeSpentSeconds,
  }) async {
    onSubmitReview();
    final now = DateTime.utc(2026, 4, 25, 10);
    return ErrorRecord(
      id: errorId,
      questionText: '题目',
      userAnswer: '答案',
      correctAnswer: '正确答案',
      subject: 'math',
      masteryLevel: 0.8,
      reviewCount: 2,
      createdAt: now,
      updatedAt: now,
    );
  }
}

class _MutableExamSprintRepository extends ExamSprintRepository {
  _MutableExamSprintRepository(this.portfolio) : super(_NoopApiClient());

  LearningPortfolioResult portfolio;

  @override
  Future<LearningPortfolioResult> fetchLearningPortfolio({
    String? userId,
    int page = 1,
    int pageSize = 20,
  }) async =>
      portfolio;
}

class _MutableAchievementRepository extends AchievementRepository {
  _MutableAchievementRepository() : super(_NoopApiClient());

  bool _isUnlocked = false;

  void unlock() {
    _isUnlocked = true;
  }

  @override
  Future<AchievementListResponse> getAchievements({
    String? category,
    AchievementRarity? rarity,
    bool includeHidden = false,
    bool includeInactive = false,
  }) async {
    return AchievementListResponse(
      achievements: <AchievementWithProgress>[
        AchievementWithProgress(
          achievement: AchievementModel(
            id: 'ach-1',
            name: _isUnlocked ? 'unlocked' : 'locked',
            type: AchievementType.milestone,
            rarity: AchievementRarity.common,
            createdAt: DateTime.utc(2026, 4, 1),
            updatedAt: DateTime.utc(2026, 4, 1),
          ),
          userProgress: UserAchievementProgress(
            achievementId: 'ach-1',
            progress: _isUnlocked ? 1 : 0,
            progressValue: _isUnlocked ? 1 : 0,
            progressTarget: 1,
            unlockedAt: _isUnlocked ? DateTime.utc(2026, 4, 25, 10) : null,
          ),
          progressPercentage: _isUnlocked ? 100 : 0,
          isUnlocked: _isUnlocked,
        ),
      ],
      totalAchievements: 1,
      totalUnlocked: _isUnlocked ? 1 : 0,
      categories: const <String, dynamic>{},
    );
  }

  @override
  Future<AchievementStats> getAchievementStats() async => AchievementStats(
        totalAchievements: 1,
        unlockedCount: _isUnlocked ? 1 : 0,
        unlockedPercentage: _isUnlocked ? 100 : 0,
        commonCount: 1,
        rareCount: 0,
        epicCount: 0,
        legendaryCount: 0,
        hiddenFound: 0,
        currentStreak: 0,
        totalPhotons: 0,
      );

  @override
  Future<StreakStats> getStreakStats() async => StreakStats(
        currentStreak: 0,
        maxStreak: 0,
        longestStreak: 0,
        freezeCharges: 0,
        maxFreezeCharges: 3,
        totalCheckinDays: 0,
      );

  @override
  Future<GalaxySkinListResponse> getGalaxySkins() async =>
      GalaxySkinListResponse(
        equippedSkinId: null,
        skins: const <GalaxySkin>[],
      );

  @override
  Future<List<UserTitle>> getTitles() async => const <UserTitle>[];

  @override
  Future<SparkContract?> getContractStatus() async => null;

  @override
  Future<AchievementMapData> getAchievementMap() async => AchievementMapData(
        nodes: const <AchievementMapNode>[],
        connections: const <Map<String, dynamic>>[],
        categories: const <Map<String, dynamic>>[],
      );
}

class _MutableGrowthNarrativeRepository extends GrowthNarrativeRepository {
  _MutableGrowthNarrativeRepository(this.current) : super(_NoopApiClient());

  WeeklyGrowthNarrative current;

  @override
  Future<WeeklyGrowthNarrative> getWeeklyNarrative() async => current;
}

class _NoopTaskNotificationScheduler extends TaskNotificationScheduler {
  _NoopTaskNotificationScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );

  @override
  Future<void> cancelTaskReminders(String taskId) async {}

  @override
  Future<List<int>> scheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async =>
      <int>[];

  @override
  Future<List<int>> rescheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async =>
      <int>[];
}

class _FakePredictionAttributionService extends PredictionAttributionService {
  @override
  Future<Map<String, dynamic>?> consumeForExecution({
    required String executionType,
    String? entityType,
    String? entityId,
  }) async =>
      null;
}

class _FakeAppEventStreamService extends AppEventStreamService {
  _FakeAppEventStreamService() : super(_UnusedRef(), _NoopApiClient());

  @override
  Future<void> recordEntityExecution({
    required String entityType,
    required String entityId,
    required String actionType,
    required String source,
    Map<String, dynamic>? payload,
  }) async {}
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedRef implements Ref<Object?> {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported provider read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
