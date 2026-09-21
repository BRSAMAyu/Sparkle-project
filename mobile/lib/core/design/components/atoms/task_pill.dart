import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/shared/entities/task_model.dart' show TaskType;

/// U-01 Step 0：tone 语义枚举 owner 唯一为 [PillTone]（semantic_pill.dart）。
/// 原 `enum TaskPillTone` 与 PillTone 值完全相同，已合并删除；
/// 本组件保留自己的 tone→token 色映射（neutral 走 surfaceTertiary/border，
/// 与 SemanticPill 的 neutral 渲染不同），故枚举合并不改变视觉输出。

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
  final PillTone? tone;

  @override
  Widget build(BuildContext context) {
    final Color background;
    final Color border;
    final Color textColor;
    final Color iconColor;

    if (tone != null) {
      // Use tone-based colors from design tokens
      switch (tone!) {
        case PillTone.info:
          background = DS.info.withValues(alpha: 0.1);
          border = DS.info.withValues(alpha: 0.3);
          textColor = DS.info;
          iconColor = DS.info;
        case PillTone.success:
          background = DS.success.withValues(alpha: 0.1);
          border = DS.success.withValues(alpha: 0.3);
          textColor = DS.success;
          iconColor = DS.success;
        case PillTone.warning:
          background = DS.warning.withValues(alpha: 0.1);
          border = DS.warning.withValues(alpha: 0.3);
          textColor = DS.warning;
          iconColor = DS.warning;
        case PillTone.danger:
          background = DS.error.withValues(alpha: 0.1);
          border = DS.error.withValues(alpha: 0.3);
          textColor = DS.error;
          iconColor = DS.error;
        case PillTone.neutral:
          background = DS.surfaceTertiary;
          border = DS.border;
          textColor = DS.textSecondary;
          iconColor = DS.textSecondary;
        case PillTone.brand:
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
