import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/features/insights/data/models/growth_dashboard.dart';
import 'package:sparkle/features/insights/presentation/providers/growth_dashboard_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/model_update_receipt.dart';

class GrowthChroniclePage extends ConsumerWidget {
  const GrowthChroniclePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardAsync = ref.watch(growthDashboardProvider);
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(context.l10n.gdChronicleTitle),
      ),
      child: ContentConstraint(
        child: dashboardAsync.when(
          data: (dashboard) => _ChronicleContent(dashboard: dashboard),
          loading: () => const SparkleListSkeleton(),
          error: (_, __) => _GrowthError(
            onRetry: () => ref.read(growthDashboardProvider.notifier).refresh(),
          ),
        ),
      ),
    );
  }
}

class _ChronicleContent extends ConsumerWidget {
  const _ChronicleContent({required this.dashboard});

  final GrowthDashboard dashboard;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final entries = dashboard.chronicleEntries;
    return RefreshIndicator(
      onRefresh: () => ref.read(growthDashboardProvider.notifier).refresh(),
      child: Semantics(
        label: context.l10n.gdChronicleSemantics,
        container: true,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing24,
          ),
          children: [
            _WeeklyStoryCard(narrative: dashboard.weeklyNarrative),
            const SizedBox(height: DS.spacing16),
            if (entries.isEmpty)
              EmptyState(
                icon: Icons.auto_stories_rounded,
                title: context.l10n.gdEmptyChronicleTitle,
                description: context.l10n.gdEmptyChronicleDesc,
              )
            else
              ...entries.map(
                (entry) => _ChronicleTimelineItem(
                  entry: entry,
                  onStatusChanged: (status) => _updateStatus(
                    context,
                    ref,
                    entry,
                    status,
                  ),
                ),
              ),
            if (dashboard.modelUpdates.isNotEmpty) ...[
              const SizedBox(height: DS.spacing16),
              ModelUpdateReceipt(update: dashboard.modelUpdates.first),
            ],
          ],
        ),
      ),
    );
  }

  void _updateStatus(
    BuildContext context,
    WidgetRef ref,
    GrowthChronicleEntry entry,
    String status,
  ) {
    final previous = entry.userStatus;
    ref
        .read(growthDashboardProvider.notifier)
        .updateEntryStatus(entry.id, status);
    final message = switch (status) {
      'confirmed' => context.l10n.gdEntryConfirmed,
      'edited' => context.l10n.gdEntryEdited,
      'rejected' => context.l10n.gdEntryRejected,
      _ => context.l10n.gdEntryEdited,
    };
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        action: SnackBarAction(
          label: context.l10n.gdUndo,
          onPressed: () => ref
              .read(growthDashboardProvider.notifier)
              .updateEntryStatus(entry.id, previous),
        ),
      ),
    );
  }
}

class _WeeklyStoryCard extends StatelessWidget {
  const _WeeklyStoryCard({required this.narrative});

  final WeeklyDashboardNarrative narrative;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: colors.primary.withValues(alpha: 0.18),
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_stories_rounded, color: colors.primary),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  context.l10n.gdGrowthStory,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          Text(
            narrative.title.isEmpty
                ? context.l10n.gdStorySummary
                : narrative.title,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: colors.onSurfaceVariant,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            narrative.story,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: colors.onSurface,
                  height: 1.5,
                ),
          ),
          if (narrative.keyInsights.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.gdKeyInsights,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: colors.onSurface,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: DS.spacing6),
            ...narrative.keyInsights.map(
              (insight) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.arrow_right_rounded,
                      color: colors.primary,
                      size: 18,
                    ),
                    const SizedBox(width: DS.spacing4),
                    Expanded(child: Text(insight)),
                  ],
                ),
              ),
            ),
          ],
          if (narrative.nextWeekSuggestion.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              '${context.l10n.gdNextWeekSuggestion}: ${narrative.nextWeekSuggestion}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: colors.onSurfaceVariant,
                    height: 1.45,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ChronicleTimelineItem extends StatefulWidget {
  const _ChronicleTimelineItem({
    required this.entry,
    required this.onStatusChanged,
  });

  final GrowthChronicleEntry entry;
  final ValueChanged<String> onStatusChanged;

  @override
  State<_ChronicleTimelineItem> createState() => _ChronicleTimelineItemState();
}

class _ChronicleTimelineItemState extends State<_ChronicleTimelineItem> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final accent = _entryColor(context, widget.entry.entryType);
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.14),
                  shape: BoxShape.circle,
                  border: Border.all(color: accent.withValues(alpha: 0.42)),
                ),
                child: Icon(
                  _entryIcon(widget.entry.entryType),
                  color: accent,
                  size: 18,
                ),
              ),
              Container(
                width: 2,
                height: 110,
                color: colors.outlineVariant,
              ),
            ],
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              borderColor: accent.withValues(alpha: 0.18),
              padding: const EdgeInsets.all(DS.spacing14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      _StatusPill(
                        label: _entryTypeLabel(context, widget.entry.entryType),
                        color: accent,
                      ),
                      _StatusPill(
                        label: _statusLabel(context, widget.entry.userStatus),
                        color: colors.secondary,
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    widget.entry.title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: DS.spacing6),
                  Text(
                    widget.entry.narrative,
                    maxLines: _expanded ? null : 3,
                    overflow: _expanded
                        ? TextOverflow.visible
                        : TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: colors.onSurface,
                          height: 1.48,
                        ),
                  ),
                  if (_expanded && widget.entry.evidenceRefs.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing10),
                    Text(
                      context.l10n.gdEvidenceChain,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: DS.spacing6),
                    Wrap(
                      spacing: DS.spacing6,
                      runSpacing: DS.spacing6,
                      children: widget.entry.evidenceRefs
                          .map((ref) => Chip(label: Text(ref)))
                          .toList(growable: false),
                    ),
                  ],
                  const SizedBox(height: DS.spacing12),
                  Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    children: [
                      TextButton.icon(
                        onPressed: () => setState(() => _expanded = !_expanded),
                        icon: Icon(
                          _expanded
                              ? Icons.expand_less_rounded
                              : Icons.expand_more_rounded,
                        ),
                        label: Text(
                          _expanded
                              ? context.l10n.insCollapse
                              : context.l10n.insExpand,
                        ),
                      ),
                      FilledButton.tonalIcon(
                        onPressed: () => widget.onStatusChanged('confirmed'),
                        icon: const Icon(Icons.check_rounded),
                        label: Text(context.l10n.gdConfirm),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => widget.onStatusChanged('edited'),
                        icon: const Icon(Icons.edit_rounded),
                        label: Text(context.l10n.gdEdit),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => widget.onStatusChanged('rejected'),
                        icon: const Icon(Icons.close_rounded),
                        label: Text(context.l10n.gdReject),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontWeight: FontWeight.w800,
            ),
      ),
    );
  }
}

class _GrowthError extends StatelessWidget {
  const _GrowthError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: EmptyState(
        icon: Icons.error_outline_rounded,
        title: context.l10n.gdLoadFailed,
        description: context.l10n.gdNoDataDesc,
        actionText: context.l10n.gdRetry,
        onAction: onRetry,
      ),
    );
  }
}

IconData _entryIcon(String entryType) {
  return switch (entryType) {
    'turning_point' => Icons.alt_route_rounded,
    'pattern_discovered' => Icons.psychology_rounded,
    'user_reflection' => Icons.rate_review_rounded,
    _ => Icons.flag_rounded,
  };
}

Color _entryColor(BuildContext context, String entryType) {
  final colors = Theme.of(context).colorScheme;
  return switch (entryType) {
    'turning_point' => colors.tertiary,
    'pattern_discovered' => colors.secondary,
    'user_reflection' => colors.primary,
    _ => colors.error,
  };
}

String _entryTypeLabel(BuildContext context, String entryType) {
  return switch (entryType) {
    'turning_point' => context.l10n.gdTurningPoint,
    'pattern_discovered' => context.l10n.gdPattern,
    'user_reflection' => context.l10n.gdReflection,
    _ => context.l10n.gdMilestone,
  };
}

String _statusLabel(BuildContext context, String status) {
  return switch (status) {
    'confirmed' => context.l10n.gdConfirmed,
    'edited' => context.l10n.gdEdited,
    'rejected' => context.l10n.gdRejected,
    _ => context.l10n.gdPending,
  };
}
