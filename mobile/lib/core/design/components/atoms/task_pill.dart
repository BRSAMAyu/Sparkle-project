import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/tokens/task_colors.dart';

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
      // Use task type-based colors
      final taskColors = TaskColors(brightness: SparkleContext(context).sparkleColors.brightness);
      background = taskColors.getTint(type);
      border = taskColors.getBorder(type);
      textColor = taskColors.getLabel(type);
      iconColor = taskColors.getIcon(type);
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
          Text(
            label,
            style: context.typo.labelSmall.copyWith(color: textColor),
          ),
        ],
      ),
    );
  }
}
