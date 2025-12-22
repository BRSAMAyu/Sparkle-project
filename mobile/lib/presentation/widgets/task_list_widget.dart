import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// 任务列表组件
/// 用于在聊天中批量显示 AI 生成的任务
class TaskListWidget extends StatelessWidget {
  final List<dynamic> tasks; // List of Map<String, dynamic>

  const TaskListWidget({
    required this.tasks, super.key,
  });

  @override
  Widget build(BuildContext context) {
    if (tasks.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
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
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          _buildTaskIcon(type),
          const SizedBox(width: 8),
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
      case 'learning': icon = Icons.menu_book; color = Colors.blue; break;
      case 'training': icon = Icons.fitness_center; color = Colors.orange; break;
      case 'error_fix': icon = Icons.bug_report; color = Colors.red; break;
      case 'reflection': icon = Icons.psychology; color = Colors.purple; break;
      case 'social': icon = Icons.people; color = Colors.teal; break;
      case 'planning': icon = Icons.event_note; color = Colors.green; break;
      default: icon = Icons.task_alt; color = Colors.grey; break;
    }
    return Icon(icon, size: 24, color: color);
  }

  Widget _buildStatusChip(BuildContext context, String status) {
    Color color;
    String label;
    switch (status) {
      case 'pending': color = Colors.grey; label = '待办'; break;
      case 'in_progress': color = Colors.blue; label = '进行中'; break;
      case 'completed': color = Colors.green; label = '已完成'; break;
      case 'abandoned': color = Colors.red; label = '已放弃'; break;
      default: color = Colors.grey; label = status; break;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12),
      ),
    );
  }
}