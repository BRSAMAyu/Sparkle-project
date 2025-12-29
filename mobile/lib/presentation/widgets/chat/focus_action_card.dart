import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

class FocusActionCard extends StatelessWidget {
  const FocusActionCard({required this.data, super.key});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final title = data['title'] as String? ?? '专注冲刺';
    final reason = data['reason'] as String?;
    final duration = (data['duration_minutes'] as int?) ?? 25;
    final taskModel = _buildTaskModel(title, duration);

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing8),
                  decoration: BoxDecoration(
                    gradient: DS.secondaryGradient,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.timer_rounded, color: DS.brandPrimaryConst, size: 18),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
                _buildDurationChip(context, duration),
              ],
            ),
            if (reason != null && reason.isNotEmpty) ...[
              const SizedBox(height: DS.sm),
              Text(
                reason,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral600,
                ),
              ),
            ],
            const SizedBox(height: DS.md),
            CustomButton.primary(
              text: '开始专注',
              icon: Icons.play_arrow_rounded,
              customGradient: DS.secondaryGradient,
              onPressed: () {
                HapticFeedback.selectionClick();
                context.push('/focus/mindfulness', extra: taskModel);
              },
              size: CustomButtonSize.small,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDurationChip(BuildContext context, int minutes) => Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: DS.spacing4),
      decoration: BoxDecoration(
        color: DS.secondaryBase.withValues(alpha: 0.1),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.secondaryBase.withValues(alpha: 0.2)),
      ),
      child: Text(
        '${minutes}m',
        style: TextStyle(
          color: DS.secondaryBase,
          fontSize: DS.fontSizeXs,
        ),
      ),
    );

  TaskModel _buildTaskModel(String title, int duration) {
    final taskData = data['task'] as Map<String, dynamic>?;
    if (taskData != null) {
      return TaskModel.fromJson(_normalizeTaskData(taskData, duration));
    }

    return TaskModel(
      id: 'focus_${DateTime.now().millisecondsSinceEpoch}',
      userId: 'focus_user',
      title: title,
      type: TaskType.learning,
      tags: const ['focus'],
      estimatedMinutes: duration,
      difficulty: 1,
      energyCost: 1,
      status: TaskStatus.pending,
      priority: 1,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );
  }

  Map<String, dynamic> _normalizeTaskData(Map<String, dynamic> data, int duration) {
    final normalized = Map<String, dynamic>.from(data);
    normalized['user_id'] ??= 'focus_user';
    normalized['tags'] ??= <String>[];
    normalized['difficulty'] ??= 1;
    normalized['energy_cost'] ??= 1;
    normalized['priority'] ??= 1;
    normalized['estimated_minutes'] ??= duration;
    normalized['created_at'] ??= DateTime.now().toIso8601String();
    normalized['updated_at'] ??= DateTime.now().toIso8601String();
    normalized['status'] ??= 'pending';
    normalized['type'] ??= 'learning';
    return normalized;
  }
}
