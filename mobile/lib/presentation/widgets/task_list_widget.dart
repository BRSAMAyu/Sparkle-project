import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 任务列表组件
/// 用于在聊天中批量显示 AI 生成的任务
class TaskListWidget extends StatelessWidget { // List of Map<String, dynamic>

  const TaskListWidget({
    required this.tasks, super.key,
  });
  final List<dynamic> tasks;

  @override
  Widget build(BuildContext context) {
    if (tasks.isEmpty) {
      return SizedBox.shrink();
    }

    return Card(
      margin: EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: Padding(
        padding: EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '批量创建任务 (${tasks.length}个)',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 10),
            ...tasks.map((taskData) => _buildTaskItem(context, taskData)),
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.bottomRight,
              child: TextButton.icon(
                onPressed: () {
                  // 导航到任务列表页面
                  context.push('/tasks');
                },
                icon: const Icon(Icons.arrow_forward_ios, size: 16),
                label: const Text('查看所有任务'),
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
      padding: EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          _buildTaskIcon(type),
          SizedBox(width: DS.sm),
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ),
          _buildStatusChip(context, status),
          IconButton(
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
      case 'learning': icon = Icons.menu_book; color = DS.brandPrimary;
      case 'training': icon = Icons.fitness_center; color = DS.brandPrimary;
      case 'error_fix': icon = Icons.bug_report; color = DS.error;
      case 'reflection': icon = Icons.psychology; color = Colors.purple;
      case 'social': icon = Icons.people; color = Colors.teal;
      case 'planning': icon = Icons.event_note; color = DS.success;
      default: icon = Icons.task_alt; color = DS.brandPrimary;
    }
    return Icon(icon, size: 24, color: color);
  }

  Widget _buildStatusChip(BuildContext context, String status) {
    Color color;
    String label;
    switch (status) {
      case 'pending': color = DS.brandPrimary; label = '待办';
      case 'in_progress': color = DS.brandPrimary; label = '进行中';
      case 'completed': color = DS.success; label = '已完成';
      case 'abandoned': color = DS.error; label = '已放弃';
      default: color = DS.brandPrimary; label = status;
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