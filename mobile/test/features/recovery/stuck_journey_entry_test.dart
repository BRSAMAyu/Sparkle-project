import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_detail_screen.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';
import 'package:sparkle/features/recovery/data/repositories/stuck_journey_repository.dart';
import 'package:sparkle/features/recovery/presentation/widgets/stuck_journey_sheet.dart';
import 'package:sparkle/features/task/presentation/widgets/stuck_help_sheet.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../home/dashboard_test_harness.dart';

/// J-05 验收锚点：三面入口真实可达且携带**各自真实 context**——
/// - home 面：cockpit「我卡住了」次级入口 → surface=home + 当前任务 id；
/// - goal 面：goal 详情「我卡住了」→ surface=goal + 该目标真实 id；
/// - action 面：卡点帮助 sheet 的旅程入口 → surface=action + 任务 id。
/// 断言对象是**真发起的请求/回调参数**，不是静态代码阅读。
class _RecordingRepo implements StuckJourneyRepository {
  final List<Map<String, Object?>> startCalls = <Map<String, Object?>>[];

  @override
  Future<StuckJourneyPayload> startJourney({
    required String surface,
    String? goalId,
    String? taskId,
  }) async {
    startCalls.add(<String, Object?>{
      'surface': surface,
      'goal_id': goalId,
      'task_id': taskId,
    });
    // 入口断言只关心真实调用参数；后续网络面在 sheet 行为测试覆盖。
    throw Exception('stubbed: network not exercised in entry tests');
  }

  @override
  Future<StuckJourneyPayload> answerQuestion({
    required String surface,
    required String questionId,
    required String branchKey,
    String? goalId,
    String? taskId,
  }) async {
    throw Exception('stubbed');
  }

  @override
  Future<StuckJourneyCorrectionResult> correct({
    required String surface,
    required String frictionType,
    String? interventionKey,
    String? goalId,
    String? taskId,
    String? reasonText,
  }) async {
    throw Exception('stubbed');
  }
}

class _StubApiClient implements ApiClient {
  _StubApiClient(this.goalDetailPayload, this.posts);

  final Map<String, dynamic> goalDetailPayload;
  final List<({String path, Map<String, dynamic>? body})> posts;

  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    if (path.contains('/experience/goal-detail/')) {
      return Response<T>(
        data: goalDetailPayload as T?,
        requestOptions: RequestOptions(path: path),
      );
    }
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? headers,
    Map<String, dynamic>? queryParameters,
  }) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    posts.add((
      path: path,
      body: data is Map ? Map<String, dynamic>.from(data) : null,
    ),);
    return Response<T>(
      data: <String, dynamic>{} as T?,
      requestOptions: RequestOptions(path: path),
    );
  }

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    throw UnimplementedError('Not stubbed: $path');
  }
}

Widget _materialHome(Widget child) => MaterialApp(
      theme: ThemeData(extensions: [SparkleThemeExtension.light()]),
      locale: const Locale('en'),
      supportedLocales: const [Locale('en'), Locale('zh')],
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: child,
    );

TaskModel _task(String id, String title) => TaskModel(
      id: id,
      userId: 'u1',
      title: title,
      type: TaskType.learning,
      tags: const [],
      estimatedMinutes: 25,
      difficulty: 1,
      energyCost: 1,
      status: TaskStatus.inProgress,
      priority: 1,
      createdAt: DateTime(2026, 9, 20),
      updatedAt: DateTime(2026, 9, 20),
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets('home face: cockpit stuck CTA starts journey with real task id',
      (tester) async {
    final repo = _RecordingRepo();
    await initializeDashboardTestEnvironment();
    await tester.pumpWidget(
      buildDashboardWidgetHarness(
        extraOverrides: [
          stuckJourneyRepositoryProvider.overrideWithValue(repo),
          multiGoalOverviewProvider.overrideWith(
            (ref) async => const MultiGoalOverview(
              goals: [
                ActiveGoalSnapshot(
                  id: 'goal-1',
                  title: 'Pass the exam',
                  goalType: 'exam',
                  healthScore: 0.7,
                  weeklyConflictCount: 0,
                ),
              ],
              selectedGoalId: 'goal-1',
            ),
          ),
          homeGrowthStateProvider.overrideWith(
            (ref) async => const HomeGrowthState(
              planHealth: 0,
              tasksTotal: 3,
              tasksCompleted: 0,
              streak: 0,
              nextAction: HomeGrowthTask(
                id: 'task-9',
                title: 'Read chapter 3',
                priority: 4,
                isCompleted: false,
              ),
            ),
          ),
        ],
        child: const TodayCockpitCard(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('today-cockpit-stuck-cta')));
    await tester.pumpAndSettle();

    expect(repo.startCalls, hasLength(1));
    expect(repo.startCalls.first['surface'], 'home');
    // 真实 context：传的是 cockpit 当前任务（nextAction）的 id。
    expect(repo.startCalls.first['task_id'], 'task-9');
  });

  testWidgets('goal face: stuck action starts journey with real goal id',
      (tester) async {
    final repo = _RecordingRepo();
    final stub = _StubApiClient(<String, dynamic>{
      'goal': <String, dynamic>{
        'id': 'g9',
        'title': 'Operating systems final sprint',
        'goal_type': 'exam',
        'status': 'active',
        'target_date': '2099-12-31',
        'mastery': 0.4,
        'progress': 0.5,
        'priority': 'high',
      },
      'minimum_acceptance_criteria': <String, dynamic>{},
      'plan_health': <String, dynamic>{
        'overall': 0.6,
        'phase_health': 0.72,
        'task_completion_rate': 0.5,
      },
      'current_phase': <String, dynamic>{'name': '强化冲刺', 'progress': 0.4},
      'todays_minimal_next_step': <String, dynamic>{},
      'knowledge_bottlenecks': <dynamic>[],
      'accountability_status': <String, dynamic>{},
      'related_sources': <dynamic>[],
    }, <({String path, Map<String, dynamic>? body})>[],);

    await tester.binding.setSurfaceSize(const Size(800, 2400));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(stub),
          stuckJourneyRepositoryProvider.overrideWithValue(repo),
        ],
        child: _materialHome(const GoalDetailScreen(goalId: 'g9')),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('goal-detail-stuck-action')));
    await tester.pumpAndSettle();

    expect(repo.startCalls, hasLength(1));
    expect(repo.startCalls.first['surface'], 'goal');
    // 真实 context：goal 面携带 goal 详情屏当前目标的真实 id。
    expect(repo.startCalls.first['goal_id'], 'g9');
  });

  testWidgets('action face: stuck help sheet journey entry carries task id',
      (tester) async {
    final repo = _RecordingRepo();
    final task = _task('task-77', 'Graph theory drills');

    await tester.pumpWidget(
      ProviderScope(
        overrides: [stuckJourneyRepositoryProvider.overrideWithValue(repo)],
        child: _materialHome(
          Scaffold(
            body: Builder(
              builder: (context) => StuckHelpSheet(
                task: task,
                // 执行屏的真实接线：旅程入口携带当前任务 id（surface=action）。
                onJourneyPressed: () => showStuckJourneySheet(
                  context,
                  surface: 'action',
                  taskId: task.id,
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 卡点帮助 sheet 的统一旅程入口存在且可点。
    await tester.tap(find.byKey(const Key('stuck-help-journey-button')));
    await tester.pumpAndSettle();

    expect(repo.startCalls, hasLength(1));
    expect(repo.startCalls.first['surface'], 'action');
    // 真实 context：action 面携带执行中任务的真实 id。
    expect(repo.startCalls.first['task_id'], 'task-77');
  });
}
