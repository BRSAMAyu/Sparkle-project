import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/animations/staggered_responsive_grid.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/task/task_card.dart';

enum TaskFilterOptions { all, pending, inProgress, completed }

final taskFilterProvider = StateProvider<TaskFilterOptions>((ref) => TaskFilterOptions.all);

class TaskListScreen extends ConsumerStatefulWidget {
  const TaskListScreen({super.key});

  @override
  ConsumerState<TaskListScreen> createState() => _TaskListScreenState();
}

class _TaskListScreenState extends ConsumerState<TaskListScreen> {
  bool _isSearching = false;
  final TextEditingController _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final taskListState = ref.watch(taskListProvider);
    final filter = ref.watch(taskFilterProvider);
    
    // Filter tasks based on chips and search query
    var tasks = _filterTasks(taskListState.tasks, filter);
    if (_searchController.text.isNotEmpty) {
      tasks = tasks.where((t) => t.title.toLowerCase().contains(_searchController.text.toLowerCase())).toList();
    }

    return Scaffold(
      appBar: AppBar(
        flexibleSpace: Container(
          decoration: BoxDecoration(
            gradient: AppDesignTokens.primaryGradient,
          ),
        ),
        title: AnimatedSwitcher(
          duration: AppDesignTokens.durationNormal,
          child: _isSearching
              ? TextField(
                  key: const ValueKey('search'),
                  controller: _searchController,
                  autofocus: true,
                  style: TextStyle(
                    color: DS.brandPrimaryConst,
                    fontSize: AppDesignTokens.fontSizeBase,
                  ),
                  decoration: InputDecoration(
                    hintText: '搜索任务...',
                    border: InputBorder.none,
                    hintStyle: TextStyle(
                      color: DS.brandPrimary.withValues(alpha: 0.7),
                    ),
                    prefixIcon: Icon(
                      Icons.search,
                      color: DS.brandPrimary70Const,
                    ),
                  ),
                  onChanged: (value) => setState(() {}),
                )
              : Row(
                  key: const ValueKey('title'),
                  children: [
                    Container(
                      padding: EdgeInsets.all(DS.sm),
                      decoration: BoxDecoration(
                        color: DS.brandPrimary.withValues(alpha: 0.2),
                        borderRadius: AppDesignTokens.borderRadius8,
                      ),
                      child: Icon(
                        Icons.task_alt_rounded,
                        color: DS.brandPrimaryConst,
                        size: 20,
                      ),
                    ),
                    SizedBox(width: DS.md),
                    Text(
                      '我的任务',
                      style: TextStyle(
                        color: DS.brandPrimaryConst,
                        fontWeight: AppDesignTokens.fontWeightBold,
                      ),
                    ),
                  ],
                ),
        ),
        actions: [
          IconButton(
            icon: Icon(_isSearching ? Icons.close_rounded : Icons.search_rounded),
            color: DS.brandPrimaryConst,
            onPressed: () {
              setState(() {
                _isSearching = !_isSearching;
                if (!_isSearching) _searchController.clear();
              });
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(taskListProvider.notifier).refreshTasks(),
        child: Column(
          children: [
            if (!_isSearching) _FilterChips(),
            Expanded(
              child: _buildTaskList(context, taskListState, tasks, ref),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          HapticFeedback.mediumImpact();
          context.push('/tasks/new');
        },
        backgroundColor: Colors.transparent,
        elevation: 0,
        child: Container(
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            gradient: AppDesignTokens.primaryGradient,
            shape: BoxShape.circle,
            boxShadow: AppDesignTokens.shadowPrimary,
          ),
          child: Icon(
            Icons.add_rounded,
            color: DS.brandPrimaryConst,
            size: 32,
          ),
        ),
      ),
    );
  }

  Widget _buildTaskList(BuildContext context, TaskListState state, List<TaskModel> tasks, WidgetRef ref) {
    if (state.isLoading && tasks.isEmpty) {
      return Center(
        child: LoadingIndicator.circular(
          showText: true,
          loadingText: '加载任务中...',
        ),
      );
    }

    if (state.error != null) {
      return CustomErrorWidget.page(
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
        return EmptyState.noTasks(
          onCreateTask: () {
            context.push('/tasks/new');
          },
        );
      }
    }

    return StaggeredResponsiveGrid(
      itemCount: tasks.length,
      builder: (context, index, animation) {
        final task = tasks[index];
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.1),
              end: Offset.zero,
            ).animate(animation),
            child: RepaintBoundary(
              child: TaskCard(
                task: task,
                onTap: () {
                  context.push('/tasks/${task.id}');
                },
                onStart: () {
                   // Handle start
                   ref.read(taskListProvider.notifier).startTask(task.id);
                },
                onComplete: () {
                   // Handle complete
                   ref.read(taskListProvider.notifier).completeTask(task.id, task.estimatedMinutes, null);
                },
              ),
            ),
          ),
        );
      },
    );
  }

  List<TaskModel> _filterTasks(List<TaskModel> tasks, TaskFilterOptions filter) {
    switch (filter) {
      case TaskFilterOptions.pending:
        return tasks.where((t) => t.status == TaskStatus.pending).toList();
      case TaskFilterOptions.inProgress:
        return tasks.where((t) => t.status == TaskStatus.inProgress).toList();
      case TaskFilterOptions.completed:
        return tasks.where((t) => t.status == TaskStatus.completed).toList();
      case TaskFilterOptions.all:
        return tasks;
    }
  }
}

class _FilterChips extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentFilter = ref.watch(taskFilterProvider);

    return Container(
      padding: EdgeInsets.symmetric(vertical: 12.0, horizontal: 16.0),
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: SizedBox(
        height: 40,
        child: ListView(
          scrollDirection: Axis.horizontal,
          children: TaskFilterOptions.values.map((filter) {
            final isSelected = currentFilter == filter;
            return Padding(
              padding: EdgeInsets.only(right: 8.0),
              child: GestureDetector(
                onTap: () {
                  HapticFeedback.selectionClick();
                  ref.read(taskFilterProvider.notifier).state = filter;
                },
                child: AnimatedContainer(
                  duration: AppDesignTokens.durationFast,
                  padding: EdgeInsets.symmetric(
                    horizontal: AppDesignTokens.spacing16,
                    vertical: AppDesignTokens.spacing8,
                  ),
                  decoration: BoxDecoration(
                    gradient: isSelected ? AppDesignTokens.primaryGradient : null,
                    color: isSelected ? null : AppDesignTokens.neutral100,
                    borderRadius: AppDesignTokens.borderRadius20,
                    border: Border.all(
                      color: isSelected
                          ? Colors.transparent
                          : AppDesignTokens.neutral300,
                      width: 1.5,
                    ),
                    boxShadow: isSelected ? AppDesignTokens.shadowSm : null,
                  ),
                  child: Center(
                    child: Text(
                      _getFilterLabel(filter),
                      style: TextStyle(
                        color: isSelected
                            ? DS.brandPrimary
                            : AppDesignTokens.neutral700,
                        fontWeight: isSelected
                            ? AppDesignTokens.fontWeightBold
                            : AppDesignTokens.fontWeightMedium,
                        fontSize: AppDesignTokens.fontSizeSm,
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

  String _getFilterLabel(TaskFilterOptions filter) {
    switch (filter) {
      case TaskFilterOptions.all:
        return '全部';
      case TaskFilterOptions.pending:
        return '待办';
      case TaskFilterOptions.inProgress:
        return '进行中';
      case TaskFilterOptions.completed:
        return '已完成';
    }
  }
}