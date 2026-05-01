import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/plan_name_provider.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/interactive_task_card.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Plan view - Tasks grouped by plan
class PlanView extends ConsumerWidget {
  const PlanView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planGroups = ref.watch(planGroupsProvider);
    final boardState = ref.watch(taskBoardProvider);
    final selectedPlanId = boardState.selectedPlanId;
    final selectedPlanName = selectedPlanId == null
        ? null
        : ref.watch(planNameProvider(selectedPlanId));

    final sortedKeys = planGroups.keys.toList()
      ..sort((a, b) {
        if (a == null) return 1;
        if (b == null) return -1;
        return a.compareTo(b);
      });

    final filteredKeys = selectedPlanId == null
        ? sortedKeys
        : sortedKeys.where((planId) => planId == selectedPlanId).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const DashboardPlanManager(),
        if (selectedPlanId != null)
          Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing12),
            child: _PlanFilterBanner(
              planName: selectedPlanName ?? '当前计划',
            ),
          ),
        if (filteredKeys.isEmpty)
          _buildEmptyState(
            context,
            isFiltered: selectedPlanId != null,
            selectedPlanName: selectedPlanName,
            onClearFilter: selectedPlanId == null
                ? null
                : () =>
                    ref.read(taskBoardProvider.notifier).clearPlanSelection(),
          )
        else
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            padding: EdgeInsets.zero,
            itemCount: filteredKeys.length,
            separatorBuilder: (context, index) =>
                const SizedBox(height: DS.spacing12),
            itemBuilder: (context, index) {
              final planId = filteredKeys[index];
              final tasks = planGroups[planId]!;
              return _PlanSection(planId: planId, tasks: tasks);
            },
          ),
      ],
    );
  }

  Widget _buildEmptyState(
    BuildContext context, {
    bool isFiltered = false,
    String? selectedPlanName,
    VoidCallback? onClearFilter,
  }) =>
      Container(
      padding: const EdgeInsets.all(DS.spacing32),
      child: Column(
        children: [
          Icon(
            Icons.view_week_rounded,
            size: 48,
            color: DS.textSecondary.withValues(alpha: 0.5),
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            isFiltered
                ? '${selectedPlanName ?? '当前计划'} 暂无任务'
                : '暂无方案任务',
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textSecondary,
            ),
          ),
          if (isFiltered) ...[
            const SizedBox(height: DS.spacing12),
            TextButton.icon(
              onPressed: onClearFilter,
              icon: const Icon(Icons.layers_clear_rounded),
              label: const Text('查看全部计划任务'),
            ),
          ],
        ],
      ),
    );
}

class DashboardPlanManager extends ConsumerWidget {
  const DashboardPlanManager({
    super.key,
    this.compact = false,
  });

  const DashboardPlanManager.compact({super.key}) : compact = true;

  static const int maxActivePlans = 3;

  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final boardState = ref.watch(taskBoardProvider);
    final activePlanId = ref.watch(activePlanProvider);
    final activePlans = _sortPlans(planState.activePlans);
    final allPlans = _sortPlans(planState.plans);
    final inactivePlans = allPlans.where((plan) => !plan.isActive).toList();
    final slots = List<PlanModel?>.generate(
      maxActivePlans,
      (index) => index < activePlans.length ? activePlans[index] : null,
    );
    final hasQuota = activePlans.length < maxActivePlans;

    return Container(
      margin: EdgeInsets.only(bottom: compact ? DS.spacing12 : DS.spacing16),
      padding: EdgeInsets.all(compact ? DS.spacing12 : DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: DS.brandPrimary.withValues(alpha: 0.12),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PlanManagerHeader(
            compact: compact,
            activeCount: activePlans.length,
            totalCount: allPlans.length,
            selectedPlanId: boardState.selectedPlanId,
          ),
          const SizedBox(height: DS.spacing12),
          if (planState.isLoading && allPlans.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: DS.spacing12),
              child: Center(
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            )
          else ...[
            if (planState.error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing12),
                child: Text(
                  planState.error!,
                  style: DS.bodySmall.copyWith(
                    color: DS.semanticError,
                  ),
                ),
              ),
            Wrap(
              spacing: DS.spacing12,
              runSpacing: DS.spacing12,
              children: slots
                  .map(
                    (plan) => SizedBox(
                      width: compact ? 220 : 240,
                      child: plan == null
                          ? _EmptyPlanSlot(
                              compact: compact,
                              hasQuota: hasQuota,
                            )
                          : _ActivePlanSlot(
                              plan: plan,
                              compact: compact,
                              isSelected:
                                  boardState.selectedPlanId == plan.id,
                              isChatContext: activePlanId == plan.id,
                            ),
                    ),
                  )
                  .toList(),
            ),
            if (!hasQuota) ...[
              const SizedBox(height: DS.spacing10),
              Text(
                '当前已占满 3 个活跃计划位，先停用或归档旧计划再创建新的。',
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
            if (inactivePlans.isNotEmpty) ...[
              const SizedBox(height: DS.spacing16),
              Text(
                compact ? '可恢复计划' : '计划库',
                style: context.sparkleTypography.labelLarge.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.textPrimary,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              ...inactivePlans.take(compact ? 3 : 6).map(
                    (plan) => _InactivePlanRow(
                      plan: plan,
                      canActivate: hasQuota,
                    ),
                  ),
            ],
          ],
        ],
      ),
    );
  }

  List<PlanModel> _sortPlans(List<PlanModel> plans) => [...plans]
    ..sort((a, b) {
      if (a.isPrimary != b.isPrimary) {
        return a.isPrimary ? -1 : 1;
      }
      if (a.isActive != b.isActive) {
        return a.isActive ? -1 : 1;
      }
      return b.updatedAt.compareTo(a.updatedAt);
    });
}

class _PlanManagerHeader extends StatelessWidget {
  const _PlanManagerHeader({
    required this.compact,
    required this.activeCount,
    required this.totalCount,
    required this.selectedPlanId,
  });

  final bool compact;
  final int activeCount;
  final int totalCount;
  final String? selectedPlanId;

  @override
  Widget build(BuildContext context) {
    final subtitle = selectedPlanId == null
        ? '把 3 个活跃计划位和任务看板放在一起管理'
        : '已按单个计划聚焦任务，回到全部即可恢复总览';

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: compact ? 32 : 36,
          height: compact ? 32 : 36,
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(
            Icons.account_tree_rounded,
            size: compact ? 16 : 18,
            color: DS.brandPrimary,
          ),
        ),
        const SizedBox(width: DS.spacing10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '计划管理',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                compact ? '活跃 $activeCount/3 · 全部 $totalCount' : subtitle,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing6,
          ),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(
            '$activeCount/3',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: DS.brandPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ),
      ],
    );
  }
}

class _PlanFilterBanner extends ConsumerWidget {
  const _PlanFilterBanner({required this.planName});

  final String planName;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing10,
        ),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.08),
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: DS.brandPrimary.withValues(alpha: 0.18),
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.filter_alt_rounded,
              size: 16,
              color: DS.brandPrimary,
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                '当前聚焦：$planName',
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
            ),
            TextButton(
              onPressed: () =>
                  ref.read(taskBoardProvider.notifier).clearPlanSelection(),
              child: const Text('查看全部'),
            ),
          ],
        ),
      );
}

class _ActivePlanSlot extends ConsumerWidget {
  const _ActivePlanSlot({
    required this.plan,
    required this.compact,
    required this.isSelected,
    required this.isChatContext,
  });

  final PlanModel plan;
  final bool compact;
  final bool isSelected;
  final bool isChatContext;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final progressPercent = (plan.progress * 100).round().clamp(0, 100);
    final taskCount = plan.tasks?.length ?? 0;

    Future<void> togglePlanFilter() async {
      final notifier = ref.read(taskBoardProvider.notifier);
      if (isSelected) {
        notifier.clearPlanSelection();
      } else {
        notifier.selectPlan(plan.id);
      }
    }

    Future<void> setChatContext() async {
      ref.read(activePlanProvider.notifier).selectPlan(plan.id);
      if (!context.mounted) return;
      AppFeedback.success(context, '已切换到 ${plan.name} 作为当前计划上下文');
    }

    Future<void> deactivatePlan() async {
      try {
        await ref.read(planListProvider.notifier).deactivatePlan(plan.id);
        if (ref.read(activePlanProvider) == plan.id) {
          ref.read(activePlanProvider.notifier).clearSelection();
        }
        if (ref.read(taskBoardProvider).selectedPlanId == plan.id) {
          ref.read(taskBoardProvider.notifier).clearPlanSelection();
        }
        if (!context.mounted) return;
        AppFeedback.success(context, '已停用 ${plan.name}');
      } catch (e) {
        if (!context.mounted) return;
        AppFeedback.error(context, e.toString());
      }
    }

    Future<void> setPrimaryPlan() async {
      try {
        await ref.read(planListProvider.notifier).setPrimaryPlan(plan.id);
        if (!context.mounted) return;
        AppFeedback.success(context, '已将 ${plan.name} 设为主计划');
      } catch (e) {
        if (!context.mounted) return;
        AppFeedback.error(context, e.toString());
      }
    }

    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: isSelected
            ? DS.brandPrimary.withValues(alpha: 0.08)
            : DS.surfacePanel,
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: isSelected
              ? DS.brandPrimary.withValues(alpha: 0.3)
              : DS.neutral200,
        ),
      ),
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
                      plan.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.labelLarge.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      _planMetaLabel(plan),
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing8),
              PopupMenuButton<String>(
                onSelected: (value) async {
                  switch (value) {
                    case 'detail':
                      await context.push('/plans/${plan.id}');
                    case 'chat':
                      await setChatContext();
                    case 'primary':
                      await setPrimaryPlan();
                    case 'filter':
                      await togglePlanFilter();
                    case 'deactivate':
                      await deactivatePlan();
                  }
                },
                itemBuilder: (context) => [
                  const PopupMenuItem(
                    value: 'detail',
                    child: Text('查看详情'),
                  ),
                  const PopupMenuItem(
                    value: 'chat',
                    child: Text('设为当前计划'),
                  ),
                  if (!plan.isPrimary)
                    const PopupMenuItem(
                      value: 'primary',
                      child: Text('设为主计划'),
                    ),
                  PopupMenuItem(
                    value: 'filter',
                    child: Text(isSelected ? '取消聚焦' : '聚焦任务'),
                  ),
                  const PopupMenuItem(
                    value: 'deactivate',
                    child: Text('停用计划'),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          Wrap(
            spacing: DS.spacing6,
            runSpacing: DS.spacing6,
            children: [
              _PlanTag(label: plan.isPrimary ? '主计划' : '活跃中'),
              if (isChatContext)
                const _PlanTag(label: '当前对话', highlighted: true),
              if (isSelected) const _PlanTag(label: '任务已聚焦'),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value: plan.progress.clamp(0, 1),
              minHeight: 6,
              backgroundColor: DS.neutral200,
              valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '进度 $progressPercent% · ${taskCount > 0 ? '$taskCount 个任务' : '任务待生成'}',
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing10),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              OutlinedButton.icon(
                onPressed: togglePlanFilter,
                icon: Icon(
                  isSelected
                      ? Icons.layers_clear_rounded
                      : Icons.filter_alt_rounded,
                  size: 16,
                ),
                label: Text(isSelected ? '查看全部' : '聚焦任务'),
              ),
              TextButton.icon(
                onPressed: () => context.push('/plans/${plan.id}'),
                icon: const Icon(Icons.open_in_new_rounded, size: 16),
                label: const Text('详情'),
              ),
            ],
          ),
          if (!compact) ...[
            const SizedBox(height: DS.spacing6),
            TextButton.icon(
              onPressed: setChatContext,
              icon: const Icon(Icons.chat_bubble_outline_rounded, size: 16),
              label: Text(isChatContext ? '当前对话已绑定' : '设为当前计划'),
            ),
          ],
        ],
      ),
    );
  }

  String _planMetaLabel(PlanModel plan) {
    final typeLabel = switch (plan.type) {
      PlanType.sprint => '冲刺计划',
      PlanType.growth => '成长计划',
    };
    if (plan.subject?.isNotEmpty ?? false) {
      return '$typeLabel · ${plan.subject}';
    }
    return typeLabel;
  }
}

class _EmptyPlanSlot extends StatelessWidget {
  const _EmptyPlanSlot({
    required this.compact,
    required this.hasQuota,
  });

  final bool compact;
  final bool hasQuota;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: DS.neutral200,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '空闲计划位',
              style: context.sparkleTypography.labelLarge.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              hasQuota ? '可以继续新建冲刺或成长计划' : '先释放一个计划位再继续',
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                FilledButton.icon(
                  onPressed: hasQuota
                      ? () => context.push('/plans/new?type=sprint')
                      : null,
                  icon: const Icon(Icons.flash_on_rounded, size: 16),
                  label: const Text('新建冲刺'),
                ),
                OutlinedButton.icon(
                  onPressed: hasQuota
                      ? () => context.push('/plans/new?type=growth')
                      : null,
                  icon: const Icon(Icons.trending_up_rounded, size: 16),
                  label: const Text('新建成长'),
                ),
                if (!compact)
                  TextButton.icon(
                    onPressed: () => context.push('/plans/history'),
                    icon: const Icon(Icons.history_rounded, size: 16),
                    label: const Text('查看历史'),
                  ),
              ],
            ),
          ],
        ),
      );
}

class _InactivePlanRow extends ConsumerWidget {
  const _InactivePlanRow({
    required this.plan,
    required this.canActivate,
  });

  final PlanModel plan;
  final bool canActivate;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Row(
          children: [
            Expanded(
              child: InkWell(
                borderRadius: DS.borderRadius12,
                onTap: () => context.push('/plans/${plan.id}'),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing4,
                    vertical: DS.spacing6,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        plan.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: context.sparkleTypography.labelLarge.copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightSemibold,
                        ),
                      ),
                      const SizedBox(height: DS.spacing2),
                      Text(
                        plan.subject?.isNotEmpty ?? false
                            ? plan.subject!
                            : (plan.type == PlanType.sprint
                                ? '冲刺计划'
                                : '成长计划'),
                        style: DS.bodySmall.copyWith(
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: DS.spacing8),
            TextButton(
              onPressed: canActivate
                  ? () async {
                      try {
                        await ref
                            .read(planListProvider.notifier)
                            .activatePlan(plan.id);
                        if (!context.mounted) return;
                        AppFeedback.success(context, '已恢复 ${plan.name}');
                      } catch (e) {
                        if (!context.mounted) return;
                        AppFeedback.error(context, e.toString());
                      }
                    }
                  : null,
              child: const Text('恢复'),
            ),
          ],
        ),
      );
}

class _PlanTag extends StatelessWidget {
  const _PlanTag({
    required this.label,
    this.highlighted = false,
  });

  final String label;
  final bool highlighted;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: (highlighted ? DS.brandPrimary : DS.textSecondary)
              .withValues(alpha: highlighted ? 0.14 : 0.08),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: context.sparkleTypography.labelSmall.copyWith(
            color: highlighted ? DS.brandPrimary : DS.textSecondary,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
      );
}

class _PlanSection extends ConsumerWidget {
  const _PlanSection({
    required this.planId,
    required this.tasks,
  });

  final String? planId;
  final List<TaskModel> tasks;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 获取计划名称，优先显示名称而非ID
    final planName = (planId != null && planId!.isNotEmpty)
        ? ref.watch(planNameProvider(planId!))
        : null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header
        Padding(
          padding: const EdgeInsets.fromLTRB(DS.spacing4, DS.spacing4, DS.spacing12, DS.spacing8),
          child: Row(
            children: [
              Icon(
                Icons.folder_rounded,
                size: 16,
                color: DS.brandPrimaryConst,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                planName ?? planId ?? '未分类',
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: (planName != null || planId != null)
                      ? DS.textPrimary
                      : DS.textSecondary,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Text(
                  '${tasks.length}',
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.brandPrimaryConst,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
            ],
          ),
        ),
        // Tasks
        ...tasks.map((task) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: InteractiveTaskCard(task: task),
            ),),
      ],
    );
  }
}
