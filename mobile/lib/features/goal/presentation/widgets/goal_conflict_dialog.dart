import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Phase-6 MultiGoal UI — conflict resolution dialog.
///
/// When the backend's MultiGoalArbitrator detects that today's tasks from
/// multiple goals would exceed the user's available time, this dialog
/// surfaces the trade-off so the user can make an informed decision
/// instead of silently losing goal progress.
///
/// Call [showGoalConflictDialog] from the dashboard or task board when a
/// multi-goal conflict is detected via the existing `goal_arbitration_card`
/// WebSocket flow or future REST endpoint.
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
      title: Text(context.l10n.goalConflictTodaySchedule),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.goalConflictTimeAvailable(totalMinutes),
            style: TextStyle(color: DS.textSecondary, fontSize: 13),
          ),
          const SizedBox(height: 16),
          ...options.map((opt) => _ConflictOptionTile(
            option: opt,
            minutesLabel: context.l10n.goalConflictMinutes(opt.suggestedMinutes),
          )),
        ],
      ),
      actions: [
        SparkleButton.ghost(
          label: context.l10n.goalConflictAgree,
          onPressed: () => Navigator.pop(context, 0),
        ),
        SparkleButton.ghost(
          label: context.l10n.goalConflictNeedAdjust,
          onPressed: () => Navigator.pop(context, -2),
        ),
      ],
    );
  }
}

class _ConflictOptionTile extends StatelessWidget {
  const _ConflictOptionTile({required this.option, required this.minutesLabel});

  final GoalConflictOption option;
  final String minutesLabel;

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
                  minutesLabel,
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
