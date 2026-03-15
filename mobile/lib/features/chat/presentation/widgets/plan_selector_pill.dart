import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Plan Selector Pill Widget
///
/// A tappable pill widget that shows the current plan selection
/// and allows changing it via a bottom sheet.
///
/// States:
/// - No plan selected: Shows "选择计划" in gray
/// - Plan selected: Shows plan name with progress indicator in primary color
class PlanSelectorPill extends ConsumerWidget {
  const PlanSelectorPill({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedPlanId = ref.watch(activePlanProvider);
    final activePlans =
        ref.watch(planListProvider.select((s) => s.activePlans));
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (selectedPlanId == null) {
      return AnimatedSwitcher(
        duration: AnimationSystem.normal,
        switchInCurve: AnimationSystem.smooth,
        switchOutCurve: AnimationSystem.smooth,
        child: _UnselectedPill(
          key: const ValueKey('plan-pill-unselected'),
          isDark: isDark,
          onTap: () => _showPlanSelector(context, ref, activePlans),
        ),
      );
    }

    // Find the selected plan details
    final selectedPlan =
        activePlans.where((p) => p.id == selectedPlanId).firstOrNull;

    if (selectedPlan == null) {
      // Plan not found in active plans - show unselected state
      return AnimatedSwitcher(
        duration: AnimationSystem.normal,
        switchInCurve: AnimationSystem.smooth,
        switchOutCurve: AnimationSystem.smooth,
        child: _UnselectedPill(
          key: const ValueKey('plan-pill-unselected'),
          isDark: isDark,
          onTap: () => _showPlanSelector(context, ref, activePlans),
        ),
      );
    }

    return AnimatedSwitcher(
      duration: AnimationSystem.normal,
      switchInCurve: AnimationSystem.smooth,
      switchOutCurve: AnimationSystem.smooth,
      child: _SelectedPill(
        key: ValueKey('plan-pill-${selectedPlan.id}'),
        plan: selectedPlan,
        isDark: isDark,
        onTap: () => _showPlanSelector(context, ref, activePlans),
      ),
    );
  }

  void _showPlanSelector(
    BuildContext context,
    WidgetRef ref,
    List<PlanModel> activePlans,
  ) {
    HapticFeedback.lightImpact();
    unawaited(
      showModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        isScrollControlled: true,
        builder: (context) => _PlanSelectorSheet(activePlans: activePlans),
      ),
    );
  }
}

class _UnselectedPill extends StatelessWidget {
  const _UnselectedPill({
    required this.isDark,
    required this.onTap,
    super.key,
  });

  final bool isDark;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: GestureDetector(
          onTap: onTap,
          child: MaterialStyler(
            material: AppMaterials.ceramic.copyWith(
              // Use surfaceTertiary to match Dashboard ceramic cards
              backgroundColor: isDark ? DS.surfaceTertiary : DS.neutral200,
            ),
            borderRadius: DS.borderRadius20,
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing8,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.add_circle_outline,
                  size: DS.iconSizeSm,
                  color: DS.neutral500,
                ),
                const SizedBox(width: DS.spacing6),
                Text(
                  '选择计划',
                  style: TextStyle(
                    color: DS.neutral600,
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _SelectedPill extends StatelessWidget {
  const _SelectedPill({
    required this.plan,
    required this.isDark,
    required this.onTap,
    super.key,
  });

  final PlanModel plan;
  final bool isDark;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final planColor = _getPlanColor();
    final progressLabel = _progressLabel();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: GestureDetector(
        onTap: onTap,
        child: MaterialStyler(
          material: AppMaterials.neoGlass.copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                planColor.withValues(alpha: 0.18),
                planColor.withValues(alpha: 0.08),
              ],
            ),
            borderColor: planColor.withValues(alpha: 0.35),
          ),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _getPlanIcon(),
                size: DS.iconSizeSm,
                color: planColor,
              ),
              const SizedBox(width: DS.spacing6),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 140),
                child: Text(
                  plan.name,
                  style: TextStyle(
                    color: isDark ? DS.textPrimary : DS.neutral900,
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightMedium,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: DS.spacing6),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing6,
                  vertical: DS.spacing4 / 2,
                ),
                decoration: BoxDecoration(
                  color: planColor.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(DS.spacing8),
                ),
                child: Text(
                  progressLabel,
                  style: TextStyle(
                    color: planColor,
                    fontSize: DS.fontSizeXs,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing4),
              Icon(
                Icons.keyboard_arrow_down_rounded,
                size: DS.iconSizeSm,
                color: DS.neutral500,
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _progressLabel() {
    final tasks = plan.tasks;
    if (tasks != null && tasks.isNotEmpty) {
      final total = tasks.length;
      final completed =
          tasks.where((task) => task.status == TaskStatus.completed).length;
      if (total > 0) {
        return '$completed/$total';
      }
    }
    return '${(plan.progress * 100).toInt()}%';
  }

  Color _getPlanColor() {
    switch (plan.type) {
      case PlanType.sprint:
        return DS.error;
      case PlanType.growth:
        return DS.success;
    }
  }

  IconData _getPlanIcon() {
    switch (plan.type) {
      case PlanType.sprint:
        return Icons.directions_run_rounded;
      case PlanType.growth:
        return Icons.trending_up_rounded;
    }
  }
}

class _PlanSelectorSheet extends StatelessWidget {
  const _PlanSelectorSheet({required this.activePlans});

  final List<PlanModel> activePlans;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: isDark ? DS.surfaceSecondary : DS.surfacePrimaryElevated,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(DS.spacing24),
        ),
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Handle bar
            Container(
              width: DS.spacing40,
              height: DS.spacing4,
              margin: const EdgeInsets.symmetric(vertical: DS.spacing12),
              decoration: BoxDecoration(
                color: isDark ? DS.neutral700 : DS.neutral300,
                borderRadius: BorderRadius.circular(DS.spacing4 / 2),
              ),
            ),
            // Header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: DS.spacing20),
              child: Row(
                children: [
                  Icon(
                    Icons.event_note_rounded,
                    color: DS.primaryBase,
                  ),
                  const SizedBox(width: DS.spacing12),
                  Text(
                    '选择计划上下文',
                    style: TextStyle(
                      fontSize: DS.fontSizeLg,
                      fontWeight: DS.fontWeightBold,
                      color: isDark ? DS.textPrimary : DS.neutral900,
                    ),
                  ),
                  const Spacer(),
                  SparkleIconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                    variant: ButtonVariant.ghost,
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            // Clear selection option
            if (activePlans.isNotEmpty) _ClearOptionTile(isDark: isDark),
            // Plans list
            if (activePlans.isEmpty)
              _EmptyState(isDark: isDark)
            else
              ...activePlans.map(
                (plan) => _PlanListTile(
                  plan: plan,
                  isDark: isDark,
                ),
              ),
            const SizedBox(height: DS.spacing16),
          ],
        ),
      ),
    );
  }
}

class _ClearOptionTile extends ConsumerWidget {
  const _ClearOptionTile({required this.isDark});

  final bool isDark;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedPlanId = ref.watch(activePlanProvider);
    final isSelected = selectedPlanId == null;

    return InkWell(
      onTap: () {
        ref.read(activePlanProvider.notifier).clearSelection();
        HapticFeedback.lightImpact();
        Navigator.pop(context);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing20,
          vertical: DS.spacing16,
        ),
        decoration: BoxDecoration(
          color: isSelected
              ? DS.primaryBase.withValues(alpha: 0.1)
              : DS.surfacePrimary.withValues(alpha: 0),
        ),
        child: Row(
          children: [
            Icon(
              Icons.not_interested_rounded,
              color: DS.neutral500,
            ),
            const SizedBox(width: DS.spacing16),
            Text(
              '不使用计划上下文',
              style: TextStyle(
                fontSize: DS.fontSizeBase,
                fontWeight:
                    isSelected ? DS.fontWeightSemibold : DS.fontWeightRegular,
                color: isDark ? DS.textPrimary : DS.neutral900,
              ),
            ),
            const Spacer(),
            if (isSelected)
              Icon(
                Icons.check_circle,
                color: DS.primaryBase,
                size: DS.iconSizeBase,
              ),
          ],
        ),
      ),
    );
  }
}

class _PlanListTile extends ConsumerWidget {
  const _PlanListTile({
    required this.plan,
    required this.isDark,
  });

  final PlanModel plan;
  final bool isDark;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedPlanId = ref.watch(activePlanProvider);
    final isSelected = selectedPlanId == plan.id;
    final planColor = _getPlanColor();

    return InkWell(
      onTap: () {
        ref.read(activePlanProvider.notifier).selectPlan(plan.id);
        HapticFeedback.lightImpact();
        Navigator.pop(context);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing20,
          vertical: DS.spacing16,
        ),
        decoration: BoxDecoration(
          color: isSelected
              ? planColor.withValues(alpha: 0.1)
              : DS.surfacePrimary.withValues(alpha: 0),
          border: Border(
            left: BorderSide(
              color: isSelected
                  ? planColor
                  : DS.surfacePrimary.withValues(alpha: 0),
              width: 4,
            ),
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing8),
              decoration: BoxDecoration(
                color: planColor.withValues(alpha: 0.15),
                borderRadius: DS.borderRadius8,
              ),
              child: Icon(
                _getPlanIcon(),
                color: planColor,
                size: DS.iconSizeBase,
              ),
            ),
            const SizedBox(width: DS.spacing16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    plan.name,
                    style: TextStyle(
                      fontSize: DS.fontSizeBase,
                      fontWeight: isSelected
                          ? DS.fontWeightSemibold
                          : DS.fontWeightMedium,
                      color: isDark ? DS.textPrimary : DS.neutral900,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: DS.spacing4 / 2),
                  Row(
                    children: [
                      Text(
                        _getPlanTypeLabel(),
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: planColor,
                        ),
                      ),
                      const SizedBox(width: DS.spacing8),
                      Icon(
                        Icons.circle,
                        size: DS.spacing4,
                        color: DS.neutral500,
                      ),
                      const SizedBox(width: DS.spacing8),
                      Text(
                        '${(plan.progress * 100).toInt()}% 完成',
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.neutral500,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            if (isSelected)
              Icon(
                Icons.check_circle,
                color: planColor,
                size: DS.iconSizeBase,
              ),
          ],
        ),
      ),
    );
  }

  Color _getPlanColor() {
    switch (plan.type) {
      case PlanType.sprint:
        return DS.error;
      case PlanType.growth:
        return DS.success;
    }
  }

  IconData _getPlanIcon() {
    switch (plan.type) {
      case PlanType.sprint:
        return Icons.directions_run_rounded;
      case PlanType.growth:
        return Icons.trending_up_rounded;
    }
  }

  String _getPlanTypeLabel() {
    switch (plan.type) {
      case PlanType.sprint:
        return '冲刺';
      case PlanType.growth:
        return '成长';
    }
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.isDark});

  final bool isDark;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(DS.xl),
        child: Column(
          children: [
            Icon(
              Icons.event_busy_rounded,
              size: DS.iconSize3xl,
              color: DS.neutral400,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              '暂无活跃计划',
              style: TextStyle(
                fontSize: DS.fontSizeBase,
                color: DS.neutral600,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              '创建一个计划后即可在此选择',
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.neutral500,
              ),
            ),
          ],
        ),
      );
}
