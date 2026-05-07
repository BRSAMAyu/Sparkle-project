import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class ChatAccessoryPill extends StatelessWidget {
  const ChatAccessoryPill({
    required this.icon,
    super.key,
    this.label,
    this.onTap,
    this.selected = false,
    this.emphasize = false,
    this.enabled = true,
    this.accentColor,
    this.iconSize = 14,
    this.padding,
    this.trailing,
    this.showLabel = true,
  });

  final IconData icon;
  final String? label;
  final VoidCallback? onTap;
  final bool selected;
  final bool emphasize;
  final bool enabled;
  final Color? accentColor;
  final double iconSize;
  final EdgeInsetsGeometry? padding;
  final Widget? trailing;
  final bool showLabel;

  @override
  Widget build(BuildContext context) {
    final accent = accentColor ?? DS.primaryBase;
    final foreground = enabled
        ? (selected ? accent : DS.textSecondary)
        : DS.textSecondary.withValues(alpha: 0.45);
    final background = selected
        ? accent.withValues(alpha: 0.14)
        : emphasize
            ? accent.withValues(alpha: 0.08)
            : DS.surfacePanel;
    final border = selected
        ? accent.withValues(alpha: 0.26)
        : emphasize
            ? accent.withValues(alpha: 0.18)
            : DS.borderSubtle;

    final content = AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      constraints: const BoxConstraints(minHeight: 30),
      padding: padding ??
          const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing6,
          ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: DS.borderRadiusFull,
        border: Border.all(color: border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: iconSize, color: foreground),
          if (showLabel && (label?.trim().isNotEmpty ?? false)) ...[
            const SizedBox(width: DS.spacing6),
            Text(
              label!,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    fontSize: DS.fontSizeXs,
                    color: foreground,
                    fontWeight:
                        selected ? DS.fontWeightSemibold : DS.fontWeightMedium,
                  ),
            ),
          ],
          if (trailing != null) ...[
            const SizedBox(width: DS.spacing4),
            trailing!,
          ],
        ],
      ),
    );

    if (onTap == null) {
      return Opacity(
        opacity: enabled ? 1 : 0.7,
        child: content,
      );
    }

    return Material(
      color: Colors.transparent,
      child: Semantics(
        button: true,
        enabled: enabled && onTap != null,
        label: label,
        child: InkWell(
          onTap: enabled ? onTap : null,
          borderRadius: DS.borderRadiusFull,
          child: content,
        ),
      ),
    );
  }
}
