import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/display/lexicon/date_formatting.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/leaderboard/leaderboard_routes.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/services/plan_description_codec.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/task_card.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

class SprintScreen extends ConsumerWidget {
  const SprintScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final activeSprint = planState.activePlans
        .where((p) => p.type == PlanType.sprint)
        .firstOrNull;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.sprintMySprint),
        actions: [
          Tooltip(
            message: context.l10n.planHistoryPlans,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.archive_outlined),
              onPressed: () => unawaited(context.push('/plans/history')),
            ),
          ),
          // D-COMM-1：自我 7 日锚视图入口（次级位置，不占内容主面积）。
          Tooltip(
            message: context.l10n.leaderboardSelfAnchorViewEntry,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.align_vertical_bottom_outlined),
              onPressed: () =>
                  unawaited(context.push(LeaderboardRoutes.selfAnchor)),
            ),
          ),
          // D-COMM-3：冲刺小队入口（次级位置，与自我锚并列；不占内容主面积）。
          Tooltip(
            message: context.l10n.squadEntryLabel,
            child: SparkleIconButton(
              key: const ValueKey('sprint-squad-entry-button'),
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.groups_outlined),
              onPressed: () => unawaited(context.push(CommunityRoutes.squads)),
            ),
          ),
          if (activeSprint != null)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.open_in_new),
              onPressed: () {
                unawaited(context.push('/plans/${activeSprint.id}'));
              },
            ),
          if (activeSprint != null)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.edit_outlined),
              onPressed: () {
                unawaited(context.push('/plans/${activeSprint.id}/edit'));
              },
            ),
        ],
      ),
      child: ContentConstraint(
        child: SparkleRefreshIndicator(
          onRefresh: () => ref.read(planListProvider.notifier).refresh(),
          child: _buildBody(context, planState, activeSprint),
        ),
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    PlanListState state,
    PlanModel? activeSprint,
  ) {
    if (state.isLoading && activeSprint == null) {
      return const _SprintSkeleton();
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
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.xl),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.flag_outlined, size: 80, color: DS.brandPrimary),
              const SizedBox(height: DS.lg),
              Text(
                context.l10n.sprintNoActive,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: DS.sm),
              Text(
                context.l10n.sprintNoActiveHint,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.xl),
              SparkleButton(
                onPressed: () {
                  unawaited(context.push('/exam-sprint/setup'));
                },
                icon: const Icon(Icons.add),
                label: context.l10n.planStartExamSprint,
              ),
            ],
          ),
        ),
      ),
    );
  }
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
                context.l10n.sprintTasks,
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
          ),
          if (fullPlan.tasks == null || fullPlan.tasks!.isEmpty)
            SliverToBoxAdapter(
              // A-SPEC 改造#3（N4/§4.3）：任务空态三要素——为何空 + 影响 +
              // 单一 CTA（去排任务），替换原裸文本 sprintNoTasks。
              child: EmptyState(
                title: context.l10n.sprintNoTasksTitle,
                description: context.l10n.sprintNoTasksHint,
                actionText: context.l10n.sprintNoTasksCta,
                onAction: () => unawaited(context.push('/plans/${plan.id}')),
                icon: Icons.task_outlined,
              ),
            )
          else
            SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final task = fullPlan.tasks![index];
                  return TaskCard(
                    task: task,
                    onTap: () => context.push('/tasks/${task.id}'),
                  );
                },
                childCount: fullPlan.tasks!.length,
              ),
            ),
        ],
      ),
      loading: () => const _SprintSkeleton(),
      error: (err, stack) => CustomErrorWidget.page(
        // A-SPEC 改造#3（N4 屏级错误三件套硬性）：人话标题 + 影响一句 +
        // 可发现的重试钮，替换原 Icon+裸文案无动作分支。错误对象不直出。
        context: context,
        title: context.l10n.sprintLoadErrorTitle,
        message: context.l10n.sprintLoadErrorImpact,
        onRetry: () => ref.invalidate(planDetailProvider(plan.id)),
      ),
    );
  }
}

class _SprintHeader extends ConsumerWidget {
  const _SprintHeader({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // A-SPEC 改造#1（N2 跨面派生值单算）：剩余天数只认服务端下传真值——
    // 与 home 内嵌冲刺仪表卡共用 examSprintDashboardProvider 单一数据源，
    // 收敛存量 S-G6 客户端本地时间推算的双算；payload 未覆盖到本计划时
    // 降级为展示目标日（date_formatting 唯一入口），不再自算天数。
    final examData = ref.watch(examSprintDashboardProvider).valueOrNull;
    final serverDaysLeft =
        (examData != null && examData.planId == plan.id) ? examData.daysLeft : null;
    final parsed = PlanDescriptionCodec.parse(plan.description);

    return Padding(
      padding: const EdgeInsets.all(DS.lg),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              plan.name,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: DS.sm),
            Text(
              parsed.overview.isNotEmpty
                  ? parsed.overview
                  : (plan.description ?? ''),
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (parsed.schedule.isNotEmpty) ...[
              const SizedBox(height: DS.sm),
              Text(
                parsed.schedule,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.5,
                    ),
              ),
            ],
            const SizedBox(height: DS.lg),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  context.l10n.sprintProgress,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                Text(
                  '${(plan.progress * 100).toStringAsFixed(0)}%',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ],
            ),
            const SizedBox(height: DS.sm),
            LinearProgressIndicator(
              value: plan.progress,
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
            ),
            const SizedBox(height: DS.xs),
            // A-SPEC 改造#1：进度口径就地标注——plan.progress 为 plan 域
            // 服务端按任务完成比结算的值，与 exam 卡「今日完成度」口径区分。
            Text(
              context.l10n.sprintProgressScope,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: DS.lg),
            if (serverDaysLeft != null)
              Chip(
                label: Text(
                  serverDaysLeft > 0
                      ? context.l10n.sprintDaysLeft(serverDaysLeft)
                      : serverDaysLeft == 0
                          ? context.l10n.examDay
                          : context.l10n.sprintEnded,
                ),
                avatar: const Icon(Icons.timelapse),
              )
            else if (plan.targetDate != null)
              Chip(
                label: Text(
                  context.l10n.sprintEndsOn(
                    formatSparkleDateOnly(plan.targetDate!, context.l10n),
                  ),
                ),
                avatar: const Icon(Icons.timelapse),
              ),
            const SizedBox(height: DS.md),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () {
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
                  unawaited(context.push('/plans/${plan.id}/review'));
                },
                icon: const Icon(Icons.rate_review_outlined, size: 18),
                label: Text(context.l10n.sprintReviewBtn),
                style: OutlinedButton.styleFrom(
                  foregroundColor: DS.brandPrimary,
                  side:
                      BorderSide(color: DS.brandPrimary.withValues(alpha: 0.4)),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
              ),
            ),
          ],
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
    unawaited(_loadCloseToUnlock());
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
          padding:
              const EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.sm),
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
                            color: DS.brandPrimaryConst,
                          ),
                          const SizedBox(width: DS.sm),
                          Text(
                            context.l10n.sprintAchievements,
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                        ],
                      ),
                      SparkleButton.ghost(
                        onPressed: () => unawaited(
                          context.push('/achievements?type=sprint'),
                        ),
                        label: context.l10n.sextViewAll,
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.sm),
                  ...sprintAchievements.take(3).map(
                        (achievement) =>
                            _SprintAchievementTile(achievement: achievement),
                      ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// A-SPEC 改造#5：稀有度→身份色映射本文件唯一一份（原 _CloseToUnlockBanner
/// 与 _SprintAchievementTile 各持一份私有 helper，重复定义收敛）。
/// 稀有度色只允许出现在图标环/描边等身份位，禁止再进进度条 valueColor。
Color _rarityColor(AchievementRarity rarity) {
  switch (rarity) {
    case AchievementRarity.common:
      return DS.neutral400;
    case AchievementRarity.rare:
      return DS.rarityRare;
    case AchievementRarity.epic:
      return DS.rarityEpic;
    case AchievementRarity.legendary:
      return DS.rarityLegendary;
  }
}

/// A-SPEC 改造#5（B-02 进度/奖励两层分离）：进度位只编码完成度——
/// 未满中性层、已满 success 语义槽；稀有度色不进进度位。
Color _progressValueColor({required bool completed}) =>
    completed ? DS.success : DS.neutral500;

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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final rarityColor = _rarityColor(closest.achievement.rarity);
    final surfaceBase = isDark ? DS.surfaceSecondary : DS.surfacePrimary;
    final accentWash = Color.lerp(
      surfaceBase,
      rarityColor,
      isDark ? 0.18 : 0.12,
    )!;

    return Container(
      key: const ValueKey('sprint-close-unlock-banner'),
      margin: const EdgeInsets.fromLTRB(DS.lg, 0, DS.lg, DS.sm),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        // A-SPEC 改造#5：渐变横幅降级为 S2 单色阶 + 稀有度描边（§5.3
        // gradient 预算 ratchet -1）；色阶仍可保留稀有度身份的低浓度 wash。
        color: accentWash,
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: rarityColor.withValues(alpha: isDark ? 0.3 : 0.18),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            // 稀有度色合法域：图标环身份位（§8.7-3），与进度位分离。
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _rarityColor(closest.achievement.rarity)
                  .withValues(alpha: 0.2),
              border: Border.all(
                color: _rarityColor(closest.achievement.rarity),
                width: 2,
              ),
            ),
            child: Icon(
              Icons.flag_outlined,
              size: DS.iconSizeSm,
              color: _rarityColor(closest.achievement.rarity),
            ),
          ),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.l10n.planSoonUnlock,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                        color: DS.textPrimary,
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
                    // 进度位诚实编码：中性/success 口径色（B-02）。
                    valueColor: AlwaysStoppedAnimation<Color>(
                      _progressValueColor(completed: progress >= 1.0),
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
                context.l10n.planDaysMore(remaining),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral500,
                    ),
              ),
              Text(
                '${closest.progressPercentage}%',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      // 进度读数归中性层，稀有度色只留在图标环身份位（B-02）。
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SprintAchievementTile extends StatelessWidget {
  const _SprintAchievementTile({required this.achievement});

  final AchievementWithProgress achievement;

  @override
  Widget build(BuildContext context) {
    final progress = achievement.progressPercentage / 100.0;
    final rarity = achievement.achievement.rarity;
    final identityColor = _rarityColor(rarity);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: DS.xs),
      child: Row(
        children: [
          // Achievement icon（稀有度色身份位）
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: identityColor.withValues(alpha: 0.2),
              border: Border.all(
                color: identityColor,
                width: 2,
              ),
            ),
            child: Icon(
              achievement.isUnlocked ? Icons.check : Icons.flag_outlined,
              size: DS.iconSizeSm,
              color: identityColor,
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
                // Progress bar（进度位诚实编码：中性/success，B-02）
                ClipRRect(
                  borderRadius: BorderRadius.circular(DS.borderRadiusSM),
                  child: LinearProgressIndicator(
                    value: progress,
                    minHeight: 4,
                    backgroundColor: DS.neutral100,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      _progressValueColor(
                        completed: achievement.isUnlocked || progress >= 1.0,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Progress percentage（读数归中性层/语义槽，不掺稀有度色）
          Text(
            achievement.isUnlocked
                ? context.l10n.planCompletedExclaim
                : '${achievement.progressPercentage}%',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: achievement.isUnlocked
                      ? DS.success
                      : DS.textSecondary,
                  fontWeight: DS.fontWeightMedium,
                ),
          ),
        ],
      ),
    );
  }
}

/// A-SPEC 改造#3（§4.4.1 骨架贴真实布局）：骨架三段与数据态同构——
/// ① header 卡（标题/概述/进度条/倒计时/复盘钮）② 成就卡（图标+标题行 +
/// 40×40 圆环成就行）③ 任务区（标题 + TaskCard 形整卡行），
/// 替换原「3 个 80×80 方块」的形异骨架，消除加载完成跳变。
class _SprintSkeleton extends StatelessWidget {
  const _SprintSkeleton();

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ① header 卡
            Container(
              padding: const EdgeInsets.all(DS.spacing16),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: DS.borderRadius16,
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SparkleSkeleton(width: 200, height: 20),
                  SizedBox(height: DS.spacing12),
                  SparkleSkeleton(width: double.infinity, height: 14),
                  SizedBox(height: DS.spacing8),
                  SparkleSkeleton(width: 260, height: 14),
                  SizedBox(height: DS.spacing16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      SparkleSkeleton(width: 60, height: 14),
                      SparkleSkeleton(width: 48, height: 14),
                    ],
                  ),
                  SizedBox(height: DS.spacing8),
                  SparkleSkeleton(height: 8),
                  SizedBox(height: DS.spacing8),
                  SparkleSkeleton(width: 120, height: 14),
                  SizedBox(height: DS.spacing12),
                  SparkleSkeleton(width: 96, height: 32, borderRadius: 16),
                  SizedBox(height: DS.spacing16),
                  SparkleSkeleton(
                    width: double.infinity,
                    height: 44,
                    borderRadius: 14,
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing16),
            // ② 成就卡
            Container(
              padding: const EdgeInsets.all(DS.spacing16),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: DS.borderRadius16,
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      SparkleSkeleton(width: 24, height: 24, borderRadius: 6),
                      SizedBox(width: DS.spacing8),
                      SparkleSkeleton(width: 110),
                    ],
                  ),
                  SizedBox(height: DS.spacing12),
                  _SkeletonAchievementRow(),
                  SizedBox(height: DS.spacing12),
                  _SkeletonAchievementRow(),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing16),
            // ③ 任务区
            const SparkleSkeleton(width: 80, height: 20),
            const SizedBox(height: DS.spacing12),
            ...List.generate(
              3,
              (_) => const Padding(
                padding: EdgeInsets.only(bottom: DS.spacing8),
                child: _SkeletonTaskRow(),
              ),
            ),
          ],
        ),
      );
}

/// 骨架成就行：圆环 + 标题/描述/进度细条 + 百分比，贴 _SprintAchievementTile。
class _SkeletonAchievementRow extends StatelessWidget {
  const _SkeletonAchievementRow();

  @override
  Widget build(BuildContext context) => const Row(
        children: [
          SparkleSkeleton(width: 40, height: 40, borderRadius: 20),
          SizedBox(width: DS.spacing12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SparkleSkeleton(height: 14),
                SizedBox(height: DS.spacing4),
                SparkleSkeleton(width: 160, height: 12),
                SizedBox(height: DS.spacing8),
                SparkleSkeleton(height: 4),
              ],
            ),
          ),
          SparkleSkeleton(width: 40, height: 14),
        ],
      );
}

/// 骨架任务行：整宽圆角卡 + 两行文案，贴 TaskCard 形制。
class _SkeletonTaskRow extends StatelessWidget {
  const _SkeletonTaskRow();

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
        ),
        child: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SparkleSkeleton(width: 220, height: 14),
            SizedBox(height: DS.spacing8),
            SparkleSkeleton(width: 140, height: 12),
          ],
        ),
      );
}
