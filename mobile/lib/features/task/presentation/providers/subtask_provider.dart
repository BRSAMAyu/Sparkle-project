import 'package:flutter_riverpod/flutter_riverpod.dart';
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
  final String? error;

  int get total => subtasks.length;
  int get completed => subtasks.where((s) => s.isCompleted).length;
  double get progress => total > 0 ? completed / total : 0.0;

  SubtaskState copyWith({
    List<SubTaskModel>? subtasks,
    bool? isLoading,
    String? error,
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
    loadSubtasks();
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
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
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
      state = state.copyWith(error: e.toString());
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
      state = state.copyWith(error: e.toString());
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
      state = state.copyWith(error: e.toString());
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
      state = state.copyWith(error: e.toString());
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
      state = state.copyWith(error: e.toString());
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
final subtaskStateProvider = Provider.family<SubtaskState, String>((ref, taskId) {
  return ref.watch(subtaskNotifierProvider(taskId));
});
