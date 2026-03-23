import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

/// Sprint action types
enum SprintAction { complete, extend, abandon }

/// Sprint actions state
class SprintActionsState {
  SprintActionsState({
    this.isProcessing = false,
    this.error,
    this.successMessage,
  });

  final bool isProcessing;
  final String? error;
  final String? successMessage;

  SprintActionsState copyWith({
    bool? isProcessing,
    String? error,
    String? successMessage,
    bool clearError = false,
    bool clearSuccess = false,
  }) =>
      SprintActionsState(
        isProcessing: isProcessing ?? this.isProcessing,
        error: clearError ? null : error ?? this.error,
        successMessage:
            clearSuccess ? null : successMessage ?? this.successMessage,
      );
}

/// Sprint actions notifier
class SprintActionsNotifier extends StateNotifier<SprintActionsState> {
  SprintActionsNotifier(this._ref) : super(SprintActionsState());

  final Ref _ref;

  Future<bool> completeSprint(String planId) async {
    state = state.copyWith(
        isProcessing: true, clearError: true, clearSuccess: true,);

    try {
      // Archive the plan to mark sprint as complete
      await _ref.read(planListProvider.notifier).archivePlan(planId);
      final linkedPrediction = await _ref
          .read(predictionAttributionServiceProvider)
          .consumeForExecution(
            executionType: 'plan',
            entityType: 'plan',
            entityId: planId,
          );
      await _ref.read(appEventStreamServiceProvider).recordEntityExecution(
        entityType: 'plan',
        entityId: planId,
        actionType: 'complete_plan',
        source: 'sprint_actions',
        payload: {
          if (linkedPrediction != null) ...{
            'prediction_id': linkedPrediction['prediction_id'],
            'candidate_id': linkedPrediction['candidate_id'],
            'prediction_action_type': linkedPrediction['action_type'],
            'prediction_surface': linkedPrediction['surface'],
            'prediction_horizon': linkedPrediction['horizon'],
            'prediction_source': linkedPrediction['source'],
          },
        },
      );

      // Refresh dashboard to clear the sprint
      await _ref.read(dashboardProvider.notifier).refresh();

      // Note: Success message should be localized by the UI component
      state = state.copyWith(
        isProcessing: false,
        successMessage: 'sprint_completed',
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        error: e.toString(),
      );
      return false;
    }
  }

  Future<bool> extendSprint(String planId, int additionalDays) async {
    state = state.copyWith(
        isProcessing: true, clearError: true, clearSuccess: true,);

    try {
      // Update the plan's target date
      final currentDashboard = _ref.read(dashboardProvider);
      final sprint = currentDashboard.sprint;

      if (sprint == null) {
        throw Exception('no_active_sprint');
      }

      // Calculate new target date
      final newTargetDate = DateTime.now().add(Duration(days: additionalDays));

      // Update the plan with new target date
      await _ref.read(planListProvider.notifier).updatePlan(
            planId,
            PlanUpdate(targetDate: newTargetDate),
          );

      // Refresh dashboard
      await _ref.read(dashboardProvider.notifier).refresh();

      // Note: Success message should be localized by the UI component
      state = state.copyWith(
        isProcessing: false,
        successMessage: 'sprint_extended:$additionalDays',
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        error: e.toString(),
      );
      return false;
    }
  }

  Future<bool> abandonSprint(String planId, String reason) async {
    state = state.copyWith(
        isProcessing: true, clearError: true, clearSuccess: true,);

    try {
      // Archive the plan
      await _ref.read(planListProvider.notifier).archivePlan(planId);

      // Refresh dashboard to clear the sprint
      await _ref.read(dashboardProvider.notifier).refresh();

      // Note: Success message should be localized by the UI component
      state = state.copyWith(
        isProcessing: false,
        successMessage: 'sprint_abandoned',
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isProcessing: false,
        error: e.toString(),
      );
      return false;
    }
  }

  void clearMessages() {
    state = state.copyWith(clearError: true, clearSuccess: true);
  }
}

/// Sprint actions provider
final sprintActionsProvider =
    StateNotifierProvider<SprintActionsNotifier, SprintActionsState>(
  SprintActionsNotifier.new,
);
