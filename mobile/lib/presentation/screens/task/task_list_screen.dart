import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/animations/staggered_list_animation.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/widgets/task/task_card.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

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
          decoration: const BoxDecoration(
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
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: AppDesignTokens.fontSizeBase,
                  ),
                  decoration: InputDecoration(
                    hintText: '搜索任务...',
                    border: InputBorder.none,
                    hintStyle: TextStyle(
                      color: Colors.white.withOpacity(0.7),
                    ),
                    prefixIcon: const Icon(
                      Icons.search,
                      color: Colors.white70,
                    ),
                  ),
                  onChanged: (value) => setState(() {}),
                )
              : Row(
                  key: const ValueKey('title'),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: AppDesignTokens.borderRadius8,
                      ),
                      child: const Icon(
                        Icons.task_alt_rounded,
                        color: Colors.white,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Text(
                      '我的任务',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: AppDesignTokens.fontWeightBold,
                      ),
                    ),
                  ],
                ),
        ),
        actions: [
          IconButton(
            icon: Icon(_isSearching ? Icons.close_rounded : Icons.search_rounded),
            color: Colors.white,
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
          // TODO: Navigate to create task screen
          // context.push('/tasks/new');
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
          child: const Icon(
            Icons.add_rounded,
            color: Colors.white,
            size: 32,
          ),
        ),
      ),
    );
  }

  Widget _buildTaskList(BuildContext context, TaskListState state, List<TaskModel> tasks, WidgetRef ref) {
    if (state.isLoading && tasks.isEmpty) {
      return const Center(
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
            // context.push('/tasks/new');
          },
        );
      }
    }

    return StaggeredListAnimation(
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
              child: Dismissible(
                key: Key(task.id),
                direction: DismissDirection.horizontal,
                background: Container(
                  color: AppDesignTokens.success,
                  alignment: Alignment.centerLeft,
                  padding: const EdgeInsets.only(left: 20),
                  child: const Icon(Icons.check, color: Colors.white),
                ),
                secondaryBackground: Container(
                  color: AppDesignTokens.error,
                  alignment: Alignment.centerRight,
                  padding: const EdgeInsets.only(right: 20),
                  child: const Icon(Icons.delete, color: Colors.white),
                ),
                confirmDismiss: (direction) async {
                  if (direction == DismissDirection.startToEnd) {
                    HapticFeedback.heavyImpact();
                    await ref.read(taskListProvider.notifier).completeTask(
                      task.id,
                      task.estimatedMinutes,
                      null,
                    );
                    return false;
                  } else {
                    HapticFeedback.mediumImpact();
                    return await showDialog(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        shape: RoundedRectangleBorder(
                          borderRadius: AppDesignTokens.borderRadius20,
                        ),
                        title: const Text(
                          '确认删除',
                          style: TextStyle(
                            fontWeight: AppDesignTokens.fontWeightBold,
                          ),
                        ),
                        content: const Text('确定要删除这个任务吗？此操作无法撤销。'),
                        actions: [
                          CustomButton.text(
                            text: '取消',
                            onPressed: () => Navigator.pop(ctx, false),
                          ),
                          CustomButton.primary(
                            text: '删除',
                            icon: Icons.delete_rounded,
                            onPressed: () => Navigator.pop(ctx, true),
                            customGradient: AppDesignTokens.errorGradient,
                            size: ButtonSize.small,
                          ),
                        ],
                      ),
                    );
                  }
                },
                onDismissed: (direction) {
                  if (direction == DismissDirection.endToStart) {
                    ref.read(taskListProvider.notifier).deleteTask(task.id);
                  }
                },
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4.0), // Padding handled by TaskCard margin mostly
                  child: TaskCard(
                    task: task,
                    onTap: () {
                      context.push('/tasks/${task.id}');
                    },
                  ),
                ),
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
      default:
        return tasks;
    }
  }
}

class _FilterChips extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentFilter = ref.watch(taskFilterProvider);

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12.0, horizontal: 16.0),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: SizedBox(
        height: 40,
        child: ListView(
          scrollDirection: Axis.horizontal,
          children: TaskFilterOptions.values.map((filter) {
            final isSelected = currentFilter == filter;
            return Padding(
              padding: const EdgeInsets.only(right: 8.0),
              child: GestureDetector(
                onTap: () {
                  HapticFeedback.selectionClick();
                  ref.read(taskFilterProvider.notifier).state = filter;
                },
                child: AnimatedContainer(
                  duration: AppDesignTokens.durationFast,
                  padding: const EdgeInsets.symmetric(
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
                            ? Colors.white
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