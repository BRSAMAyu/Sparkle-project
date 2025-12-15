import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/animations/staggered_list_animation.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/widgets/task/task_card.dart';
import 'package:sparkle/presentation/widgets/empty_state.dart';
import 'package:sparkle/presentation/widgets/error_widget.dart';
import 'package:sparkle/presentation/widgets/loading_indicator.dart';

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
        title: _isSearching
            ? TextField(
                controller: _searchController,
                autofocus: true,
                decoration: const InputDecoration(
                  hintText: 'Search tasks...',
                  border: InputBorder.none,
                  hintStyle: TextStyle(color: Colors.white70),
                ),
                style: const TextStyle(color: Colors.white),
                onChanged: (value) => setState(() {}),
              )
            : const Text('My Tasks'),
        actions: [
          IconButton(
            icon: Icon(_isSearching ? Icons.close : Icons.search),
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
          // TODO: Navigate to create task screen
          // context.push('/tasks/new');
        },
        child: Container(
          width: 60,
          height: 60,
          decoration: const BoxDecoration(
            gradient: AppDesignTokens.primaryGradient,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Color(0x4DFF6B35), // Primary shadow
                blurRadius: 16,
                offset: Offset(0, 8),
              ),
            ],
          ),
          child: const Icon(Icons.add, color: Colors.white),
        ),
      ),
    );
  }

  Widget _buildTaskList(BuildContext context, TaskListState state, List<TaskModel> tasks, WidgetRef ref) {
    if (state.isLoading && tasks.isEmpty) {
      return const LoadingIndicator(isLoading: true);
    }

    if (state.error != null) {
      return AppErrorWidget(
        message: state.error!,
        onRetry: () => ref.read(taskListProvider.notifier).refreshTasks(),
      );
    }

    if (tasks.isEmpty) {
      return EmptyState(
        message: _searchController.text.isNotEmpty 
            ? 'No tasks found matching "${_searchController.text}"' 
            : 'No tasks found. Create one to get started!',
        icon: Icons.task_alt,
        actionButtonText: 'Create Task',
        onActionPressed: () {
          // context.push('/tasks/new');
        },
      );
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
                    await ref.read(taskListProvider.notifier).completeTask(task.id, task.estimatedMinutes, null);
                    return false; 
                  } else {
                    return await showDialog(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text('Confirm Delete'),
                        content: const Text('Are you sure you want to delete this task?'),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
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

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 16.0),
      child: SizedBox(
        height: 40,
        child: ListView(
          scrollDirection: Axis.horizontal,
          children: TaskFilterOptions.values.map((filter) {
            final isSelected = currentFilter == filter;
            return Padding(
              padding: const EdgeInsets.only(right: 8.0),
              child: ChoiceChip(
                label: Text(
                  filter.name[0].toUpperCase() + filter.name.substring(1),
                  style: TextStyle(
                    color: isSelected ? Colors.white : AppDesignTokens.neutral600,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  ),
                ),
                selected: isSelected,
                selectedColor: Colors.transparent, 
                backgroundColor: AppDesignTokens.neutral100,
                shape: RoundedRectangleBorder(
                  borderRadius: AppDesignTokens.borderRadius16,
                  side: BorderSide(
                    color: isSelected ? Colors.transparent : AppDesignTokens.neutral300,
                  ),
                ),
                onSelected: (selected) {
                  if (selected) {
                    ref.read(taskFilterProvider.notifier).state = filter;
                  }
                },
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}