import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_completion_result.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

class TaskFeedbackDialog extends StatelessWidget {

  const TaskFeedbackDialog({
    required this.result, required this.onClose, super.key,
  });
  final TaskCompletionResult result;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) => Dialog(
      shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius20),
      backgroundColor: DS.brandPrimary,
      child: Padding(
        padding: EdgeInsets.all(AppDesignTokens.spacing20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    gradient: AppDesignTokens.primaryGradient,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.auto_awesome, color: DS.brandPrimaryConst, size: 24),
                ),
                SizedBox(width: AppDesignTokens.spacing12),
                Text(
                  '学习反馈',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: AppDesignTokens.fontWeightBold,
                  ),
                ),
              ],
            ),
            SizedBox(height: AppDesignTokens.spacing20),
            
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
                      strong: TextStyle(fontWeight: FontWeight.bold, color: AppDesignTokens.primaryDark),
                    ),
                  ),
                ),
              )
            else
              Text('任务已完成！继续保持。'),
              
            SizedBox(height: AppDesignTokens.spacing20),
            
            // Stats Updates
            if (result.flameUpdate != null || result.statsUpdate != null)
              Container(
                padding: EdgeInsets.all(AppDesignTokens.spacing12),
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
                        color: DS.brandPrimaryConst,
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

            SizedBox(height: AppDesignTokens.spacing24),
            
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
        SizedBox(height: DS.xs),
        Text(value, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        Text(label, style: TextStyle(color: AppDesignTokens.neutral500, fontSize: 12)),
      ],
    );
}
