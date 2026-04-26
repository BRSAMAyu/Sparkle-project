import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class ReviewPlanHubScreen extends ConsumerWidget {
  const ReviewPlanHubScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reviewAsync = ref.watch(todayReviewListProvider);
    final nightlyAsync = ref.watch(nightlyReviewProvider);
    final dashboard = ref.watch(dashboardProvider);
    final planState = ref.watch(planListProvider);
    final taskState = ref.watch(taskListProvider);
    final planNameMap = {
      for (final plan in [...planState.plans, ...planState.activePlans])
        plan.id: plan.name,
    };
    final today = DateTime.now();
    final todayPlanTasks = taskState.tasks
        .where(
          (task) =>
              task.planId != null &&
              task.status != TaskStatus.completed &&
              task.status != TaskStatus.abandoned &&
              (task.dueDate == null ||
                  (task.dueDate!.year == today.year &&
                      task.dueDate!.month == today.month &&
                      task.dueDate!.day == today.day)),
        )
        .take(5)
        .toList();

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.reviewPlanHubTitle),
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.spacing16),
          children: [
            _HeroCard(
              onStartToday: () => context.push('/review?mode=today'),
            ),
            const SizedBox(height: DS.spacing16),
            reviewAsync.when(
              data: (items) => _SummaryCard(
                icon: Icons.auto_stories_rounded,
                title: context.l10n.reviewPlanHubTodayList,
                subtitle: items.isEmpty
                    ? context.l10n.reviewPlanHubNoDueErrors
                    : context.l10n.reviewPlanHubHasErrors(items.length),
                actionLabel: context.l10n.reviewPlanHubStartToday,
                onAction: () => context.push('/review?mode=today'),
              ),
              loading: () => const _LoadingCard(title: context.l10n.reviewPlanHubTodayList),
              error: (error, _) => _SummaryCard(
                icon: Icons.auto_stories_rounded,
                title: context.l10n.reviewPlanHubTodayList,
                subtitle: context.l10n.reviewPlanHubLoadFailed(error),
                actionLabel: context.l10n.reviewPlanHubOpenReview,
                onAction: () => context.push('/review?mode=today'),
              ),
            ),
            const SizedBox(height: DS.spacing12),
            nightlyAsync.when(
              data: (payload) {
                final summary =
                    payload?.widgetPayload?.data['summary']?.toString();
                return _SummaryCard(
                  icon: Icons.nights_stay_outlined,
                  title: context.l10n.reviewPlanHubNightlyReview,
                  subtitle: summary?.isNotEmpty ?? false
                      ? summary!
                      : (payload == null
                          ? context.l10n.reviewPlanHubNoNightlyReview
                          : context.l10n.reviewPlanHubHasNightlyReview),
                  actionLabel: payload == null ? '查看复习页' : '查看今晚回顾',
                  onAction: () => context.push('/review?mode=today'),
                );
              },
              loading: () => const _LoadingCard(title: context.l10n.reviewPlanHubNightlyReview),
              error: (_, __) => _SummaryCard(
                icon: Icons.nights_stay_outlined,
                title: context.l10n.reviewPlanHubNightlyReview,
                subtitle: context.l10n.reviewPlanHubNightlyUnavailable,
                actionLabel: context.l10n.reviewPlanHubOpenReview,
                onAction: () => context.push('/review?mode=today'),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.reviewPlanHubPlanIntegration,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: DS.spacing12),
            if (dashboard.sprint != null)
              _PlanBridgeCard(
                title: dashboard.sprint!.name,
                subtitle:
                    context.l10n.reviewPlanHubSprintProgress((dashboard.sprint!.progress * 100).toInt(), dashboard.sprint!.daysLeft),
                icon: Icons.flash_on_rounded,
                onTap: () => context.push('/sprint'),
              ),
            if (dashboard.growth != null) ...[
              const SizedBox(height: DS.spacing8),
              _PlanBridgeCard(
                title: dashboard.growth!.name,
                subtitle:
                    context.l10n.reviewPlanHubGrowthProgress((dashboard.growth!.progress * 100).toInt(), (dashboard.growth!.masteryLevel * 100).toInt()),
                icon: Icons.trending_up_rounded,
                onTap: () => context.push('/growth'),
              ),
            ],
            if (dashboard.sprint == null && dashboard.growth == null)
              _SummaryCard(
                icon: Icons.layers_clear_outlined,
                title: context.l10n.reviewPlanHubNoActivePlan,
                subtitle: context.l10n.reviewPlanHubCreatePlanFirst,
                actionLabel: context.l10n.reviewPlanHubCreatePlan,
                onAction: () => context.push('/plans/new?type=growth'),
              ),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.reviewPlanHubTodayPlanTasks,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: DS.spacing12),
            if (todayPlanTasks.isEmpty)
              Container(
                padding: const EdgeInsets.all(DS.spacing16),
                decoration: BoxDecoration(
                  color: DS.surfacePanel,
                  borderRadius: DS.borderRadius16,
                  border: Border.all(color: DS.borderSubtle),
                ),
                child: Text(
                  context.l10n.reviewPlanHubNoPlanTasks,
                  style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                ),
              )
            else
              ...todayPlanTasks.map(
                (task) => Card(
                  margin: const EdgeInsets.only(bottom: DS.spacing8),
                  child: ListTile(
                    leading: const Icon(Icons.task_alt_rounded),
                    title: Text(task.title),
                    subtitle: Text(
                      '${planNameMap[task.planId] ?? '计划任务'} · ${task.estimatedMinutes} 分钟',
                    ),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => context.push('/tasks/${task.id}'),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({required this.onStartToday});

  final VoidCallback onStartToday;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing20),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              DS.brandPrimary.withValues(alpha: 0.16),
              DS.info.withValues(alpha: 0.1),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: DS.borderRadius20,
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.14)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.reviewPlanHubHeroDescription,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.reviewPlanHubHeroSubtitle,
              style:
                  DS.bodyMedium.copyWith(color: DS.textSecondary, height: 1.5),
            ),
            const SizedBox(height: DS.spacing16),
            SparkleButton(
              onPressed: onStartToday,
              icon: const Icon(Icons.play_arrow_rounded),
              label: context.l10n.reviewPlanHubStartTodayReview,
            ),
          ],
        ),
      );
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.onAction,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: DS.brandPrimaryConst),
                const SizedBox(width: DS.spacing8),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing10),
            Text(
              subtitle,
              style:
                  DS.bodyMedium.copyWith(color: DS.textSecondary, height: 1.5),
            ),
            const SizedBox(height: DS.spacing12),
            Align(
              alignment: Alignment.centerRight,
              child: SparkleButton.ghost(
                onPressed: onAction,
                label: actionLabel,
              ),
            ),
          ],
        ),
      );
}

class _PlanBridgeCard extends StatelessWidget {
  const _PlanBridgeCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadius16,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: DS.surfacePanel,
            borderRadius: DS.borderRadius16,
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Row(
            children: [
              Icon(icon, color: DS.brandPrimaryConst),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      subtitle,
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded),
            ],
          ),
        ),
      );
}

class _LoadingCard extends StatelessWidget {
  const _LoadingCard({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          children: [
            const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: DS.spacing12),
            Text(title),
          ],
        ),
      );
}
