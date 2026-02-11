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

  /// 🔧 安全获取品牌主色，避免SparkleThemeExtension未注册错误
  Color _safeGetColor(BuildContext context) {
    try {
      return ThemeManager().current.colors.brandPrimary;
    } catch (e) {
      // Fallback color if SparkleThemeExtension is not registered
      return DS.brandPrimary;
    }
  }

  @override
  Widget build(BuildContext context) {
    // 🔧 修复：安全获取baseColor，避免SparkleThemeExtension未注册错误
    final baseColor = color ?? _safeGetColor(context);
    final background = baseColor.withValues(alpha: 0.12);
    final border = baseColor.withValues(alpha: 0.3);
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
            SizedBox(width: 8),
          ],
          Container(
            width: dense ? 6 : 8,
            height: dense ? 6 : 8,
            decoration: BoxDecoration(
              color: baseColor,
              shape: BoxShape.circle,
            ),
          ),
          SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(fontSize: dense ? 12 : 14, color: baseColor),
          ),
        ],
      ),
    );
  }
}
