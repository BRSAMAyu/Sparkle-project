// N35（A-SPEC6）验收：离线写操作三态诚实——排队成功必须有排队的样子。
//
// 锁定不变量：
//   1. 离线 pause/resume（OfflineEnqueuedException）→ 本地乐观置位目标
//      状态 + syncStatus pending（待同步标记）+ 排队信号位；error 位
//      必须为 null（绝不把入队成功报成「出错了」）。
//   2. 离线 complete 保持乐观完成态 + 排队信号，绝不落 syncStatus failed。
//   3. N34：getTasksCached/getTodayTasksCached 的 fromCache/asOf 传导进
//      TaskListState（UI 挂「截至 X」stale 徽标的数据源）。
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StubScheduler extends TaskNotificationScheduler {
  _StubScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );
}

class _StubAttributionService extends PredictionAttributionService {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StubEventStreamService extends AppEventStreamService {
  _StubEventStreamService() : super(_UnusedRef(), _UnusedApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StubGalaxyRepository extends EnhancedGalaxyRepository {
  _StubGalaxyRepository() : super(_UnusedApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 所有生命周期操作都「离线入队成功」的仓库（回放端成熟、网络断）。
class _OfflineEnqueuingRepository extends TaskRepository {
  _OfflineEnqueuingRepository() : super(_UnusedApiClient());

  @override
  Future<TaskModel> pauseTask(String id, {String? reason}) async =>
      throw OfflineEnqueuedException('pauseTask queued for sync');

  @override
  Future<TaskModel> resumeTask(String id) async =>
      throw OfflineEnqueuedException('resumeTask queued for sync');

  @override
  Future<TaskModel> startTask(String id) async =>
      throw OfflineEnqueuedException('startTask queued for sync');

  @override
  Future<TaskModel> abandonTask(String id) async =>
      throw OfflineEnqueuedException('abandonTask queued for sync');

  @override
  Future<TaskCompletionResult> completeTask(
    String id,
    int? actualMinutes,
    String? note,
  ) async =>
      throw OfflineEnqueuedException('completeTask queued for sync');

  @override
  Future<CacheAwareResult<PaginatedResponse<TaskModel>>> getTasksCached({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      CacheAwareResult(
        PaginatedResponse<TaskModel>(
          items: [_seedTask()],
          total: 1,
          page: 1,
          pageSize: pageSize,
        ),
      );

  @override
  Future<CacheAwareResult<List<TaskModel>>> getTodayTasksCached() async =>
      CacheAwareResult<List<TaskModel>>([_seedTask()]);

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      <TaskModel>[];
}

/// 离线兜底走本地快照的仓库（N34 传导验收）。
class _SnapshotServingRepository extends _OfflineEnqueuingRepository {
  @override
  Future<CacheAwareResult<PaginatedResponse<TaskModel>>> getTasksCached({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      CacheAwareResult(
        PaginatedResponse<TaskModel>(
          items: [_seedTask()],
          total: 1,
          page: 1,
          pageSize: pageSize,
        ),
        fromCache: true,
        asOf: DateTime(2026, 9, 21, 22, 30),
      );

  @override
  Future<CacheAwareResult<List<TaskModel>>> getTodayTasksCached() async =>
      CacheAwareResult<List<TaskModel>>(
        [_seedTask()],
        fromCache: true,
        asOf: DateTime(2026, 9, 21, 22, 30),
      );
}

TaskModel _seedTask() => TaskModel(
      id: 'task-1',
      userId: 'user-1',
      title: '线代错题重做',
      type: TaskType.learning,
      tags: const [],
      estimatedMinutes: 30,
      difficulty: 2,
      energyCost: 1,
      priority: 1,
      status: TaskStatus.inProgress,
      createdAt: DateTime(2026, 9, 20),
      updatedAt: DateTime(2026, 9, 20),
    );

Future<TaskNotifier> _pumpNotifier(ProviderContainer container) async {
  final notifier = container.read(taskListProvider.notifier);
  // Let the constructor's parallel initial loads populate state.
  await Future<void>.delayed(const Duration(milliseconds: 60));
  return notifier;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues(const {});

  ProviderContainer buildContainer(TaskRepository repo) {
    final container = ProviderContainer(
      overrides: [
        taskRepositoryProvider.overrideWithValue(repo),
        taskNotificationSchedulerProvider.overrideWithValue(_StubScheduler()),
        predictionAttributionServiceProvider
            .overrideWithValue(_StubAttributionService()),
        appEventStreamServiceProvider
            .overrideWithValue(_StubEventStreamService()),
        enhancedGalaxyRepositoryProvider
            .overrideWithValue(_StubGalaxyRepository()),
      ],
    );
    return container;
  }

  group('N35 · 离线暂停/恢复的三态诚实', () {
    test('离线 pauseTask → UI 显示已暂停 + 待同步标记（非错误）', () async {
      final container = buildContainer(_OfflineEnqueuingRepository());
      addTearDown(container.dispose);
      final notifier = await _pumpNotifier(container);
      container.read(taskListProvider);

      await notifier.pauseTask('task-1', reason: '地铁断网');

      final state = container.read(taskListProvider);
      // 诚实三态：任务已置位为暂停 + 同步 pending（待同步标记）。
      final task = state.tasks.firstWhere((t) => t.id == 'task-1');
      expect(task.status, TaskStatus.paused);
      expect(task.syncStatus, TaskSyncStatus.pending);
      // 排队信号在位（UI 据此播报「已保存待同步」）。
      expect(state.offlineQueuedTaskId, 'task-1');
      expect(state.offlineQueuedOp, 'pause');
      // 绝不进 error 位——入队成功不是错误。
      expect(state.error, isNull);
      expect(state.isLoading, isFalse);
    });

    test('离线 resumeTask → UI 显示进行中 + 待同步标记（非错误）', () async {
      final container = buildContainer(_OfflineEnqueuingRepository());
      addTearDown(container.dispose);
      final notifier = await _pumpNotifier(container);

      await notifier.resumeTask('task-1');

      final state = container.read(taskListProvider);
      final task = state.tasks.firstWhere((t) => t.id == 'task-1');
      expect(task.status, TaskStatus.inProgress);
      expect(task.syncStatus, TaskSyncStatus.pending);
      expect(state.offlineQueuedTaskId, 'task-1');
      expect(state.offlineQueuedOp, 'resume');
      expect(state.error, isNull);
    });

    test('离线 startTask → UI 显示进行中 + 待同步标记（非错误）', () async {
      final container = buildContainer(_OfflineEnqueuingRepository());
      addTearDown(container.dispose);
      final notifier = await _pumpNotifier(container);

      await notifier.startTask('task-1');

      final state = container.read(taskListProvider);
      final task = state.tasks.firstWhere((t) => t.id == 'task-1');
      expect(task.status, TaskStatus.inProgress);
      expect(task.syncStatus, TaskSyncStatus.pending);
      expect(state.offlineQueuedOp, 'start');
      expect(state.error, isNull);
    });

    test('离线 abandonTask → UI 显示已放弃 + 待同步标记（非错误）', () async {
      final container = buildContainer(_OfflineEnqueuingRepository());
      addTearDown(container.dispose);
      final notifier = await _pumpNotifier(container);

      await notifier.abandonTask('task-1');

      final state = container.read(taskListProvider);
      final task = state.tasks.firstWhere((t) => t.id == 'task-1');
      expect(task.status, TaskStatus.abandoned);
      expect(task.syncStatus, TaskSyncStatus.pending);
      expect(state.offlineQueuedOp, 'abandon');
      expect(state.error, isNull);
    });

    test('离线 completeTask → 保持完成乐观态 + 排队信号，不标失败', () async {
      final container = buildContainer(_OfflineEnqueuingRepository());
      addTearDown(container.dispose);
      final notifier = await _pumpNotifier(container);

      final result = await notifier.completeTask('task-1', 42, null);

      // 无 TaskCompletionResult（离线无回执），但任务态必须诚实已排队。
      expect(result, isNull);
      final state = container.read(taskListProvider);
      final task = state.tasks.firstWhere((t) => t.id == 'task-1');
      expect(task.status, TaskStatus.completed);
      expect(task.syncStatus, TaskSyncStatus.pending,
          reason: '排队成功绝不能落 syncStatus.failed',);
      expect(state.offlineQueuedOp, 'complete');
      expect(state.error, isNull);
    });
  });

  group('N34 · 任务面快照溯源传导', () {
    test('断网快照读 → tasksFromCache/cachedAsOf 进状态（stale 徽标数据源）',
        () async {
      final container = buildContainer(_SnapshotServingRepository());
      addTearDown(container.dispose);
      await _pumpNotifier(container);

      final state = container.read(taskListProvider);
      expect(state.tasksFromCache, isTrue);
      expect(state.todayTasksFromCache, isTrue);
      expect(state.cachedAsOf, DateTime(2026, 9, 21, 22, 30));
      // 断网冷启动有数据（不为空）。
      expect(state.tasks, isNotEmpty);
      expect(state.todayTasks, isNotEmpty);
    });

    test('在线读（非快照）→ fromCache=false、asOf 为空', () async {
      final container = buildContainer(_OfflineEnqueuingRepository());
      addTearDown(container.dispose);
      await _pumpNotifier(container);

      final state = container.read(taskListProvider);
      expect(state.tasksFromCache, isFalse);
      expect(state.cachedAsOf, isNull);
    });
  });
}
