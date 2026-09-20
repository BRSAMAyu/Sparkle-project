// M6-03 regression tests: task completion sync status must reflect the
// SERVER result, never local post-completion steps.
//
// Locks two invariants:
//   1. When the server completes the task successfully but a local
//      post-completion step (attribution / event stream) throws, the task
//      stays `syncStatus: synced` — it must not be mislabeled `failed`.
//   2. `retryCompleteTask` is idempotent for already-completed tasks whose
//      sync is confirmed: it must not call the server again (no duplicate
//      completion / double rewards).
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:shared_preferences/shared_preferences.dart';
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
import '../../../../shared/i18n_test_helper.dart';

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeTaskRepository extends TaskRepository {
  _FakeTaskRepository() : super(_UnusedApiClient());

  int completeCalls = 0;

  @override
  Future<TaskCompletionResult> completeTask(
    String id,
    int? actualMinutes, // X-04: nullable to match TaskRepository.completeTask
    String? note,
  ) async {
    completeCalls++;
    return TaskCompletionResult(
      task: <String, dynamic>{
        'id': id,
        'user_id': 'user-1',
        'title': 'Deep link task',
        'type': 'LEARNING',
        'tags': <String>[],
        'estimated_minutes': 30,
        'difficulty': 2,
        'energy_cost': 1,
        'priority': 1,
        'status': 'COMPLETED',
        'created_at': DateTime(2026, 1, 1).toIso8601String(),
        'updated_at': DateTime(2026, 1, 1).toIso8601String(),
      },
    );
  }

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      PaginatedResponse<TaskModel>(
        items: [_seedTask()],
        total: 1,
        page: 1,
        pageSize: pageSize,
      );

  @override
  Future<List<TaskModel>> getTodayTasks() async => [_seedTask()];

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      <TaskModel>[];
}

TaskModel _seedTask() => TaskModel(
      id: 'task-1',
      userId: 'user-1',
      title: 'Deep link task',
      type: TaskType.learning,
      tags: const [],
      estimatedMinutes: 30,
      difficulty: 2,
      energyCost: 1,
      priority: 1,
      status: TaskStatus.pending,
      createdAt: DateTime(2026, 1, 1),
      updatedAt: DateTime(2026, 1, 1),
    );

class _ThrowingAttributionService extends PredictionAttributionService {
  int consumeCalls = 0;

  @override
  Future<Map<String, dynamic>?> consumeForExecution({
    required String executionType,
    String? entityType,
    String? entityId,
  }) async {
    consumeCalls++;
    throw Exception('attribution service unavailable');
  }
}

class _FakeEventStreamService extends AppEventStreamService {
  _FakeEventStreamService() : super(_UnusedRef(), _UnusedApiClient());

  int executionRecords = 0;

  @override
  Future<void> recordEntityExecution({
    required String entityType,
    required String entityId,
    required String actionType,
    required String source,
    Map<String, dynamic>? payload,
  }) async {
    executionRecords++;
  }
}

class _StubScheduler extends TaskNotificationScheduler {
  int cancelCalls = 0;

  _StubScheduler()
      : super(
          NotificationService(_UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );

  @override
  Future<void> cancelTaskReminders(String taskId) async {
    cancelCalls++;
  }
}

class _FailingTaskRepository extends _FakeTaskRepository {
  @override
  Future<TaskCompletionResult> completeTask(
    String id,
    int? actualMinutes, // X-04: nullable to match TaskRepository.completeTask
    String? note,
  ) async {
    completeCalls++;
    throw DioException(
      requestOptions: RequestOptions(path: '/tasks/$id/complete'),
      type: DioExceptionType.connectionError,
      message: 'offline',
    );
  }
}

class _StubGalaxyRepository extends EnhancedGalaxyRepository {
  _StubGalaxyRepository() : super(_UnusedApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Future<TaskNotifier> _pumpNotifier(
  ProviderContainer container,
) async {
  final notifier = container.read(taskListProvider.notifier);
  // Let the constructor's parallel initial loads populate state.tasks.
  await Future<void>.delayed(const Duration(milliseconds: 60));
  return notifier;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);

  group('M6-03 task completion sync status', () {
    test(
        'server success keeps syncStatus synced when post-completion '
        'attribution throws', () async {
      SharedPreferences.setMockInitialValues(const {});
      final fakeRepo = _FakeTaskRepository();
      final container = ProviderContainer(
        overrides: [
          taskRepositoryProvider.overrideWithValue(fakeRepo),
          taskNotificationSchedulerProvider.overrideWithValue(_StubScheduler()),
          predictionAttributionServiceProvider
              .overrideWithValue(_ThrowingAttributionService()),
          appEventStreamServiceProvider
              .overrideWithValue(_FakeEventStreamService()),
          enhancedGalaxyRepositoryProvider
              .overrideWithValue(_StubGalaxyRepository()),
        ],
      );
      addTearDown(container.dispose);

      final notifier = await _pumpNotifier(container);

      final result = await notifier.completeTask('task-1', 25, null);

      expect(result, isNotNull, reason: 'server completion succeeded');
      expect(fakeRepo.completeCalls, 1);

      final task =
          container.read(taskListProvider).tasks.firstWhere((t) => t.id == 'task-1');
      expect(
        task.syncStatus,
        TaskSyncStatus.synced,
        reason:
            'A failing local post-completion step (attribution) must not '
            'overwrite the confirmed server success with syncStatus.failed',
      );
      expect(task.status, TaskStatus.completed);
    });

    test('retryCompleteTask is idempotent for already-synced completions',
        () async {
      SharedPreferences.setMockInitialValues(const {});
      final fakeRepo = _FakeTaskRepository();
      final container = ProviderContainer(
        overrides: [
          taskRepositoryProvider.overrideWithValue(fakeRepo),
          taskNotificationSchedulerProvider.overrideWithValue(_StubScheduler()),
          predictionAttributionServiceProvider
              .overrideWithValue(_ThrowingAttributionService()),
          appEventStreamServiceProvider
              .overrideWithValue(_FakeEventStreamService()),
          enhancedGalaxyRepositoryProvider
              .overrideWithValue(_StubGalaxyRepository()),
        ],
      );
      addTearDown(container.dispose);

      final notifier = await _pumpNotifier(container);

      await notifier.completeTask('task-1', 25, null);
      expect(fakeRepo.completeCalls, 1);

      // User taps the retry entry shown in the UI. The server already
      // confirmed completion, so this must be a no-op on the server side.
      await notifier.retryCompleteTask('task-1', 25, null);

      expect(
        fakeRepo.completeCalls,
        1,
        reason:
            'Retrying an already-completed (synced) task must not call the '
            'server completion endpoint again',
      );
      final task =
          container.read(taskListProvider).tasks.firstWhere((t) => t.id == 'task-1');
      expect(task.syncStatus, TaskSyncStatus.synced);
    });

    test('does not cancel reminders when the server completion fails',
        () async {
      SharedPreferences.setMockInitialValues(const {});
      final scheduler = _StubScheduler();
      final container = ProviderContainer(
        overrides: [
          taskRepositoryProvider.overrideWithValue(_FailingTaskRepository()),
          taskNotificationSchedulerProvider.overrideWithValue(scheduler),
          predictionAttributionServiceProvider
              .overrideWithValue(_ThrowingAttributionService()),
          appEventStreamServiceProvider
              .overrideWithValue(_FakeEventStreamService()),
          enhancedGalaxyRepositoryProvider
              .overrideWithValue(_StubGalaxyRepository()),
        ],
      );
      addTearDown(container.dispose);

      final notifier = await _pumpNotifier(container);

      final result = await notifier.completeTask('task-1', 25, null);

      expect(result, isNull, reason: 'server completion failed');
      expect(
        scheduler.cancelCalls,
        0,
        reason:
            'Reminder cancellation must happen only after server '
            'confirmation — on failure the task is still open and its '
            'reminders must stay active',
      );
    });
  });
}
