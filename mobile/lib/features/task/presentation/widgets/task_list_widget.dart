import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 任务列表组件
/// 用于在聊天中批量显示 AI 生成的任务
class TaskListWidget extends StatelessWidget {
  // List of Map<String, dynamic>

  const TaskListWidget({
    required this.tasks,
    super.key,
  });
  final List<Map<String, dynamic>> tasks;

  @override
  Widget build(BuildContext context) {
    if (tasks.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.taskBatchCreateTitle(tasks.length),
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 10),
            ...tasks.map((taskData) => _buildTaskItem(context, taskData)),
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.bottomRight,
              child: SparkleButton(
                label: context.l10n.taskViewAll,
                variant: ButtonVariant.ghost,
                icon: const Icon(Icons.arrow_forward_ios, size: 16),
                onPressed: () {
                  // 导航到任务列表页面
                  context.push('/tasks');
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTaskItem(BuildContext context, Map<String, dynamic> taskData) {
    final title = taskData['title'] as String;
    final type = taskData['type'] as String;
    final status = taskData['status'] as String;
    final id = taskData['id'] as String;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          _buildTaskIcon(type),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ),
          _buildStatusChip(context, status),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            size: 32,
            icon: const Icon(Icons.info_outline, size: 20),
            onPressed: () {
              // 导航到任务详情页面
              context.push('/tasks/$id');
            },
          ),
        ],
      ),
    );
  }

  Widget _buildTaskIcon(String type) {
    IconData icon;
    Color color;
    switch (type) {
      case 'learning':
        icon = Icons.menu_book;
        color = DS.brandPrimary;
      case 'training':
        icon = Icons.fitness_center;
        color = DS.brandPrimary;
      case 'error_fix':
        icon = Icons.bug_report;
        color = DS.error;
      case 'reflection':
        icon = Icons.psychology;
        color = DS.rarityEpic;
      case 'social':
        icon = Icons.people;
        color = DS.info;
      case 'planning':
        icon = Icons.event_note;
        color = DS.success;
      default:
        icon = Icons.task_alt;
        color = DS.brandPrimary;
    }
    return Icon(icon, size: 24, color: color);
  }

  Widget _buildStatusChip(BuildContext context, String status) {
    final l10n = context.l10n;
    Color color;
    String label;
    switch (status) {
      case 'pending':
        color = DS.brandPrimary;
        label = l10n.taskStatusPending;
      case 'in_progress':
        color = DS.brandPrimary;
        label = l10n.taskStatusInProgress;
      case 'completed':
        color = DS.success;
        label = l10n.taskStatusCompleted;
      case 'abandoned':
        color = DS.error;
        label = l10n.taskStatusAbandoned;
      default:
        color = DS.brandPrimary;
        label = status;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12),
      ),
    );
  }
}
