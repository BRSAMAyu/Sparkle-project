import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/plan/data/repositories/execution_copilot_repository.dart';

class ExecutionCopilotState {
  const ExecutionCopilotState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.error,
    this.copilot = const {},
    this.timeline = const {},
  });

  final bool isLoading;
  final bool isSubmitting;
  final String? error;
  final Map<String, dynamic> copilot;
  final Map<String, dynamic> timeline;

  ExecutionCopilotState copyWith({
    bool? isLoading,
    bool? isSubmitting,
    String? error,
    Map<String, dynamic>? copilot,
    Map<String, dynamic>? timeline,
    bool clearError = false,
  }) =>
      ExecutionCopilotState(
        isLoading: isLoading ?? this.isLoading,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : error ?? this.error,
        copilot: copilot ?? this.copilot,
        timeline: timeline ?? this.timeline,
      );
}

class ExecutionCopilotNotifier extends StateNotifier<ExecutionCopilotState> {
  ExecutionCopilotNotifier(this._repo, this.planId)
      : super(const ExecutionCopilotState()) {
    unawaited(load());
  }

  final ExecutionCopilotRepository _repo;
  final String planId;

  Future<void> load({int days = 7}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final copilot = await _repo.getCopilot(planId);
      final timeline = await _repo.getTimeline(planId, days: days);
      state = state.copyWith(
        isLoading: false,
        copilot: copilot,
        timeline: timeline,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<bool> submitCheckpoint({
    required String status,
    String? taskId,
    String? note,
    int timelineDays = 7,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      await _repo.checkpoint(
        planId: planId,
        status: status,
        taskId: taskId,
        note: note,
      );
      final copilot = await _repo.getCopilot(planId);
      final timeline = await _repo.getTimeline(planId, days: timelineDays);
      state = state.copyWith(
        isSubmitting: false,
        copilot: copilot,
        timeline: timeline,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: e.toString(),
      );
      return false;
    }
  }

  Future<bool> adoptTodayTopActions({
    int take = 3,
    int timelineDays = 7,
  }) async {
    final todayActions =
        (state.copilot['today_actions'] as List<dynamic>?) ?? const <dynamic>[];
    final adoptable =
        todayActions.whereType<Map<String, dynamic>>().take(take).toList();
    if (adoptable.isEmpty) {
      return false;
    }

    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      for (final action in adoptable) {
        final taskId = action['task_id']?.toString();
        await _repo.checkpoint(
          planId: planId,
          status: 'done',
          taskId: taskId,
          note: 'adopted_via_execution_copilot',
        );
      }
      final copilot = await _repo.getCopilot(planId);
      final timeline = await _repo.getTimeline(planId, days: timelineDays);
      state = state.copyWith(
        isSubmitting: false,
        copilot: copilot,
        timeline: timeline,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: e.toString(),
      );
      return false;
    }
  }
}

final executionCopilotProvider = StateNotifierProvider.family<
    ExecutionCopilotNotifier, ExecutionCopilotState, String>(
  (ref, planId) => ExecutionCopilotNotifier(
    ref.watch(executionCopilotRepositoryProvider),
    planId,
  ),
);
