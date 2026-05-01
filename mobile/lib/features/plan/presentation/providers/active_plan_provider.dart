import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

/// Active Plan Provider
///
/// Tracks the currently selected plan for chat context.
/// Multiple plans can be active, but chat needs a single context.
/// User explicitly selects which plan to use.
///
/// Usage:
/// ```dart
/// final selectedPlanId = ref.read(activePlanProvider);
/// ref.read(activePlanProvider.notifier).selectPlan('plan_id');
/// ref.read(activePlanProvider.notifier).clearSelection();
/// ```
class ActivePlanNotifier extends PersistentNotifier<String?> {
  ActivePlanNotifier(this._ref)
      : super(
          namespace: 'active_plan',
          key: 'selected_id',
          defaultValue: null,
          serializer: (s) => s,
          deserializer: (s) => (s == null || s.isEmpty) ? null : s,
        );

  final Ref _ref;

  /// Select a plan as the active chat context
  void selectPlan(String? planId) {
    state = planId;
  }

  /// Select plan based on task's planId (null-safe)
  /// P0-1: Auto-switch plan context when starting task execution
  void selectFromTaskPlanId(String? planId) {
    if (planId != null) {
      state = planId;
    }
  }

  /// Clear the active plan selection
  void clearSelection() {
    state = null;
  }

  /// Auto-select the first active plan if no plan is selected
  void autoSelectFirstActivePlan() {
    if (state != null) return; // Already has a selection

    final activePlans = _ref.read(planListProvider).activePlans;
    if (activePlans.isNotEmpty) {
      state = activePlans.first.id;
    }
  }
}

/// Core keepAlive provider for the currently active plan (for chat context).
///
/// Returns the plan_id of the currently selected plan, or null if no plan is selected.
final activePlanProvider = StateNotifierProvider<ActivePlanNotifier, String?>(
  ActivePlanNotifier.new,
);
