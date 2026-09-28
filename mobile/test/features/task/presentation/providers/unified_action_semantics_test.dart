// V4-U08 任务计划日历统一行动语义 —— 验收测试（每验收面一正一反）。
//
// 锁三条不变量：
//   验收1「四页面看到同 task/version；重复点击一次写入」：
//     任务/计划/日历/目标四个页面全部经由 taskListProvider（或目标页
//     GoalDetailNotifier 自有链）写入；同一任务的同一终态写在飞时，重复
//     点击合流为一次服务端写入；不同任务互不合流（守卫不过度吞写）。
//   验收2「改日程有键盘/按钮路径，不仅拖动」：
//     改期唯一写入口 rescheduleTaskDueDate——拖拽确认与按钮路径同链，
//     在飞时重复触发一次写入；写入后读模型（taskListProvider）同步可见。
//   验收3「计划时长不作为完成证据，删除/放弃不同语义」：
//     日历聚合专注时长只认实测 actualMinutes，估时不顶替（不造进度）；
//     放弃保留任务记录（仅置终态），删除移除条目——两条路径两种结局。
import 'dart:async';

import 'package:dio/dio.dart';
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
import 'package:sparkle/features/calendar/data/datasources/calendar_remote_datasource.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/calendar/presentation/providers/unified_calendar_provider.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/goal/presentation/providers/goal_detail_provider.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';

import '../../../../shared/i18n_test_helper.dart';

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Response<T> _okResponse<T>(String path, [Map<String, dynamic>? data]) =>
    Response<T>(
      requestOptions: RequestOptions(path: path),
      data: (data ?? const <String, dynamic>{}) as T,
    );

/// 目标页（goal 家族）用的假 API：GET 返回最小合法 goal-detail 读模型，
/// POST 按 path 计数；/complete 可用 [completeGate] 拴住在飞窗口。
class _GatedGoalApiClient implements ApiClient {
  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    if (path.contains('/experience/goal-detail/')) {
      return _okResponse<T>(path, _goalDetailPayload());
    }
    return _okResponse<T>(path);
  }

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    if (path.endsWith('/complete')) {
      completePosts++;
      await completeGate.future;
    }
    return _okResponse<T>(path);
  }

  int completePosts = 0;
  final Completer<void> completeGate = Completer<void>();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Map<String, dynamic> _goalDetailPayload() => <String, dynamic>{
      'goal': <String, dynamic>{
        'id': 'goal-1',
        'title': '目标G',
        'goal_type': 'learning',
        'status': 'active',
        'mastery': 0.1,
        'progress': 0.1,
        'priority': 'normal',
      },
      'minimum_acceptance_criteria': <String, dynamic>{
        'description': 'd',
        'status': 'pending_confirmation',
        'thresholds': <Map<String, dynamic>>[],
      },
      'plan_health': <String, dynamic>{
        'overall': 0.5,
        'phase_health': 0.5,
        'task_completion_rate': 0.5,
      },
      'current_phase': <String, dynamic>{'name': 'P1', 'progress': 0.5},
      'todays_minimal_next_step': <String, dynamic>{
        'task_id': 'task-g1',
        'title': '今日最小步骤',
        'type': 'learning',
        'estimated_minutes': 15,
      },
      'knowledge_bottlenecks': const <Map<String, dynamic>>[],
      'accountability_status': <String, dynamic>{
        'partner_count': 0,
        'active_commitments': 0,
      },
      'related_sources': const <Map<String, dynamic>>[],
    };

/// 任务仓储假体：完成/放弃/删除/更新全部计数；完成可用 [completeGate]
/// 拴住制造在飞窗口（并发双击的必要条件）。
/// 维护可变服务端状态（mutations 落盘、读投影它），模拟真实读 models：
/// provider 的 refreshTasks 会重新拉取，更新/删除必须对后续读可见。
class _CountingTaskRepository extends TaskRepository {
  _CountingTaskRepository() : super(_UnusedApiClient());

  int completeCalls = 0;
  int abandonCalls = 0;
  int deleteCalls = 0;
  int updateCalls = 0;
  TaskUpdate? lastUpdate;
  bool holdComplete = false;
  final Completer<void> completeGate = Completer<void>();

  final Map<String, TaskModel> _serverState = {
    'task-1': _seedTask('task-1'),
    'task-2': _seedTask('task-2'),
  };

  List<TaskModel> get _currentItems =>
      _serverState.values.toList(growable: false);

  TaskModel _completed(String id) => (_serverState[id] ?? _seedTask(id))
      .copyWith(status: TaskStatus.completed, completedAt: DateTime(2026));

  @override
  Future<TaskCompletionResult> completeTask(
    String id,
    int? actualMinutes,
    String? note,
  ) async {
    completeCalls++;
    if (holdComplete) {
      await completeGate.future;
    }
    final updated = _completed(id);
    _serverState[id] = updated;
    return TaskCompletionResult(
      task: updated.toJson(),
      feedback: 'ok',
    );
  }

  @override
  Future<TaskModel> abandonTask(String id) async {
    abandonCalls++;
    final updated = (_serverState[id] ?? _seedTask(id))
        .copyWith(status: TaskStatus.abandoned);
    _serverState[id] = updated;
    return updated;
  }

  @override
  Future<void> deleteTask(String id) async {
    deleteCalls++;
    _serverState.remove(id);
  }

  @override
  Future<TaskModel> updateTask(String id, TaskUpdate task) async {
    updateCalls++;
    lastUpdate = task;
    final updated = (_serverState[id] ?? _seedTask(id))
        .copyWith(dueDate: task.dueDate ?? _serverState[id]?.dueDate);
    _serverState[id] = updated;
    return updated;
  }

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      PaginatedResponse<TaskModel>(
        items: _currentItems,
        total: _currentItems.length,
        page: 1,
        pageSize: pageSize,
      );

  // N34：provider 走缓存感知读——fake 覆盖 Cached 变体（真实请求零依赖）。
  @override
  Future<CacheAwareResult<PaginatedResponse<TaskModel>>> getTasksCached({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      CacheAwareResult(
        PaginatedResponse<TaskModel>(
          items: _currentItems,
          total: _currentItems.length,
          page: 1,
          pageSize: pageSize,
        ),
      );

  @override
  Future<CacheAwareResult<List<TaskModel>>> getTodayTasksCached() async =>
      const CacheAwareResult<List<TaskModel>>(<TaskModel>[]);

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      <TaskModel>[];

  // V4-U08 验收3 读取面：日历月聚合走日期范围读。
  @override
  Future<List<TaskModel>> getTasksByDateRange(
    DateTime start,
    DateTime end,
  ) async =>
      seededRangeTasks;

  List<TaskModel> seededRangeTasks = <TaskModel>[];
}

class _CountingCalendarRepository extends CalendarRepository {
  _CountingCalendarRepository()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          CalendarRemoteDataSource(_UnusedApiClient()),
        );

  int removedLinkedEvents = 0;

  @override
  Future<List<CalendarEventModel>> getEvents({
    DateTime? startDate,
    DateTime? endDate,
    bool forceRemote = false,
  }) async =>
      const <CalendarEventModel>[];

  @override
  Future<void> removeTaskLinkedEvent(String taskId) async {
    removedLinkedEvents++;
  }

  @override
  Future<CalendarEventModel?> syncTaskLinkedEvent(TaskModel task) async =>
      null;
}

class _StubScheduler extends TaskNotificationScheduler {
  _StubScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );

  int rescheduleCalls = 0;

  @override
  Future<List<int>> rescheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async {
    rescheduleCalls++;
    return const <int>[];
  }

  @override
  Future<List<int>> scheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async =>
      const <int>[];

  @override
  Future<void> cancelTaskReminders(String taskId) async {}
}

class _ThrowingAttributionService extends PredictionAttributionService {
  @override
  Future<Map<String, dynamic>?> consumeForExecution({
    required String executionType,
    String? entityType,
    String? entityId,
  }) async =>
      null;
}

class _FakeEventStreamService extends AppEventStreamService {
  _FakeEventStreamService() : super(_UnusedRef(), _UnusedApiClient());

  @override
  Future<void> recordEntityExecution({
    required String entityType,
    required String entityId,
    required String actionType,
    required String source,
    Map<String, dynamic>? payload,
  }) async {}
}

class _StubGalaxyRepository extends EnhancedGalaxyRepository {
  _StubGalaxyRepository() : super(_UnusedApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// dashboard 拉取在测试里为纯静态 loading 态（cognitive=empty），
/// 统一日历聚合只读它拼认知快照，不需要真实数据。
class _StaticDashboardNotifier extends DashboardNotifier {
  // 形参仅满足 riverpod Create<Tearoff> 签名，本体不使用。
  _StaticDashboardNotifier(Ref _) : super(_UnusedDashboardRepo());

  @override
  Future<void> fetchData() async {}
}

class _UnusedDashboardRepo extends DashboardRepository {
  _UnusedDashboardRepo() : super(_UnusedApiClient());
}

class _StaticPlanNotifier extends PlanNotifier {
  _StaticPlanNotifier(Ref ref) : super(_UnusedPlanRepo(), ref); // ignore: avoid_unused_constructor_parameters


  @override
  Future<void> loadPlans({PlanType? type}) async {}

  @override
  Future<void> loadActivePlans() async {}
}

class _UnusedPlanRepo extends PlanRepository {
  _UnusedPlanRepo() : super(_UnusedApiClient());
}

TaskModel _seedTask(String id, {DateTime? dueDate}) => TaskModel(
      id: id,
      userId: 'user-1',
      title: '任务$id',
      type: TaskType.learning,
      tags: const [],
      estimatedMinutes: 30,
      difficulty: 2,
      energyCost: 1,
      priority: 1,
      status: TaskStatus.pending,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
      dueDate: dueDate,
    );

Future<TaskNotifier> _pumpTaskNotifier(ProviderContainer container) async {
  final notifier = container.read(taskListProvider.notifier);
  await Future<void>.delayed(const Duration(milliseconds: 60));
  return notifier;
}

ProviderContainer _makeContainer({
  required TaskRepository taskRepository,
  CalendarRepository? calendarRepository,
}) {
  SharedPreferences.setMockInitialValues(const {});
  return ProviderContainer(
    overrides: [
      taskRepositoryProvider.overrideWithValue(taskRepository),
      calendarRepositoryProvider
          .overrideWithValue(calendarRepository ?? _CountingCalendarRepository()),
      taskNotificationSchedulerProvider.overrideWithValue(_StubScheduler()),
      predictionAttributionServiceProvider
          .overrideWithValue(_ThrowingAttributionService()),
      appEventStreamServiceProvider.overrideWithValue(_FakeEventStreamService()),
      enhancedGalaxyRepositoryProvider.overrideWithValue(_StubGalaxyRepository()),
      dashboardProvider.overrideWith(_StaticDashboardNotifier.new),
      planListProvider.overrideWith(_StaticPlanNotifier.new),
    ],
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('V4-U08 验收1 · 重复点击一次写入（统一写入权威）', () {
    test('在飞完成写：并发双击合流为一次服务端写入，两次调用返回同一结果',
        () async {
      final repo = _CountingTaskRepository()..holdComplete = true;
      final container = _makeContainer(taskRepository: repo);
      addTearDown(container.dispose);
      final notifier = await _pumpTaskNotifier(container);

      final first = notifier.completeTask('task-1', 25, null);
      // 等第一次调用完成在飞登记，再模拟第二次点击。
      await Future<void>.delayed(const Duration(milliseconds: 10));
      final second = notifier.completeTask('task-1', 25, null);
      repo.completeGate.complete();

      final r1 = await first;
      final r2 = await second;

      expect(
        repo.completeCalls,
        1,
        reason: '同一任务完成写在飞时的重复点击必须合流为一次服务端写入',
      );
      expect(identical(r1, r2), isTrue, reason: '并发重复点击共享同一次写入结果');
      final task = container
          .read(taskListProvider)
          .tasks
          .firstWhere((t) => t.id == 'task-1');
      expect(task.status, TaskStatus.completed);
    });

    test('反面：守卫只按「任务+操作」合流——不同任务的并发完成各自写入，'
        '在飞结束后再次点击也照常发起新写入', () async {
      final repo = _CountingTaskRepository()..holdComplete = true;
      final container = _makeContainer(taskRepository: repo);
      addTearDown(container.dispose);
      final notifier = await _pumpTaskNotifier(container);

      final f1 = notifier.completeTask('task-1', 25, null);
      await Future<void>.delayed(const Duration(milliseconds: 10));
      final f2 = notifier.completeTask('task-2', 25, null);
      repo.completeGate.complete();
      await Future.wait(<Future<TaskCompletionResult?>>[f1, f2]);

      expect(repo.completeCalls, 2, reason: '不同任务不得被误合流');

      // 在飞结束后（守卫已摘除），对同任务的再次调用必须照常写入。
      await notifier.completeTask('task-2', 30, null);
      expect(
        repo.completeCalls,
        3,
        reason: '守卫只存在于在飞窗口，不吞掉后续合法写入',
      );
    });

    test('目标页完成写在飞：并发双击合流为一次 POST /complete', () async {
      final api = _GatedGoalApiClient();
      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(api),
          appEventStreamServiceProvider.overrideWithValue(
            _FakeEventStreamService(),
          ),
        ],
      );
      addTearDown(container.dispose);

      // 等初始 load() 落定，让今日步骤出现在状态里。
      final notifier = container.read(goalDetailProvider('goal-1').notifier);
      for (var i = 0; i < 20; i++) {
        await Future<void>.delayed(const Duration(milliseconds: 10));
        if (container.read(goalDetailProvider('goal-1')).value != null) break;
      }
      expect(
        container.read(goalDetailProvider('goal-1')).value?.todaysMinimalNextStep
            .taskId,
        'task-g1',
      );

      final first = notifier.completeNextStep();
      await Future<void>.delayed(const Duration(milliseconds: 10));
      final second = notifier.completeNextStep();
      api.completeGate.complete();

      final r1 = await first;
      final r2 = await second;

      expect(
        api.completePosts,
        1,
        reason: '目标页完成写在飞时的重复点击合流为一次 POST /complete',
      );
      expect(identical(r1, r2), isTrue, reason: '庆祝载荷只发一次');
    });
  });

  group('V4-U08 验收2 · 改日程键盘/按钮路径与拖拽同链（一次写入）', () {
    test('按钮路径写入口 rescheduleTaskDueDate：经 updateTask 一次写入，'
        '读模型 dueDate 同步可见', () async {
      final repo = _CountingTaskRepository();
      final container = _makeContainer(taskRepository: repo);
      addTearDown(container.dispose);
      final notifier = await _pumpTaskNotifier(container);

      final newDue = DateTime(2026, 10, 8);
      await notifier.rescheduleTaskDueDate('task-1', newDue);

      expect(repo.updateCalls, 1, reason: '改期经唯一写入口发生一次写入');
      expect(repo.lastUpdate?.dueDate, newDue);
      final task = container
          .read(taskListProvider)
          .tasks
          .firstWhere((t) => t.id == 'task-1');
      expect(
        task.dueDate,
        newDue,
        reason: '任务/计划/日历页共享的读模型同步看到同一条任务的同一版本',
      );
    });

    test('反面：改期写在飞时重复触发合流为一次；结束后再次改期照常写入',
        () async {
      final repo = _CountingTaskRepository();
      final container = _makeContainer(taskRepository: repo);
      addTearDown(container.dispose);
      final notifier = await _pumpTaskNotifier(container);

      // 首次改期（含读模型刷新链路）落地。
      await notifier.rescheduleTaskDueDate('task-1', DateTime(2026, 10, 8));
      expect(repo.updateCalls, 1);

      // 在飞窗口由 updateTask 内部的日历刷新 await 构成，这里以连续两次
      // 未 await 的调用模拟双击：同键写必须合流。
      final f1 = notifier.rescheduleTaskDueDate('task-1', DateTime(2026, 10, 9));
      final f2 = notifier.rescheduleTaskDueDate('task-1', DateTime(2026, 10, 9));
      await Future.wait(<Future<void>>[f1, f2]);

      expect(
        repo.updateCalls,
        2,
        reason: '同键在飞合流：双击只新增一次写入（1 次铺垫 + 1 次合流）',
      );
      final task = container
          .read(taskListProvider)
          .tasks
          .firstWhere((t) => t.id == 'task-1');
      expect(task.dueDate, DateTime(2026, 10, 9));
    });
  });

  group('V4-U08 验收3 · 估时不作为完成证据；删除/放弃不同语义', () {
    test('日历聚合专注时长只认实测：actualMinutes 计入', () async {
      final repo = _CountingTaskRepository();
      final day = DateTime(2026, 10, 5);
      repo.seededRangeTasks = [
        _seedTask('done-a', dueDate: day).copyWith(
          status: TaskStatus.completed,
          actualMinutes: 25,
        ),
      ];
      final container = _makeContainer(taskRepository: repo);
      addTearDown(container.dispose);

      await container
          .read(unifiedCalendarProvider.notifier)
          .loadMonth(DateTime(2026, 10), force: true);

      final aggregate =
          container.read(unifiedCalendarProvider).getDayAggregate(day);
      expect(aggregate?.focusMinutes, 25, reason: '实测分钟是真实的专注证据');
    });

    test('反面：无实测不造专注——估时 30 分钟不得顶替 actualMinutes 进聚合',
        () async {
      final repo = _CountingTaskRepository();
      final day = DateTime(2026, 10, 5);
      repo.seededRangeTasks = [
        // 完成但无实测：estimatedMinutes=30 不得计入。
        _seedTask('done-b', dueDate: day).copyWith(
          status: TaskStatus.completed,
        ),
        // 进行中任务即便有估时也一律不计。
        _seedTask('wip-c', dueDate: day).copyWith(
          status: TaskStatus.inProgress,
        ),
      ];
      final container = _makeContainer(taskRepository: repo);
      addTearDown(container.dispose);

      await container
          .read(unifiedCalendarProvider.notifier)
          .loadMonth(DateTime(2026, 10), force: true);

      final aggregate =
          container.read(unifiedCalendarProvider).getDayAggregate(day);
      expect(
        aggregate?.focusMinutes,
        0,
        reason: '计划时长（估时）不是完成证据；无实测按 0 计，不造进度',
      );
      expect(aggregate?.completedCount, 1, reason: '完成计数不受影响');
    });

    test('放弃 ≠ 删除：放弃保留任务记录仅置终态', () async {
      final repo = _CountingTaskRepository();
      final container = _makeContainer(taskRepository: repo);
      addTearDown(container.dispose);
      final notifier = await _pumpTaskNotifier(container);

      await notifier.abandonTask('task-1');

      expect(repo.abandonCalls, 1);
      expect(repo.deleteCalls, 0, reason: '放弃不得触发删除写入');
      final tasks = container.read(taskListProvider).tasks;
      expect(
        tasks.where((t) => t.id == 'task-1'),
        isNotEmpty,
        reason: '放弃是终态不是抹除——任务记录仍在读模型中（日历/星图可见历史）',
      );
      expect(
        tasks.firstWhere((t) => t.id == 'task-1').status,
        TaskStatus.abandoned,
      );
    });

    test('删除 ≠ 放弃：删除把条目从读模型移除（可撤销删除是另一条路径）',
        () async {
      final repo = _CountingTaskRepository();
      final calendarRepo = _CountingCalendarRepository();
      final container = _makeContainer(
        taskRepository: repo,
        calendarRepository: calendarRepo,
      );
      addTearDown(container.dispose);
      final notifier = await _pumpTaskNotifier(container);

      await notifier.deleteTask('task-1');

      expect(repo.deleteCalls, 1);
      expect(repo.abandonCalls, 0, reason: '删除不得降级为放弃');
      expect(
        calendarRepo.removedLinkedEvents,
        1,
        reason: '删除同时清掉日历联动事件',
      );
      expect(
        container.read(taskListProvider).tasks.where((t) => t.id == 'task-1'),
        isEmpty,
        reason: '删除是移除条目——与放弃（保留记录）语义不同',
      );
    });
  });
}
