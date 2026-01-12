import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';

class TaskFeedbackDialog extends StatelessWidget {
  const TaskFeedbackDialog({
    required this.result,
    required this.onClose,
    super.key,
  });
  final TaskCompletionResult result;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) => Dialog(
        shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius20),
        backgroundColor: DS.brandPrimary,
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(DS.sm),
                    decoration: BoxDecoration(
                      gradient: DS.primaryGradient,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.auto_awesome,
                        color: DS.brandPrimaryConst, size: 24,),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Text(
                    '学习反馈',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing20),

              // Content
              if (result.feedback != null)
                Container(
                  constraints: const BoxConstraints(maxHeight: 300),
                  child: SingleChildScrollView(
                    child: MarkdownBody(
                      data: result.feedback!,
                      styleSheet: MarkdownStyleSheet(
                        p: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              fontSize: DS.fontSizeBase,
                              height: 1.5,
                            ),
                        strong: TextStyle(
                            fontWeight: FontWeight.bold, color: DS.primaryDark,),
                      ),
                    ),
                  ),
                )
              else
                const Text('任务已完成！继续保持。'),

              const SizedBox(height: DS.spacing20),

              // Stats Updates
              if (result.flameUpdate != null || result.statsUpdate != null)
                Container(
                  padding: const EdgeInsets.all(DS.spacing12),
                  decoration: BoxDecoration(
                    color: DS.neutral50,
                    borderRadius: DS.borderRadius12,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      if (result.flameUpdate != null)
                        _StatItem(
                          icon: Icons.local_fire_department,
                          color: DS.brandPrimaryConst,
                          value:
                              "+${result.flameUpdate!['brightness_change']}%",
                          label: '亮度',
                        ),
                      if (result.statsUpdate != null)
                        _StatItem(
                          icon: Icons.emoji_events,
                          color: Colors.amber,
                          value: "${result.statsUpdate!['streak_days']}天",
                          label: '连胜',
                        ),
                    ],
                  ),
                ),

              const SizedBox(height: DS.spacing24),

              CustomButton.primary(
                text: '太棒了',
                onPressed: onClose,
              ),
            ],
          ),
        ),
      );
}

class _StatItem extends StatelessWidget {
  const _StatItem({
    required this.icon,
    required this.color,
    required this.value,
    required this.label,
  });
  final IconData icon;
  final Color color;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Icon(icon, color: color),
          const SizedBox(height: DS.xs),
          Text(value,
              style:
                  const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),),
          Text(label, style: TextStyle(color: DS.neutral500, fontSize: 12)),
        ],
      );
}
