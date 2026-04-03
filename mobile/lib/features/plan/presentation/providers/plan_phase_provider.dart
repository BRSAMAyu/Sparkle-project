import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/plan/data/models/plan_phase_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

final planPhasesProvider =
    FutureProvider.family<PlanPhaseBundle, String>((ref, planId) async {
  final repository = ref.watch(planRepositoryProvider);
  return repository.getPlanPhases(planId);
});

final planPhaseControllerProvider =
    Provider<PlanPhaseController>(PlanPhaseController.new);

class PlanPhaseController {
  PlanPhaseController(this._ref);

  final Ref _ref;

  Future<void> createPhase(
    String planId, {
    required String name,
    required int phaseIndex,
  }) async {
    try {
      await _ref.read(planRepositoryProvider).createPhase(
            planId,
            name: name,
            phaseIndex: phaseIndex,
          );
      _ref
        ..invalidate(planPhasesProvider(planId))
        ..invalidate(planDetailProvider(planId));
      await _ref.read(planListProvider.notifier).refresh();
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> activatePhase(
    String planId,
    String phaseCardId,
  ) async {
    try {
      await _ref.read(planRepositoryProvider).activatePhase(phaseCardId);
      _ref
        ..invalidate(planPhasesProvider(planId))
        ..invalidate(planDetailProvider(planId));
      await _ref.read(planListProvider.notifier).refresh();
      return {'success': true};
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> completePhase(
    String planId,
    String phaseCardId,
  ) async {
    try {
      final result =
          await _ref.read(planRepositoryProvider).completePhase(phaseCardId);
      _ref
        ..invalidate(planPhasesProvider(planId))
        ..invalidate(planDetailProvider(planId));
      await _ref.read(planListProvider.notifier).refresh();
      return result;
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> submitFeedback(
    String planId,
    String phaseCardId, {
    required double rating,
    String? reflection,
    bool blocked = false,
    bool lifeChanged = false,
    bool requestCompassReview = false,
  }) async {
    try {
      final result = await _ref.read(planRepositoryProvider).submitPhaseFeedback(
            phaseCardId,
            rating: rating,
            reflection: reflection,
            blocked: blocked,
            lifeChanged: lifeChanged,
            requestCompassReview: requestCompassReview,
          );
      _ref
        ..invalidate(planPhasesProvider(planId))
        ..invalidate(planDetailProvider(planId));
      await _ref.read(planListProvider.notifier).refresh();
      return result;
    } catch (e) {
      rethrow;
    }
  }
}
