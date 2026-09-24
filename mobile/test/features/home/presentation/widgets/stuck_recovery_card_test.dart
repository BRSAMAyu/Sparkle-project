import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_card.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/home/presentation/providers/stuck_recovery_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/stuck_recovery_card.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// J-05 ·「我卡住了」旗舰恢复旅程——中断回流最小闭环链路测试。
///
/// 覆盖：停滞检测（纯函数）→ 首页卡片可见性守门（非停滞/执行中/未认证
/// 不可见）→ CTA 最小重启动作（resume + 置执行态 + 进执行屏）→ 完成
/// 正反馈（reconnected 相 → ack 归零）→「暂不」本会话硬关。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
  });

  group('findStalledTask（停滞检测纯函数）', () {
    final now = DateTime(2026, 9, 22, 12);

    test('stale inProgress task is detected', () {
      final task = _task(
        id: 't1',
        status: TaskStatus.inProgress,
        updatedAt: now.subtract(const Duration(hours: 50)),
      );
      expect(findStalledTask([task], now: now)?.id, 't1');
    });

    test('fresh inProgress task is not stalled', () {
      final task = _task(
        id: 't2',
        status: TaskStatus.inProgress,
        updatedAt: now.subtract(const Duration(hours: 2)),
      );
      expect(findStalledTask([task], now: now), isNull);
    });

    test('pending (never started) is never stalled, however old', () {
      final task = _task(
        id: 't3',
        status: TaskStatus.pending,
        updatedAt: now.subtract(const Duration(days: 30)),
      );
      expect(findStalledTask([task], now: now), isNull);
    });

    test('completed / abandoned are excluded', () {
      final tasks = [
        _task(
          id: 't4',
          status: TaskStatus.completed,
          updatedAt: now.subtract(const Duration(days: 3)),
        ),
        _task(
          id: 't5',
          status: TaskStatus.abandoned,
          updatedAt: now.subtract(const Duration(days: 3)),
        ),
      ];
      expect(findStalledTask(tasks, now: now), isNull);
    });

    test('stale paused/stuck count; picks the most recently touched one', () {
      final tasks = [
        _task(
          id: 'older',
          status: TaskStatus.paused,
          updatedAt: now.subtract(const Duration(days: 10)),
        ),
        _task(
          id: 'newer',
          status: TaskStatus.stuck,
          updatedAt: now.subtract(const Duration(days: 3)),
        ),
        _task(
          id: 'fresh',
          status: TaskStatus.inProgress,
          updatedAt: now.subtract(const Duration(minutes: 10)),
        ),
      ];
      expect(findStalledTask(tasks, now: now)?.id, 'newer');
    });

    test('pausedAt later than updatedAt is honored as last touch', () {
      final task = _task(
        id: 't6',
        status: TaskStatus.paused,
        updatedAt: now.subtract(const Duration(days: 5)),
        pausedAt: now.subtract(const Duration(minutes: 10)),
      );
      expect(findStalledTask([task], now: now), isNull);
    });
  });

  group('StuckRecoveryCard（首页承接卡链路）', () {
    testWidgets('stalled task renders recovery card with empathy copy',
        (tester) async {
      final harness = await _pump(
        tester,
        tasks: [
          _task(
            id: 'stale-1',
            title: '积分换元重讲',
            status: TaskStatus.inProgress,
            updatedAt: DateTime.now().subtract(const Duration(hours: 50)),
          ),
        ],
      );

      expect(find.byType(SparkleCard), findsOneWidget);
      expect(find.text('回来就好，任务还在'), findsOneWidget);
      // 共情行含任务名与中断天数（50h → 2 天）。
      expect(find.textContaining('积分换元重讲'), findsOneWidget);
      expect(find.textContaining('2 天'), findsOneWidget);
      expect(find.text('先做 5 分钟'), findsOneWidget);
      expect(find.text('暂不'), findsOneWidget);
      harness.container.dispose();
    });

    testWidgets('non-stalled user sees nothing (fresh task)', (tester) async {
      final harness = await _pump(
        tester,
        tasks: [
          _task(
            id: 'fresh-1',
            title: '刚碰过的任务',
            status: TaskStatus.inProgress,
            updatedAt: DateTime.now().subtract(const Duration(minutes: 30)),
          ),
        ],
      );

      expect(find.byType(SparkleCard), findsNothing);
      expect(find.text('先做 5 分钟'), findsNothing);
      harness.container.dispose();
    });

    testWidgets('hidden while a task is executing (never-interrupt rule)',
        (tester) async {
      final activeTask = _task(
        id: 'active-9',
        title: '正在执行的任务',
        status: TaskStatus.inProgress,
        updatedAt: DateTime.now(),
      );
      final harness = await _pump(
        tester,
        tasks: [
          _task(
            id: 'stale-2',
            title: '积分换元重讲',
            status: TaskStatus.paused,
            updatedAt: DateTime.now().subtract(const Duration(days: 4)),
          ),
        ],
        activeTask: activeTask,
      );

      expect(find.byType(SparkleCard), findsNothing);
      harness.container.dispose();
    });

    testWidgets('hidden when unauthenticated', (tester) async {
      final harness = await _pump(
        tester,
        authenticated: false,
        tasks: [
          _task(
            id: 'stale-3',
            title: '积分换元重讲',
            status: TaskStatus.inProgress,
            updatedAt: DateTime.now().subtract(const Duration(days: 4)),
          ),
        ],
      );

      expect(find.byType(SparkleCard), findsNothing);
      harness.container.dispose();
    });

    testWidgets('CTA restarts the task and walks into execution screen',
        (tester) async {
      final harness = await _pump(
        tester,
        tasks: [
          _task(
            id: 'stale-4',
            title: '积分换元重讲',
            status: TaskStatus.stuck,
            updatedAt: DateTime.now().subtract(const Duration(days: 3)),
          ),
        ],
      );

      await tester.tap(find.text('先做 5 分钟'));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(seconds: 1));

      // resume（stuck → 需要恢复）被调用，且进入执行屏。
      expect(harness.notifier.resumedTaskIds, ['stale-4']);
      expect(find.text('J05_EXEC_STUB'), findsOneWidget);
      // 执行态已置位（next_actions_card 同款：activeTaskProvider 置位后进屏）。
      expect(
        harness.container.read(activeTaskProvider)?.id,
        'stale-4',
      );
      harness.container.dispose();
    });

    testWidgets('completing the restarted task closes the loop with '
        'positive feedback, ack resets', (tester) async {
      final harness = await _pump(
        tester,
        tasks: [
          _task(
            id: 'stale-5',
            title: '积分换元重讲',
            status: TaskStatus.stuck,
            updatedAt: DateTime.now().subtract(const Duration(days: 3)),
          ),
        ],
      );

      await tester.tap(find.text('先做 5 分钟'));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(seconds: 1));
      expect(find.text('J05_EXEC_STUB'), findsOneWidget);

      // 执行屏内完成任务（completeTask 乐观置位任务列表 → 控制器收到），
      // 然后按真实完成流 pop 回 home。
      harness.notifier.completeLocally('stale-5');
      await tester.pump();
      await tester.tap(find.text('J05_EXEC_STUB'));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(seconds: 1));

      // 回到 home——正反馈相可见（执行守门只挡真正在飞的任务）。
      expect(find.text('重新接上了'), findsOneWidget);
      expect(find.textContaining('积分换元重讲'), findsOneWidget);

      await tester.tap(find.text('好的'));
      await tester.pump();
      expect(find.text('重新接上了'), findsNothing);
      harness.container.dispose();
    });

    testWidgets('dismiss keeps the card hidden for the rest of the session',
        (tester) async {
      final harness = await _pump(
        tester,
        tasks: [
          _task(
            id: 'stale-6',
            title: '积分换元重讲',
            status: TaskStatus.paused,
            updatedAt: DateTime.now().subtract(const Duration(days: 2)),
          ),
        ],
      );

      await tester.tap(find.text('暂不'));
      await tester.pump();
      expect(find.byType(SparkleCard), findsNothing);

      // 会话内任务列表再变化（刷新）也不复活——「暂不」本会话硬关。
      harness.notifier.touchList();
      await tester.pump();
      expect(find.byType(SparkleCard), findsNothing);
      harness.container.dispose();
    });
  });
}

class _Harness {
  _Harness(this.container, this.notifier);

  final ProviderContainer container;
  final _StaticTaskListNotifier notifier;
}

Future<_Harness> _pump(
  WidgetTester tester, {
  required List<TaskModel> tasks,
  bool authenticated = true,
  TaskModel? activeTask,
}) async {
  final notifier = _StaticTaskListNotifier(tasks);
  final router = GoRouter(
    initialLocation: '/home',
    routes: [
      GoRoute(
        path: '/home',
        builder: (_, __) => const Scaffold(
          body: Center(child: StuckRecoveryCard()),
        ),
      ),
      GoRoute(
        path: '/tasks/:id/execute',
        builder: (context, _) => Scaffold(
          body: Center(
            // 真实执行流完成任务后 pop 回 home——stub 同款。
            child: TextButton(
              onPressed: () => context.go('/home'),
              child: const Text('J05_EXEC_STUB'),
            ),
          ),
        ),
      ),
    ],
  );

  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith(
        (ref) => _FakeAuthNotifier(
          AuthState(
            isAuthenticated: authenticated,
            user: authenticated ? _buildUser() : null,
          ),
        ),
      ),
      taskListProvider.overrideWith((ref) => notifier),
      if (activeTask != null)
        activeTaskProvider.overrideWith((ref) => activeTask),
    ],
  );

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: testMaterialApp(routerConfig: router),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 100));
  return _Harness(container, notifier);
}

TaskModel _task({
  required String id,
  required TaskStatus status,
  required DateTime updatedAt,
  String title = '任务',
  DateTime? pausedAt,
}) =>
    TaskModel(
      id: id,
      userId: 'user-1',
      title: title,
      type: TaskType.learning,
      tags: const [],
      estimatedMinutes: 30,
      difficulty: 2,
      energyCost: 2,
      status: status,
      priority: 2,
      createdAt: updatedAt.subtract(const Duration(days: 1)),
      updatedAt: updatedAt,
      pausedAt: pausedAt,
    );

UserModel _buildUser() => UserModel(
      id: 'j05-recovery-user',
      username: 'j05_tester',
      email: 'j05@example.com',
      nickname: 'J05 Tester',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _StaticTaskListNotifier extends TaskNotifier {
  _StaticTaskListNotifier(List<TaskModel> tasks)
      : super(
          _NoopTaskRepository(),
          TaskNotificationScheduler(
            NotificationService(_UnusedRef(), autoInitialize: false),
            TaskNotificationIdMapper(),
          ),
          _UnusedRef(),
        ) {
    state = TaskListState(tasks: tasks, todayTasks: tasks);
  }

  final resumedTaskIds = <String>[];

  @override
  Future<void> resumeTask(String id) async {
    resumedTaskIds.add(id);
    // 模拟仓库行为：状态置回进行中、updatedAt 刷新。
    _patch(
      id,
      (task) => task.copyWith(
        status: TaskStatus.inProgress,
        updatedAt: DateTime.now(),
      ),
    );
  }

  void completeLocally(String id) {
    _patch(
      id,
      (task) => task.copyWith(
        status: TaskStatus.completed,
        completedAt: DateTime.now(),
      ),
    );
  }

  /// 触发一次任务列表状态发布（控制器应保持「暂不」的会话硬关）。
  void touchList() {
    state = state.copyWith(tasks: [...state.tasks]);
  }

  void _patch(String id, TaskModel Function(TaskModel) transform) {
    final tasks = <TaskModel>[];
    TaskModel? patched;
    for (final task in state.tasks) {
      if (task.id != id) {
        tasks.add(task);
      } else {
        patched = transform(task);
        tasks.add(patched);
      }
    }
    if (patched == null) return;
    final todayTasks = state.todayTasks
        .map((task) => task.id == id ? patched! : task)
        .toList();
    state = state.copyWith(tasks: tasks, todayTasks: todayTasks);
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

class _NoopTaskRepository extends TaskRepository {
  _NoopTaskRepository() : super(_NoopApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier(AuthState authState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = authState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _UnusedRef implements Ref<Object?> {
  @override
  T read<T>(ProviderListenable<T> provider) {
    // ApiClient 构造读 authInterceptorProvider（plan_provider_test 同款）。
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository()
      : super(
          _UnusedApiClient(),
          SecureTokenStorage(storage: _MemorySecureStorage()),
        );
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MemorySecureStorage implements FlutterSecureStorage {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
