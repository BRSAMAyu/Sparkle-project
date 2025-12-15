import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/widgets/custom_button.dart';
import 'package:sparkle/presentation/widgets/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/error_widget.dart';

class TaskDetailScreen extends ConsumerWidget {
  final String taskId;

  const TaskDetailScreen({required this.taskId, super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskAsync = ref.watch(taskDetailProvider(taskId));

    return Scaffold(
      body: taskAsync.when(
        data: (task) => _TaskDetailView(task: task),
        loading: () => const LoadingIndicator(isLoading: true),
        error: (err, stack) => AppErrorWidget(
          message: 'Failed to load task: $err',
          onRetry: () => ref.refresh(taskDetailProvider(taskId)),
        ),
      ),
    );
  }
}

class _TaskDetailView extends ConsumerWidget {
  final TaskModel task;

  const _TaskDetailView({required this.task});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        Expanded(
          child: CustomScrollView(
            slivers: [
              _buildSliverAppBar(context),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildInfoSection(context),
                      const SizedBox(height: AppDesignTokens.spacing24),
                      Text('Execution Guide', style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: AppDesignTokens.spacing12),
                      _buildGuideSection(context),
                      const SizedBox(height: AppDesignTokens.spacing80), // Space for bottom bar
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        _BottomActionBar(task: task),
      ],
    );
  }

  Widget _buildSliverAppBar(BuildContext context) {
    return SliverAppBar(
      expandedHeight: 200.0,
      pinned: true,
      flexibleSpace: FlexibleSpaceBar(
        background: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                AppDesignTokens.primaryLight.withOpacity(0.8),
                AppDesignTokens.neutral50,
              ],
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
            ),
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(AppDesignTokens.spacing16),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Hero(
                    tag: 'task-title-${task.id}',
                    child: Material(
                      color: Colors.transparent,
                      child: Text(
                        task.title,
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: AppDesignTokens.fontWeightBold,
                          color: AppDesignTokens.neutral900,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: AppDesignTokens.spacing8),
                  Wrap(
                    spacing: AppDesignTokens.spacing8,
                    children: [
                      Chip(
                        label: Text(toBeginningOfSentenceCase(task.type.name) ?? task.type.name),
                        backgroundColor: Colors.white.withOpacity(0.8),
                        avatar: Icon(Icons.category, size: 16, color: AppDesignTokens.primaryBase),
                      ),
                      Chip(
                        label: Text(toBeginningOfSentenceCase(task.status.name) ?? task.status.name),
                        backgroundColor: _getStatusColor(task.status).withOpacity(0.2),
                        labelStyle: TextStyle(color: _getStatusColor(task.status), fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInfoSection(BuildContext context) {
    return Column(
      children: [
        _InfoTileCard(
          icon: Icons.timer_outlined,
          title: 'Estimated Time',
          content: '${task.estimatedMinutes} minutes',
          gradient: AppDesignTokens.primaryGradient,
        ),
        const SizedBox(height: AppDesignTokens.spacing12),
        Row(
          children: [
            Expanded(
              child: _InfoTileCard(
                icon: Icons.star_border,
                title: 'Difficulty',
                content: '${task.difficulty} / 5',
                gradient: AppDesignTokens.warningGradient,
              ),
            ),
            const SizedBox(width: AppDesignTokens.spacing12),
            Expanded(
              child: _InfoTileCard(
                icon: Icons.local_fire_department,
                title: 'Energy',
                content: '${task.energyCost} / 5',
                gradient: AppDesignTokens.errorGradient,
              ),
            ),
          ],
        ),
        if (task.dueDate != null) ...[
          const SizedBox(height: AppDesignTokens.spacing12),
          _InfoTileCard(
            icon: Icons.calendar_today,
            title: 'Due Date',
            content: DateFormat.yMMMd().format(task.dueDate!),
            gradient: AppDesignTokens.infoGradient,
          ),
        ],
      ],
    );
  }

  Widget _buildGuideSection(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppDesignTokens.spacing16),
      decoration: BoxDecoration(
        color: AppDesignTokens.neutral50,
        borderRadius: AppDesignTokens.borderRadius12,
        border: Border.all(color: AppDesignTokens.neutral200),
      ),
      child: MarkdownBody(
        data: task.guideContent ?? 'No guide available for this task.',
        styleSheet: MarkdownStyleSheet(
          h1: Theme.of(context).textTheme.titleLarge,
          p: Theme.of(context).textTheme.bodyMedium,
          code: TextStyle(
            backgroundColor: AppDesignTokens.neutral200,
            fontFamily: 'monospace',
          ),
        ),
      ),
    );
  }

  Color _getStatusColor(TaskStatus status) {
    switch (status) {
      case TaskStatus.pending: return AppDesignTokens.warning;
      case TaskStatus.inProgress: return AppDesignTokens.info;
      case TaskStatus.completed: return AppDesignTokens.success;
      case TaskStatus.abandoned: return AppDesignTokens.neutral500;
    }
  }
}

class _InfoTileCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String content;
  final LinearGradient gradient;

  const _InfoTileCard({
    required this.icon,
    required this.title,
    required this.content,
    required this.gradient,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppDesignTokens.spacing12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: AppDesignTokens.borderRadius12,
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: gradient,
              borderRadius: AppDesignTokens.borderRadius8,
            ),
            child: Icon(icon, color: Colors.white, size: 20),
          ),
          const SizedBox(width: AppDesignTokens.spacing12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppDesignTokens.neutral600)),
                Text(content, style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BottomActionBar extends ConsumerWidget {
  final TaskModel task;
  const _BottomActionBar({required this.task});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 10,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        child: Row(
          children: [
            Expanded(
              child: CustomButton(
                text: 'Edit',
                variant: CustomButtonVariant.secondary,
                onPressed: () {
                  // TODO: Navigate to Edit Screen
                },
              ),
            ),
            const SizedBox(width: AppDesignTokens.spacing16),
            Expanded(
              child: CustomButton(
                text: 'Start',
                variant: CustomButtonVariant.primary,
                onPressed: () {
                  ref.read(activeTaskProvider.notifier).state = task;
                  // TODO: Navigate to execution screen
                   context.push('/tasks/${task.id}/execute');
                },
              ),
            ),
            const SizedBox(width: AppDesignTokens.spacing8),
            IconButton(
              icon: const Icon(Icons.delete_outline, color: AppDesignTokens.error),
              onPressed: () {
                showDialog(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('Delete Task?'),
                    content: const Text('This action cannot be undone.'),
                    shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius16),
                    actions: [
                      TextButton(
                        child: const Text('Cancel'),
                        onPressed: () => Navigator.of(ctx).pop(),
                      ),
                      TextButton(
                        child: const Text('Delete', style: TextStyle(color: AppDesignTokens.error)),
                        onPressed: () {
                          Navigator.of(ctx).pop();
                          ref.read(taskListProvider.notifier).deleteTask(task.id);
                          context.pop(); 
                        },
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}