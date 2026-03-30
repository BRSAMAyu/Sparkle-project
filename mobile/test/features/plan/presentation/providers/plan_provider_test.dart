import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class _FakePlanRepository extends PlanRepository {
  _FakePlanRepository({
    required this.getPlansHandler,
    required this.getActivePlansHandler,
    this.getPlanHandler,
    this.generateTasksHandler,
  }) : super(_NoopApiClient());

  final Future<List<PlanModel>> Function({PlanType? type, bool? isActive})
      getPlansHandler;
  final Future<List<PlanModel>> Function() getActivePlansHandler;
  final Future<PlanModel> Function(String id)? getPlanHandler;
  final Future<List<TaskModel>> Function(String planId, {int count})?
      generateTasksHandler;

  @override
  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) =>
      getPlansHandler(type: type, isActive: isActive);

  @override
  Future<List<PlanModel>> getActivePlans() => getActivePlansHandler();

  @override
  Future<PlanModel> getPlan(String id) async {
    return await getPlanHandler?.call(id) ?? _plan(id: id, name: 'Plan $id');
  }

  @override
  Future<List<TaskModel>> generateTasks(String planId, {int count = 5}) async {
    return await generateTasksHandler?.call(planId, count: count) ??
        <TaskModel>[];
  }
}

class _FakeTaskRepository extends TaskRepository {
  _FakeTaskRepository() : super(_NoopApiClient());
}

class _RecordingTaskNotifier extends TaskNotifier {
  _RecordingTaskNotifier()
      : super(
          _FakeTaskRepository(),
          TaskNotificationScheduler(
            NotificationService(_UnusedRef(), autoInitialize: false),
            TaskNotificationIdMapper(),
          ),
          _UnusedRef(),
        );

  int refreshCount = 0;

  @override
  Future<void> loadTodayTasks() async {}

  @override
  Future<void> loadRecommendedTasks() async {}

  @override
  Future<void> loadTasks({TaskFilter? filter}) async {}

  @override
  Future<void> refreshTasks() async {
    refreshCount += 1;
  }
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedRef implements Ref {
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

PlanModel _plan({
  required String id,
  required String name,
  PlanType type = PlanType.growth,
  bool isActive = true,
}) {
  final now = DateTime.utc(2026, 3, 31);
  return PlanModel(
    id: id,
    userId: 'user-1',
    name: name,
    type: type,
    dailyAvailableMinutes: 45,
    masteryLevel: 0.4,
    progress: 0.5,
    isActive: isActive,
    createdAt: now,
    updatedAt: now,
    description: 'desc',
  );
}

ProviderContainer _createContainer({
  required PlanRepository repo,
  _RecordingTaskNotifier? taskNotifier,
}) {
  return ProviderContainer(
    overrides: [
      planRepositoryProvider.overrideWithValue(repo),
      if (taskNotifier != null)
        taskListProvider.overrideWith((ref) => taskNotifier),
    ],
  );
}

Future<void> _drainMicrotasks() async {
  await Future<void>.delayed(Duration.zero);
  await Future<void>.delayed(Duration.zero);
}

void main() {
  group('PlanNotifier', () {
    test('loads plans and active plans on bootstrap', () async {
      final repo = _FakePlanRepository(
        getPlansHandler: ({type, isActive}) async => [
          _plan(id: 'plan-1', name: 'Growth'),
          _plan(id: 'plan-2', name: 'Sprint', type: PlanType.sprint),
        ],
        getActivePlansHandler: () async =>
            [_plan(id: 'plan-1', name: 'Growth')],
      );

      final container = _createContainer(repo: repo);
      addTearDown(container.dispose);

      final notifier = container.read(planListProvider.notifier);
      await notifier.loadPlans();
      await notifier.loadActivePlans();

      final state = container.read(planListProvider);
      expect(state.error, isNull);
      expect(state.plans, hasLength(2));
      expect(state.activePlans, hasLength(1));
      expect(state.activePlans.first.id, 'plan-1');
    });

    test('surfaces repository failures as stable error state', () async {
      final repo = _FakePlanRepository(
        getPlansHandler: ({type, isActive}) async {
          throw Exception('plans unavailable');
        },
        getActivePlansHandler: () async => [],
      );

      final container = _createContainer(repo: repo);
      addTearDown(container.dispose);

      final notifier = container.read(planListProvider.notifier);
      await notifier.loadPlans();

      final state = container.read(planListProvider);
      expect(state.isLoading, isFalse);
      expect(state.error, contains('plans unavailable'));
    });

    test('marks loading during filtered loads and forwards the requested type',
        () async {
      Future<List<PlanModel>> pendingPlans = Future.value(<PlanModel>[
        _plan(id: 'bootstrap', name: 'Bootstrap'),
      ]);
      final requestedTypes = <PlanType?>[];

      final repo = _FakePlanRepository(
        getPlansHandler: ({type, isActive}) {
          requestedTypes.add(type);
          return pendingPlans;
        },
        getActivePlansHandler: () async => <PlanModel>[],
      );

      final container = _createContainer(repo: repo);
      addTearDown(container.dispose);

      final notifier = container.read(planListProvider.notifier);
      await _drainMicrotasks();

      final completer = Completer<List<PlanModel>>();
      pendingPlans = completer.future;

      final loadFuture = notifier.loadPlans(type: PlanType.sprint);
      expect(container.read(planListProvider).isLoading, isTrue);
      expect(container.read(planListProvider).error, isNull);

      completer.complete(<PlanModel>[
        _plan(id: 'plan-sprint', name: 'Sprint Plan', type: PlanType.sprint),
      ]);
      await loadFuture;

      final state = container.read(planListProvider);
      expect(requestedTypes, contains(PlanType.sprint));
      expect(state.isLoading, isFalse);
      expect(state.error, isNull);
      expect(state.plans.single.type, PlanType.sprint);
    });

    test('generateTasks refreshes task state and invalidates plan details',
        () async {
      final generatedCalls = <Map<String, Object>>[];
      var getPlanCalls = 0;
      final taskNotifier = _RecordingTaskNotifier();
      final repo = _FakePlanRepository(
        getPlansHandler: ({type, isActive}) async => <PlanModel>[
          _plan(id: 'plan-1', name: 'Growth'),
        ],
        getActivePlansHandler: () async => <PlanModel>[
          _plan(id: 'plan-1', name: 'Growth'),
        ],
        getPlanHandler: (id) async {
          getPlanCalls += 1;
          return _plan(id: id, name: 'Growth');
        },
        generateTasksHandler: (planId, {count = 5}) async {
          generatedCalls.add(<String, Object>{
            'planId': planId,
            'count': count,
          });
          return <TaskModel>[];
        },
      );

      final container =
          _createContainer(repo: repo, taskNotifier: taskNotifier);
      addTearDown(container.dispose);

      final notifier = container.read(planListProvider.notifier);
      await _drainMicrotasks();

      await container.read(planDetailProvider('plan-1').future);
      expect(getPlanCalls, 1);

      await notifier.generateTasks('plan-1', 3);

      expect(generatedCalls, <Map<String, Object>>[
        <String, Object>{'planId': 'plan-1', 'count': 3},
      ]);
      expect(taskNotifier.refreshCount, 1);

      await container.read(planDetailProvider('plan-1').future);
      expect(getPlanCalls, 2);

      final state = container.read(planListProvider);
      expect(state.isLoading, isFalse);
      expect(state.error, isNull);
    });
  });
}
