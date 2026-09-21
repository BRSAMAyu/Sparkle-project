import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';

/// Semantic tone for pill components.
enum PillTone { info, success, warning, danger, neutral, brand }

/// Generic pill component that uses semantic design tokens.
class SemanticPill extends StatelessWidget {
  const SemanticPill({
    required this.label,
    required this.tone,
    super.key,
    this.icon,
    this.dense = false,
    this.onTap,
    this.selected = false,
    this.onDeleted,
  });

  final String label;
  final PillTone tone;
  final IconData? icon;
  final bool dense;
  final VoidCallback? onTap;

  /// U-01 Step 1（README 规则 5 扩 owner）：ChoiceChip/FilterChip 的选中态等价。
  /// true 时提高 tone 的存在感（bg/border alpha 提升，无 [icon] 时前置 check 图标，
  /// 对齐 M3 chip 选中时的 checkmark 语义）。
  final bool selected;

  /// U-01 Step 1（README 规则 5 扩 owner）：InputChip/Chip.onDeleted 的等价删除区。
  /// 非空时在尾部渲染独立可点删除钮（带删除语义），整体 pill 的 [onTap] 不受影响。
  final VoidCallback? onDeleted;

  Color _getBackgroundColor(PillTone tone, BuildContext context) {
    final alpha = selected ? 0.18 : 0.1;
    switch (tone) {
      case PillTone.info:
        return DS.info.withValues(alpha: alpha);
      case PillTone.success:
        return DS.success.withValues(alpha: alpha);
      case PillTone.warning:
        return DS.warning.withValues(alpha: alpha);
      case PillTone.danger:
        return DS.error.withValues(alpha: alpha);
      case PillTone.neutral:
        return DS.textSecondary.withValues(alpha: alpha);
      case PillTone.brand:
        return DS.brandPrimary.withValues(alpha: alpha);
    }
  }

  Color _getBorderColor(PillTone tone, BuildContext context) {
    final alpha = selected ? 0.5 : 0.3;
    switch (tone) {
      case PillTone.info:
        return DS.info.withValues(alpha: alpha);
      case PillTone.success:
        return DS.success.withValues(alpha: alpha);
      case PillTone.warning:
        return DS.warning.withValues(alpha: alpha);
      case PillTone.danger:
        return DS.error.withValues(alpha: alpha);
      case PillTone.neutral:
        return DS.textSecondary.withValues(alpha: alpha);
      case PillTone.brand:
        return DS.brandPrimary.withValues(alpha: alpha);
    }
  }

  Color _getTextColor(PillTone tone, BuildContext context) {
    switch (tone) {
      case PillTone.info:
        return DS.info;
      case PillTone.success:
        return DS.success;
      case PillTone.warning:
        return DS.warning;
      case PillTone.danger:
        return DS.error;
      case PillTone.neutral:
        return DS.textSecondary;
      case PillTone.brand:
        return DS.brandPrimary;
    }
  }

  Color _getIconColor(PillTone tone, BuildContext context) =>
      _getTextColor(tone, context);

  @override
  Widget build(BuildContext context) {
    final horizontal = dense ? context.space.sm : context.space.md;
    final vertical = dense ? context.space.xs : context.space.sm;
    final textColor = _getTextColor(tone, context);

    return SparklePressable(
      onTap: onTap,
      enabled: onTap != null,
      backgroundColor: _getBackgroundColor(tone, context),
      border: BorderSide(color: _getBorderColor(tone, context)),
      borderRadius: context.radius.fullRadius,
      padding: context.space.edge(horizontal: horizontal, vertical: vertical),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (selected && icon == null) ...[
            Icon(
              Icons.check,
              size: dense ? 14 : 16,
              color: textColor,
            ),
            SizedBox(width: context.space.xs),
          ],
          if (icon != null) ...[
            Icon(
              icon,
              size: dense ? 14 : 16,
              color: _getIconColor(tone, context),
            ),
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
          if (onDeleted != null) ...[
            SizedBox(width: context.space.xs),
            GestureDetector(
              onTap: onDeleted,
              behavior: HitTestBehavior.opaque,
              child: Semantics(
                button: true,
                label: '删除',
                child: Padding(
                  padding: const EdgeInsets.all(2),
                  child: Icon(
                    Icons.close,
                    size: dense ? 14 : 16,
                    color: textColor.withValues(alpha: 0.7),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
