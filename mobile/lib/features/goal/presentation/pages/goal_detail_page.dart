import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/strategy_migration_wizard.dart';
import 'package:sparkle/features/community/presentation/widgets/similar_goal_pursuers_card.dart';
import 'package:sparkle/features/goal/data/models/scenario_pack_models.dart';
import 'package:sparkle/features/goal/data/services/scenario_pack_service.dart';
import 'package:sparkle/features/goal/presentation/providers/goal_detail_provider.dart';
import 'package:sparkle/features/goal/presentation/widgets/goal_bottleneck_strip.dart';
import 'package:sparkle/features/goal/presentation/widgets/goal_detail_l10n.dart';
import 'package:sparkle/features/goal/presentation/widgets/journey_progress_card.dart';
import 'package:sparkle/features/goal/presentation/widgets/minimum_criteria_card.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';

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
            label: l10n.goalDetailEdit,
            child: IconButton(
              icon: const Icon(Icons.edit_rounded),
              onPressed: () {
                final data = state.valueOrNull;
                if (data == null) return;
                _showEditDialog(
                    context, ref, goalId, data.goal.title, data.goal.goalType);
              },
            ),
          ),
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
      backgroundColor: DS.surface,
      body: state.when(
        data: (data) => SparkleRefreshIndicator(
          onRefresh: () => ref.read(goalDetailProvider(goalId).notifier).load(),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
            children: [
              _GoalHeader(data: data),
              JourneyProgressFutureCard(goalId: goalId),
              if (data.strategyBelief != null) ...[
                const SizedBox(height: 14),
                StrategyMigrationWizard(
                  goalId: goalId,
                  belief: data.strategyBelief,
                  onMigrated: (_) =>
                      ref.read(goalDetailProvider(goalId).notifier).load(),
                ),
              ],
              const SizedBox(height: 14),
              MinimumCriteriaCard(
                criteria: data.minimumAcceptanceCriteria,
                onConfirm: () async {
                  try {
                    await ref
                        .read(goalDetailProvider(goalId).notifier)
                        .confirmMinimumCriteria();
                    if (!context.mounted) return;
                    AppFeedback.undoable(
                      context: context,
                      message: l10n.goalDetailConfirmedSnack,
                      actionLabel: l10n.goalDetailUndo,
                      onAction: () {
                        unawaited(
                          ref
                              .read(goalDetailProvider(goalId).notifier)
                              .undoConfirmMinimumCriteria()
                              .catchError((Object _) {}),
                        );
                      },
                    );
                  } catch (e) {
                    if (!context.mounted) return;
                    AppFeedback.error(context, l10n.goalDetailLoadFailed);
                  }
                },
              ),
              const SizedBox(height: DS.spacing20),
              GoalBottleneckStrip(items: data.knowledgeBottlenecks),
              const SizedBox(height: DS.spacing20),
              _TodayStepCard(goalId: goalId, step: data.todaysMinimalNextStep),
              const SizedBox(height: 14),
              _PlanHealthBand(goalId: goalId, data: data),
              const SizedBox(height: 14),
              _AccountabilityCard(summary: data.accountabilityStatus),
              const SizedBox(height: 14),
              _RelatedSourcesCard(sources: data.relatedSources),
              const SizedBox(height: 14),
              SimilarGoalPursuersCard(goalId: goalId),
            ],
          ),
        ),
        loading: () => const _GoalDetailSkeleton(),
        error: (_, __) => _ErrorState(
          onRetry: () => ref.read(goalDetailProvider(goalId).notifier).load(),
        ),
      ),
    );
  }
}

/// Async wrapper that fetches journey progress and renders [JourneyProgressCard].
class JourneyProgressFutureCard extends ConsumerWidget {
  const JourneyProgressFutureCard({required this.goalId, super.key});

  final String goalId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final progressAsync = ref.watch(_journeyProgressProvider(goalId));
    return progressAsync.when(
      data: (progress) => JourneyProgressCard(progress: progress),
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }
}

final _journeyProgressProvider = FutureProvider.family<JourneyProgress, String>(
  (ref, goalId) =>
      ref.read(scenarioPackServiceProvider).getProgress(goalId: goalId),
);

class _GoalHeader extends StatelessWidget {
  const _GoalHeader({required this.data});

  final GoalDetailData data;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final textTheme = Theme.of(context).textTheme;
    final progress = data.goal.progress;

    return Semantics(
      container: true,
      label: data.goal.title,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceHigh,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Hero(
              tag: 'goal-${data.goal.id}',
              child: Material(
                type: MaterialType.transparency,
                child: SizedBox(
                  height: 76,
                  width: 76,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      CircularProgressIndicator(
                        value: progress,
                        strokeWidth: 8,
                        backgroundColor: DS.surfaceHigh,
                      ),
                      Text(
                        '${(progress * 100).round()}%',
                        style: textTheme.labelLarge?.copyWith(
                          color: DS.textPrimary,
                          fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
            ),
            ),
            const SizedBox(width: DS.spacing16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    data.goal.title,
                    style: textTheme.titleLarge?.copyWith(
                      color: DS.textPrimary,
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
                      _buildTargetDateChip(context, data.goal.targetDate, l10n),
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

  static Widget _buildTargetDateChip(
    BuildContext context,
    String? targetDate,
    dynamic l10n,
  ) {
    final isZh = Localizations.localeOf(context).languageCode == 'zh';
    if (targetDate == null) {
      return _InfoChip(
        icon: Icons.event_outlined,
        label: l10n.goalDetailNoTargetDate as String,
        semanticsLabel: l10n.goalDetailTargetDate as String,
      );
    }

    final parsed = DateTime.tryParse(targetDate);
    final isOverdue =
        parsed != null && parsed.isBefore(DateTime.now().add(const Duration(days: 1)).copyWith(hour: 0, minute: 0, second: 0));

    if (!isOverdue) {
      return _InfoChip(
        icon: Icons.event_outlined,
        label: targetDate,
        semanticsLabel: l10n.goalDetailTargetDate as String,
      );
    }

    // Overdue: show warning chip
    final overdueLabel = isZh ? '已过期' : 'Overdue';
    final amber = const Color(0xFFE6A817);
    return Semantics(
      label: '${l10n.goalDetailTargetDate}: $targetDate, $overdueLabel',
      child: Chip(
        avatar: Icon(Icons.warning_amber_rounded, size: 18, color: amber),
        label: Text('$targetDate · $overdueLabel'),
        backgroundColor: amber.withValues(alpha: 0.12),
        side: BorderSide(color: amber.withValues(alpha: 0.5)),
        labelStyle: Theme.of(context)
            .textTheme
            .labelMedium
            ?.copyWith(color: amber, fontWeight: FontWeight.w700),
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
    final textTheme = Theme.of(context).textTheme;

    return Semantics(
      container: true,
      label: l10n.goalDetailTodayStep,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.playlist_add_check_rounded,
                  color: DS.textPrimary,
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    l10n.goalDetailTodayStep,
                    style: textTheme.titleMedium?.copyWith(
                      color: DS.textPrimary,
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
                  color: DS.textPrimary,
                ),
              )
            else ...[
              Text(
                step.title!,
                style: textTheme.titleSmall?.copyWith(
                  color: DS.textPrimary,
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
                      foreground: DS.textPrimary,
                      background: DS.brandPrimary.withValues(alpha: 0.18),
                    ),
                  if (step.estimatedMinutes != null)
                    _InfoChip(
                      icon: Icons.timer_outlined,
                      label:
                          '${l10n.goalDetailEstimated} ${l10n.goalDetailMinutes(step.estimatedMinutes!)}',
                      foreground: DS.textPrimary,
                      background: DS.brandPrimary.withValues(alpha: 0.18),
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
                      try {
                        await ref
                            .read(goalDetailProvider(goalId).notifier)
                            .startNextStep();
                        if (!context.mounted) return;
                        AppFeedback.undoable(
                          context: context,
                          message: l10n.goalDetailStartedSnack,
                          actionLabel: l10n.goalDetailUndo,
                          onAction: () => unawaited(
                            ref
                                .read(goalDetailProvider(goalId).notifier)
                                .undoStartNextStep(),
                          ),
                        );
                      } catch (e) {
                        if (!context.mounted) return;
                        AppFeedback.error(
                          context,
                          '${l10n.goalDetailStart}: $e',
                        );
                      }
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
                        try {
                          await ref
                              .read(goalDetailProvider(goalId).notifier)
                              .completeNextStep();
                        } catch (e) {
                          if (!context.mounted) return;
                          AppFeedback.error(
                            context,
                            '${l10n.goalDetailComplete}: $e',
                          );
                        }
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

class _PlanHealthBand extends ConsumerWidget {
  const _PlanHealthBand({required this.goalId, required this.data});

  final String goalId;
  final GoalDetailData data;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final activePlanId = ref.watch(activePlanProvider);
    return _SectionCard(
      icon: Icons.monitor_heart_outlined,
      title: l10n.goalDetailPlanHealth,
      trailing: activePlanId != null
          ? TextButton.icon(
              onPressed: () => context.push('/plans/$activePlanId'),
              icon: const Icon(Icons.arrow_forward_rounded, size: 18),
              label: Text(
                Localizations.localeOf(context).languageCode == 'zh'
                    ? '查看计划'
                    : 'View Plan',
              ),
            )
          : null,
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
    final textTheme = Theme.of(context).textTheme;

    return _SectionCard(
      icon: Icons.source_outlined,
      title: l10n.goalDetailRelatedSources,
      children: [
        if (sources.isEmpty)
          Text(
            l10n.goalDetailNoSources,
            style: textTheme.bodyMedium?.copyWith(
              color: DS.textSecondary,
            ),
          )
        else
          for (final source in sources)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.description_outlined, color: DS.brandPrimary),
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
    final textTheme = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: DS.brandPrimary),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  title,
                  style: textTheme.titleMedium?.copyWith(
                    color: DS.textPrimary,
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
                    color: DS.textPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Text(
                '${(value * 100).round()}%',
                style: textTheme.labelLarge?.copyWith(
                  color: DS.textSecondary,
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
    final fg = foreground ?? DS.textSecondary;
    return Semantics(
      label: semanticsLabel == null ? label : '$semanticsLabel: $label',
      child: Chip(
        avatar: Icon(icon, size: 18, color: fg),
        label: Text(label),
        backgroundColor: background ?? DS.surfaceHigh,
        side: BorderSide(color: DS.borderSubtle),
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
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline_rounded,
              size: 44,
              color: DS.error,
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

class _GoalDetailSkeleton extends StatelessWidget {
  const _GoalDetailSkeleton();

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        padding: EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: circular progress + title area
            Row(
              children: [
                const SparkleSkeleton(width: 76, height: 76, borderRadius: 999),
                SizedBox(width: DS.spacing16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SparkleSkeleton(width: 180, height: 20),
                      SizedBox(height: DS.spacing8),
                      const SparkleSkeleton(width: 120, height: 14),
                      SizedBox(height: DS.spacing12),
                      Row(
                        children: [
                          const SparkleSkeleton(width: 60, height: 24),
                          SizedBox(width: DS.spacing8),
                          const SparkleSkeleton(width: 80, height: 24),
                          SizedBox(width: DS.spacing8),
                          const SparkleSkeleton(width: 50, height: 24),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            SizedBox(height: DS.spacing20),
            // Strategy card
            const SparkleCardSkeleton(),
            SizedBox(height: DS.spacing14),
            // Minimum criteria card
            const SparkleCardSkeleton(),
            SizedBox(height: DS.spacing14),
            // Today step card
            const SparkleCardSkeleton(),
            SizedBox(height: DS.spacing14),
            // Plan health band
            const SparkleCardSkeleton(),
            SizedBox(height: DS.spacing14),
            // Accountability card
            const SparkleCardSkeleton(),
            SizedBox(height: DS.spacing14),
            // Metrics
            ...List.generate(
              3,
              (_) => Padding(
                padding: EdgeInsets.only(bottom: DS.spacing12),
                child: Row(
                  children: [
                    const SparkleSkeleton(width: 80, height: 14),
                    SizedBox(width: DS.spacing12),
                    const Expanded(child: SparkleSkeleton(height: 8)),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
}

Future<void> _showEditDialog(
  BuildContext context,
  WidgetRef ref,
  String goalId,
  String currentTitle,
  String currentDescription, // reserved type string for future use
) async {
  final l10n = context.l10n;
  final titleController = TextEditingController(text: currentTitle);
  final descriptionController = TextEditingController(text: currentDescription);

  final result = await showModalBottomSheet<Map<String, String>>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) => Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: DS.textSecondary.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            l10n.goalDetailEdit,
            style: Theme.of(ctx)
                .textTheme
                .titleLarge
                ?.copyWith(fontWeight: FontWeight.w700, color: DS.textPrimary),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: titleController,
            decoration: InputDecoration(
              labelText: l10n.goalDetailEditTitle,
              hintText: l10n.goalDetailEditHintTitle,
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: descriptionController,
            decoration: InputDecoration(
              labelText: l10n.goalDetailEditDescription,
              hintText: l10n.goalDetailEditHintDescription,
            ),
            maxLines: 3,
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () => Navigator.of(ctx).pop({
                'title': titleController.text.trim(),
                'description': descriptionController.text.trim(),
              }),
              child: Text(l10n.goalDetailEditSave),
            ),
          ),
        ],
      ),
    ),
  );

  if (result == null || !context.mounted) return;

  final newTitle = result['title'] ?? '';
  final newDescription = result['description'] ?? '';
  if (newTitle.isEmpty) return;

  try {
    await ref.read(goalDetailProvider(goalId).notifier).updateGoal(
          title: newTitle,
          description: newDescription.isNotEmpty ? newDescription : null,
        );
    if (!context.mounted) return;
    AppFeedback.success(context, l10n.goalDetailEditSuccess);
  } catch (e) {
    if (!context.mounted) return;
    AppFeedback.error(context, l10n.goalDetailEditFailed);
  }
}
