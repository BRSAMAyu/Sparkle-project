import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class _FakePlanRepository extends PlanRepository {
  _FakePlanRepository({
    required this.getPlansHandler,
    required this.getActivePlansHandler,
    this.generateTasksHandler,
  }) : super(_NoopApiClient());

  final Future<List<PlanModel>> Function({PlanType? type, bool? isActive})
      getPlansHandler;
  final Future<List<PlanModel>> Function() getActivePlansHandler;
  final Future<List<TaskModel>> Function(String planId, {int count})?
      generateTasksHandler;

  @override
  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) =>
      getPlansHandler(type: type, isActive: isActive);

  @override
  Future<List<PlanModel>> getActivePlans() => getActivePlansHandler();

  @override
  Future<List<TaskModel>> generateTasks(String planId, {int count = 5}) async {
    return await generateTasksHandler?.call(planId, count: count) ?? <TaskModel>[];
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

void main() {
  group('PlanNotifier', () {
    test('loads plans and active plans on bootstrap', () async {
      final repo = _FakePlanRepository(
        getPlansHandler: ({type, isActive}) async => [
          _plan(id: 'plan-1', name: 'Growth'),
          _plan(id: 'plan-2', name: 'Sprint', type: PlanType.sprint),
        ],
        getActivePlansHandler: () async => [_plan(id: 'plan-1', name: 'Growth')],
      );

      final container = ProviderContainer(
        overrides: [
          planRepositoryProvider.overrideWithValue(repo),
        ],
      );
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

      final container = ProviderContainer(
        overrides: [
          planRepositoryProvider.overrideWithValue(repo),
        ],
      );
      addTearDown(container.dispose);

      final notifier = container.read(planListProvider.notifier);
      await notifier.loadPlans();

      final state = container.read(planListProvider);
      expect(state.isLoading, isFalse);
      expect(state.error, contains('plans unavailable'));
    });
  });
}
