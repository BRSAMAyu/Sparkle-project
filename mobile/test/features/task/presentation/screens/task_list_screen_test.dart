import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/screens/task_list_screen.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('task list shows guided empty state when there are no tasks', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          taskListProvider.overrideWith(
            (ref) => _RecoveryTaskNotifier(TaskListState()),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const TaskListScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('今天还没有待办事项'), findsOneWidget);
    expect(find.text('创建第一项任务'), findsOneWidget);
  });

  testWidgets('task list shows retry state and recovers after retry',
      (tester) async {
    // HYGIENE-DEBT（wt239 登记）修复：
    // 1) FAB 抢 tap——撤掉 900x1600 大视口（重试钮命中区被悬浮钮遮挡的根因），
    //    默认 800x600 下居中错误页的重试钮位于 FAB 命中区之外，真 tap 走用户路径；
    // 2) harness 缺 GoRouter——TaskListScreen 的返回/FAB/空态动作全走
    //    context.push/go/pop 扩展，testMaterialApp 挂上 router 配置（含存根路由），
    //    使 tap 路径下任何导航都合法可达，不再「GoRouter was not found」。
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => const TaskListScreen(),
        ),
        GoRoute(
          path: '/home',
          builder: (context, state) => const Text('home-stub'),
        ),
        GoRoute(
          path: '/tasks/new',
          builder: (context, state) => const Text('new-task-stub'),
        ),
        GoRoute(
          path: '/tasks/:id',
          builder: (context, state) =>
              Text('task-stub:${state.pathParameters['id']}'),
        ),
      ],
    );

    final notifier = _RecoveryTaskNotifier(
      TaskListState(error: UiErrorCategory.server),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          taskListProvider.overrideWith((ref) => notifier),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          routerConfig: router,
        ),
      ),
    );

    await tester.pump();
    // 让错误页的 SparkleStaggerItem 入场动画落定，重试钮进入可命中状态。
    await tester.pump(const Duration(milliseconds: 300));

    // N15/EE-G1 契约（A-SPEC3 改造#2）：原始异常文本不入 UI——错误经唯一
    // 映射 owner 人话化（'task list 500' 命中 500 → ERR-SERVER 人话）。
    // ERR-CANAL（9cbad7a9）后 [ERR-*] 码由 user_facing_error.dart 作为次级
    // 尾缀附加，TaskListScreen 走 uiErrorMessage 首读文案，不含码——断言
    // 与现行 lexicon owner 契约对齐。
    expect(find.textContaining('task list 500'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    // N15：类别经 lexicon owner 出人话（zh 测试环境映射「服务器出现问题」）。
    expect(find.textContaining('服务器出现问题'), findsOneWidget);
    expect(find.text('重试'), findsOneWidget);

    // 触发重试：真 tap 用户路径（不再直调 onRetry 回调的弱断言）。
    await tester.tap(find.text('重试'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(notifier.refreshCount, equals(1));
    expect(find.text('修复网络错误态'), findsOneWidget);
  });
}

class _RecoveryTaskNotifier extends TaskNotifier {
  _RecoveryTaskNotifier(TaskListState initial)
      : super(
          _FakeTaskRepository(),
          _NoopTaskNotificationScheduler(),
          _FakeRef(),
        ) {
    state = initial;
  }

  int refreshCount = 0;

  @override
  Future<void> loadTasks({TaskFilter? filter}) async {}

  @override
  Future<void> loadTodayTasks() async {}

  @override
  Future<void> loadRecommendedTasks() async {}

  @override
  Future<void> refreshTasks() async {
    refreshCount += 1;
    final now = DateTime.utc(2026, 4, 25);
    state = state.copyWith(
      clearError: true,
      tasks: [
        TaskModel(
          id: 'task-1',
          userId: 'user-1',
          title: '修复网络错误态',
          type: TaskType.learning,
          tags: const ['network'],
          estimatedMinutes: 25,
          difficulty: 2,
          energyCost: 1,
          status: TaskStatus.pending,
          priority: 1,
          createdAt: now,
          updatedAt: now,
        ),
      ],
    );
  }
}

class _FakeTaskRepository extends TaskRepository {
  _FakeTaskRepository() : super(_NoopApiClient());

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 20,
  }) async =>
      PaginatedResponse<TaskModel>(
        items: const <TaskModel>[],
        total: 0,
        page: page,
        pageSize: pageSize,
      );

  @override
  Future<List<TaskModel>> getTodayTasks() async => const <TaskModel>[];

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      const <TaskModel>[];
}

class _NoopTaskNotificationScheduler extends TaskNotificationScheduler {
  _NoopTaskNotificationScheduler()
      : super(
          NotificationService(_FakeRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_FakeRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
