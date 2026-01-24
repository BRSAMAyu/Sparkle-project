import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/presentation/providers/task_drag_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/task_card.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// A wrapper that makes a TaskCard draggable
///
/// When the user long-presses and drags the card, it can be dropped on a
/// calendar date to update the task's due date.
class DraggableTaskCard extends ConsumerWidget {
  const DraggableTaskCard({
    required this.task,
    this.onTap,
    this.onStart,
    this.onComplete,
    this.compact = false,
    this.enableDrag = true,
    super.key,
  });

  final TaskModel task;
  final VoidCallback? onTap;
  final VoidCallback? onStart;
  final VoidCallback? onComplete;
  final bool compact;
  final bool enableDrag;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (!enableDrag) {
      return TaskCard(
        task: task,
        onTap: onTap,
        onStart: onStart,
        onComplete: onComplete,
        compact: compact,
      );
    }

    return LongPressDraggable<TaskModel>(
      data: task,
      dragAnchorStrategy: pointerDragAnchorStrategy,
      maxSimultaneousDrags: 1,
      onDragStarted: () {
        HapticFeedback.mediumImpact();
        ref.read(taskDragProvider.notifier).startDrag(task);
      },
      onDragEnd: (details) {
        ref.read(taskDragProvider.notifier).endDrag();
      },
      onDragCompleted: () {
        ref.read(taskDragProvider.notifier).endDrag();
      },
      onDraggableCanceled: (velocity, offset) {
        ref.read(taskDragProvider.notifier).cancelDrag();
      },
      feedback: Material(
        elevation: 8,
        borderRadius: BorderRadius.circular(12),
        child: Opacity(
          opacity: 0.8,
          child: Container(
            width: 300,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  DS.primaryBase.withValues(alpha: 0.1),
                  DS.surfaceBase,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: DS.primaryBase.withValues(alpha: 0.5),
                width: 2,
              ),
              boxShadow: [
                BoxShadow(
                  color: DS.primaryBase.withValues(alpha: 0.3),
                  blurRadius: 12,
                  spreadRadius: 4,
                ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 4,
                  height: 40,
                  decoration: BoxDecoration(
                    color: DS.primaryBase,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        task.title,
                        style: TextStyle(
                          color: DS.brandPrimary,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(Icons.calendar_today,
                              size: 12, color: DS.brandPrimary54,),
                          const SizedBox(width: 4),
                          Text(
                            task.dueDate != null
                                ? '${task.dueDate!.month}月${task.dueDate!.day}日'
                                : '未设置',
                            style: TextStyle(
                              color: DS.brandPrimary54,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                Icon(Icons.drag_indicator, color: DS.brandPrimary38, size: 20),
              ],
            ),
          ),
        ),
      ),
      childWhenDragging: Opacity(
        opacity: 0.4,
        child: TaskCard(
          task: task,
          onTap: onTap,
          onStart: onStart,
          onComplete: onComplete,
          compact: compact,
        ),
      ),
      child: Stack(
        children: [
          TaskCard(
            task: task,
            onTap: onTap,
            onStart: onStart,
            onComplete: onComplete,
            compact: compact,
          ),
          // Drag handle indicator
          Positioned(
            top: 8,
            right: 8,
            child: Icon(
              Icons.drag_indicator,
              color: DS.brandPrimary38.withValues(alpha: 0.5),
              size: 16,
            ),
          ),
        ],
      ),
    );
  }
}

/// A drag target widget for calendar cells
///
/// Wrap calendar day cells with this widget to allow task drop.
class CalendarDayDragTarget extends ConsumerWidget {
  const CalendarDayDragTarget({
    required this.date,
    required this.child,
    this.onTaskDropped,
    super.key,
  });

  final DateTime date;
  final Widget child;
  final Function(TaskModel task, DateTime newDueDate)? onTaskDropped;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dragState = ref.watch(taskDragProvider);
    final isHovered = dragState.isDragging &&
        dragState.hoveredDate != null &&
        _isSameDay(dragState.hoveredDate!, date);

    return DragTarget<TaskModel>(
      onWillAcceptWithDetails: (details) {
        ref.read(taskDragProvider.notifier).updateHover(date);
        return true;
      },
      onMove: (details) {
        ref.read(taskDragProvider.notifier).updateHover(date);
      },
      onLeave: (data) {
        // Clear hover when leaving
      },
      onAcceptWithDetails: (details) {
        final result =
            ref.read(taskDragProvider.notifier).dropOnDate(date);
        if (result != null) {
          onTaskDropped?.call(result.task, result.newDueDate);
        }
      },
      builder: (context, candidateData, rejectedData) => Container(
          decoration: isHovered
              ? BoxDecoration(
                  border: Border.all(
                    color: DS.primaryBase.withValues(alpha: 0.8),
                    width: 2,
                  ),
                  borderRadius: BorderRadius.circular(8),
                )
              : null,
          child: child,
        ),
    );
  }

  bool _isSameDay(DateTime a, DateTime b) => a.year == b.year && a.month == b.month && a.day == b.day;
}
