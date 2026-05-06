import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/goal/presentation/widgets/goal_conflict_dialog.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';
import 'package:sparkle/features/home/presentation/widgets/goal_switcher.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

class MultiGoalDashboardCard extends ConsumerWidget {
  const MultiGoalDashboardCard({
    super.key,
    this.overview,
  });

  final MultiGoalOverview? overview;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (overview != null) {
      return _MultiGoalDashboardContent(overview: overview!);
    }

    final asyncOverview = ref.watch(multiGoalOverviewProvider);
    return asyncOverview.when(
      data: (data) => _MultiGoalDashboardContent(overview: data),
      loading: () => const _MultiGoalDashboardSkeleton(),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(multiGoalOverviewProvider),
      ),
    );
  }
}

class _MultiGoalDashboardContent extends ConsumerStatefulWidget {
  const _MultiGoalDashboardContent({required this.overview});

  final MultiGoalOverview overview;

  @override
  ConsumerState<_MultiGoalDashboardContent> createState() =>
      _MultiGoalDashboardContentState();
}

class _MultiGoalDashboardContentState
    extends ConsumerState<_MultiGoalDashboardContent> {
  bool _expanded = true;

  @override
  Widget build(BuildContext context) {
    final overview = widget.overview;
    if (overview.goals.isEmpty) {
      return const SizedBox.shrink();
    }

    final zh = I18nService.instance.isChinese;
    final suggestion = overview.suggestion;
    final selectedGoalId = overview.selectedGoalId;

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardSectionShell(
          key: const ValueKey('multi-goal-dashboard-card'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DashboardSectionHeader(
                icon: Icons.account_tree_rounded,
                accentColor: DS.info,
                title: overview.goals.length == 1
                    ? context.l10n.dashboardActivePlan
                    : (zh ? '多目标仪表盘' : 'Multi-goal Dashboard'),
                summary: overview.goals.length == 1
                    ? context.l10n.dashboardBriefingSummary
                    : (zh
                        ? '${overview.goals.length} 个活跃目标'
                        : '${overview.goals.length} active goals'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    GoalSwitcher(overview: overview, dense: true),
                    const SizedBox(width: DS.spacing4),
                    GestureDetector(
                      onTap: () => setState(() => _expanded = !_expanded),
                      child: Padding(
                        padding: const EdgeInsets.all(DS.spacing4),
                        child: AnimatedRotation(
                          turns: _expanded ? 0.5 : 0,
                          duration: DS.durationFast,
                          child: Icon(
                            Icons.expand_more_rounded,
                            size: 18,
                            color: DS.textSecondary,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              AnimatedCrossFade(
                firstChild: const SizedBox(width: double.infinity, height: 0),
                secondChild: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (suggestion != null && suggestion.hasConflict) ...[
                      const SizedBox(height: DS.spacing14),
                      _SuggestionCard(
                        suggestion: suggestion,
                        isSelected: suggestion.primaryGoalId == selectedGoalId,
                        onResolveConflict: () => _showConflictResolution(context, overview),
                      ),
                    ],
                    const SizedBox(height: DS.spacing14),
                    Column(
                      children: [
                        for (final goal in overview.goals.take(5)) ...[
                          _GoalRow(
                            goal: goal,
                            isSelected: goal.id == selectedGoalId,
                            onTap: () {
                              unawaited(
                                ref
                                    .read(activeGoalProvider.notifier)
                                    .selectGoal(goal.id),
                              );
                              ref.invalidate(multiGoalOverviewProvider);
                              try {
                                unawaited(
                                  context.push(
                                    '/goals/${Uri.encodeComponent(goal.id)}',
                                  ),
                                );
                              } catch (_) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(context.l10n.planViewDetails),
                                  ),
                                );
                              }
                            },
                          ),
                          if (goal != overview.goals.take(5).last)
                            const SizedBox(height: DS.spacing8),
                        ],
                      ],
                    ),
                  ],
                ),
                crossFadeState: _expanded
                    ? CrossFadeState.showSecond
                    : CrossFadeState.showFirst,
                duration: DS.durationFast,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SuggestionCard extends ConsumerWidget {
  const _SuggestionCard({
    required this.suggestion,
    required this.isSelected,
    this.onResolveConflict,
  });

  final GoalArbitrationSuggestion suggestion;
  final bool isSelected;
  final VoidCallback? onResolveConflict;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final zh = I18nService.instance.isChinese;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.warning.withValues(alpha: 0.08),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.warning.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.lightbulb_outline_rounded,
                size: 18,
                color: DS.warning,
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  zh ? '今天我建议先做' : 'Suggested first today',
                  style: context.sparkleTypography.labelLarge.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            suggestion.rationale,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: context.sparkleTypography.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.35,
            ),
          ),
          if (!isSelected) ...[
            const SizedBox(height: DS.spacing10),
            Row(
              children: [
                SparkleButton.ghost(
                  label: zh ? '采用建议' : 'Use suggestion',
                  icon: const Icon(Icons.check_rounded),
                  onPressed: () {
                    unawaited(
                      ref
                          .read(activeGoalProvider.notifier)
                          .selectGoal(suggestion.primaryGoalId),
                    );
                    ref.invalidate(multiGoalOverviewProvider);
                  },
                ),
                if (onResolveConflict != null) ...[
                  const SizedBox(width: DS.spacing8),
                  SparkleButton.ghost(
                    label: zh ? '手动调整' : 'Adjust',
                    icon: const Icon(Icons.tune_rounded),
                    onPressed: onResolveConflict!,
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}

Future<void> _showConflictResolution(BuildContext context, MultiGoalOverview overview) async {
  final totalMinutes = overview.goals.fold<int>(
    0,
    (sum, g) => sum + (g.timeFraction != null ? (g.timeFraction! * 120).round() : 30),
  );
  final options = overview.goals.take(5).map((g) {
    final isCritical = g.weeklyConflictCount > 2 || (g.healthScore < 0.5);
    return GoalConflictOption(
      goalId: g.id,
      goalTitle: g.title,
      suggestedMinutes: g.timeFraction != null ? (g.timeFraction! * 120).round() : 30,
      reason: g.currentPhase ?? '',
      urgency: isCritical ? 'critical' : '',
    );
  }).toList();

  await showGoalConflictDialog(
    context,
    totalAvailableMinutes: totalMinutes,
    options: options,
  );
}

class _GoalRow extends StatelessWidget {
  const _GoalRow({
    required this.goal,
    required this.isSelected,
    required this.onTap,
  });

  final ActiveGoalSnapshot goal;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final accent =
        isSelected ? DS.brandPrimary : _healthColor(goal.healthScore);

    return Semantics(
      button: true,
      label: goal.title,
      child: InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadius16,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing12),
          decoration: BoxDecoration(
            color: isSelected
                ? DS.brandPrimary.withValues(alpha: 0.08)
                : DS.surfaceOverlay.withValues(alpha: 0.5),
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color: isSelected
                  ? DS.brandPrimary.withValues(alpha: 0.26)
                  : DS.borderSubtle,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    isSelected
                        ? Icons.radio_button_checked_rounded
                        : Icons.radio_button_unchecked_rounded,
                    size: 18,
                    color: accent,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      goal.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.bodyMedium.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ),
                  _HealthPill(score: goal.healthScore, color: accent),
                ],
              ),
              const SizedBox(height: DS.spacing10),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  _MetaPill(
                    icon: Icons.event_rounded,
                    label: _deadlineLabel(goal.deadlineDays, zh),
                  ),
                  _MetaPill(
                    icon: Icons.timeline_rounded,
                    label: goal.currentPhase ?? (zh ? '进行中' : 'In progress'),
                  ),
                  _MetaPill(
                    icon: Icons.warning_amber_rounded,
                    label: zh
                        ? '本周冲突 ${goal.weeklyConflictCount}'
                        : '${goal.weeklyConflictCount} conflicts',
                  ),
                  if (goal.timeFraction != null)
                    _MetaPill(
                      icon: Icons.pie_chart_rounded,
                      label: '${(goal.timeFraction! * 100).round()}%',
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HealthPill extends StatelessWidget {
  const _HealthPill({
    required this.score,
    required this.color,
  });

  final double score;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: DS.borderRadiusFull,
        ),
        child: Text(
          '${(score * 100).round()}%',
          style: context.sparkleTypography.labelSmall.copyWith(
            color: color,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

class _MetaPill extends StatelessWidget {
  const _MetaPill({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: 5,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePrimaryElevated,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ],
        ),
      );
}

class _MultiGoalDashboardSkeleton extends StatelessWidget {
  const _MultiGoalDashboardSkeleton();

  @override
  Widget build(BuildContext context) => const ContentConstraint(
        child: Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing10,
          ),
          child: SparkleCardSkeleton(),
        ),
      );
}

Color _healthColor(double score) {
  if (score >= 0.72) return DS.success;
  if (score >= 0.46) return DS.warning;
  return DS.error;
}

String _deadlineLabel(int? days, bool zh) {
  if (days == null) return zh ? '无截止日' : 'No deadline';
  if (days == 0) return zh ? '今天截止' : 'Due today';
  if (days < 0) return zh ? '已逾期 ${days.abs()} 天' : '${days.abs()}d overdue';
  return zh ? '剩余 $days 天' : '${days}d left';
}
