import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';

class WeeklyGrowthNarrativeCard extends ConsumerStatefulWidget {
  const WeeklyGrowthNarrativeCard({
    super.key,
    this.initialExpanded = false,
  });

  final bool initialExpanded;

  @override
  ConsumerState<WeeklyGrowthNarrativeCard> createState() =>
      _WeeklyGrowthNarrativeCardState();
}

class _WeeklyGrowthNarrativeCardState
    extends ConsumerState<WeeklyGrowthNarrativeCard> {
  late bool _expanded = widget.initialExpanded;

  @override
  void didUpdateWidget(covariant WeeklyGrowthNarrativeCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!oldWidget.initialExpanded && widget.initialExpanded) {
      _expanded = true;
    }
  }

  @override
  Widget build(BuildContext context) {
    final narrativeAsync = ref.watch(weeklyGrowthNarrativeProvider);
    return narrativeAsync.when(
      data: (narrative) => _NarrativeSurface(
        narrative: narrative,
        expanded: _expanded,
        onToggleExpanded: () => setState(() => _expanded = !_expanded),
      ),
      loading: () => const _NarrativeLoadingSurface(),
      error: (_, __) => _NarrativeErrorSurface(
        onRetry: () => ref.invalidate(weeklyGrowthNarrativeProvider),
      ),
    );
  }
}

class _NarrativeSurface extends StatelessWidget {
  const _NarrativeSurface({
    required this.narrative,
    required this.expanded,
    required this.onToggleExpanded,
  });

  final WeeklyGrowthNarrative narrative;
  final bool expanded;
  final VoidCallback onToggleExpanded;

  @override
  Widget build(BuildContext context) {
    final metrics = _metrics(context, narrative);
    final accent = narrative.hasData ? DS.success : DS.info;
    final highlights = narrative.highlights.isNotEmpty
        ? narrative.highlights
        : narrative.sentences.take(3).toList(growable: false);

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: accent.withValues(alpha: 0.18),
      padding: const EdgeInsets.all(DS.spacing16),
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
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  narrative.hasData
                      ? Icons.auto_stories_rounded
                      : Icons.flag_rounded,
                  color: accent,
                  size: 20,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      narrative.period,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      narrative.dateRangeLabel,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
              IconButton(
                tooltip: expanded
                    ? context.l10n.insCollapse
                    : context.l10n.insExpand,
                onPressed: onToggleExpanded,
                icon: Icon(
                  expanded
                      ? Icons.expand_less_rounded
                      : Icons.expand_more_rounded,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            narrative.body,
            maxLines: expanded ? null : 3,
            overflow: expanded ? TextOverflow.visible : TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  height: 1.55,
                  color: DS.textPrimary,
                ),
          ),
          if (expanded && highlights.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            ...highlights.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Icon(
                        Icons.brightness_1_rounded,
                        size: 8,
                        color: accent,
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: Text(
                        item,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.45,
                            ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
          if (expanded && narrative.hasBiggestImprovement) ...[
            const SizedBox(height: DS.spacing4),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: accent.withValues(alpha: 0.18),
                ),
              ),
              child: Text(
                '${context.l10n.wgnBiggestImprovement(narrative.biggestImprovementNode)} '
                '${narrative.biggestImprovementBefore.toStringAsFixed(0)}% → '
                '${narrative.biggestImprovementAfter.toStringAsFixed(0)}%',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
            ),
          ],
          if (expanded && narrative.nextWeekSuggestion.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.wgnNextWeekGoal(narrative.nextWeekSuggestion),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                    height: 1.45,
                  ),
            ),
          ],
          AnimatedCrossFade(
            firstChild: const SizedBox.shrink(),
            secondChild: Padding(
              padding: const EdgeInsets.only(top: DS.spacing12),
              child: Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: metrics,
              ),
            ),
            crossFadeState:
                expanded ? CrossFadeState.showSecond : CrossFadeState.showFirst,
            duration: const Duration(milliseconds: 180),
          ),
        ],
      ),
    );
  }

  List<Widget> _metrics(BuildContext context, WeeklyGrowthNarrative narrative) {
    final items = <Widget>[];
    if (narrative.studyDays > 0) {
      items.add(
        _MetricPill(
          icon: Icons.calendar_today_rounded,
          label: context.l10n.insStudyDays(narrative.studyDays),
        ),
      );
    }
    if (narrative.tasksCompleted > 0) {
      items.add(
        _MetricPill(
          icon: Icons.task_alt_rounded,
          label: context.l10n.insTasksDone(narrative.tasksCompleted),
        ),
      );
    }
    if (narrative.errorsFixed > 0) {
      items.add(
        _MetricPill(
          icon: Icons.psychology_alt_rounded,
          label: context.l10n.insErrorsFixed(narrative.errorsFixed),
        ),
      );
    }
    if (narrative.reflectionRecords > 0) {
      items.add(
        _MetricPill(
          icon: Icons.rate_review_rounded,
          label: context.l10n.insReflections(narrative.reflectionRecords),
        ),
      );
    }
    if (narrative.masteryDelta > 0) {
      items.add(
        _MetricPill(
          icon: Icons.trending_up_rounded,
          label: context.l10n.insMasteryGain(narrative.masteryDelta.toInt()),
        ),
      );
    }
    if (narrative.planCompletedCount > 0) {
      items.add(
        _MetricPill(
          icon: Icons.flag_circle_rounded,
          label: _localized(
            zh: '计划收尾 ${narrative.planCompletedCount}',
            en: '${narrative.planCompletedCount} plans near done',
          ),
        ),
      );
    }
    if (narrative.planDriftCount > 0) {
      items.add(
        _MetricPill(
          icon: Icons.route_rounded,
          label: _localized(
            zh: '计划漂移 ${narrative.planDriftCount}',
            en: '${narrative.planDriftCount} plan drifts',
          ),
        ),
      );
    }
    if (narrative.auroraCorrectionCount > 0) {
      items.add(
        _MetricPill(
          icon: Icons.tune_rounded,
          label: _localized(
            zh: 'Aurora 校准 ${narrative.auroraCorrectionCount}',
            en: '${narrative.auroraCorrectionCount} Aurora corrections',
          ),
        ),
      );
    }
    if (items.isEmpty) {
      items.add(
        _MetricPill(
          icon: Icons.flag_rounded,
          label: context.l10n.insFirstWeek,
        ),
      );
    }
    return items;
  }

  String _localized({required String zh, required String en}) =>
      I18nService.instance.isChinese ? zh : en;
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceBase.withValues(alpha: 0.72),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.textSecondary,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
      );
}

class _NarrativeLoadingSurface extends StatelessWidget {
  const _NarrativeLoadingSurface();

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(DS.spacing16),
        child: Row(
          children: [
            SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: DS.info,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Text(
                I18nService.instance.isChinese
                    ? '正在整理这周的成长线索...'
                    : 'Organizing this week\'s growth threads...',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ),
          ],
        ),
      );
}

class _NarrativeErrorSurface extends StatelessWidget {
  const _NarrativeErrorSurface({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: DS.warning.withValues(alpha: 0.18),
        padding: const EdgeInsets.all(DS.spacing16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.sync_problem_rounded, color: DS.warning, size: 20),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Text(
                I18nService.instance.isChinese
                    ? '这周故事暂时没有同步成功，先继续学习，稍后再看。'
                    : 'This week\'s story didn\'t sync. Keep learning and check back later.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
            ),
            IconButton(
              tooltip: context.l10n.insRetry,
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
            ),
          ],
        ),
      );
}
