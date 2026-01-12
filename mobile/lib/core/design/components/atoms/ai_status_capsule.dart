import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';

/// Capsule indicator for AI status.
class AiStatusCapsule extends StatelessWidget {
  const AiStatusCapsule({
    required this.label,
    super.key,
    this.icon,
    this.color,
    this.dense = false,
    this.onTap,
  });

  final String label;
  final IconData? icon;
  final Color? color;
  final bool dense;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final baseColor = color ?? context.colors.brandPrimary;
    final background = baseColor.withValues(alpha: 0.12);
    final border = baseColor.withValues(alpha: 0.3);
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
            Icon(icon, size: dense ? 14 : 16, color: baseColor),
            SizedBox(width: context.space.xs),
          ],
          Container(
            width: dense ? 6 : 8,
            height: dense ? 6 : 8,
            decoration: BoxDecoration(
              color: baseColor,
              shape: BoxShape.circle,
            ),
          ),
          SizedBox(width: context.space.xs),
          Text(
            label,
            style: context.typo.labelSmall.copyWith(color: baseColor),
          ),
        ],
      ),
    );
  }
}
