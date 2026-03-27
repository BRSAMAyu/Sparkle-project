import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class MirofishStageMetric {
  const MirofishStageMetric({
    required this.label,
    required this.value,
    this.accent,
    this.icon,
  });

  final String label;
  final String value;
  final Color? accent;
  final IconData? icon;
}

class MirofishStageHeader extends StatelessWidget {
  const MirofishStageHeader({
    required this.icon,
    required this.title,
    required this.subtitle,
    super.key,
    this.eyebrow,
    this.metrics = const <MirofishStageMetric>[],
    this.primaryLabel,
    this.onPrimaryTap,
    this.secondaryLabel,
    this.onSecondaryTap,
    this.footer,
    this.accent,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String? eyebrow;
  final List<MirofishStageMetric> metrics;
  final String? primaryLabel;
  final VoidCallback? onPrimaryTap;
  final String? secondaryLabel;
  final VoidCallback? onSecondaryTap;
  final Widget? footer;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final headerAccent = accent ?? scheme.primary;
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: headerAccent.withValues(alpha: 0.16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      headerAccent.withValues(alpha: 0.96),
                      Color.lerp(
                            headerAccent,
                            DS.brandPrimary,
                            0.28,
                          ) ??
                          headerAccent,
                    ],
                  ),
                  borderRadius: BorderRadius.circular(18),
                  boxShadow: [
                    BoxShadow(
                      color: headerAccent.withValues(alpha: 0.18),
                      blurRadius: 18,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: Icon(icon, color: Colors.white, size: 26),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if ((eyebrow ?? '').isNotEmpty) ...[
                      Text(
                        eyebrow!,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: headerAccent,
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: 6),
                    ],
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                            height: 1.15,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                            height: 1.48,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (metrics.isNotEmpty) ...[
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: metrics
                  .map(
                    (metric) => _MirofishMetricCard(
                      metric: metric,
                      fallbackAccent: headerAccent,
                    ),
                  )
                  .toList(),
            ),
          ],
          if ((primaryLabel ?? '').isNotEmpty ||
              (secondaryLabel ?? '').isNotEmpty) ...[
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                if ((primaryLabel ?? '').isNotEmpty && onPrimaryTap != null)
                  FilledButton.icon(
                    onPressed: onPrimaryTap,
                    icon: const Icon(Icons.arrow_forward_rounded),
                    label: Text(primaryLabel!),
                  ),
                if ((secondaryLabel ?? '').isNotEmpty && onSecondaryTap != null)
                  OutlinedButton.icon(
                    onPressed: onSecondaryTap,
                    icon: const Icon(Icons.tune_rounded),
                    label: Text(secondaryLabel!),
                  ),
              ],
            ),
          ],
          if (footer != null) ...[
            const SizedBox(height: 16),
            footer!,
          ],
        ],
      ),
    );
  }
}

class _MirofishMetricCard extends StatelessWidget {
  const _MirofishMetricCard({
    required this.metric,
    required this.fallbackAccent,
  });

  final MirofishStageMetric metric;
  final Color fallbackAccent;

  @override
  Widget build(BuildContext context) {
    final accent = metric.accent ?? fallbackAccent;
    return Container(
      constraints: const BoxConstraints(minWidth: 104, maxWidth: 172),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (metric.icon != null) ...[
                Icon(metric.icon, size: 14, color: accent),
                const SizedBox(width: 6),
              ],
              Flexible(
                child: Text(
                  metric.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: DS.textSecondary,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            metric.value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: accent,
                  fontWeight: FontWeight.w800,
                ),
          ),
        ],
      ),
    );
  }
}
