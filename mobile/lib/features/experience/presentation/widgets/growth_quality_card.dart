import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/experience/data/experience_models.dart';
import 'package:sparkle/features/experience/presentation/providers/experience_provider.dart';

class GrowthQualityCard extends ConsumerWidget {
  const GrowthQualityCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncValue = ref.watch(experienceGrowthDashboardProvider);
    return asyncValue.when(
      data: (data) => _GrowthQualitySurface(data: data),
      loading: () => const SizedBox.shrink(),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(experienceGrowthDashboardProvider),
      ),
    );
  }
}

class _GrowthQualitySurface extends StatelessWidget {
  const _GrowthQualitySurface({required this.data});

  final ExperienceGrowthDashboard data;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final quality = data.streakQuality;
    final dashboard = data.learningDashboard;
    final accent = quality.score >= 0.72
        ? DS.success
        : quality.score >= 0.42
            ? DS.info
            : DS.warning;

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        0,
        DS.spacing16,
        DS.spacing10,
      ),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: accent.withValues(alpha: 0.18),
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _QualityRing(score: quality.score, color: accent),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.streakQualityLabel,
                        style: TextStyle(
                          color: DS.textSecondary,
                          fontSize: DS.fontSizeXs,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        quality.label.isNotEmpty
                            ? quality.label
                            : l10n.streakQualityDefaultSummary,
                        style: TextStyle(
                          color: DS.textPrimary,
                          fontSize: DS.fontSizeBase,
                          fontWeight: DS.fontWeightSemibold,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                _MetricChip(
                  icon: Icons.timer_rounded,
                  label: l10n.streakQualityFocusMin7d(dashboard.focusMinutes7d),
                ),
                _MetricChip(
                  icon: Icons.task_alt_rounded,
                  label: l10n.streakQualityTasksCompleted(dashboard.tasksCompleted, dashboard.tasksTotal),
                ),
                if (quality.currentStreak > 0)
                  _MetricChip(
                    icon: Icons.local_fire_department_rounded,
                    label: l10n.streakQualityDayStreak(quality.currentStreak),
                  ),
              ],
            ),
            if (data.weeklyNarrative != null &&
                data.weeklyNarrative!.isNotEmpty) ...[
              const SizedBox(height: DS.spacing12),
              Text(
                data.weeklyNarrative!,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: DS.fontSizeSm,
                  height: 1.52,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _QualityRing extends StatelessWidget {
  const _QualityRing({
    required this.score,
    required this.color,
  });

  final double score;
  final Color color;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 48,
        height: 48,
        child: Stack(
          fit: StackFit.expand,
          children: [
            CircularProgressIndicator(
              value: score,
              strokeWidth: 5,
              backgroundColor: color.withValues(alpha: 0.12),
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
            Center(
              child: Text(
                '${(score * 100).round()}',
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: 12,
                  fontWeight: DS.fontWeightBold,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ),
          ],
        ),
      );
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay.withValues(alpha: 0.7),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 11,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ],
        ),
      );
}
