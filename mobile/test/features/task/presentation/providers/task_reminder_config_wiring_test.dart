// V3-FIX-385①（wt700）：taskReminderConfigProvider 真分裂双定义回归测试。
//
// 修前事实：settings_provider.dart 的 StateNotifierProvider（设置 UI 写面，
// TaskReminderSettingsScreen/统一设置屏经 show 子句绑定）与
// task_notification_scheduler.dart 的 StateProvider（task_provider.dart
// :231/:285/:819 任务执行面读取）是两个独立状态容器——设置写入永不达
// 任务执行读取（split-brain，配置静默失效）。
//
// 锁定不变量：
//   1. 设置面经真实 notifier 路径（updateConfig：乐观更新 + 服务端持久化）
//      修改提醒配置后，执行面 task_provider 触发提醒调度时收到的 config
//      必须随之变化（enabled 与提前量都要）。
//   2. 执行面收到的 config 与设置面状态同源（单一事实源）。
//
// 探针方式：假 scheduler 捕获 scheduleTaskReminders 实收 config——即
// task_provider.dart 内 `_ref.read(taskReminderConfigProvider)` 的真实
// 返回值，不经任何测试侧转接。
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart'
    as scheduler_face;
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart'
    as settings_face;
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';

class _UnusedRef implements Ref {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeUserSettingsServer {
  Map<String, dynamic> settings = <String, dynamic>{
    'task_reminders_enabled': true,
    'task_reminder_times': <int>[1440, 60, 15],
  };
}

class _FakeUserRepository extends UserRepository {
  _FakeUserRepository(this._server) : super(_UnusedApiClient());

  final _FakeUserSettingsServer _server;

  @override
  Future<Map<String, dynamic>> fetchUserSettings() async =>
      Map<String, dynamic>.of(_server.settings);

  @override
  Future<void> updateUserSettings(Map<String, dynamic> payload) async {
    _server.settings.addAll(payload);
  }
}

class _FakeTaskRepository extends TaskRepository {
  _FakeTaskRepository() : super(_UnusedApiClient());

  PaginatedResponse<TaskModel> _emptyPage(int pageSize) =>
      PaginatedResponse<TaskModel>(
        items: const <TaskModel>[],
        total: 0,
        page: 1,
        pageSize: pageSize,
      );

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      _emptyPage(pageSize);

  @override
  Future<CacheAwareResult<PaginatedResponse<TaskModel>>> getTasksCached({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      CacheAwareResult(_emptyPage(pageSize));

  @override
  Future<CacheAwareResult<List<TaskModel>>> getTodayTasksCached() async =>
      const CacheAwareResult<List<TaskModel>>(<TaskModel>[]);

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      <TaskModel>[];

  @override
  Future<TaskModel> createTask(
    TaskCreate task, {
    bool generateGuide = false,
  }) async => TaskModel(
        id: 'task-wt700',
        userId: 'user-1',
        title: task.title,
        type: task.type,
        tags: const <String>[],
        estimatedMinutes: task.estimatedMinutes,
        difficulty: task.difficulty,
        energyCost: task.energyCost,
        priority: 1,
        status: TaskStatus.pending,
        dueDate: DateTime.now().add(const Duration(days: 3)),
        createdAt: DateTime(2026),
        updatedAt: DateTime(2026),
      );
}

/// 捕获 task_provider 执行面传入的提醒配置（探针桩）。
class _ConfigCapturingScheduler extends scheduler_face.TaskNotificationScheduler {
  _ConfigCapturingScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );

  final List<scheduler_face.TaskReminderConfig?> scheduleConfigs =
      <scheduler_face.TaskReminderConfig?>[];

  @override
  Future<List<int>> scheduleTaskReminders(
    TaskModel task, {
    scheduler_face.TaskReminderConfig? config,
  }) async {
    scheduleConfigs.add(config);
    return <int>[];
  }

  @override
  Future<void> refreshAllReminders(
    List<TaskModel> pendingTasks, {
    scheduler_face.TaskReminderConfig? config,
  }) async {}
}

class _StubCalendarRepository implements CalendarRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
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

class _UnusedAuthRepository implements AuthRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class _StaticAuthNotifier extends AuthNotifier {
  _StaticAuthNotifier(AuthState initialState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = initialState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000700',
      username: 'wt700_user',
      email: 'wt700@example.com',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

ProviderContainer _buildContainer(
  _FakeUserSettingsServer server,
  _ConfigCapturingScheduler scheduler,
) {
  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith(
        (ref) => _StaticAuthNotifier(
          AuthState(isAuthenticated: true, user: _buildUser()),
        ),
      ),
      userRepositoryProvider.overrideWithValue(_FakeUserRepository(server)),
      taskRepositoryProvider.overrideWithValue(_FakeTaskRepository()),
      scheduler_face.taskNotificationSchedulerProvider
          .overrideWithValue(scheduler),
      calendarRepositoryProvider.overrideWithValue(_StubCalendarRepository()),
      predictionAttributionServiceProvider
          .overrideWithValue(_StubAttributionService()),
      appEventStreamServiceProvider
          .overrideWithValue(_StubEventStreamService()),
      enhancedGalaxyRepositoryProvider
          .overrideWithValue(_StubGalaxyRepository()),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues(const {});

  group('V3-FIX-385① taskReminderConfigProvider 单一事实源', () {
    test('设置面修改提醒配置后，执行面 task_provider 调度收到新配置', () async {
      final server = _FakeUserSettingsServer();
      final scheduler = _ConfigCapturingScheduler();
      final container = _buildContainer(server, scheduler);

      // 设置面构建（读取即构建）并等构造期服务端加载落地（避免与后续
      // updateConfig 的乐观写竞争覆盖）。
      final initialReminders =
          container.read(settings_face.taskReminderConfigProvider).reminders;
      await Future<void>.delayed(const Duration(milliseconds: 60));
      expect(
        container.read(settings_face.taskReminderConfigProvider).reminders,
        initialReminders,
        reason: '前置：构造期服务端加载已落地且不改变缺省提前量',
      );

      // 设置面：走 TaskReminderSettingsScreen 使用的真实 notifier 更新路径
      //（乐观更新 + 服务端持久化 + refreshAllReminders）。
      await container
          .read(settings_face.taskReminderConfigProvider.notifier)
          .updateConfig(enabled: false, reminders: const [30]);

      expect(server.settings['task_reminders_enabled'], isFalse,
          reason: '前置：设置写入已持久化到服务端',);
      expect(server.settings['task_reminder_times'], [30]);

      // 执行面：task_provider.createTask → _ref.read(taskReminderConfigProvider)
      // → scheduleTaskReminders(config: …)。探针捕获实收 config。
      final notifier = container.read(taskListProvider.notifier);
      await Future<void>.delayed(const Duration(milliseconds: 60));
      await notifier.createTask(
        TaskCreate(
          title: 'V3-FIX-385 探针任务',
          type: TaskType.learning,
          estimatedMinutes: 30,
          difficulty: 1,
        ),
      );

      expect(scheduler.scheduleConfigs, isNotEmpty,
          reason: '有截止日的任务创建必须触发提醒调度',);
      final captured = scheduler.scheduleConfigs.last;
      expect(captured, isNotNull);
      expect(
        captured!.enabled,
        isFalse,
        reason: '用户在设置面关停提醒后，任务执行面调度必须读到关停'
            '（修前：执行面读 scheduler 侧独立 StateProvider，恒为默认 true，静默失效）',
      );
      expect(
        captured.reminders,
        [30],
        reason: '用户修改的提醒提前量必须传导到执行面调度',
      );
    });
  });
}
