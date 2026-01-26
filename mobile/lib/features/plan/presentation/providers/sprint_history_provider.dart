import 'package:sparkle/shared/entities/task_model.dart' show TaskStatus;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

/// Sprint history item - represents a completed/archived sprint
class SprintHistoryItem {
  SprintHistoryItem({
    required this.id,
    required this.name,
    required this.startDate,
    this.endDate,
    required this.finalProgress,
    required this.totalTasks,
    required this.completedTasks,
    required this.status,
  });

  factory SprintHistoryItem.fromPlan(PlanModel plan, SprintStatus status) {
    // Count tasks from plan
    final totalTasks = plan.tasks?.length ?? 0;
    final completedTasks = plan.tasks?.where((t) => t.status == TaskStatus.completed).length ?? 0;

    return SprintHistoryItem(
      id: plan.id,
      name: plan.name,
      startDate: plan.createdAt,
      endDate: plan.targetDate,
      finalProgress: plan.progress,
      totalTasks: totalTasks,
      completedTasks: completedTasks,
      status: status,
    );
  }

  final String id;
  final String name;
  final DateTime startDate;
  final DateTime? endDate;
  final double finalProgress;
  final int totalTasks;
  final int completedTasks;
  final SprintStatus status;

  /// Calculate duration in days
  int get durationDays {
    if (endDate == null) return 0;
    return endDate!.difference(startDate).inDays;
  }

  /// Get status key for localization
  String get statusKey {
    switch (status) {
      case SprintStatus.completed:
        return 'sprint_status_completed';
      case SprintStatus.abandoned:
        return 'sprint_status_abandoned';
      case SprintStatus.extended:
        return 'sprint_status_extended';
    }
  }

  /// Get status color
  SprintStatusColor get statusColor {
    switch (status) {
      case SprintStatus.completed:
        return SprintStatusColor.success;
      case SprintStatus.abandoned:
        return SprintStatusColor.error;
      case SprintStatus.extended:
        return SprintStatusColor.warning;
    }
  }

  SprintHistoryItem copyWith({
    String? id,
    String? name,
    DateTime? startDate,
    DateTime? endDate,
    double? finalProgress,
    int? totalTasks,
    int? completedTasks,
    SprintStatus? status,
  }) =>
      SprintHistoryItem(
        id: id ?? this.id,
        name: name ?? this.name,
        startDate: startDate ?? this.startDate,
        endDate: endDate ?? this.endDate,
        finalProgress: finalProgress ?? this.finalProgress,
        totalTasks: totalTasks ?? this.totalTasks,
        completedTasks: completedTasks ?? this.completedTasks,
        status: status ?? this.status,
      );
}

/// Sprint status enum
enum SprintStatus { completed, abandoned, extended }

/// Sprint status color enum
enum SprintStatusColor { success, warning, error }

/// Sprint history state
class SprintHistoryState {
  SprintHistoryState({
    this.items = const [],
    this.isLoading = false,
    this.error,
  });

  final List<SprintHistoryItem> items;
  final bool isLoading;
  final String? error;

  SprintHistoryState copyWith({
    List<SprintHistoryItem>? items,
    bool? isLoading,
    String? error,
    bool clearError = false,
  }) =>
      SprintHistoryState(
        items: items ?? this.items,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : error ?? this.error,
      );
}

/// Sprint history notifier
class SprintHistoryNotifier extends StateNotifier<SprintHistoryState> {
  SprintHistoryNotifier(this._ref) : super(SprintHistoryState()) {
    fetchHistory();
  }

  final Ref _ref;

  Future<void> fetchHistory() async {
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      final planState = _ref.read(planListProvider);

      // Filter for sprint-type plans that are archived (not active)
      final archivedSprintPlans = planState.plans
          .where((p) => p.type == PlanType.sprint && !p.isActive)
          .toList();

      // Convert to SprintHistoryItem
      final historyItems = archivedSprintPlans.map((plan) {
        // Determine status based on progress
        SprintStatus status;
        if (plan.progress >= 0.95) {
          status = SprintStatus.completed;
        } else if (plan.progress == 0) {
          status = SprintStatus.abandoned;
        } else {
          status = SprintStatus.extended;
        }

        return SprintHistoryItem.fromPlan(plan, status);
      }).toList();

      // Sort by start date descending
      historyItems.sort((a, b) => b.startDate.compareTo(a.startDate));

      state = state.copyWith(items: historyItems, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> refresh() async {
    await fetchHistory();
  }
}

/// Sprint history provider
final sprintHistoryProvider =
    StateNotifierProvider<SprintHistoryNotifier, SprintHistoryState>(
  SprintHistoryNotifier.new,
);

/// Individual sprint history item provider
final sprintHistoryItemProvider =
    FutureProvider.family<SprintHistoryItem?, String>((ref, id) async {
  final historyState = ref.watch(sprintHistoryProvider);

  // Find the item in history
  final item = historyState.items.firstWhere(
    (i) => i.id == id,
    orElse: () => throw Exception('Sprint not found'),
  );

  return item;
});
