import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/providers/streak_quality_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class StreakQualityIndicator extends ConsumerWidget {
  const StreakQualityIndicator({
    super.key,
    this.onOpenDetails,
    this.compact = false,
  });

  final VoidCallback? onOpenDetails;
  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncQuality = ref.watch(streakQualityProvider);
    return asyncQuality.when(
      data: (snapshot) => _StreakQualityContent(
        snapshot: snapshot,
        compact: compact,
        onOpenDetails: onOpenDetails,
      ),
      loading: () => const SizedBox.square(
        dimension: 112,
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) {
        final fallback = ref.watch(streakStatsProvider);
        return _StreakQualityFallback(
          currentStreak: fallback.currentStreak,
          onOpenDetails: onOpenDetails,
        );
      },
    );
  }
}

class _StreakQualityContent extends StatelessWidget {
  const _StreakQualityContent({
    required this.snapshot,
    required this.compact,
    this.onOpenDetails,
  });

  final StreakQualitySnapshot snapshot;
  final bool compact;
  final VoidCallback? onOpenDetails;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final scheme = Theme.of(context).colorScheme;
    final quality = snapshot.todayQuality;
    final accent = quality.isQualityDay ? scheme.tertiary : scheme.primary;

    return Semantics(
      button: true,
      label: l10n.streakQualitySemantics(
        snapshot.qualityStreak,
        snapshot.currentStreak,
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _showQualitySheet(context, snapshot, onOpenDetails),
        child: Padding(
          padding: EdgeInsets.all(compact ? 4 : 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox.square(
                dimension: compact ? 104 : 120,
                child: CustomPaint(
                  painter: _QualityRingPainter(
                    outerProgress:
                        (snapshot.qualityStreak / 30).clamp(0.0, 1.0),
                    innerProgress:
                        (snapshot.currentStreak / 30).clamp(0.0, 1.0),
                    outerColor: accent,
                    innerColor: scheme.primary,
                    backgroundColor: scheme.outlineVariant,
                  ),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.local_fire_department_rounded,
                          color: accent,
                          size: 22,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${snapshot.qualityStreak}',
                          style:
                              Theme.of(context).textTheme.titleLarge?.copyWith(
                                    color: scheme.onSurface,
                                    fontWeight: FontWeight.w800,
                                  ),
                        ),
                        Text(
                          l10n.streakQualityDaysShort,
                          style:
                              Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: scheme.onSurfaceVariant,
                                  ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                l10n.streakQualityScoreLabel(
                  (quality.qualityScore * 100).round(),
                ),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: scheme.onSurface,
                      fontWeight: FontWeight.w700,
                    ),
              ),
              if (!compact && snapshot.celebrationTrigger != null) ...[
                const SizedBox(height: 6),
                Text(
                  snapshot.celebrationTrigger!.evidence,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: scheme.onSurfaceVariant,
                      ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StreakQualityFallback extends StatelessWidget {
  const _StreakQualityFallback({
    required this.currentStreak,
    this.onOpenDetails,
  });

  final int currentStreak;
  final VoidCallback? onOpenDetails;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final scheme = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      label: l10n.streakQualityUnavailable,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onOpenDetails,
        child: SizedBox.square(
          dimension: 112,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.local_fire_department_rounded,
                color: scheme.primary,
                size: 28,
              ),
              const SizedBox(height: 6),
              Text(
                '$currentStreak',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: scheme.onSurface,
                      fontWeight: FontWeight.w800,
                    ),
              ),
              Text(
                l10n.streakQualityUnavailable,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

void _showQualitySheet(
  BuildContext context,
  StreakQualitySnapshot snapshot,
  VoidCallback? onOpenDetails,
) {
  final l10n = AppLocalizations.of(context)!;
  final scheme = Theme.of(context).colorScheme;
  unawaited(
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.streakQualityTitle,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: scheme.onSurface,
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 6),
              Text(
                l10n.streakQualitySubtitle,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 18),
              _BreakdownGrid(quality: snapshot.todayQuality),
              const SizedBox(height: 18),
              Text(
                l10n.streakQualityWeeklyTrend,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: scheme.onSurface,
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 10),
              _QualityTrendBars(points: snapshot.weeklyQualityTrend),
              if (snapshot.celebrationTrigger != null) ...[
                const SizedBox(height: 18),
                _EvidenceCard(trigger: snapshot.celebrationTrigger!),
              ],
              if (onOpenDetails != null) ...[
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: () {
                      Navigator.of(context).pop();
                      onOpenDetails();
                    },
                    icon: const Icon(Icons.open_in_new_rounded),
                    label: Text(l10n.streakQualityViewDetails),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    ),
  );
}

class _BreakdownGrid extends StatelessWidget {
  const _BreakdownGrid({required this.quality});

  final StreakQuality quality;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return LayoutBuilder(
      builder: (context, constraints) {
        final itemWidth = (constraints.maxWidth - 10) / 2;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            _BreakdownTile(
              width: itemWidth,
              icon: Icons.timer_outlined,
              label: l10n.streakQualityEffectiveMinutes,
              value: l10n.streakQualityMinutesValue(
                quality.effectiveMinutes,
              ),
            ),
            _BreakdownTile(
              width: itemWidth,
              icon: Icons.task_alt_rounded,
              label: l10n.streakQualityCoreTasks,
              value: '${quality.coreTasksCompleted}',
            ),
            _BreakdownTile(
              width: itemWidth,
              icon: Icons.psychology_alt_outlined,
              label: l10n.streakQualityBreakthroughs,
              value: '${quality.difficultBreakthroughs}',
            ),
            _BreakdownTile(
              width: itemWidth,
              icon: Icons.route_outlined,
              label: l10n.streakQualityPlanConsistency,
              value: '${(quality.planConsistency * 100).round()}%',
            ),
            _BreakdownTile(
              width: itemWidth,
              icon: Icons.healing_outlined,
              label: l10n.streakQualityRecoveryScore,
              value: '${(quality.recoveryScore * 100).round()}%',
            ),
          ],
        );
      },
    );
  }
}

class _BreakdownTile extends StatelessWidget {
  const _BreakdownTile({
    required this.width,
    required this.icon,
    required this.label,
    required this.value,
  });

  final double width;
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: width,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Row(
        children: [
          Icon(icon, color: scheme.primary, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: scheme.onSurfaceVariant,
                      ),
                ),
                Text(
                  value,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: scheme.onSurface,
                        fontWeight: FontWeight.w800,
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

class _QualityTrendBars extends StatelessWidget {
  const _QualityTrendBars({required this.points});

  final List<StreakQualityTrendPoint> points;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    if (points.isEmpty) {
      return Text(
        AppLocalizations.of(context)!.streakQualityEmpty,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: scheme.onSurfaceVariant,
            ),
      );
    }

    return SizedBox(
      height: 96,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: points
            .map(
              (point) => Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  child: Semantics(
                    label: '${(point.qualityScore * 100).round()}%',
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Expanded(
                          child: Align(
                            alignment: Alignment.bottomCenter,
                            child: FractionallySizedBox(
                              heightFactor: point.qualityScore.clamp(0.08, 1.0),
                              child: DecoratedBox(
                                decoration: BoxDecoration(
                                  color: Color.lerp(
                                        scheme.primary,
                                        scheme.tertiary,
                                        point.qualityScore,
                                      ) ??
                                      scheme.primary,
                                  borderRadius: BorderRadius.circular(999),
                                ),
                                child: const SizedBox(width: 14),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          point.date == null ? '' : '${point.date!.day}',
                          style:
                              Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: scheme.onSurfaceVariant,
                                  ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _EvidenceCard extends StatelessWidget {
  const _EvidenceCard({required this.trigger});

  final StreakCelebrationTrigger trigger;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: scheme.tertiaryContainer,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.streakQualityEvidence,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: scheme.onTertiaryContainer,
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            trigger.evidence,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: scheme.onTertiaryContainer,
                ),
          ),
          if (trigger.suggestedMessage.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.lightbulb_outline, size: 16, color: scheme.onTertiaryContainer),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    trigger.suggestedMessage,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: scheme.onTertiaryContainer,
                          fontStyle: FontStyle.italic,
                        ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _QualityRingPainter extends CustomPainter {
  const _QualityRingPainter({
    required this.outerProgress,
    required this.innerProgress,
    required this.outerColor,
    required this.innerColor,
    required this.backgroundColor,
  });

  final double outerProgress;
  final double innerProgress;
  final Color outerColor;
  final Color innerColor;
  final Color backgroundColor;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    _drawRing(
      canvas,
      center,
      size.width / 2 - 8,
      8,
      outerProgress,
      outerColor,
    );
    _drawRing(
      canvas,
      center,
      size.width / 2 - 22,
      6,
      innerProgress,
      innerColor,
    );
  }

  void _drawRing(
    Canvas canvas,
    Offset center,
    double radius,
    double strokeWidth,
    double progress,
    Color color,
  ) {
    final backgroundPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    final foregroundPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    final rect = Rect.fromCircle(center: center, radius: radius);
    canvas
      ..drawCircle(center, radius, backgroundPaint)
      ..drawArc(
        rect,
        -1.5708,
        6.2832 * progress.clamp(0.0, 1.0),
        false,
        foregroundPaint,
      );
  }

  @override
  bool shouldRepaint(covariant _QualityRingPainter oldDelegate) =>
      oldDelegate.outerProgress != outerProgress ||
      oldDelegate.innerProgress != innerProgress ||
      oldDelegate.outerColor != outerColor ||
      oldDelegate.innerColor != innerColor ||
      oldDelegate.backgroundColor != backgroundColor;
}
