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
  });

  final String label;
  final PillTone tone;
  final IconData? icon;
  final bool dense;
  final VoidCallback? onTap;

  Color _getBackgroundColor(PillTone tone, BuildContext context) {
    switch (tone) {
      case PillTone.info:
        return DS.info.withValues(alpha: 0.1);
      case PillTone.success:
        return DS.success.withValues(alpha: 0.1);
      case PillTone.warning:
        return DS.warning.withValues(alpha: 0.1);
      case PillTone.danger:
        return DS.error.withValues(alpha: 0.1);
      case PillTone.neutral:
        return DS.textSecondary.withValues(alpha: 0.1);
      case PillTone.brand:
        return DS.brandPrimary.withValues(alpha: 0.1);
    }
  }

  Color _getBorderColor(PillTone tone, BuildContext context) {
    switch (tone) {
      case PillTone.info:
        return DS.info.withValues(alpha: 0.3);
      case PillTone.success:
        return DS.success.withValues(alpha: 0.3);
      case PillTone.warning:
        return DS.warning.withValues(alpha: 0.3);
      case PillTone.danger:
        return DS.error.withValues(alpha: 0.3);
      case PillTone.neutral:
        return DS.textSecondary.withValues(alpha: 0.3);
      case PillTone.brand:
        return DS.brandPrimary.withValues(alpha: 0.3);
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

  Color _getIconColor(PillTone tone, BuildContext context) => _getTextColor(tone, context);

  @override
  Widget build(BuildContext context) {
    final horizontal = dense ? context.space.sm : context.space.md;
    final vertical = dense ? context.space.xs : context.space.sm;

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
          if (icon != null) ...[
            Icon(icon, size: dense ? 14 : 16, color: _getIconColor(tone, context)),
            SizedBox(width: context.space.xs),
          ],
          Text(
            label,
            style: context.typo.labelSmall.copyWith(color: _getTextColor(tone, context)),
          ),
        ],
      ),
    );
  }
}
