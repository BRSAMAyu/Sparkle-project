import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// State for task drag and drop operations
class TaskDragState {
  const TaskDragState({
    this.draggedTask,
    this.hoveredDate,
    this.isDragging = false,
  });

  final TaskModel? draggedTask;
  final DateTime? hoveredDate;
  final bool isDragging;

  TaskDragState copyWith({
    TaskModel? draggedTask,
    DateTime? hoveredDate,
    bool? isDragging,
    bool clearHovered = false,
  }) =>
      TaskDragState(
        draggedTask: draggedTask ?? this.draggedTask,
        hoveredDate: clearHovered ? null : hoveredDate ?? this.hoveredDate,
        isDragging: isDragging ?? this.isDragging,
      );
}

/// Notifier for task drag and drop operations
class TaskDragNotifier extends StateNotifier<TaskDragState> {
  TaskDragNotifier() : super(const TaskDragState());

  /// Start dragging a task
  void startDrag(TaskModel task) {
    state = TaskDragState(
      draggedTask: task,
      isDragging: true,
    );
  }

  /// Update the hovered date during drag
  void updateHover(DateTime? date) {
    if (state.isDragging) {
      state = state.copyWith(hoveredDate: date);
    }
  }

  /// Handle drop on a specific date
  ///
  /// Returns the task and new due date if successful, null otherwise
  ({TaskModel task, DateTime newDueDate})? dropOnDate(DateTime date) {
    if (!state.isDragging || state.draggedTask == null) {
      return null;
    }

    final task = state.draggedTask!;
    final newDueDate = DateTime(date.year, date.month, date.day);

    // Reset state
    state = const TaskDragState();

    return (task: task, newDueDate: newDueDate);
  }

  /// End the current drag operation
  void endDrag() {
    state = const TaskDragState();
  }

  /// Cancel the current drag operation
  void cancelDrag() {
    state = const TaskDragState();
  }
}

/// Provider for task drag state
final taskDragProvider =
    StateNotifierProvider<TaskDragNotifier, TaskDragState>((ref) => TaskDragNotifier());
