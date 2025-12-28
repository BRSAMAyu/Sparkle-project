import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_completion_result.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

class TaskFeedbackDialog extends StatelessWidget {
  final TaskCompletionResult result;
  final VoidCallback onClose;

  const TaskFeedbackDialog({
    required this.result, required this.onClose, super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius20),
      backgroundColor: DS.brandPrimary,
      child: Padding(
        padding: const EdgeInsets.all(AppDesignTokens.spacing20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.sm),
                  decoration: const BoxDecoration(
                    gradient: AppDesignTokens.primaryGradient,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.auto_awesome, color: DS.brandPrimary, size: 24),
                ),
                const SizedBox(width: AppDesignTokens.spacing12),
                Text(
                  '学习反馈',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: AppDesignTokens.fontWeightBold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppDesignTokens.spacing20),
            
            // Content
            if (result.feedback != null)
              Container(
                constraints: const BoxConstraints(maxHeight: 300),
                child: SingleChildScrollView(
                  child: MarkdownBody(
                    data: result.feedback!,
                    styleSheet: MarkdownStyleSheet(
                      p: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontSize: AppDesignTokens.fontSizeBase,
                        height: 1.5,
                      ),
                      strong: const TextStyle(fontWeight: FontWeight.bold, color: AppDesignTokens.primaryDark),
                    ),
                  ),
                ),
              )
            else
              const Text('任务已完成！继续保持。'),
              
            const SizedBox(height: AppDesignTokens.spacing20),
            
            // Stats Updates
            if (result.flameUpdate != null || result.statsUpdate != null)
              Container(
                padding: const EdgeInsets.all(AppDesignTokens.spacing12),
                decoration: BoxDecoration(
                  color: AppDesignTokens.neutral50,
                  borderRadius: AppDesignTokens.borderRadius12,
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    if (result.flameUpdate != null)
                      _StatItem(
                        icon: Icons.local_fire_department,
                        color: Colors.orange,
                        value: "+${result.flameUpdate!['brightness_change']}%",
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

            const SizedBox(height: AppDesignTokens.spacing24),
            
            CustomButton.primary(
              text: '太棒了',
              onPressed: onClose,
            ),
          ],
        ),
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String value;
  final String label;

  const _StatItem({
    required this.icon,
    required this.color,
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: color),
        const SizedBox(height: DS.xs),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        Text(label, style: const TextStyle(color: AppDesignTokens.neutral500, fontSize: 12)),
      ],
    );
  }
}
