import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';

/// Phase-6 MultiGoal UI — conflict resolution dialog.
///
/// When the backend's MultiGoalArbitrator detects that today's tasks from
/// multiple goals would exceed the user's available time, this dialog
/// surfaces the trade-off so the user can make an informed decision
/// instead of silently losing goal progress.
///
/// This is a standalone widget (not wired into any screen yet) because
/// the backend MultiGoal arbitration API needs a REST endpoint first.
/// Once the endpoint is available, call [showGoalConflictDialog] from the
/// dashboard or task board when a conflict is detected.
class GoalConflictOption {
  const GoalConflictOption({
    required this.goalId,
    required this.goalTitle,
    required this.suggestedMinutes,
    required this.reason,
    this.urgency = '',
  });

  final String goalId;
  final String goalTitle;
  final int suggestedMinutes;
  final String reason;
  final String urgency;
}

/// Show the conflict dialog. Returns the user's chosen option index, or
/// -1 if they dismissed the dialog.
Future<int> showGoalConflictDialog(
  BuildContext context, {
  required int totalAvailableMinutes,
  required List<GoalConflictOption> options,
}) {
  return showSensoryDialog<int>(
    context: context,
    builder: (context) => _ConflictDialog(
      totalMinutes: totalAvailableMinutes,
      options: options,
    ),
  ).then((value) => value ?? -1);
}

class _ConflictDialog extends StatelessWidget {
  const _ConflictDialog({
    required this.totalMinutes,
    required this.options,
  });

  final int totalMinutes;
  final List<GoalConflictOption> options;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('今天的安排'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '你今天大概只有 $totalMinutes 分钟。',
            style: TextStyle(color: DS.textSecondary, fontSize: 13),
          ),
          const SizedBox(height: 16),
          ...options.map((opt) => _ConflictOptionTile(option: opt)),
        ],
      ),
      actions: [
        SparkleButton.ghost(
          label: '同意',
          onPressed: () => Navigator.pop(context, 0),
        ),
        SparkleButton.ghost(
          label: '我需要调整',
          onPressed: () => Navigator.pop(context, -2),
        ),
      ],
    );
  }
}

class _ConflictOptionTile extends StatelessWidget {
  const _ConflictOptionTile({required this.option});

  final GoalConflictOption option;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 4,
            height: 40,
            decoration: BoxDecoration(
              color: option.urgency == 'critical'
                  ? DS.error
                  : DS.brandPrimary,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  option.goalTitle,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                if (option.reason.isNotEmpty)
                  Text(
                    option.reason,
                    style: TextStyle(color: DS.textSecondary, fontSize: 12),
                  ),
                Text(
                  '${option.suggestedMinutes} 分钟',
                  style: TextStyle(color: DS.textSecondary, fontSize: 11),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
