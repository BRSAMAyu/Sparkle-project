import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';

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
    final baseColor = color ?? context.sparkleColors.brandPrimary;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final background = isDark
        ? Color.alphaBlend(
            baseColor.withValues(alpha: 0.18),
            DS.surfaceSecondary,
          )
        : baseColor.withValues(alpha: 0.12);
    final border = isDark
        ? baseColor.withValues(alpha: 0.48)
        : baseColor.withValues(alpha: 0.3);
    final horizontal = dense ? 4.0 : 8.0;
    final vertical = dense ? 2.0 : 4.0;

    return SparklePressable(
      onTap: onTap,
      enabled: onTap != null,
      backgroundColor: background,
      border: BorderSide(color: border),
      borderRadius: BorderRadius.circular(8),
      padding: EdgeInsets.symmetric(horizontal: horizontal, vertical: vertical),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: dense ? 14 : 16, color: baseColor),
            const SizedBox(width: 8),
          ],
          Container(
            width: dense ? 6 : 8,
            height: dense ? 6 : 8,
            decoration: BoxDecoration(
              color: baseColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              softWrap: false,
              style: TextStyle(fontSize: dense ? 12 : 14, color: baseColor),
            ),
          ),
        ],
      ),
    );
  }
}
