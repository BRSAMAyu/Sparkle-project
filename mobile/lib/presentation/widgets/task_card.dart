import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// 任务卡片组件
/// 用于在聊天中显示 AI 生成的任务
class TaskCard extends StatelessWidget {
  final Map<String, dynamic> data;
  final Function(String taskId)? onAction;

  const TaskCard({
    Key? key,
    required this.data,
    this.onAction,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final taskId = data['id'] as String;
    final title = data['title'] as String;
    final description = data['description'] as String?;
    final taskType = data['type'] as String;
    final status = data['status'] as String;
    final estimatedMinutes = data['estimated_minutes'] as int?;
    final priority = data['priority'] as int? ?? 2;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: InkWell(
        onTap: () => onAction?.call(taskId),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 标题行
              Row(
                children: [
                  _buildTypeIcon(taskType),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  _buildStatusChip(context, status),
                ],
              ),
              
              // 描述
              if (description != null && description.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  description,
                  style: Theme.of(context).textTheme.bodyMedium,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              
              // 底部信息
              const SizedBox(height: 12),
              Row(
                children: [
                  // 预估时间
                  if (estimatedMinutes != null) ...[
                    Icon(Icons.timer_outlined, size: 16, 
                         color: Theme.of(context).hintColor),
                    const SizedBox(width: 4),
                    Text('$estimatedMinutes 分钟'),
                    const SizedBox(width: 16),
                  ],
                  // 优先级
                  ...List.generate(
                    priority,
                    (_) => Icon(Icons.star, size: 14, color: Colors.amber),
                  ),
                  const Spacer(),
                  // 快捷操作按钮
                  if (status == 'pending')
                    TextButton.icon(
                      onPressed: () => _startTask(context, taskId),
                      icon: const Icon(Icons.play_arrow, size: 18),
                      label: const Text('开始'),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTypeIcon(String type) {
    IconData icon;
    Color color;
    
    switch (type) {
      case 'learning':
        icon = Icons.menu_book;
        color = Colors.blue;
        break;
      case 'training':
        icon = Icons.fitness_center;
        color = Colors.orange;
        break;
      case 'error_fix':
        icon = Icons.bug_report;
        color = Colors.red;
        break;
      case 'reflection':
        icon = Icons.psychology;
        color = Colors.purple;
        break;
      case 'social': // Added social
        icon = Icons.people;
        color = Colors.teal;
        break;
      case 'planning': // Added planning
        icon = Icons.event_note;
        color = Colors.green;
        break;
      default:
        icon = Icons.task_alt;
        color = Colors.grey;
    }
    
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(icon, size: 20, color: color),
    );
  }

  Widget _buildStatusChip(BuildContext context, String status) {
    Color color;
    String label;
    
    switch (status) {
      case 'pending':
        color = Colors.grey;
        label = '待办';
        break;
      case 'in_progress':
        color = Colors.blue;
        label = '进行中';
        break;
      case 'completed':
        color = Colors.green;
        label = '已完成';
        break;
      case 'abandoned':
        color = Colors.red;
        label = '已放弃';
        break;
      default:
        color = Colors.grey;
        label = status;
    }
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12),
      ),
    );
  }

  void _startTask(BuildContext context, String taskId) {
    // 导航到任务执行页面
    context.push('/tasks/$taskId/execute');
  }
}