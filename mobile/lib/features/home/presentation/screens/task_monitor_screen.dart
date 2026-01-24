import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/shared/entities/background_task_model.dart';

/// Background task state
class BackgroundTaskState {
  const BackgroundTaskState({
    this.tasks = const [],
    this.isLoading = false,
    this.error,
    this.selectedFilter = BackgroundTaskFilter.all,
  });

  final List<BackgroundTaskModel> tasks;
  final bool isLoading;
  final String? error;
  final BackgroundTaskFilter selectedFilter;

  List<BackgroundTaskModel> get filteredTasks {
    switch (selectedFilter) {
      case BackgroundTaskFilter.running:
        return tasks.where((t) => t.isActive).toList();
      case BackgroundTaskFilter.completed:
        return tasks.where((t) => t.isCompleted).toList();
      case BackgroundTaskFilter.failed:
        return tasks.where((t) => t.isFailed).toList();
      case BackgroundTaskFilter.all:
      default:
        return tasks;
    }
  }

  BackgroundTaskState copyWith({
    List<BackgroundTaskModel>? tasks,
    bool? isLoading,
    String? error,
    BackgroundTaskFilter? selectedFilter,
    bool clearError = false,
  }) =>
      BackgroundTaskState(
        tasks: tasks ?? this.tasks,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : error ?? this.error,
        selectedFilter: selectedFilter ?? this.selectedFilter,
      );
}

/// Background task filter
enum BackgroundTaskFilter {
  all('全部'),
  running('运行中'),
  completed('已完成'),
  failed('失败');

  final String label;
  const BackgroundTaskFilter(this.label);
}

/// Background task notifier
class BackgroundTaskNotifier extends StateNotifier<BackgroundTaskState> {
  BackgroundTaskNotifier() : super(const BackgroundTaskState());

  Timer? _pollTimer;

  /// Start polling for updates (every 5 seconds)
  void startPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      // TODO: Fetch latest tasks from API
    });
  }

  /// Stop polling
  void stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  /// Set filter
  void setFilter(BackgroundTaskFilter filter) {
    state = state.copyWith(selectedFilter: filter);
  }

  @override
  void dispose() {
    stopPolling();
    super.dispose();
  }
}

/// Provider for background tasks
final backgroundTaskProvider =
    StateNotifierProvider<BackgroundTaskNotifier, BackgroundTaskState>((ref) => BackgroundTaskNotifier());

/// Task monitor screen
class TaskMonitorScreen extends ConsumerStatefulWidget {
  const TaskMonitorScreen({super.key});

  @override
  ConsumerState<TaskMonitorScreen> createState() => _TaskMonitorScreenState();
}

class _TaskMonitorScreenState extends ConsumerState<TaskMonitorScreen> {
  @override
  void initState() {
    super.initState();
    // Start polling for updates
    ref.read(backgroundTaskProvider.notifier).startPolling();
  }

  @override
  void dispose() {
    ref.read(backgroundTaskProvider.notifier).stopPolling();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(backgroundTaskProvider);
    final filteredTasks = state.filteredTasks;

    return Scaffold(
      backgroundColor: DS.deepSpaceStart,
      appBar: AppBar(
        backgroundColor: DS.deepSpaceStart,
        title: Text(
          '后台任务监控',
          style: TextStyle(color: DS.brandPrimary),
        ),
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new, color: DS.brandPrimary),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Column(
        children: [
          _buildFilterChips(state.selectedFilter),
          Expanded(
            child: state.isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      valueColor: AlwaysStoppedAnimation<Color>(DS.primaryBase),
                    ),
                  )
                : filteredTasks.isEmpty
                    ? _buildEmptyState()
                    : _buildTaskList(filteredTasks),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChips(BackgroundTaskFilter selectedFilter) => Container(
      padding: const EdgeInsets.symmetric(vertical: DS.md, horizontal: DS.sm),
      child: Wrap(
        spacing: DS.sm,
        children: BackgroundTaskFilter.values.map((filter) {
          final isSelected = selectedFilter == filter;
          return FilterChip(
            label: Text(filter.label),
            selected: isSelected,
            onSelected: (_) {
              ref.read(backgroundTaskProvider.notifier).setFilter(filter);
            },
            backgroundColor: DS.brandPrimary10,
            selectedColor: DS.primaryBase.withValues(alpha: 0.3),
            checkmarkColor: DS.primaryBase,
            labelStyle: TextStyle(
              color: isSelected ? DS.primaryBase : DS.brandPrimary70,
              fontSize: 13,
            ),
            side: BorderSide.none,
          );
        }).toList(),
      ),
    );

  Widget _buildEmptyState() => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.task_alt,
            size: 64,
            color: DS.brandPrimary38,
          ),
          const SizedBox(height: DS.md),
          Text(
            '暂无后台任务',
            style: TextStyle(
              color: DS.brandPrimary54,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );

  Widget _buildTaskList(List<BackgroundTaskModel> tasks) => RefreshIndicator(
      onRefresh: () async {
        // TODO: Refresh tasks from API
      },
      color: DS.primaryBase,
      child: ListView.builder(
        padding: const EdgeInsets.all(DS.md),
        itemCount: tasks.length,
        itemBuilder: (context, index) {
          return _buildTaskCard(tasks[index]);
        },
      ),
    );

  Widget _buildTaskCard(BackgroundTaskModel task) => Container(
      margin: const EdgeInsets.only(bottom: DS.md),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.surfaceBase,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _getStatusColor(task.status).withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _buildStatusIcon(task.status),
              const SizedBox(width: DS.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      task.name,
                      style: TextStyle(
                        color: DS.brandPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    if (task.progressMessage != null)
                      Text(
                        task.progressMessage!,
                        style: TextStyle(
                          color: DS.brandPrimary54,
                          fontSize: 13,
                        ),
                      ),
                  ],
                ),
              ),
              _buildStatusChip(task.status),
            ],
          ),
          if (task.isActive || task.isFailed) ...[
            const SizedBox(height: DS.md),
            _buildProgressBar(task),
          ],
          if (task.errorMessage != null && task.isFailed) ...[
            const SizedBox(height: DS.sm),
            Container(
              padding: const EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                color: DS.semanticError.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                task.errorMessage!,
                style: TextStyle(
                  color: DS.semanticError,
                  fontSize: 12,
                ),
              ),
            ),
          ],
          if (task.isFailed) ...[
            const SizedBox(height: DS.sm),
            Row(
              children: [
                TextButton.icon(
                  onPressed: () {
                    // TODO: Retry task
                  },
                  icon: Icon(Icons.refresh, size: 16, color: DS.primaryBase),
                  label: Text(
                    '重试',
                    style: TextStyle(color: DS.primaryBase, fontSize: 13),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );

  Widget _buildStatusIcon(BackgroundTaskStatus status) {
    IconData icon;
    Color color;

    switch (status) {
      case BackgroundTaskStatus.pending:
        icon = Icons.schedule;
        color = DS.brandPrimary38;
      case BackgroundTaskStatus.running:
        icon = Icons.sync;
        color = DS.primaryBase;
      case BackgroundTaskStatus.completed:
        icon = Icons.check_circle;
        color = DS.semanticSuccess;
      case BackgroundTaskStatus.failed:
        icon = Icons.error;
        color = DS.semanticError;
      case BackgroundTaskStatus.cancelled:
        icon = Icons.cancel;
        color = DS.brandPrimary38;
    }

    if (status == BackgroundTaskStatus.running) {
      return SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          valueColor: AlwaysStoppedAnimation<Color>(color),
        ),
      );
    }

    return Icon(icon, color: color, size: 20);
  }

  Widget _buildStatusChip(BackgroundTaskStatus status) {
    String label;
    Color color;

    switch (status) {
      case BackgroundTaskStatus.pending:
        label = '等待中';
        color = DS.brandPrimary38;
      case BackgroundTaskStatus.running:
        label = '运行中';
        color = DS.primaryBase;
      case BackgroundTaskStatus.completed:
        label = '已完成';
        color = DS.semanticSuccess;
      case BackgroundTaskStatus.failed:
        label = '失败';
        color = DS.semanticError;
      case BackgroundTaskStatus.cancelled:
        label = '已取消';
        color = DS.brandPrimary38;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.sm, vertical: DS.xs),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildProgressBar(BackgroundTaskModel task) => Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Row(
          children: [
            Expanded(
              child: Stack(
                children: [
                  Container(
                    height: 4,
                    decoration: BoxDecoration(
                      color: DS.brandPrimary10,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  FractionallySizedBox(
                    widthFactor: task.progress,
                    child: Container(
                      height: 4,
                      decoration: BoxDecoration(
                        color: _getStatusColor(task.status),
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: DS.sm),
            Text(
              '${task.progressPercent}%',
              style: TextStyle(
                color: DS.brandPrimary70,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ],
    );

  Color _getStatusColor(BackgroundTaskStatus status) {
    switch (status) {
      case BackgroundTaskStatus.pending:
        return DS.brandPrimary38;
      case BackgroundTaskStatus.running:
        return DS.primaryBase;
      case BackgroundTaskStatus.completed:
        return DS.semanticSuccess;
      case BackgroundTaskStatus.failed:
        return DS.semanticError;
      case BackgroundTaskStatus.cancelled:
        return DS.brandPrimary38;
    }
  }
}
