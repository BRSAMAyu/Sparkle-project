import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/features/task/data/repositories/subtask_repository.dart';
import 'package:sparkle/shared/entities/subtask_model.dart';

/// State for subtask list management
class SubtaskState {
  const SubtaskState({
    this.subtasks = const [],
    this.isLoading = false,
    this.error,
  });

  final List<SubTaskModel> subtasks;
  final bool isLoading;

  /// N15（A-SPEC3）：UI 可达错误字段只存类型化类别（渲染侧经
  /// error_lexicon owner 出人话）；原始异常细节只进 debugPrint 日志。
  final UiErrorCategory? error;

  int get total => subtasks.length;
  int get completed => subtasks.where((s) => s.isCompleted).length;
  double get progress => total > 0 ? completed / total : 0.0;

  SubtaskState copyWith({
    List<SubTaskModel>? subtasks,
    bool? isLoading,
    UiErrorCategory? error,
    bool clearError = false,
  }) =>
      SubtaskState(
        subtasks: subtasks ?? this.subtasks,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : error ?? this.error,
      );
}

/// Notifier for managing subtasks for a specific task
class SubtaskNotifier extends StateNotifier<SubtaskState> {
  SubtaskNotifier(this._repository, this._taskId) : super(const SubtaskState()) {
    unawaited(loadSubtasks());
  }

  final SubtaskRepository _repository;
  final String _taskId;

  /// Load all subtasks for the parent task
  Future<void> loadSubtasks() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final subtasks = await _repository.getSubtasks(_taskId);
      state = state.copyWith(
        subtasks: subtasks,
        isLoading: false,
      );
    } catch (e) {
      debugPrint('[subtask] load failed: $e');
      state = state.copyWith(
        isLoading: false,
        error: categorizeUiError(e),
      );
    }
  }

  /// Add a new subtask
  Future<void> addSubtask(SubTaskCreate subtask) async {
    try {
      final newSubtask = await _repository.createSubtask(_taskId, subtask);
      state = state.copyWith(
        subtasks: [...state.subtasks, newSubtask],
      );
    } catch (e) {
      debugPrint('[subtask] add failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
    }
  }

  /// Toggle subtask completion status
  Future<void> toggleSubtask(SubTaskModel subtask) async {
    final newStatus = subtask.isCompleted
        ? SubTaskStatus.pending
        : SubTaskStatus.completed;

    try {
      final updatedSubtask = await _repository.updateSubtask(
        subtask.id,
        SubTaskUpdate(status: newStatus),
      );

      state = state.copyWith(
        subtasks: state.subtasks
            .map((s) => s.id == updatedSubtask.id ? updatedSubtask : s)
            .toList(),
      );
    } catch (e) {
      debugPrint('[subtask] toggle failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
    }
  }

  /// Update a subtask
  Future<void> updateSubtask(SubTaskModel subtask, SubTaskUpdate update) async {
    try {
      final updatedSubtask = await _repository.updateSubtask(subtask.id, update);
      state = state.copyWith(
        subtasks: state.subtasks
            .map((s) => s.id == updatedSubtask.id ? updatedSubtask : s)
            .toList(),
      );
    } catch (e) {
      debugPrint('[subtask] update failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
    }
  }

  /// Delete a subtask
  Future<void> deleteSubtask(String subtaskId) async {
    try {
      await _repository.deleteSubtask(subtaskId);
      state = state.copyWith(
        subtasks: state.subtasks.where((s) => s.id != subtaskId).toList(),
      );
    } catch (e) {
      debugPrint('[subtask] delete failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
    }
  }

  /// Reorder subtasks
  Future<void> reorderSubtasks(int oldIndex, int newIndex) async {
    if (oldIndex < newIndex) {
      newIndex -= 1;
    }

    final subtasks = List<SubTaskModel>.from(state.subtasks);
    final item = subtasks.removeAt(oldIndex);
    subtasks.insert(newIndex, item);

    // Update state optimistically
    state = state.copyWith(subtasks: subtasks);

    // Persist reorder to backend
    try {
      final reorderItems = subtasks
          .asMap()
          .entries
          .map((e) => SubTaskReorderItem(subtaskId: e.value.id, order: e.key))
          .toList();
      await _repository.reorderSubtasks(reorderItems);
    } catch (e) {
      // Revert on error by reloading
      debugPrint('[subtask] reorder failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
      await loadSubtasks();
    }
  }

  /// Refresh subtasks from server
  Future<void> refresh() async {
    await loadSubtasks();
  }

  /// Clear any error
  void clearError() {
    state = state.copyWith(clearError: true);
  }
}

/// Provider for SubtaskNotifier, parameterized by task ID
final subtaskNotifierProvider =
    StateNotifierProvider.family<SubtaskNotifier, SubtaskState, String>(
  (ref, taskId) {
    final repository = ref.watch(subtaskRepositoryProvider);
    return SubtaskNotifier(repository, taskId);
  },
);

/// Provider to get subtask state for a task (shorthand)
final subtaskStateProvider = Provider.family<SubtaskState, String>((ref, taskId) => ref.watch(subtaskNotifierProvider(taskId)));
