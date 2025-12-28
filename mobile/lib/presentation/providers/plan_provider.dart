import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/plan_model.dart';
import 'package:sparkle/data/repositories/plan_repository.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';

// 1. PlanListState Class
class PlanListState {

  PlanListState({
    this.isLoading = false,
    this.plans = const [],
    this.activePlans = const [],
    this.error,
  });
  final bool isLoading;
  final List<PlanModel> plans;
  final List<PlanModel> activePlans;
  final String? error;

  PlanListState copyWith({
    bool? isLoading,
    List<PlanModel>? plans,
    List<PlanModel>? activePlans,
    String? error,
    bool clearError = false,
  }) => PlanListState(
      isLoading: isLoading ?? this.isLoading,
      plans: plans ?? this.plans,
      activePlans: activePlans ?? this.activePlans,
      error: clearError ? null : error ?? this.error,
    );
}

// 2. PlanNotifier Class
class PlanNotifier extends StateNotifier<PlanListState> {

  PlanNotifier(this._planRepository, this._ref) : super(PlanListState()) {
    loadPlans();
    loadActivePlans();
  }
  final PlanRepository _planRepository;
  final Ref _ref;

  Future<void> _runWithErrorHandling(Future<void> Function() action) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await action();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    } finally {
      // In case the action itself doesn't set isLoading to false
      if (state.isLoading) {
        state = state.copyWith(isLoading: false);
      }
    }
  }

  Future<void> loadPlans({PlanType? type}) async {
    await _runWithErrorHandling(() async {
      final plans = await _planRepository.getPlans(type: type);
      state = state.copyWith(plans: plans);
    });
  }

  Future<void> loadActivePlans() async {
    await _runWithErrorHandling(() async {
      final activePlans = await _planRepository.getActivePlans();
      state = state.copyWith(activePlans: activePlans);
    });
  }

  Future<void> createPlan(PlanCreate plan) async {
    await _runWithErrorHandling(() async {
      await _planRepository.createPlan(plan);
      await refresh();
    });
  }

  Future<void> updatePlan(String id, PlanUpdate planUpdate) async {
    await _runWithErrorHandling(() async {
      await _planRepository.updatePlan(id, planUpdate);
      await refresh();
    });
  }

  Future<void> deletePlan(String id) async {
    await _runWithErrorHandling(() async {
      await _planRepository.deletePlan(id);
      await refresh();
    });
  }

  Future<void> activatePlan(String id) async {
    await _runWithErrorHandling(() async {
      await _planRepository.activatePlan(id);
      await refresh();
    });
  }

  Future<void> deactivatePlan(String id) async {
    await _runWithErrorHandling(() async {
      await _planRepository.deactivatePlan(id);
      await refresh();
    });
  }

  Future<void> generateTasks(String planId, int count) async {
    await _runWithErrorHandling(() async {
      await _planRepository.generateTasks(planId, count: count);
      // Also refresh the tasks list
      _ref.read(taskListProvider.notifier).refreshTasks();
      // Invalidate the plan details to show the new tasks
      _ref.invalidate(planDetailProvider(planId));
    });
  }

  Future<void> refresh() async {
    await loadPlans();
    await loadActivePlans();
  }
}

// 3. Providers

final planListProvider = StateNotifierProvider<PlanNotifier, PlanListState>((ref) => PlanNotifier(ref.watch(planRepositoryProvider), ref));

final planDetailProvider = FutureProvider.family<PlanModel, String>((ref, id) async {
  final planRepo = ref.watch(planRepositoryProvider);
  return planRepo.getPlan(id);
});
