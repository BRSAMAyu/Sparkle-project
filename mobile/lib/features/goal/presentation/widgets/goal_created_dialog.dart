import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class SparkleGoalCreatedDialog extends StatelessWidget {
  const SparkleGoalCreatedDialog({
    required this.goalName,
    required this.firstMilestone,
    required this.onSeePlan,
    required this.onStartFirstTask,
    super.key,
    this.packName,
    this.packDurationLabel,
  });

  final String goalName;
  final String firstMilestone;
  final String? packName;
  final String? packDurationLabel;
  final VoidCallback onSeePlan;
  final VoidCallback onStartFirstTask;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;

    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: DS.borderRadius20),
      title: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              gradient: DS.primaryGradient,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.auto_awesome, color: Colors.white, size: 28),
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            l10n.goalCreatedPlanReady,
            textAlign: TextAlign.center,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ],
      ),
      content: SizedBox(
        width: double.maxFinite,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              goalName,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: DS.fontWeightBold,
                color: DS.brandPrimary,
              ),
            ),
            const SizedBox(height: DS.spacing16),
            if (packName != null) ...[
              _InfoRow(
                icon: Icons.map_outlined,
                label: l10n.goalCreatedLearningPath,
                value: packDurationLabel != null
                    ? '$packName · $packDurationLabel'
                    : packName!,
              ),
            ],
            _InfoRow(
              icon: Icons.flag_outlined,
              label: l10n.goalCreatedFirstMilestone,
              value: firstMilestone,
            ),
            const SizedBox(height: DS.spacing8),
            Container(
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: DS.borderRadius8,
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Row(
                children: [
                  Icon(Icons.lightbulb_outline, size: 18, color: DS.warning),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      l10n.goalCreatedMinBarTip,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      actions: [
        OutlinedButton(
          onPressed: onSeePlan,
          style: OutlinedButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: DS.borderRadius12,
            ),
          ),
          child: Text(l10n.goalCreatedSeeFullPlan),
        ),
        FilledButton(
          onPressed: onStartFirstTask,
          style: FilledButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: DS.borderRadius12,
            ),
          ),
          child: Text(l10n.goalCreatedStartFirstTask),
        ),
      ],
      actionsAlignment: MainAxisAlignment.spaceBetween,
    );
  }

  static Future<void> show(
    BuildContext context, {
    required String goalName,
    required String firstMilestone,
    required VoidCallback onSeePlan,
    required VoidCallback onStartFirstTask,
    String? packName,
    String? packDurationLabel,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => SparkleGoalCreatedDialog(
        goalName: goalName,
        firstMilestone: firstMilestone,
        packName: packName,
        packDurationLabel: packDurationLabel,
        onSeePlan: onSeePlan,
        onStartFirstTask: onStartFirstTask,
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: DS.iconSizeSm, color: DS.brandPrimary),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
                const SizedBox(height: DS.spacing2),
                Text(
                  value,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
