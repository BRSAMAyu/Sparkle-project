import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

class GoalSwitcher extends ConsumerWidget {
  const GoalSwitcher({
    super.key,
    this.overview,
    this.dense = false,
  });

  final MultiGoalOverview? overview;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (overview != null) {
      return _GoalSwitcherContent(overview: overview!, dense: dense);
    }

    final asyncOverview = ref.watch(multiGoalOverviewProvider);
    return asyncOverview.maybeWhen(
      data: (data) => _GoalSwitcherContent(overview: data, dense: dense),
      orElse: () => _GoalSwitcherFrame(
        dense: dense,
        child: const SizedBox(
          height: 20,
          width: 140,
          child: LinearProgressIndicator(minHeight: 2),
        ),
      ),
    );
  }
}

class _GoalSwitcherContent extends ConsumerWidget {
  const _GoalSwitcherContent({
    required this.overview,
    required this.dense,
  });

  final MultiGoalOverview overview;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final zh = I18nService.instance.isChinese;
    if (overview.goals.isEmpty) {
      return _GoalSwitcherFrame(
        dense: dense,
        child: Text(
          zh ? '暂无关注目标' : 'No focus goal',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: context.sparkleTypography.bodySmall.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      );
    }

    final selectedGoal = overview.selectedGoal ?? overview.goals.first;
    return _GoalSwitcherFrame(
      dense: dense,
      child: PopupMenuButton<String>(
        tooltip: zh ? '切换当前关注目标' : 'Switch focus goal',
        initialValue: selectedGoal.id,
        onSelected: (goalId) {
          unawaited(ref.read(activeGoalProvider.notifier).selectGoal(goalId));
          ref.invalidate(multiGoalOverviewProvider);
        },
        itemBuilder: (context) => [
          for (final goal in overview.goals)
            PopupMenuItem<String>(
              value: goal.id,
              child: Row(
                children: [
                  Icon(
                    goal.id == selectedGoal.id
                        ? Icons.radio_button_checked_rounded
                        : Icons.radio_button_unchecked_rounded,
                    size: 18,
                    color: goal.id == selectedGoal.id
                        ? DS.brandPrimary
                        : DS.textTertiary,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      goal.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
        ],
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.flag_rounded,
              size: dense ? 16 : 18,
              color: DS.brandPrimary,
            ),
            const SizedBox(width: DS.spacing6),
            Flexible(
              child: Text(
                selectedGoal.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.sparkleTypography.bodySmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ),
            const SizedBox(width: DS.spacing4),
            Icon(
              Icons.expand_more_rounded,
              size: dense ? 16 : 18,
              color: DS.textSecondary,
            ),
          ],
        ),
      ),
    );
  }
}

class _GoalSwitcherFrame extends StatelessWidget {
  const _GoalSwitcherFrame({
    required this.child,
    required this.dense,
  });

  final Widget child;
  final bool dense;

  @override
  Widget build(BuildContext context) => Material(
        color: DS.surfacePrimaryElevated.withValues(alpha: 0.82),
        borderRadius: DS.borderRadiusFull,
        child: Container(
          constraints: BoxConstraints(
            minHeight: dense ? 34 : 40,
            maxWidth: dense ? 220 : 320,
          ),
          padding: EdgeInsets.symmetric(
            horizontal: dense ? DS.spacing10 : DS.spacing12,
            vertical: dense ? DS.spacing6 : DS.spacing8,
          ),
          decoration: BoxDecoration(
            borderRadius: DS.borderRadiusFull,
            border: Border.all(color: DS.borderSubtle),
          ),
          child: child,
        ),
      );
}
