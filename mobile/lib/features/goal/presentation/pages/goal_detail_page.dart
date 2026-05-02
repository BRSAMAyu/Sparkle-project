import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/goal/presentation/providers/goal_detail_provider.dart';
import 'package:sparkle/features/goal/presentation/widgets/goal_bottleneck_strip.dart';
import 'package:sparkle/features/goal/presentation/widgets/goal_detail_l10n.dart';
import 'package:sparkle/features/goal/presentation/widgets/minimum_criteria_card.dart';

class GoalDetailPage extends ConsumerWidget {
  const GoalDetailPage({
    required this.goalId,
    super.key,
  });

  final String goalId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(goalDetailProvider(goalId));
    final l10n = context.l10n;
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        leading: Semantics(
          button: true,
          label: l10n.goalDetailBack,
          child: IconButton(
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: () => context.pop(),
          ),
        ),
        title: Text(l10n.goalDetailTitle),
        actions: [
          Semantics(
            button: true,
            label: l10n.goalDetailRefresh,
            child: IconButton(
              icon: const Icon(Icons.refresh_rounded),
              onPressed: () =>
                  ref.read(goalDetailProvider(goalId).notifier).load(),
            ),
          ),
        ],
      ),
      backgroundColor: colorScheme.surface,
      body: state.when(
        data: (data) => RefreshIndicator(
          onRefresh: () => ref.read(goalDetailProvider(goalId).notifier).load(),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
            children: [
              _GoalHeader(data: data),
              const SizedBox(height: 14),
              MinimumCriteriaCard(
                criteria: data.minimumAcceptanceCriteria,
                onConfirm: () {
                  ref
                      .read(goalDetailProvider(goalId).notifier)
                      .confirmMinimumCriteria();
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(l10n.goalDetailConfirmedSnack),
                      action: SnackBarAction(
                        label: l10n.goalDetailUndo,
                        onPressed: () => ref
                            .read(goalDetailProvider(goalId).notifier)
                            .undoConfirmMinimumCriteria(),
                      ),
                    ),
                  );
                },
                onModify: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text(l10n.goalDetailModifySnack)),
                  );
                },
              ),
              const SizedBox(height: 22),
              GoalBottleneckStrip(items: data.knowledgeBottlenecks),
              const SizedBox(height: 22),
              _TodayStepCard(goalId: goalId, step: data.todaysMinimalNextStep),
              const SizedBox(height: 14),
              _PlanHealthBand(data: data),
              const SizedBox(height: 14),
              _AccountabilityCard(summary: data.accountabilityStatus),
              const SizedBox(height: 14),
              _RelatedSourcesCard(sources: data.relatedSources),
            ],
          ),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _ErrorState(
          onRetry: () => ref.read(goalDetailProvider(goalId).notifier).load(),
        ),
      ),
    );
  }
}

class _GoalHeader extends StatelessWidget {
  const _GoalHeader({required this.data});

  final GoalDetailData data;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final progress = data.goal.progress;

    return Semantics(
      container: true,
      label: data.goal.title,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: colorScheme.outlineVariant),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 76,
              width: 76,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CircularProgressIndicator(
                    value: progress,
                    strokeWidth: 8,
                    backgroundColor: colorScheme.surfaceContainerHighest,
                  ),
                  Text(
                    '${(progress * 100).round()}%',
                    style: textTheme.labelLarge?.copyWith(
                      color: colorScheme.onSurface,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    data.goal.title,
                    style: textTheme.titleLarge?.copyWith(
                      color: colorScheme.onSurface,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _InfoChip(
                        icon: Icons.flag_outlined,
                        label: data.goal.status,
                        semanticsLabel:
                            '${l10n.goalDetailStatus}: ${data.goal.status}',
                      ),
                      _InfoChip(
                        icon: Icons.psychology_outlined,
                        label: l10n.goalDetailMasteryPercent(
                          (data.goal.mastery * 100).round(),
                        ),
                        semanticsLabel: l10n.goalDetailMastery,
                      ),
                      _InfoChip(
                        icon: Icons.event_outlined,
                        label:
                            data.goal.targetDate ?? l10n.goalDetailNoTargetDate,
                        semanticsLabel: l10n.goalDetailTargetDate,
                      ),
                      _InfoChip(
                        icon: Icons.priority_high_rounded,
                        label: data.goal.priority,
                        semanticsLabel: l10n.goalDetailPriority,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TodayStepCard extends ConsumerWidget {
  const _TodayStepCard({
    required this.goalId,
    required this.step,
  });

  final String goalId;
  final TodaysMinimalNextStep step;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Semantics(
      container: true,
      label: l10n.goalDetailTodayStep,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: colorScheme.primaryContainer,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.playlist_add_check_rounded,
                  color: colorScheme.onPrimaryContainer,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    l10n.goalDetailTodayStep,
                    style: textTheme.titleMedium?.copyWith(
                      color: colorScheme.onPrimaryContainer,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (!step.hasTask)
              Text(
                l10n.goalDetailNoTodayStep,
                style: textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onPrimaryContainer,
                ),
              )
            else ...[
              Text(
                step.title!,
                style: textTheme.titleSmall?.copyWith(
                  color: colorScheme.onPrimaryContainer,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (step.type != null)
                    _InfoChip(
                      icon: Icons.category_outlined,
                      label: step.type!,
                      foreground: colorScheme.onPrimaryContainer,
                      background: colorScheme.primary.withValues(alpha: 0.18),
                    ),
                  if (step.estimatedMinutes != null)
                    _InfoChip(
                      icon: Icons.timer_outlined,
                      label:
                          '${l10n.goalDetailEstimated} ${l10n.goalDetailMinutes(step.estimatedMinutes!)}',
                      foreground: colorScheme.onPrimaryContainer,
                      background: colorScheme.primary.withValues(alpha: 0.18),
                    ),
                ],
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  FilledButton.icon(
                    onPressed: () async {
                      await ref
                          .read(goalDetailProvider(goalId).notifier)
                          .startNextStep();
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(l10n.goalDetailStartedSnack),
                          action: SnackBarAction(
                            label: l10n.goalDetailUndo,
                            onPressed: () => unawaited(
                              ref
                                  .read(goalDetailProvider(goalId).notifier)
                                  .undoStartNextStep(),
                            ),
                          ),
                        ),
                      );
                    },
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: Text(l10n.goalDetailStart),
                  ),
                  OutlinedButton.icon(
                    onPressed: () async {
                      final confirmed = await showDialog<bool>(
                        context: context,
                        builder: (context) => AlertDialog(
                          title: Text(l10n.goalDetailCompletedTitle),
                          content: Text(l10n.goalDetailCompletedBody),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.of(context).pop(false),
                              child: Text(l10n.goalDetailCancel),
                            ),
                            FilledButton(
                              onPressed: () => Navigator.of(context).pop(true),
                              child: Text(l10n.goalDetailComplete),
                            ),
                          ],
                        ),
                      );
                      if (confirmed ?? false) {
                        await ref
                            .read(goalDetailProvider(goalId).notifier)
                            .completeNextStep();
                      }
                    },
                    icon: const Icon(Icons.check_rounded),
                    label: Text(l10n.goalDetailComplete),
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

class _PlanHealthBand extends StatelessWidget {
  const _PlanHealthBand({required this.data});

  final GoalDetailData data;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return _SectionCard(
      icon: Icons.monitor_heart_outlined,
      title: l10n.goalDetailPlanHealth,
      children: [
        _MetricLine(
          label: l10n.goalDetailProgress,
          value: data.planHealth.overall,
        ),
        _MetricLine(
          label: l10n.goalDetailPhaseHealth,
          value: data.planHealth.phaseHealth,
        ),
        _MetricLine(
          label: l10n.goalDetailTaskCompletion,
          value: data.planHealth.taskCompletionRate,
        ),
        const SizedBox(height: 8),
        _InfoChip(
          icon: Icons.timeline_outlined,
          label: '${l10n.goalDetailCurrentPhase}: ${data.currentPhase.name}',
        ),
      ],
    );
  }
}

class _AccountabilityCard extends StatelessWidget {
  const _AccountabilityCard({required this.summary});

  final AccountabilityStatusSummary summary;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return _SectionCard(
      icon: Icons.diversity_3_outlined,
      title: l10n.goalDetailAccountability,
      trailing: TextButton.icon(
        onPressed: () => context.push('/community/accountability'),
        icon: const Icon(Icons.arrow_forward_rounded),
        label: Text(l10n.goalDetailOpenCommunity),
      ),
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _InfoChip(
              icon: Icons.people_outline_rounded,
              label: l10n.goalDetailPartners(summary.partnerCount),
            ),
            _InfoChip(
              icon: Icons.task_alt_rounded,
              label: l10n.goalDetailCommitments(summary.activeCommitments),
            ),
            _InfoChip(
              icon: Icons.update_rounded,
              label: summary.lastCheckin ?? l10n.goalDetailNoCheckin,
            ),
          ],
        ),
      ],
    );
  }
}

class _RelatedSourcesCard extends StatelessWidget {
  const _RelatedSourcesCard({required this.sources});

  final List<RelatedSource> sources;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return _SectionCard(
      icon: Icons.source_outlined,
      title: l10n.goalDetailRelatedSources,
      children: [
        if (sources.isEmpty)
          Text(
            l10n.goalDetailNoSources,
            style: textTheme.bodyMedium?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          )
        else
          for (final source in sources)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading:
                  Icon(Icons.description_outlined, color: colorScheme.primary),
              title: Text(
                source.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Text(
                '${source.type} · ${l10n.goalDetailRelevance((source.relevance * 100).round())}',
              ),
            ),
      ],
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.icon,
    required this.title,
    required this.children,
    this.trailing,
  });

  final IconData icon;
  final String title;
  final List<Widget> children;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: colorScheme.primary),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  title,
                  style: textTheme.titleMedium?.copyWith(
                    color: colorScheme.onSurface,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              if (trailing != null) trailing!,
            ],
          ),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }
}

class _MetricLine extends StatelessWidget {
  const _MetricLine({
    required this.label,
    required this.value,
  });

  final String label;
  final double value;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurface,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Text(
                '${(value * 100).round()}%',
                style: textTheme.labelLarge?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          LinearProgressIndicator(value: value, minHeight: 6),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({
    required this.icon,
    required this.label,
    this.semanticsLabel,
    this.foreground,
    this.background,
  });

  final IconData icon;
  final String label;
  final String? semanticsLabel;
  final Color? foreground;
  final Color? background;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final fg = foreground ?? colorScheme.onSurfaceVariant;
    return Semantics(
      label: semanticsLabel == null ? label : '$semanticsLabel: $label',
      child: Chip(
        avatar: Icon(icon, size: 18, color: fg),
        label: Text(label),
        backgroundColor: background ?? colorScheme.surfaceContainerHighest,
        side: BorderSide(color: colorScheme.outlineVariant),
        labelStyle:
            Theme.of(context).textTheme.labelMedium?.copyWith(color: fg),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colorScheme = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline_rounded,
              size: 44,
              color: colorScheme.error,
            ),
            const SizedBox(height: 12),
            Text(l10n.goalDetailLoadFailed),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(l10n.goalDetailRetry),
            ),
          ],
        ),
      ),
    );
  }
}
