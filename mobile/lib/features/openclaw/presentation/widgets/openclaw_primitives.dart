import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

enum OpenClawVisualTone {
  connected,
  offline,
  active,
  attention,
}

Color openClawToneColor(OpenClawVisualTone tone) => switch (tone) {
      OpenClawVisualTone.connected => DS.semanticSuccess,
      OpenClawVisualTone.offline => DS.warning,
      OpenClawVisualTone.active => DS.info,
      OpenClawVisualTone.attention => DS.brandPrimaryConst,
    };

class OpenClawMetricPill extends StatelessWidget {
  const OpenClawMetricPill({
    required this.label,
    super.key,
    this.icon,
    this.tone = OpenClawVisualTone.active,
    this.emphasized = false,
  });

  final String label;
  final IconData? icon;
  final OpenClawVisualTone tone;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final color = openClawToneColor(tone);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: emphasized ? 0.14 : 0.1),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: color.withValues(alpha: emphasized ? 0.2 : 0.12),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: color),
            const SizedBox(width: DS.spacing6),
          ],
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: DS.bodySmall.copyWith(
                color: color,
                fontWeight:
                    emphasized ? DS.fontWeightBold : DS.fontWeightSemiBold,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class OpenClawIdentityStrip extends StatelessWidget {
  const OpenClawIdentityStrip({
    required this.label,
    required this.description,
    super.key,
    this.tone = OpenClawVisualTone.active,
  });

  final String label;
  final String description;
  final OpenClawVisualTone tone;

  @override
  Widget build(BuildContext context) {
    final color = openClawToneColor(tone);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            color.withValues(alpha: 0.12),
            color.withValues(alpha: 0.05),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: color.withValues(alpha: 0.16)),
      ),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              Icons.cloud_sync_rounded,
              size: 16,
              color: color,
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: DS.bodySmall.copyWith(
                    color: color,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: DS.spacing2),
                Text(
                  description,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
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

class OpenClawStatusCapsule extends StatelessWidget {
  const OpenClawStatusCapsule({
    required this.title,
    required this.subtitle,
    super.key,
    this.icon = Icons.cloud_sync_rounded,
    this.tone = OpenClawVisualTone.active,
    this.metrics = const <Widget>[],
    this.trailing,
    this.expanded = false,
    this.onToggleExpanded,
    this.expandedContent,
    this.padding,
    this.showToggle = true,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final OpenClawVisualTone tone;
  final List<Widget> metrics;
  final Widget? trailing;
  final bool expanded;
  final VoidCallback? onToggleExpanded;
  final Widget? expandedContent;
  final EdgeInsetsGeometry? padding;
  final bool showToggle;

  @override
  Widget build(BuildContext context) {
    final color = openClawToneColor(tone);
    return Container(
      width: double.infinity,
      padding: padding ?? const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            color.withValues(alpha: 0.12),
            color.withValues(alpha: 0.06),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        border: Border.all(color: color.withValues(alpha: 0.16)),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.06),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: color, size: 20),
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: DS.bodyMedium.copyWith(
                        color: color,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      subtitle,
                      maxLines: expanded ? null : 1,
                      overflow: expanded
                          ? TextOverflow.visible
                          : TextOverflow.ellipsis,
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                  ],
                ),
              ),
              if (trailing != null) ...[
                const SizedBox(width: DS.spacing8),
                trailing!,
              ],
            ],
          ),
          if (metrics.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: metrics,
            ),
          ],
          if (showToggle &&
              (onToggleExpanded != null || expandedContent != null))
            InkWell(
              onTap: onToggleExpanded,
              borderRadius: BorderRadius.circular(12),
              child: Padding(
                padding: const EdgeInsets.only(top: DS.spacing8),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        expanded ? '收起细节' : '展开细节',
                        style: DS.bodySmall.copyWith(
                          color: DS.textSecondary,
                          fontWeight: DS.fontWeightSemiBold,
                        ),
                      ),
                    ),
                    Icon(
                      expanded
                          ? Icons.expand_less_rounded
                          : Icons.expand_more_rounded,
                      size: 18,
                      color: DS.textSecondary,
                    ),
                  ],
                ),
              ),
            ),
          if (expanded && expandedContent != null) ...[
            const SizedBox(height: DS.spacing10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(DS.spacing10),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: color.withValues(alpha: 0.1)),
              ),
              child: expandedContent,
            ),
          ],
        ],
      ),
    );
  }
}

class OpenClawSectionSurface extends StatelessWidget {
  const OpenClawSectionSurface({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.summary,
    super.key,
    this.tone = OpenClawVisualTone.active,
    this.expanded = false,
    this.onToggle,
    this.expandedChild,
    this.toggleLabel,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Widget summary;
  final OpenClawVisualTone tone;
  final bool expanded;
  final VoidCallback? onToggle;
  final Widget? expandedChild;
  final String? toggleLabel;

  @override
  Widget build(BuildContext context) {
    final color = openClawToneColor(tone);
    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, size: 18, color: color),
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      subtitle,
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          summary,
          if (expandedChild != null) ...[
            const SizedBox(height: DS.spacing12),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: onToggle,
                icon: Icon(
                  expanded
                      ? Icons.keyboard_arrow_up_rounded
                      : Icons.edit_note_rounded,
                ),
                label: Text(
                  toggleLabel ?? (expanded ? '收起' : '展开'),
                ),
              ),
            ),
            AnimatedSwitcher(
              duration: DS.durationNormal,
              switchInCurve: Curves.easeOutCubic,
              switchOutCurve: Curves.easeOutCubic,
              child: expanded
                  ? Padding(
                      key: const ValueKey('expanded'),
                      padding: const EdgeInsets.only(top: DS.spacing4),
                      child: expandedChild,
                    )
                  : const SizedBox.shrink(key: ValueKey('collapsed')),
            ),
          ],
        ],
      ),
    );
  }
}
