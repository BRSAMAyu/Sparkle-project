import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/knowledge/presentation/widgets/knowledge_card.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_card.dart'; // New widget for plan card
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Agent 消息渲染器
/// 根据消息中的 widgets 字段动态渲染不同类型的组件
class AgentMessageRenderer extends StatelessWidget {
  const AgentMessageRenderer({
    required this.message,
    super.key,
    this.onTaskAction,
    this.onConfirmation,
  });
  final ChatMessageModel message;
  final Function(String taskId)? onTaskAction;
  final Function(String actionId, bool confirmed)? onConfirmation;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. 文本内容（如果有）
          if (message.content.isNotEmpty)
            _buildTextBubble(context, message.content),

          // 2. 渲染所有 widgets
          if (message.widgets != null && message.widgets!.isNotEmpty)
            ...message.widgets!.map((widget) => _buildWidget(context, widget)),

          // 3. 错误提示（如果有）
          if ((message.hasErrors ?? false) && message.errors != null)
            _buildErrorCard(context, message.errors!),

          // 4. 确认操作（如果需要）
          if ((message.requiresConfirmation ?? false) &&
              message.confirmationData != null)
            _buildConfirmationCard(context, message.confirmationData!),
        ],
      );

  Widget _buildTextBubble(BuildContext context, String text) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(text),
      );

  Widget _buildWidget(BuildContext context, WidgetPayload widget) {
    switch (widget.type) {
      case 'task_card':
        try {
          // Ensure mandatory fields for TaskModel are present
          final data = Map<String, dynamic>.from(widget.data);
          data['user_id'] ??= 'unknown';
          data['tags'] ??= <String>[];
          data['difficulty'] ??= 1;
          data['energy_cost'] ??= 1;
          data['priority'] ??= 1;
          data['created_at'] ??= DateTime.now().toIso8601String();
          data['updated_at'] ??= DateTime.now().toIso8601String();

          // Handle 'type' mapping if it's a string that might not match exactly or needs defaulting
          // Assuming the backend/LLM sends correct string matching the enum (e.g., "learning")

          final task = TaskModel.fromJson(data);
          return TaskCard(
            task: task,
            onTap: () => onTaskAction?.call(task.id),
          );
        } catch (e) {
          debugPrint('Error parsing TaskModel in AgentMessageRenderer: $e');
          return Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(DS.sm),
              child: Text('Invalid task data: $e'),
            ),
          );
        }

      case 'knowledge_card':
        return KnowledgeCard(data: widget.data);

      case 'task_list':
        final rawTasks = widget.data['tasks'] as List<dynamic>?;
        return TaskListWidget(
          tasks: (rawTasks ?? <dynamic>[])
              .whereType<Map<String, dynamic>>()
              .toList(),
        );

      case 'plan_card':
        return PlanCard(data: widget.data);

      default:
        // 未知类型：显示 JSON
        return _buildUnknownWidget(widget);
    }
  }

  Widget _buildErrorCard(BuildContext context, List<ErrorInfo> errors) => Card(
        color: Theme.of(context).colorScheme.errorContainer,
        margin: const EdgeInsets.symmetric(vertical: 8),
        child: Padding(
          padding: const EdgeInsets.all(DS.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.warning_amber,
                    color: Theme.of(context).colorScheme.error,
                  ),
                  const SizedBox(width: DS.sm),
                  Text('操作遇到问题',
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.error,),),
                ],
              ),
              const SizedBox(height: DS.sm),
              ...errors.map((e) => Text('• ${e.message}',
                  style:
                      TextStyle(color: Theme.of(context).colorScheme.error),),),
              if (errors.any((e) => e.suggestion != null))
                Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: Text(
                    '建议：${errors.firstWhere((e) => e.suggestion != null).suggestion}',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(fontStyle: FontStyle.italic),
                  ),
                ),
            ],
          ),
        ),
      );

  Widget _buildConfirmationCard(
    BuildContext context,
    ConfirmationData data,
  ) =>
      Card(
        color: Theme.of(context).colorScheme.tertiaryContainer,
        margin: const EdgeInsets.symmetric(vertical: 8),
        child: Padding(
          padding: const EdgeInsets.all(DS.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '需要确认',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: DS.sm),
              Text(data.description),
              const SizedBox(height: DS.md),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => onConfirmation?.call(data.actionId, false),
                    child: const Text('取消'),
                  ),
                  const SizedBox(width: DS.sm),
                  ElevatedButton(
                    onPressed: () => onConfirmation?.call(data.actionId, true),
                    child: const Text('确认执行'),
                  ),
                ],
              ),
            ],
          ),
        ),
      );

  Widget _buildUnknownWidget(WidgetPayload widget) => Card(
        margin: const EdgeInsets.symmetric(vertical: 8),
        child: Padding(
          padding: const EdgeInsets.all(DS.sm),
          child: Text('Unknown widget type: ${widget.type}'),
        ),
      );
}
