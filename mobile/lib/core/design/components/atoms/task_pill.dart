import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/shared/entities/task_model.dart' show TaskType;

/// Tone mapping for task pills.
enum TaskPillTone { info, success, warning, danger, neutral, brand }

/// Task pill displaying semantic task colors.
class TaskPill extends StatelessWidget {
  const TaskPill({
    required this.type,
    required this.label,
    super.key,
    this.icon,
    this.dense = false,
    this.onTap,
    this.tone,
  });

  final TaskType type;
  final String label;
  final IconData? icon;
  final bool dense;
  final VoidCallback? onTap;
  final TaskPillTone? tone;

  @override
  Widget build(BuildContext context) {
    final Color background;
    final Color border;
    final Color textColor;
    final Color iconColor;

    if (tone != null) {
      // Use tone-based colors from design tokens
      switch (tone!) {
        case TaskPillTone.info:
          background = DS.info.withValues(alpha: 0.1);
          border = DS.info.withValues(alpha: 0.3);
          textColor = DS.info;
          iconColor = DS.info;
        case TaskPillTone.success:
          background = DS.success.withValues(alpha: 0.1);
          border = DS.success.withValues(alpha: 0.3);
          textColor = DS.success;
          iconColor = DS.success;
        case TaskPillTone.warning:
          background = DS.warning.withValues(alpha: 0.1);
          border = DS.warning.withValues(alpha: 0.3);
          textColor = DS.warning;
          iconColor = DS.warning;
        case TaskPillTone.danger:
          background = DS.error.withValues(alpha: 0.1);
          border = DS.error.withValues(alpha: 0.3);
          textColor = DS.error;
          iconColor = DS.error;
        case TaskPillTone.neutral:
          background = DS.surfaceTertiary;
          border = DS.border;
          textColor = DS.textSecondary;
          iconColor = DS.textSecondary;
        case TaskPillTone.brand:
          background = DS.brandPrimary.withValues(alpha: 0.1);
          border = DS.brandPrimary.withValues(alpha: 0.3);
          textColor = DS.brandPrimary;
          iconColor = DS.brandPrimary;
      }
    } else {
      // Task type colors come from the single palette source
      // (SparkleColors.task* / taskColorFor — batch2 convergence).
      // Explicit extension application: design_system.dart's SparkleContext
      // also exposes `colors` (entry unification lands in batch 3).
      final taskColor =
          context.colors.taskColorFor(type);
      background = taskColor.withValues(alpha: 0.1);
      border = taskColor.withValues(alpha: 0.3);
      textColor = taskColor;
      iconColor = taskColor;
    }

    final horizontal = dense ? context.space.sm : context.space.md;
    final vertical = dense ? context.space.xs : context.space.sm;

    return SparklePressable(
      onTap: onTap,
      enabled: onTap != null,
      backgroundColor: background,
      border: BorderSide(color: border),
      borderRadius: context.radius.fullRadius,
      padding: context.space.edge(horizontal: horizontal, vertical: vertical),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: dense ? 14 : 16, color: iconColor),
            SizedBox(width: context.space.xs),
          ],
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              softWrap: false,
              style: context.typo.labelSmall.copyWith(color: textColor),
            ),
          ),
        ],
      ),
    );
  }
}
