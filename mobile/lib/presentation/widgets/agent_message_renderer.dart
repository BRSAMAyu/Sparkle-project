import 'package:flutter/material.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/presentation/widgets/task_card.dart';
import 'package:sparkle/presentation/widgets/knowledge_card.dart';
import 'package:sparkle/presentation/widgets/task_list_widget.dart'; // New widget for task list
import 'package:sparkle/presentation/widgets/plan_card.dart';       // New widget for plan card

/// Agent 消息渲染器
/// 根据消息中的 widgets 字段动态渲染不同类型的组件
class AgentMessageRenderer extends StatelessWidget {
  final ChatMessageModel message;
  final Function(String taskId)? onTaskAction;
  final Function(String actionId, bool confirmed)? onConfirmation;

  const AgentMessageRenderer({
    required this.message, super.key,
    this.onTaskAction,
    this.onConfirmation,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 1. 文本内容（如果有）
        if (message.content.isNotEmpty)
          _buildTextBubble(context, message.content),
        
        // 2. 渲染所有 widgets
        if (message.widgets != null && message.widgets!.isNotEmpty)
          ...message.widgets!.map((widget) => _buildWidget(context, widget)),
        
        // 3. 错误提示（如果有）
        if (message.hasErrors == true && message.errors != null)
          _buildErrorCard(context, message.errors!),
        
        // 4. 确认操作（如果需要）
        if (message.requiresConfirmation == true && 
            message.confirmationData != null)
          _buildConfirmationCard(context, message.confirmationData!),
      ],
    );
  }

  Widget _buildTextBubble(BuildContext context, String text) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(text),
    );
  }

  Widget _buildWidget(BuildContext context, WidgetPayload widget) {
    switch (widget.type) {
      case 'task_card':
        return TaskCard(
          data: widget.data,
          onAction: onTaskAction,
        );
      
      case 'knowledge_card':
        return KnowledgeCard(data: widget.data);
      
      case 'task_list':
        return TaskListWidget(tasks: widget.data['tasks'] as List);
      
      case 'plan_card':
        return PlanCard(data: widget.data);
      
      default:
        // 未知类型：显示 JSON
        return _buildUnknownWidget(widget);
    }
  }

  Widget _buildErrorCard(BuildContext context, List<ErrorInfo> errors) {
    return Card(
      color: Theme.of(context).colorScheme.errorContainer,
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.warning_amber, 
                     color: Theme.of(context).colorScheme.error,),
                const SizedBox(width: 8),
                Text('操作遇到问题', style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
            ),
            const SizedBox(height: 8),
            ...errors.map((e) => Text('• ${e.message}', style: TextStyle(color: Theme.of(context).colorScheme.error))),
            if (errors.any((e) => e.suggestion != null))
              Padding(
                padding: const EdgeInsets.only(top: 8.0),
                child: Text(
                  '建议：${errors.firstWhere((e) => e.suggestion != null).suggestion}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(fontStyle: FontStyle.italic),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildConfirmationCard(
    BuildContext context, 
    ConfirmationData data,
  ) {
    return Card(
      color: Theme.of(context).colorScheme.tertiaryContainer,
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '需要确认',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(data.description),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => onConfirmation?.call(data.actionId, false),
                  child: const Text('取消'),
                ),
                const SizedBox(width: 8),
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
  }

  Widget _buildUnknownWidget(WidgetPayload widget) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Text('Unknown widget type: ${widget.type}'),
      ),
    );
  }
}