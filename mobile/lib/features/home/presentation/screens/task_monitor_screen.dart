import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/response_parser.dart';
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
  all,
  running,
  completed,
  failed;

  String label(BuildContext context) {
    switch (this) {
      case BackgroundTaskFilter.all:
        return context.l10n.taskMonitorFilterAll;
      case BackgroundTaskFilter.running:
        return context.l10n.taskMonitorFilterRunning;
      case BackgroundTaskFilter.completed:
        return context.l10n.taskMonitorFilterCompleted;
      case BackgroundTaskFilter.failed:
        return context.l10n.taskMonitorFilterFailed;
    }
  }
}

/// Background task notifier
class BackgroundTaskNotifier extends StateNotifier<BackgroundTaskState> {
  BackgroundTaskNotifier(this._apiClient) : super(const BackgroundTaskState());

  final ApiClient _apiClient;
  Timer? _pollTimer;
  StreamSubscription<SSEEvent>? _streamSubscription;

  Future<void> fetchTasks() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final response = await _apiClient.get<dynamic>('/background-tasks');
      final items = ApiResponseParser.unwrapList(
        response.data,
        action: 'fetchBackgroundTasks',
      );
      final tasks = items
          .whereType<Map<String, dynamic>>()
          .map(BackgroundTaskModel.fromJson)
          .toList();
      state = state.copyWith(tasks: tasks, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void _startRealtimeStream() {
    if (_streamSubscription != null) {
      unawaited(_streamSubscription!.cancel());
    }
    _streamSubscription = _apiClient
        .getStream('/background-tasks/stream/events')
        .listen(_handleRealtimeEvent);
  }

  void _handleRealtimeEvent(SSEEvent event) {
    if (event.event != 'task_update') return;
    final payload = event.jsonData;
    final taskJson = payload?['task'];
    if (taskJson is! Map<String, dynamic>) return;
    final incoming = BackgroundTaskModel.fromJson(taskJson);
    final current = [...state.tasks];
    final index = current.indexWhere((item) => item.id == incoming.id);
    if (index >= 0) {
      current[index] = incoming;
    } else {
      current.insert(0, incoming);
    }
    state = state.copyWith(tasks: current);
  }

  Future<void> retryTask(String taskId) async {
    try {
      await _apiClient.post<dynamic>('/background-tasks/$taskId/retry');
      await fetchTasks();
    } catch (error, stackTrace) {
      debugPrint('TaskMonitor retryTask failed: $error');
      debugPrintStack(stackTrace: stackTrace);
    }
  }

  /// Start polling for updates (every 5 seconds)
  void startPolling() {
    _pollTimer?.cancel();
    unawaited(fetchTasks());
    _startRealtimeStream();
    _pollTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => unawaited(fetchTasks()),
    );
  }

  /// Stop polling
  void stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
    if (_streamSubscription != null) {
      unawaited(_streamSubscription!.cancel());
    }
    _streamSubscription = null;
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
    StateNotifierProvider<BackgroundTaskNotifier, BackgroundTaskState>(
  (ref) => BackgroundTaskNotifier(ref.watch(apiClientProvider)),
);

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

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.taskMonitorTitle),
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back_ios_new),
          onPressed: () => Navigator.pop(context),
          variant: ButtonVariant.ghost,
        ),
      ),
      child: ContentConstraint(
        child: Column(
          children: [
            _buildFilterChips(state.selectedFilter),
            Expanded(
              child: state.isLoading
                  ? Center(
                      child: CircularProgressIndicator(
                        valueColor:
                            AlwaysStoppedAnimation<Color>(DS.primaryBase),
                      ),
                    )
                  : filteredTasks.isEmpty
                      ? _buildEmptyState()
                      : _buildTaskList(filteredTasks),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterChips(BackgroundTaskFilter selectedFilter) => Builder(
        builder: (context) => Container(
          padding:
              const EdgeInsets.symmetric(vertical: DS.md, horizontal: DS.sm),
          child: Wrap(
            spacing: DS.sm,
            children: BackgroundTaskFilter.values.map((filter) {
              final isSelected = selectedFilter == filter;
              return FilterChip(
                label: Text(filter.label(context)),
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
        ),
      );

  Widget _buildEmptyState() => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.task_alt,
              size: 64,
              color: DS.brandPrimary38Const,
            ),
            const SizedBox(height: DS.md),
            Text(
              context.l10n.taskMonitorEmpty,
              style: TextStyle(
                color: DS.brandPrimary54,
                fontSize: 16,
              ),
            ),
          ],
        ),
      );

  Widget _buildTaskList(List<BackgroundTaskModel> tasks) =>
      SparkleRefreshIndicator(
        onRefresh: () => ref.read(backgroundTaskProvider.notifier).fetchTasks(),
        child: ListView.builder(
          padding: const EdgeInsets.all(DS.md),
          itemCount: tasks.length,
          itemBuilder: (context, index) => _buildTaskCard(tasks[index]),
        ),
      );

  Widget _buildTaskCard(BackgroundTaskModel task) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        margin: const EdgeInsets.only(bottom: DS.md),
        padding: const EdgeInsets.all(DS.md),
        borderColor: _getStatusColor(task.status).withValues(alpha: 0.3),
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
                          color: DS.brandPrimaryConst,
                          fontSize: 16,
                          fontWeight: DS.fontWeightBold,
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
                _buildStatusChip(task.status, context),
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
                    onPressed: () => ref
                        .read(backgroundTaskProvider.notifier)
                        .retryTask(task.id),
                    icon: Icon(Icons.refresh, size: 16, color: DS.primaryBase),
                    label: Text(
                      context.l10n.commonRetry,
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

  Widget _buildStatusChip(BackgroundTaskStatus status, BuildContext context) {
    String label;
    Color color;

    switch (status) {
      case BackgroundTaskStatus.pending:
        label = context.l10n.taskMonitorStatusPending;
        color = DS.brandPrimary38;
      case BackgroundTaskStatus.running:
        label = context.l10n.taskMonitorFilterRunning;
        color = DS.primaryBase;
      case BackgroundTaskStatus.completed:
        label = context.l10n.taskMonitorFilterCompleted;
        color = DS.semanticSuccess;
      case BackgroundTaskStatus.failed:
        label = context.l10n.taskMonitorFilterFailed;
        color = DS.semanticError;
      case BackgroundTaskStatus.cancelled:
        label = context.l10n.taskMonitorStatusCancelled;
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
          fontWeight: DS.fontWeightMedium,
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
                        color: DS.brandPrimary10Const,
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
                  color: DS.brandPrimary70Const,
                  fontSize: 12,
                  fontWeight: DS.fontWeightMedium,
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
