import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/shared/entities/subtask_model.dart';

/// Provider for subtask list state
class SubtaskListState {
  const SubtaskListState({
    this.subtasks = const [],
    this.isLoading = false,
    this.error,
  });

  final List<SubTaskModel> subtasks;
  final bool isLoading;
  final String? error;

  int get total => subtasks.length;
  int get completed => subtasks.where((s) => s.isCompleted).length;
  double get progress => total > 0 ? completed / total : 0;

  SubtaskListState copyWith({
    List<SubTaskModel>? subtasks,
    bool? isLoading,
    String? error,
    bool clearError = false,
  }) =>
      SubtaskListState(
        subtasks: subtasks ?? this.subtasks,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : error ?? this.error,
      );
}

/// Subtask list widget
class SubtaskListWidget extends ConsumerStatefulWidget {
  const SubtaskListWidget({
    required this.parentTaskId,
    required this.onSubtaskToggle,
    required this.onSubtaskDelete,
    this.onSubtaskAdd,
    this.onReorder,
    this.readOnly = false,
    super.key,
  });

  final String parentTaskId;
  final void Function(SubTaskModel) onSubtaskToggle;
  final void Function(String) onSubtaskDelete;
  final void Function(String, String)? onSubtaskAdd;
  final void Function(List<SubTaskModel>)? onReorder;
  final bool readOnly;

  @override
  ConsumerState<SubtaskListWidget> createState() => _SubtaskListWidgetState();
}

class _SubtaskListWidgetState extends ConsumerState<SubtaskListWidget> {
  final TextEditingController _titleController = TextEditingController();

  @override
  void dispose() {
    _titleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildProgressIndicator(),
          const SizedBox(height: DS.md),
          if (!widget.readOnly && widget.onSubtaskAdd != null)
            _buildQuickAddInput(),
          const SizedBox(height: DS.md),
          _buildSubtaskList(),
        ],
      );

  Widget _buildProgressIndicator() => Consumer(
        builder: (context, ref, child) => const SizedBox.shrink(),
      );

  Widget _buildQuickAddInput() => Row(
        children: [
          Expanded(
            child: TextField(
              controller: _titleController,
              style: TextStyle(color: DS.brandPrimaryConst, fontSize: 14),
              decoration: InputDecoration(
                hintText: context.l10n.subtaskAddHint,
                hintStyle:
                    TextStyle(color: DS.brandPrimary38Const, fontSize: 14),
                border: InputBorder.none,
                filled: true,
                fillColor: DS.brandPrimary10,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: DS.md,
                  vertical: DS.sm,
                ),
                isDense: true,
              ),
              onSubmitted: (value) {
                if (value.trim().isNotEmpty) {
                  widget.onSubtaskAdd?.call(widget.parentTaskId, value.trim());
                  _titleController.clear();
                }
              },
            ),
          ),
          const SizedBox(width: DS.sm),
          Tooltip(
            message: context.l10n.subtaskAddTooltip,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              size: 36,
              onPressed: () {
                if (_titleController.text.trim().isNotEmpty) {
                  widget.onSubtaskAdd?.call(
                    widget.parentTaskId,
                    _titleController.text.trim(),
                  );
                  _titleController.clear();
                }
              },
              icon: Icon(Icons.add_circle, color: DS.primaryBase),
            ),
          ),
        ],
      );

  Widget _buildSubtaskList() => Consumer(
        builder: (context, ref, child) => _buildEmptyState(),
      );

  Widget _buildEmptyState() => Container(
        padding: const EdgeInsets.all(DS.lg),
        alignment: Alignment.center,
        child: Column(
          children: [
            Icon(
              Icons.checklist,
              size: 48,
              color: DS.brandPrimary38Const,
            ),
            const SizedBox(height: DS.sm),
            Text(
              context.l10n.subtaskEmpty,
              style: TextStyle(
                color: DS.brandPrimary54,
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
}

/// Single subtask item widget
class SubtaskItemWidget extends StatelessWidget {
  const SubtaskItemWidget({
    required this.subtask,
    required this.onToggle,
    required this.onDelete,
    this.onEdit,
    this.isDragging = false,
    super.key,
  });

  final SubTaskModel subtask;
  final VoidCallback onToggle;
  final VoidCallback onDelete;
  final void Function(String)? onEdit;
  final bool isDragging;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: DS.xs),
        decoration: BoxDecoration(
          color: isDragging ? DS.brandPrimary10 : DS.surfaceBase,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: subtask.isCompleted
                ? DS.semanticSuccess.withValues(alpha: 0.3)
                : DS.brandPrimary10,
          ),
        ),
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(
            horizontal: DS.md,
            vertical: DS.xs,
          ),
          leading: Checkbox(
            value: subtask.isCompleted,
            onChanged: (_) => onToggle(),
            activeColor: DS.semanticSuccess,
            checkColor: DS.brandPrimary,
          ),
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                subtask.title,
                style: TextStyle(
                  color:
                      subtask.isCompleted ? DS.brandPrimary38 : DS.brandPrimary,
                  fontSize: 14,
                  decoration:
                      subtask.isCompleted ? TextDecoration.lineThrough : null,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              if (subtask.estimatedMinutes != 25) ...[
                const SizedBox(height: 2),
                Row(
                  children: [
                    Icon(Icons.schedule, size: 12, color: DS.brandPrimary54),
                    const SizedBox(width: 4),
                    Text(
                      '${subtask.estimatedMinutes} 分钟',
                      style: TextStyle(
                        color: DS.brandPrimary54,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
          subtitle: _buildSubtitle(),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.drag_handle, color: DS.brandPrimary38Const, size: 20),
              Tooltip(
                message: context.l10n.delete,
                child: SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  size: 32,
                  icon: Icon(
                    Icons.close,
                    color: DS.brandPrimary38Const,
                    size: 18,
                  ),
                  onPressed: onDelete,
                ),
              ),
            ],
          ),
        ),
      );

  Widget _buildSubtitle() {
    final hasDescription =
        subtask.description != null && subtask.description!.isNotEmpty;
    final hasGuide =
        subtask.guideContent != null && subtask.guideContent!.isNotEmpty;

    if (!hasDescription && !hasGuide) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (hasDescription)
          Text(
            subtask.description!,
            style: TextStyle(
              color: DS.brandPrimary54,
              fontSize: 12,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        if (hasGuide) ...[
          const SizedBox(height: 4),
          Text(
            subtask.guideContent!,
            style: TextStyle(
              color: DS.brandPrimary38,
              fontSize: 11,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ],
    );
  }
}

/// Subtask progress indicator widget
class SubtaskProgressIndicator extends StatelessWidget {
  const SubtaskProgressIndicator({
    required this.completed,
    required this.total,
    this.showLabel = true,
    super.key,
  });

  final int completed;
  final int total;
  final bool showLabel;

  double get progress => total > 0 ? completed / total : 0;

  @override
  Widget build(BuildContext context) {
    if (total == 0) {
      return const SizedBox.shrink();
    }

    return Row(
      children: [
        Expanded(
          child: Stack(
            children: [
              Container(
                height: 4,
                decoration: BoxDecoration(
                  color: DS.brandPrimary10Const,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              FractionallySizedBox(
                widthFactor: progress,
                child: Container(
                  height: 4,
                  decoration: BoxDecoration(
                    color: progress >= 1 ? DS.semanticSuccess : DS.primaryBase,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            ],
          ),
        ),
        if (showLabel) ...[
          const SizedBox(width: DS.sm),
          Text(
            '$completed/$total',
            style: TextStyle(
              color: DS.brandPrimary70Const,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ],
    );
  }
}
