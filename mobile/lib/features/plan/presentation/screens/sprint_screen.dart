import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
// import 'package:sparkle/features/task/presentation/widgets/task_card.dart'; // Assuming TaskCard is available

class SprintScreen extends ConsumerWidget {
  const SprintScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final activeSprint = planState.activePlans
        .where((p) => p.type == PlanType.sprint)
        .firstOrNull;

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('My Sprint'),
        actions: [
          IconButton(
            icon: const Icon(Icons.archive_outlined),
            tooltip: '历史计划',
            onPressed: () => context.push('/plans/history'),
          ),
          if (activeSprint != null)
            IconButton(
              icon: const Icon(Icons.open_in_new),
              onPressed: () {
                context.push('/plans/${activeSprint.id}');
              },
            ),
          if (activeSprint != null)
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              onPressed: () {
                context.push('/plans/${activeSprint.id}/edit');
              },
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(planListProvider.notifier).refresh(),
        child: _buildBody(context, planState, activeSprint),
      ),
    );
  }

  Widget _buildBody(
      BuildContext context, PlanListState state, PlanModel? activeSprint,) {
    if (state.isLoading && activeSprint == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (activeSprint == null) {
      return const _NoActiveSprintView();
    }

    return _ActiveSprintView(plan: activeSprint);
  }
}

class _NoActiveSprintView extends StatelessWidget {
  const _NoActiveSprintView();

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.xl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.flag_outlined, size: 80, color: DS.brandPrimary),
              const SizedBox(height: DS.lg),
              Text(
                'No Active Sprint',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: DS.sm),
              const Text(
                'Create a new sprint plan to focus on a short-term goal.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.xl),
              ElevatedButton.icon(
                onPressed: () {
                  context.push('/plans/new?type=sprint');
                },
                icon: const Icon(Icons.add),
                label: const Text('Create Sprint Plan'),
              ),
            ],
          ),
        ),
      );
}

class _ActiveSprintView extends ConsumerWidget {
  const _ActiveSprintView({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // We need the full plan details (with tasks), so we watch the detail provider
    final planDetailAsync = ref.watch(planDetailProvider(plan.id));

    return planDetailAsync.when(
      data: (fullPlan) => CustomScrollView(
        slivers: [
          SliverToBoxAdapter(child: _SprintHeader(plan: fullPlan)),
          // Sprint Achievements Progress Section
          const SliverToBoxAdapter(child: _SprintAchievementsProgress()),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(DS.lg),
              child: Text(
                'Tasks',
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
          ),
          if (fullPlan.tasks == null || fullPlan.tasks!.isEmpty)
            const SliverToBoxAdapter(
                child: Center(child: Text('No tasks in this sprint.')),)
          else
            SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final task = fullPlan.tasks![index];
                  // return TaskCard(task: task); // TODO: Uncomment when TaskCard is available and integrated
                  return ListTile(
                      title: Text(task.title),
                      subtitle: Text(task.status.name),);
                },
                childCount: fullPlan.tasks!.length,
              ),
            ),
        ],
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, stack) => Center(child: Text('Error: $err')),
    );
  }
}

class _SprintHeader extends StatelessWidget {
  const _SprintHeader({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context) {
    final daysLeft = plan.targetDate?.difference(DateTime.now()).inDays ?? 0;

    return Padding(
      padding: const EdgeInsets.all(DS.lg),
      child: Card(
        elevation: 4,
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(plan.name,
                  style: Theme.of(context).textTheme.headlineMedium,),
              const SizedBox(height: DS.sm),
              Text(plan.description ?? '',
                  style: Theme.of(context).textTheme.bodyMedium,),
              const SizedBox(height: DS.lg),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Progress',
                      style: Theme.of(context).textTheme.bodyLarge,),
                  Text('${(plan.progress * 100).toStringAsFixed(0)}%',
                      style: Theme.of(context).textTheme.bodyLarge,),
                ],
              ),
              const SizedBox(height: DS.sm),
              LinearProgressIndicator(
                value: plan.progress,
                minHeight: 8,
                borderRadius: BorderRadius.circular(4),
              ),
              const SizedBox(height: DS.lg),
              Chip(
                label:
                    Text(daysLeft > 0 ? '$daysLeft days left' : 'Sprint ended'),
                avatar: const Icon(Icons.timelapse),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Sprint Achievements Progress Widget
/// Shows relevant sprint achievements and their progress
class _SprintAchievementsProgress extends ConsumerStatefulWidget {
  const _SprintAchievementsProgress();

  @override
  ConsumerState<_SprintAchievementsProgress> createState() =>
      _SprintAchievementsProgressState();
}

class _SprintAchievementsProgressState
    extends ConsumerState<_SprintAchievementsProgress> {
  List<AchievementWithProgress> _closeToUnlock = [];
  bool _isLoadingClose = false;

  @override
  void initState() {
    super.initState();
    _loadCloseToUnlock();
  }

  Future<void> _loadCloseToUnlock() async {
    if (_isLoadingClose) return;
    setState(() => _isLoadingClose = true);
    try {
      final close = await ref
          .read(achievementProvider.notifier)
          .getCloseToUnlockAchievements(category: 'sprint');
      if (mounted) {
        setState(() => _closeToUnlock = close);
      }
    } finally {
      if (mounted) {
        setState(() => _isLoadingClose = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final achievementState = ref.watch(achievementProvider);

    // Filter sprint achievements
    final sprintAchievements = achievementState.achievements
        .where((a) => a.achievement.type == AchievementType.sprint)
        .toList();

    if (sprintAchievements.isEmpty && _closeToUnlock.isEmpty) {
      return const SizedBox.shrink();
    }

    // Sort by progress (descending), then by rarity
    sprintAchievements.sort((a, b) {
      if (a.isUnlocked != b.isUnlocked) {
        return a.isUnlocked ? -1 : 1;
      }
      return b.progressPercentage.compareTo(a.progressPercentage);
    });

    return Column(
      children: [
        // P0功能: 成就临界提示横幅
        if (_closeToUnlock.isNotEmpty)
          _CloseToUnlockBanner(
            achievements: _closeToUnlock,
            onRefresh: _loadCloseToUnlock,
          ),
        // Sprint Achievements Card
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.sm),
          child: Card(
            elevation: 2,
            child: Padding(
              padding: const EdgeInsets.all(DS.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.military_tech,
                            size: DS.iconSizeSm,
                            color: DS.brandPrimary,
                          ),
                          const SizedBox(width: DS.sm),
                          Text(
                            'Sprint Achievements',
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                        ],
                      ),
                      TextButton(
                        onPressed: () => context.push('/achievements?type=sprint'),
                        child: const Text('View All'),
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.sm),
                  ...sprintAchievements.take(3).map((achievement) =>
                      _SprintAchievementTile(achievement: achievement),),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// P0功能: 成就临界提示横幅
/// 显示接近解锁的成就（80%以上进度）
class _CloseToUnlockBanner extends StatelessWidget {
  const _CloseToUnlockBanner({
    required this.achievements,
    this.onRefresh,
  });

  final List<AchievementWithProgress> achievements;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final closest = achievements.first;
    final progressTarget = closest.userProgress?.progressTarget ?? 1;
    final progressValue = closest.userProgress?.progressValue ?? 0;
    final remaining = progressTarget - progressValue;
    final progress = closest.progressPercentage / 100.0;

    return Container(
      margin: const EdgeInsets.fromLTRB(DS.lg, 0, DS.lg, DS.sm),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            DS.brandPrimary.withValues(alpha: 0.1),
            DS.brandPrimary.withValues(alpha: 0.05),
          ],
        ),
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: DS.brandPrimary.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _getRarityColor(closest.achievement.rarity)
                  .withValues(alpha: 0.2),
              border: Border.all(
                color: _getRarityColor(closest.achievement.rarity),
                width: 2,
              ),
            ),
            child: Icon(
              Icons.flag_outlined,
              size: DS.iconSizeSm,
              color: _getRarityColor(closest.achievement.rarity),
            ),
          ),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '即将解锁！',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                        color: DS.brandPrimary,
                      ),
                ),
                Text(
                  closest.achievement.name,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightMedium,
                      ),
                ),
                const SizedBox(height: DS.xs),
                ClipRRect(
                  borderRadius: BorderRadius.circular(DS.borderRadiusSM),
                  child: LinearProgressIndicator(
                    value: progress,
                    minHeight: 4,
                    backgroundColor: DS.neutral100,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      _getRarityColor(closest.achievement.rarity),
                    ),
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '再$remaining',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral500,
                    ),
              ),
              Text(
                '${closest.progressPercentage}%',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: _getRarityColor(closest.achievement.rarity),
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Color _getRarityColor(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return DS.neutral400;
      case AchievementRarity.rare:
        return const Color(0xFFFFD700);
      case AchievementRarity.epic:
        return const Color(0xFF9B59B6);
      case AchievementRarity.legendary:
        return const Color(0xFFFF6B6B);
    }
  }
}

class _SprintAchievementTile extends StatelessWidget {
  const _SprintAchievementTile({required this.achievement});

  final AchievementWithProgress achievement;

  @override
  Widget build(BuildContext context) {
    final progress = achievement.progressPercentage / 100.0;
    final rarity = achievement.achievement.rarity;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: DS.xs),
      child: Row(
        children: [
          // Achievement icon
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _getRarityColor(rarity).withValues(alpha: 0.2),
              border: Border.all(
                color: _getRarityColor(rarity),
                width: 2,
              ),
            ),
            child: Icon(
              achievement.isUnlocked ? Icons.check : Icons.flag_outlined,
              size: DS.iconSizeSm,
              color: _getRarityColor(rarity),
            ),
          ),
          const SizedBox(width: DS.sm),
          // Achievement info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  achievement.achievement.name,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightMedium,
                      ),
                ),
                Text(
                  achievement.achievement.description ?? '',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: DS.xs),
                // Progress bar
                ClipRRect(
                  borderRadius: BorderRadius.circular(DS.borderRadiusSM),
                  child: LinearProgressIndicator(
                    value: progress,
                    minHeight: 4,
                    backgroundColor: DS.neutral100,
                    valueColor: AlwaysStoppedAnimation<Color>(_getRarityColor(rarity)),
                  ),
                ),
              ],
            ),
          ),
          // Progress percentage
          Text(
            achievement.isUnlocked ? '完成!' : '${achievement.progressPercentage}%',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: _getRarityColor(rarity),
                  fontWeight: DS.fontWeightMedium,
                ),
          ),
        ],
      ),
    );
  }

  Color _getRarityColor(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return DS.neutral400;
      case AchievementRarity.rare:
        return const Color(0xFFFFD700);
      case AchievementRarity.epic:
        return const Color(0xFF9B59B6);
      case AchievementRarity.legendary:
        return const Color(0xFFFF6B6B);
    }
  }
}
