import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/experience/data/experience_models.dart';
import 'package:sparkle/features/experience/presentation/providers/experience_provider.dart';

class GoalDetailSnapshotCard extends ConsumerWidget {
  const GoalDetailSnapshotCard({
    super.key,
    this.onOpenGoal,
  });

  final ValueChanged<String?>? onOpenGoal;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncValue = ref.watch(currentGoalDetailSnapshotProvider);
    return asyncValue.when(
      data: (snapshot) {
        if (!snapshot.active) return const SizedBox.shrink();
        return _GoalDetailSnapshotSurface(
          snapshot: snapshot,
          onOpenGoal: onOpenGoal,
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(currentGoalDetailSnapshotProvider),
      ),
    );
  }
}

class _GoalDetailSnapshotSurface extends StatelessWidget {
  const _GoalDetailSnapshotSurface({
    required this.snapshot,
    this.onOpenGoal,
  });

  final GoalDetailSnapshot snapshot;
  final ValueChanged<String?>? onOpenGoal;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final percent = (snapshot.progress * 100).round();
    final bottleneck = snapshot.graphNodes.isNotEmpty
        ? snapshot.graphNodes.first
        : snapshot.whyThisMatters;

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        0,
        DS.spacing16,
        DS.spacing10,
      ),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: DS.brandPrimary.withValues(alpha: 0.18),
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.simulationCurrentGoal,
                        style: TextStyle(
                          color: DS.textSecondary,
                          fontSize: DS.fontSizeXs,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        snapshot.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: DS.textPrimary,
                          fontSize: DS.fontSizeLg,
                          fontWeight: DS.fontWeightBold,
                          height: 1.18,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                _ProgressBadge(percent: percent),
              ],
            ),
            if (snapshot.criteria.isNotEmpty) ...[
              const SizedBox(height: DS.spacing12),
              Text(
                l10n.goalDetailMinimumLine,
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: DS.fontSizeXs,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              ...snapshot.criteria.take(3).map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.check_circle_outline_rounded,
                            size: 16,
                            color: DS.success,
                          ),
                          const SizedBox(width: DS.spacing6),
                          Expanded(
                            child: Text(
                              item,
                              style: TextStyle(
                                color: DS.textPrimary,
                                fontSize: DS.fontSizeSm,
                                height: 1.52,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
            ],
            if (bottleneck != null && bottleneck.isNotEmpty) ...[
              const SizedBox(height: DS.spacing10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: DS.info.withValues(alpha: 0.08),
                  borderRadius: DS.borderRadius12,
                  border: Border.all(color: DS.info.withValues(alpha: 0.16)),
                ),
                child: Text(
                  l10n.knowledgeMapReminder(bottleneck),
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: DS.fontSizeSm,
                    height: 1.52,
                  ),
                ),
              ),
            ],
            if (snapshot.nextTaskTitle != null || onOpenGoal != null) ...[
              const SizedBox(height: DS.spacing12),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  if (snapshot.nextTaskTitle != null)
                    _GoalPill(
                      icon: Icons.play_arrow_rounded,
                      label: snapshot.nextTaskTitle!,
                    ),
                  if (onOpenGoal != null)
                    SparkleButton.ghost(
                      label: l10n.goalDetailOpenGoal,
                      icon: const Icon(Icons.arrow_forward_rounded),
                      onPressed: () => onOpenGoal!(snapshot.goalId),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ProgressBadge extends StatelessWidget {
  const _ProgressBadge({required this.percent});

  final int percent;

  @override
  Widget build(BuildContext context) => Container(
        width: 56,
        height: 56,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.1),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.18)),
        ),
        child: Text(
          '$percent%',
          style: TextStyle(
            color: DS.brandPrimary,
            fontSize: DS.fontSizeBase,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

class _GoalPill extends StatelessWidget {
  const _GoalPill({
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
          color: DS.brandPrimary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.brandPrimary),
            const SizedBox(width: DS.spacing4),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: 11,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ),
          ],
        ),
      );
}
