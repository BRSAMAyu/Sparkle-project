import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/scroll_edge_haptics.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/task_card.dart';
import 'package:sparkle/shared/entities/task_model.dart';

enum TaskFilterOptions { all, pending, inProgress, completed }

enum TaskPriorityFilterOptions { all, high, medium, low }

final taskFilterProvider =
    StateProvider<TaskFilterOptions>((ref) => TaskFilterOptions.all);
final taskPriorityFilterProvider = StateProvider<TaskPriorityFilterOptions>(
  (ref) => TaskPriorityFilterOptions.all,
);

class TaskListScreen extends ConsumerStatefulWidget {
  const TaskListScreen({super.key});

  @override
  ConsumerState<TaskListScreen> createState() => _TaskListScreenState();
}

class _TaskListScreenState extends ConsumerState<TaskListScreen> {
  bool _isSearching = false;
  bool _isReorderMode = false;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    ref.listenManual<String?>(
      taskListProvider.select((state) => state.error),
      (previous, next) {
        if (!mounted || next == null || next == previous) {
          return;
        }
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            SparkleSnackBar.error(
              next,
              onRetry: () =>
                  ref.read(taskListProvider.notifier).refreshTasks(),
              retryLabel: context.l10n.retry,
            ),
          );
      },
    );
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final taskListState = ref.watch(taskListProvider);
    final filter = ref.watch(taskFilterProvider);
    final priorityFilter = ref.watch(taskPriorityFilterProvider);
    final canReorder = !_isSearching &&
        filter == TaskFilterOptions.all &&
        priorityFilter == TaskPriorityFilterOptions.all &&
        _searchController.text.isEmpty;

    // Filter tasks based on chips and search query
    var tasks = _filterTasks(taskListState.tasks, filter);
    tasks = _filterTasksByPriority(tasks, priorityFilter);
    if (_searchController.text.isNotEmpty) {
      tasks = tasks
          .where(
            (t) => t.title
                .toLowerCase()
                .contains(_searchController.text.toLowerCase()),
          )
          .toList();
    }

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            if (context.canPop()) {
              context.pop();
              return;
            }
            context.go('/home');
          },
        ),
        title: AnimatedSwitcher(
          duration: DS.durationNormal,
          child: _isSearching
              ? TextField(
                  key: const ValueKey('search'),
                  controller: _searchController,
                  autofocus: true,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: DS.fontSizeBase,
                  ),
                  decoration: InputDecoration(
                    hintText: context.l10n.taskSearchHint,
                    border: InputBorder.none,
                    hintStyle: TextStyle(
                      color: DS.textSecondary,
                    ),
                    prefixIcon: Icon(
                      Icons.search,
                      color: DS.textSecondary,
                    ),
                  ),
                  onChanged: (value) => setState(() {}),
                )
              : Row(
                  key: const ValueKey('title'),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(DS.spacing6),
                      decoration: BoxDecoration(
                        color: DS.brandPrimary.withValues(alpha: 0.2),
                        borderRadius: DS.borderRadius8,
                      ),
                      child: Icon(
                        Icons.task_alt_rounded,
                        color: DS.primaryBase,
                        size: DS.iconSizeSm,
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Text(
                        context.l10n.taskListTitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightBold,
                          fontSize: DS.fontSizeBase,
                        ),
                      ),
                    ),
                  ],
                ),
        ),
        actions: [
          PopupMenuButton<TaskPriorityFilterOptions>(
            tooltip: context.l10n.taskListFilterTooltip,
            initialValue: priorityFilter,
            onSelected: (value) {
              ref.read(taskPriorityFilterProvider.notifier).state = value;
            },
            itemBuilder: (context) => TaskPriorityFilterOptions.values
                .map(
                  (filter) => PopupMenuItem(
                    value: filter,
                    child: Text(_getPriorityFilterLabel(filter)),
                  ),
                )
                .toList(),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: DS.spacing6),
              child: Row(
                children: [
                  Icon(
                    Icons.filter_alt_rounded,
                    size: DS.iconSizeBase,
                    color: DS.textPrimary,
                  ),
                  if (priorityFilter != TaskPriorityFilterOptions.all) ...[
                    const SizedBox(width: DS.spacing4),
                    Text(
                      _getPriorityFilterShortLabel(priorityFilter),
                      style: TextStyle(
                        color: DS.textPrimary,
                        fontSize: DS.fontSizeXs,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          if (canReorder || _isReorderMode)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: Icon(
                _isReorderMode ? Icons.check_rounded : Icons.reorder_rounded,
                size: DS.iconSizeBase,
                color: DS.textPrimary,
              ),
              onPressed: () {
                setState(() {
                  _isReorderMode = !_isReorderMode;
                });
              },
            ),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: Icon(
              _isSearching ? Icons.close_rounded : Icons.search_rounded,
              size: DS.iconSizeBase,
              color: DS.textPrimary,
            ),
            onPressed: () {
              setState(() {
                _isSearching = !_isSearching;
                if (!_isSearching) _searchController.clear();
              });
            },
          ),
        ],
      ),
      floatingActionButton: SparkleIconButton(
        size: 60,
        onPressed: () {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
          context.push('/tasks/new');
        },
        icon: Icon(
          Icons.add_rounded,
          color: DS.textPrimary,
          size: 32,
        ),
      ),
      child: RefreshIndicator(
        onRefresh: () => ref.read(taskListProvider.notifier).refreshTasks(),
        child: ContentConstraint(
          child: Column(
            children: [
              if (!_isSearching) const _FilterChips(),
              if (taskListState.error != null && tasks.isNotEmpty)
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.fromLTRB(
                    DS.spacing16,
                    DS.spacing12,
                    DS.spacing16,
                    0,
                  ),
                  padding: const EdgeInsets.all(DS.spacing12),
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.08),
                    borderRadius: DS.borderRadius12,
                    border: Border.all(
                      color: DS.warning.withValues(alpha: 0.24),
                    ),
                  ),
                  child: Text(
                    context.l10n.taskListPartialErrorHint,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: DS.fontSizeSm,
                    ),
                  ),
                ),
              if (!canReorder && !_isSearching && _isReorderMode)
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.fromLTRB(
                    DS.spacing16,
                    DS.spacing12,
                    DS.spacing16,
                    0,
                  ),
                  padding: const EdgeInsets.all(DS.spacing12),
                  decoration: BoxDecoration(
                    color: DS.info.withValues(alpha: 0.08),
                    borderRadius: DS.borderRadius12,
                    border: Border.all(
                      color: DS.info.withValues(alpha: 0.24),
                    ),
                  ),
                  child: Text(
                    context.l10n.taskListReorderDisabledHint,
                  ),
                ),
              Expanded(
                child: _buildTaskList(
                  context,
                  taskListState,
                  tasks,
                  ref,
                  canReorder: canReorder,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTaskList(
    BuildContext context,
    TaskListState state,
    List<TaskModel> tasks,
    WidgetRef ref, {
    required bool canReorder,
  }) {
    if (state.isLoading && tasks.isEmpty) {
      return const SparkleListSkeleton(count: 5);
    }

    if (state.error != null && state.tasks.isEmpty) {
      return CustomErrorWidget.page(
        context: context,
        message: state.error!,
        onRetry: () => ref.read(taskListProvider.notifier).refreshTasks(),
      );
    }

    if (tasks.isEmpty) {
      if (_searchController.text.isNotEmpty) {
        return EmptyState.noResults(
          searchQuery: _searchController.text,
        );
      } else {
        return EmptyState(
          type: EmptyStateType.noTasks,
          title: context.l10n.taskListEmptyTitle,
          description: context.l10n.taskListEmptyDescription,
          actionText: context.l10n.taskListEmptyAction,
          onAction: () {
            context.push('/tasks/new');
          },
        );
      }
    }

    if (_isReorderMode && canReorder) {
      return ScrollEdgeHaptics(
        child: ReorderableListView.builder(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing6,
            DS.spacing16,
            80,
          ),
          onReorder: (oldIndex, newIndex) async {
            await ref.read(taskListProvider.notifier).reorderTasks(
                  oldIndex,
                  newIndex,
                );
          },
          itemCount: tasks.length,
          buildDefaultDragHandles: false,
          itemBuilder: (context, index) {
            final task = tasks[index];
            return Container(
              key: ValueKey('task-reorder-${task.id}'),
              margin: const EdgeInsets.only(bottom: DS.spacing8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: TaskCard(
                      task: task,
                      compact: true,
                      onTap: () => context.push('/tasks/${task.id}'),
                      onStart: () {
                        ref.read(taskListProvider.notifier).startTask(task.id);
                      },
                      onComplete: () {
                        ref
                            .read(taskListProvider.notifier)
                            .completeTask(task.id, task.estimatedMinutes, null);
                      },
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  ReorderableDragStartListener(
                    index: index,
                    child: Container(
                      margin: const EdgeInsets.only(top: DS.spacing12),
                      padding: const EdgeInsets.all(DS.spacing8),
                      decoration: BoxDecoration(
                        color: DS.surfaceSecondary,
                        borderRadius: DS.borderRadius12,
                      ),
                      child: Icon(
                        Icons.drag_indicator_rounded,
                        color: DS.textSecondary,
                      ),
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      );
    }

    final showSummary = !_isSearching &&
        ref.read(taskFilterProvider) == TaskFilterOptions.all &&
        tasks.length > 2;

    return ScrollEdgeHaptics(
      child: ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(
          parent: BouncingScrollPhysics(),
        ),
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing6,
          DS.spacing16,
          72,
        ),
        itemCount: tasks.length + (showSummary ? 1 : 0),
        separatorBuilder: (_, __) => const SizedBox(height: DS.spacing8),
        itemBuilder: (context, index) {
          if (showSummary && index == 0) {
            return _TaskListSummary(
              totalCount: tasks.length,
              pendingCount: tasks
                  .where((task) => task.status == TaskStatus.pending)
                  .length,
              inProgressCount: tasks
                  .where((task) =>
                      task.status == TaskStatus.inProgress ||
                      task.status == TaskStatus.stuck)
                  .length,
              completedCount: tasks
                  .where((task) => task.status == TaskStatus.completed)
                  .length,
            );
          }
          final task = tasks[index - (showSummary ? 1 : 0)];
          return RepaintBoundary(
            child: TaskCard(
              task: task,
              compact: true,
              onTap: () => context.push('/tasks/${task.id}'),
              onStart: () {
                unawaited(
                  ref.read(taskListProvider.notifier).startTask(task.id),
                );
              },
              onComplete: () {
                unawaited(
                  ref
                      .read(taskListProvider.notifier)
                      .completeTask(task.id, task.estimatedMinutes, null),
                );
              },
            ),
          );
        },
      ),
    );
  }

  List<TaskModel> _filterTasks(
    List<TaskModel> tasks,
    TaskFilterOptions filter,
  ) {
    switch (filter) {
      case TaskFilterOptions.pending:
        return tasks.where((t) => t.status == TaskStatus.pending).toList();
      case TaskFilterOptions.inProgress:
        return tasks
            .where((t) =>
                t.status == TaskStatus.inProgress ||
                t.status == TaskStatus.stuck)
            .toList();
      case TaskFilterOptions.completed:
        return tasks.where((t) => t.status == TaskStatus.completed).toList();
      case TaskFilterOptions.all:
        return tasks;
    }
  }

  List<TaskModel> _filterTasksByPriority(
    List<TaskModel> tasks,
    TaskPriorityFilterOptions filter,
  ) {
    switch (filter) {
      case TaskPriorityFilterOptions.high:
        return tasks.where((t) => t.priority >= 4).toList();
      case TaskPriorityFilterOptions.medium:
        return tasks.where((t) => t.priority >= 2 && t.priority <= 3).toList();
      case TaskPriorityFilterOptions.low:
        return tasks.where((t) => t.priority <= 1).toList();
      case TaskPriorityFilterOptions.all:
        return tasks;
    }
  }

  String _getPriorityFilterLabel(TaskPriorityFilterOptions filter) {
    final l10n = context.l10n;
    switch (filter) {
      case TaskPriorityFilterOptions.all:
        return l10n.taskFilterAll;
      case TaskPriorityFilterOptions.high:
        return l10n.taskPriorityHigh;
      case TaskPriorityFilterOptions.medium:
        return l10n.taskPriorityMedium;
      case TaskPriorityFilterOptions.low:
        return l10n.taskPriorityLow;
    }
  }

  String _getPriorityFilterShortLabel(TaskPriorityFilterOptions filter) {
    final l10n = context.l10n;
    switch (filter) {
      case TaskPriorityFilterOptions.high:
        return l10n.taskPriorityHighShort;
      case TaskPriorityFilterOptions.medium:
        return l10n.taskPriorityMediumShort;
      case TaskPriorityFilterOptions.low:
        return l10n.taskPriorityLowShort;
      case TaskPriorityFilterOptions.all:
        return l10n.taskFilterAll;
    }
  }
}

class _FilterChips extends ConsumerWidget {
  const _FilterChips();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentFilter = ref.watch(taskFilterProvider);

    return Container(
      margin: const EdgeInsets.fromLTRB(
        DS.spacing16,
        DS.spacing8,
        DS.spacing16,
        0,
      ),
      padding: const EdgeInsets.symmetric(
        vertical: DS.spacing4,
        horizontal: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.neutral300.withValues(alpha: 0.4)),
      ),
      child: SizedBox(
        height: 34,
        child: ListView(
          scrollDirection: Axis.horizontal,
          children: TaskFilterOptions.values.map((filter) {
            final isSelected = currentFilter == filter;
            return Padding(
              padding: const EdgeInsets.only(right: DS.spacing8),
              child: GestureDetector(
                onTap: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  );
                  ref.read(taskFilterProvider.notifier).state = filter;
                },
                child: AnimatedContainer(
                  duration: DS.durationFast,
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing12,
                    vertical: DS.spacing6,
                  ),
                  decoration: BoxDecoration(
                    gradient: isSelected ? DS.primaryGradient : null,
                    color: isSelected ? null : DS.surfacePrimary,
                    borderRadius: DS.borderRadius20,
                    border: Border.all(
                      color: isSelected ? Colors.transparent : DS.neutral300,
                      width: 1.5,
                    ),
                    boxShadow: isSelected ? DS.shadowSm : null,
                  ),
                  child: Center(
                    child: Text(
                      _getFilterLabel(context, filter),
                      style: TextStyle(
                        color: isSelected ? DS.brandPrimary : DS.neutral700,
                        fontWeight: isSelected
                            ? DS.fontWeightBold
                            : DS.fontWeightMedium,
                        fontSize: DS.fontSizeSm,
                        height: 1,
                      ),
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  String _getFilterLabel(BuildContext context, TaskFilterOptions filter) {
    final l10n = context.l10n;
    switch (filter) {
      case TaskFilterOptions.all:
        return l10n.taskFilterAll;
      case TaskFilterOptions.pending:
        return l10n.taskStatusPending;
      case TaskFilterOptions.inProgress:
        return l10n.taskStatusInProgress;
      case TaskFilterOptions.completed:
        return l10n.taskStatusCompleted;
    }
  }
}

class _TaskListSummary extends StatelessWidget {
  const _TaskListSummary({
    required this.totalCount,
    required this.pendingCount,
    required this.inProgressCount,
    required this.completedCount,
  });

  final int totalCount;
  final int pendingCount;
  final int inProgressCount;
  final int completedCount;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.neutral300.withValues(alpha: 0.35)),
        ),
        child: Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing6,
          children: [
            _TaskMetricChip(label: l10n.taskFilterAll, value: totalCount, tone: DS.info),
            _TaskMetricChip(
              label: l10n.taskStatusPending,
              value: pendingCount,
              tone: DS.brandPrimary,
            ),
            _TaskMetricChip(
              label: l10n.taskStatusInProgress,
              value: inProgressCount,
              tone: DS.warning,
            ),
            _TaskMetricChip(
              label: l10n.taskStatusCompleted,
              value: completedCount,
              tone: DS.semanticSuccess,
            ),
          ],
        ),
      );
  }
}

class _TaskMetricChip extends StatelessWidget {
  const _TaskMetricChip({
    required this.label,
    required this.value,
    required this.tone,
  });

  final String label;
  final int value;
  final Color tone;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: tone.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: tone.withValues(alpha: 0.2)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: DS.fontSizeXs,
              ),
            ),
            const SizedBox(width: DS.spacing6),
            Text(
              '$value',
              style: TextStyle(
                color: tone,
                fontWeight: DS.fontWeightBold,
                fontSize: DS.fontSizeSm,
              ),
            ),
          ],
        ),
      );
}
