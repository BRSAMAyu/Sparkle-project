import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/input_formatters.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_providers.dart';
import 'package:sparkle/features/community/presentation/widgets/group_recommendation_card.dart';
import 'package:sparkle/features/community/presentation/widgets/shared_resource_card.dart';

class GroupsHubView extends ConsumerWidget {
  const GroupsHubView({
    super.key,
    this.padding = const EdgeInsets.fromLTRB(16, 16, 16, 32),
  });

  final EdgeInsets padding;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupsAsync = ref.watch(myGroupsProvider);
    final recommendationsAsync = ref.watch(groupRecommendationsProvider);
    final directoryAsync = ref.watch(groupDiscoverProvider);

    return SparkleRefreshIndicator(
      onRefresh: () async {
        ref
          ..invalidate(myGroupsProvider)
          ..invalidate(groupRecommendationsProvider)
          ..invalidate(groupDiscoverProvider);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: padding,
        children: [
          // NAV-IA P-4：小队入口补位——Community（同伴关系的家）内零小队
          // 入口是结构性失衡（`/community/squads` 此前仅 sprint 屏与错题
          // 分享弹窗两个入边）。首行一行式入口直达小队列表，把「找到小队」
          // 从 3 跳收敛到 1 跳；sprint 屏既有入口保留不动。
          const _SquadsEntryTile(),
          const SizedBox(height: DS.spacing20),
          // S-03 收敛①：今日打卡——打卡动作从群聊/伙伴详情收敛进社群首页，
          // 数字直读 myGroups 真源（today_checkin_count），打卡走既有
          // checkin 接口（与群聊同一仓库方法），不造并行真源。
          const _TodayCheckinSection(),
          const SizedBox(height: DS.spacing20),
          // My groups first — the primary action
          _MyGroupsSection(state: groupsAsync),
          const SizedBox(height: DS.spacing20),
          // S-03 收敛②：成果反馈——伙伴共享 artifact 的质量分浏览 + 采纳
          // 反馈（既有 /community/resources 读接口与 adopt 接口，孤儿
          // SharedResourceCard 组件在此接回产品面）。
          const _ArtifactFeedbackSection(),
          const SizedBox(height: DS.spacing20),
          // Discovery & recommendations below
          _CommunityHero(directoryAsync: directoryAsync),
          const SizedBox(height: DS.spacing20),
          _RecommendationsSection(state: recommendationsAsync),
        ],
      ),
    );
  }
}

/// NAV-IA P-4：冲刺小队一行式入口（样式照 `_JoinedGroupTile` 既有家族：
/// GraphiteCardSurface + ListTile，sprint 语义 = timer 图标 + warning 底）。
class _SquadsEntryTile extends StatelessWidget {
  const _SquadsEntryTile();

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        key: const ValueKey('community-squads-entry'),
        surfaceRole: SparkleSurfaceRole.card,
        padding: EdgeInsets.zero,
        onTap: () => context.push(CommunityRoutes.squads),
        child: ListTile(
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          leading: Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              color: DS.warning.withValues(alpha: 0.16),
            ),
            child: Icon(
              Icons.timer_outlined,
              color: DS.textPrimary,
            ),
          ),
          title: Text(context.l10n.squadEntryLabel),
          subtitle: Text(context.l10n.communitySquadsEntryHint),
          trailing: const Icon(Icons.chevron_right),
        ),
      );
}

/// S-03 收敛①：今日打卡段——小队/群组的每日打卡入口收敛到社群首页。
/// 展示我的群组今日打卡计数（真源数字直显，不自算），并提供打卡动作；
/// 打卡复用群聊同一 `CommunityRepository.checkin`，成功后失效相关
/// provider 让计数与群详情回到真源。冲刺群排前。
class _TodayCheckinSection extends ConsumerWidget {
  const _TodayCheckinSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupsAsync = ref.watch(myGroupsProvider);
    final l10n = context.l10n;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _HubSectionHeader(
          icon: Icons.local_fire_department_outlined,
          title: l10n.communityHubCheckinTitle,
          hint: l10n.communityHubCheckinHint,
        ),
        const SizedBox(height: DS.spacing12),
        groupsAsync.when(
          data: (groups) {
            if (groups.isEmpty) {
              return CompactEmptyState(
                message: l10n.communityHubCheckinEmpty,
                icon: Icons.local_fire_department_outlined,
                actionText: l10n.communityDiscoverGroups,
                onAction: () => context.push('/community/groups/discover'),
              );
            }
            // 冲刺群排前（V3 主线），同类内按今日打卡数降序，取前 3。
            final sorted = [...groups]..sort((a, b) {
                final sprintDelta =
                    (b.isSprint ? 1 : 0) - (a.isSprint ? 1 : 0);
                if (sprintDelta != 0) return sprintDelta;
                return b.todayCheckinCount.compareTo(a.todayCheckinCount);
              });
            final visible = sorted.take(3);
            return Column(
              children: [
                for (final group in visible)
                  Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing8),
                    child: _CheckinTile(group: group),
                  ),
              ],
            );
          },
          loading: () => const SparkleListSkeleton(count: 2),
          error: (error, _) => CompactErrorCard(
            onRetry: () => ref.invalidate(myGroupsProvider),
          ),
        ),
      ],
    );
  }
}

class _CheckinTile extends ConsumerWidget {
  const _CheckinTile({required this.group});

  final GroupListItem group;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final isSprint = group.isSprint;

    return GraphiteCardSurface(
      key: ValueKey('community-checkin-tile-${group.id}'),
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      onTap: () => context.push('/chat/group/${group.id}'),
      child: ListTile(
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            color: isSprint
                ? DS.warning.withValues(alpha: 0.16)
                : DS.brandPrimary.withValues(alpha: 0.12),
          ),
          child: Icon(
            isSprint ? Icons.timer_outlined : Icons.groups_2_outlined,
            color: DS.textPrimary,
          ),
        ),
        title: Text(
          group.name,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontWeight: DS.fontWeightSemiBold,
            color: DS.textPrimary,
          ),
        ),
        subtitle: Text(
          l10n.communityHubCheckinGroupCount(group.todayCheckinCount),
          style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textSecondary),
        ),
        trailing: SparkleButton(
          key: const ValueKey('community-checkin-open-button'),
          label: l10n.communityCheckInAction,
          variant: ButtonVariant.secondary,
          size: ButtonSize.small,
          onPressed: () => unawaited(
            _showHubCheckinDialog(context, ref, group),
          ),
        ),
      ),
    );
  }
}

/// 打卡对话框：字段与群聊打卡一致（时长 + 内容），成功后以
/// 「+{flame} 火苗喂进群火堆」回执把 Flame 锚定在群活跃语义上
/// （火苗只代表群活跃度，与付费无关）。
Future<void> _showHubCheckinDialog(
  BuildContext context,
  WidgetRef ref,
  GroupListItem group,
) async {
  unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
  // 打卡对话框内选中的目标 id（下拉 onChanged 写入；null=不关联）。
  // 闭包捕获局部变量，无需提升为状态。
  String? goalPickerValue;
  // S-04：回执动作要做路由跳转——在 context 仍活跃的同步期先抓 GoRouter
  // 引用，避免打卡成功后 invalidate 触发重建使旧 element 失效。
  final hubRouter = GoRouter.of(context);
  final durationController = TextEditingController(text: '60');
  final messageController = TextEditingController();

  await showSensoryDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(dialogContext.l10n.communityCheckInTitle),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: durationController,
            decoration: InputDecoration(
              labelText: dialogContext.l10n.communityCheckInDurationLabel,
              suffixText: dialogContext.l10n.commonMinutesShort,
            ),
            keyboardType: TextInputType.number,
            inputFormatters: SparkleInputFormatters.digitsOnly,
          ),
          const SizedBox(height: DS.lg),
          TextField(
            controller: messageController,
            decoration: InputDecoration(
              labelText: dialogContext.l10n.communityCheckInMessageLabel,
              hintText: dialogContext.l10n.communityCheckInMessageHint,
            ),
          ),
          // S-04：可选目标关联——打卡后可一键回到 Goal trajectory（GJ16）。
          // 数据源是既有 /goals 列表（activeGoalsProvider），不建新真源；
          // 加载失败时下拉不可用但打卡仍可完成（回链是可选增强）。
          Consumer(builder: (context, ref, _) {
            final goalsAsync = ref.watch(activeGoalsProvider);
            return goalsAsync.maybeWhen(
              data: (goals) => goals.isEmpty
                  ? const SizedBox.shrink()
                  : DropdownButtonFormField<String>(
                      key: const ValueKey('community-checkin-goal-picker'),
                      decoration: InputDecoration(
                        labelText:
                            dialogContext.l10n.communityCheckinGoalLabel,
                        // 语义提示走 label；组件内 hint 在窄容器会挤压溢出。
                      ),
                      items: [
                        DropdownMenuItem<String>(
                          child: Text(
                            dialogContext.l10n.communityCheckinGoalNone,
                            style: TextStyle(color: DS.textSecondary),
                          ),
                        ),
                        ...goals.map(
                          (g) => DropdownMenuItem<String>(
                            value: g.id,
                            child: Text(
                              g.title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ),
                      ],
                      onChanged: (value) => goalPickerValue = value,
                    ),
              orElse: () => const SizedBox.shrink(),
            );
          },),
        ],
      ),
      actions: [
        SparkleButton.ghost(
          label: dialogContext.l10n.cancel,
          onPressed: () => Navigator.pop(dialogContext),
        ),
        SparkleButton.primary(
          label: dialogContext.l10n.communityCheckInAction,
          onPressed: () async {
            final duration = int.tryParse(durationController.text) ?? 0;
            final message = messageController.text;
            final linkedGoalId = goalPickerValue;
            Navigator.pop(dialogContext);
            try {
              final link = await ref
                  .read(communityRepositoryProvider)
                  .checkinWithGoalLink(group.id,
                      todayDurationMinutes: duration,
                      message: message,
                      goalId: linkedGoalId,);
              // 回真源：今日打卡计数与群详情一并失效。
              ref
                ..invalidate(myGroupsProvider)
                ..invalidate(groupDetailProvider(group.id));
              if (!context.mounted) return;
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.checkin),
              );
              if (link.hasGoalLink) {
                // GJ16：从 check-in 回到 Goal trajectory 的一跳。
                final goalId = link.goalId!;
                AppFeedback.undoable(
                  context: context,
                  // 紧凑文案：动作按钮与消息同行，长文案会挤压溢出。
                  message: context.l10n.communityHubCheckinGoalSuccess(
                      link.response.flameEarned,),
                  actionLabel:
                      context.l10n.communityHubCheckinViewGoalTrajectory,
onAction: () => unawaited(
                      hubRouter.push('/goals/${Uri.encodeComponent(goalId)}'),
                    ),
                );
              } else {
                AppFeedback.success(
                  context,
                  context.l10n
                      .communityHubCheckinSuccess(link.response.flameEarned),
                );
              }
            } catch (e) {
              // N9：原始异常只进日志，用户面为固定人类话术。
              debugPrint('community hub checkin failed: $e');
              if (!context.mounted) return;
              AppFeedback.error(
                context,
                context.l10n.communityHubCheckinFailed,
              );
            }
          },
        ),
      ],
    ),
  );
  durationController.dispose();
  messageController.dispose();
}

/// S-03 收敛②：成果反馈段——伙伴共享 artifact（质量分排序）浏览 + 采纳。
/// 数据走既有 `CommunityShareRepository.fetchSharedResources`（真实
/// `/community/resources` 读接口），采纳走既有 `adoptResource` 写接口；
/// 加载/错误/空态诚实分面，单段失败不拖垮整页。
class _ArtifactFeedbackSection extends ConsumerWidget {
  const _ArtifactFeedbackSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final resourcesAsync = ref.watch(sharedResourcesProvider);
    final l10n = context.l10n;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _HubSectionHeader(
          icon: Icons.emoji_events_outlined,
          title: l10n.communityHubArtifactTitle,
          hint: l10n.communityHubArtifactHint,
        ),
        const SizedBox(height: DS.spacing12),
        resourcesAsync.when(
          data: (resources) {
            if (resources.isEmpty) {
              return CompactEmptyState(
                message: l10n.communityHubArtifactEmpty,
                icon: Icons.emoji_events_outlined,
              );
            }
            return SizedBox(
              height: 220,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: resources.length,
                separatorBuilder: (_, __) => const SizedBox(width: DS.md),
                itemBuilder: (context, index) => SizedBox(
                  width: 260,
                  child: SharedResourceCard(
                    key: ValueKey(
                      'community-artifact-card-${resources[index].id}',
                    ),
                    resource: resources[index],
                    onAdopt: resources[index].isOwn
                        ? null // 自己的共享无「采纳到我的空间」语义
                        : () => unawaited(
                            _adoptResource(context, ref, resources[index].id),
                          ),
                    // S-04：给同伴成果一条反馈（不自动成为 mastery）。
                    onFeedback: () => unawaited(
                      _showFeedbackDialog(context, ref, resources[index]),
                    ),
                    // S-04：主人查看收到的反馈并显式采纳为 Goal outcome evidence。
                    onAdoptFeedback: resources[index].isOwn &&
                            resources[index].feedbackCount > 0
                        ? () => unawaited(
                            _showAdoptEvidenceSheet(context, ref, resources[index]),
                          )
                        : null,
                  ),
                ),
              ),
            );
          },
          loading: () => const SparkleListSkeleton(count: 2),
          error: (error, _) => CompactErrorCard(
            onRetry: () => ref.invalidate(sharedResourcesProvider),
          ),
        ),
      ],
    );
  }

  Future<void> _adoptResource(
    BuildContext context,
    WidgetRef ref,
    String sharedResourceId,
  ) async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
    try {
      await ref
          .read(communityShareRepositoryProvider)
          .adoptResource(sharedResourceId: sharedResourceId);
      if (!context.mounted) return;
      AppFeedback.success(context, context.l10n.communityHubArtifactAdopted);
    } catch (e) {
      // N9：原始异常只进日志，用户面为固定人类话术。
      debugPrint('community hub artifact adopt failed: $e');
      if (!context.mounted) return;
      AppFeedback.error(
        context,
        context.l10n.communityHubArtifactAdoptFailed,
      );
    }
  }
}

/// S-04：给同伴共享成果一条反馈/ack。仅写社群表面记录 + 事件，
/// 后端不因此改任何 mastery——这是「反馈 ≠ 掌握度」的产品面锚点。
Future<void> _showFeedbackDialog(
  BuildContext context,
  WidgetRef ref,
  SharedResourceInfo resource,
) async {
  unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
  var verdict = ResourceFeedbackVerdict.helpful;
  final commentController = TextEditingController();

  final ok = await showSensoryDialog<bool>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (dialogContext, setState) => AlertDialog(
        title: Text(dialogContext.l10n.sharedResourceFeedbackTitle),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              dialogContext.l10n.sharedResourceFeedbackNoMasteryHint,
              style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textSecondary),
            ),
            const SizedBox(height: DS.sm),
            Wrap(
              spacing: DS.sm,
              children: ResourceFeedbackVerdict.values
                  .map(
                    (v) => SparkleButton(
                      key: ValueKey('feedback-verdict-$v'),
                      label: _verdictLabel(dialogContext, v),
                      size: ButtonSize.small,
                      onPressed:
                          verdict == v ? null : () => setState(() => verdict = v),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: DS.sm),
            TextField(
              controller: commentController,
              decoration: InputDecoration(
                labelText: dialogContext.l10n.sharedResourceFeedbackComment,
              ),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            label: dialogContext.l10n.cancel,
            onPressed: () => Navigator.pop(dialogContext, false),
          ),
          SparkleButton.primary(
            key: const ValueKey('shared-resource-feedback-submit'),
            label: dialogContext.l10n.sharedResourceFeedbackSubmit,
            onPressed: () => Navigator.pop(dialogContext, true),
          ),
        ],
      ),
    ),
  );
  final comment = commentController.text;
  commentController.dispose();
  if (ok != true) return;
  try {
    await ref
        .read(communityShareRepositoryProvider)
        .giveFeedback(
          sharedResourceId: resource.id,
          verdict: verdict,
          comment: comment,
        );
    if (!context.mounted) return;
    AppFeedback.success(
        context, context.l10n.sharedResourceFeedbackThanks,);
  } catch (e) {
    // N9：原始异常只进日志，用户面为固定人类话术。
    debugPrint('community resource feedback failed: $e');
    if (!context.mounted) return;
    AppFeedback.error(context, context.l10n.sharedResourceFeedbackFailed);
  }
}

/// S-04：主人的反馈面板——查看收到的反馈，把其中未采纳的**显式采纳**
/// 为 Goal 的 outcome evidence（后端走 services/evidence 既有链 + Goal
/// 轨迹回执，且永不 bump mastery）。
Future<void> _showAdoptEvidenceSheet(
  BuildContext context,
  WidgetRef ref,
  SharedResourceInfo resource,
) async {
  unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
  final repository = ref.read(communityShareRepositoryProvider);
  await showModalBottomSheet<void>(
    context: context,
    builder: (sheetContext) => SafeArea(
      child: FutureBuilder<List<ResourceFeedbackItem>>(
        future: repository.fetchFeedback(sharedResourceId: resource.id),
        builder: (sheetContext, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Padding(
              padding: EdgeInsets.all(DS.xl),
              child: SparkleListSkeleton(count: 2),
            );
          }
          if (snapshot.hasError) {
            return Padding(
              padding: const EdgeInsets.all(DS.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(sheetContext.l10n.sharedResourceFeedbackLoadFailed),
                  const SizedBox(height: DS.sm),
                  SparkleButton.ghost(
                    label: sheetContext.l10n.commonClose,
                    onPressed: () => Navigator.pop(sheetContext),
                  ),
                ],
              ),
            );
          }
          final items = snapshot.data ?? const <ResourceFeedbackItem>[];
          return ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.all(DS.md),
            children: [
              Text(
                sheetContext.l10n.sharedResourceFeedbackSheetTitle(
                    resource.resourceTitle ??
                        sheetContext.l10n.sharedResourceTitle,),
                style: const TextStyle(
                    fontSize: DS.fontSizeMd, fontWeight: DS.fontWeightBold,),
              ),
              const SizedBox(height: DS.sm),
              if (items.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: DS.lg),
                  child: Text(
                      sheetContext.l10n.sharedResourceFeedbackEmpty,),
                )
              else
                ...items.map(
                  (item) => _FeedbackTile(
                    item: item,
                    onAdopt: item.isRetracted || item.isAdopted
                        ? null
                        : () => unawaited(_adoptFeedback(
                              context,
                              ref,
                              resource,
                              item,
                            ),),
                  ),
                ),
            ],
          );
        },
      ),
    ),
  );
}

Future<void> _adoptFeedback(
  BuildContext context,
  WidgetRef ref,
  SharedResourceInfo resource,
  ResourceFeedbackItem item,
) async {
  try {
    final result = await ref
        .read(communityShareRepositoryProvider)
        .adoptFeedbackAsEvidence(
          sharedResourceId: resource.id,
          feedbackId: item.id,
        );
    // 先关面板再失效真源，避免在活跃手势下重建面板子树。
    if (!context.mounted) return;
    if (context.canPop()) Navigator.pop(context);
    ref.invalidate(sharedResourcesProvider);
    AppFeedback.success(
      context,
      context.l10n.sharedResourceFeedbackAdoptedEvidence(
        (result['goal_title'] ?? '').toString(),
      ),
    );
  } catch (e) {
    // N9：原始异常只进日志，用户面为固定人类话术。
    debugPrint('community feedback adopt failed: $e');
    if (!context.mounted) return;
    AppFeedback.error(context, context.l10n.sharedResourceFeedbackFailed);
  }
}

String _verdictLabel(BuildContext context, ResourceFeedbackVerdict verdict) {
  final l10n = context.l10n;
  switch (verdict) {
    case ResourceFeedbackVerdict.helpful:
      return l10n.sharedResourceVerdictHelpful;
    case ResourceFeedbackVerdict.insightful:
      return l10n.sharedResourceVerdictInsightful;
    case ResourceFeedbackVerdict.applied:
      return l10n.sharedResourceVerdictApplied;
  }
}

/// 反馈面板里的一条反馈（同伴名 + 词表 + 采纳动作；撤回态诚实标注）。
class _FeedbackTile extends StatelessWidget {
  const _FeedbackTile({required this.item, this.onAdopt});

  final ResourceFeedbackItem item;
  final VoidCallback? onAdopt;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final verdictLabel = switch (item.verdict) {
      'insightful' => l10n.sharedResourceVerdictInsightful,
      'applied' => l10n.sharedResourceVerdictApplied,
      _ => l10n.sharedResourceVerdictHelpful,
    };
    return ListTile(
      contentPadding: EdgeInsets.zero,
      dense: true,
      leading: Icon(
        item.isRetracted ? Icons.block_outlined : Icons.forum_outlined,
        size: 18,
        color: item.isRetracted ? DS.textTertiary : DS.brandPrimary,
      ),
      title: Text(
        item.giverName ?? l10n.sharedResourceAnonymous,
        style: TextStyle(fontSize: DS.fontSizeSm, color: DS.textPrimary),
      ),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item.isRetracted
                ? l10n.sharedResourceVerdictRetracted
                : verdictLabel,
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: item.isRetracted ? DS.textTertiary : DS.textSecondary,
            ),
          ),
          if (item.comment != null && item.comment!.isNotEmpty)
            Text(
              item.comment!,
              style: TextStyle(
                  fontSize: DS.fontSizeXs, color: DS.textSecondary,),
            ),
        ],
      ),
      trailing: item.isAdopted && !item.isRetracted
          ? Text(
              l10n.sharedResourceFeedbackAdopted,
              style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textTertiary),
            )
          : (onAdopt != null
              ? SparkleButton(
                  key: ValueKey('adopt-evidence-${item.id}'),
                  label: l10n.sharedResourceAdoptEvidence,
                  variant: ButtonVariant.ghost,
                  size: ButtonSize.small,
                  onPressed: onAdopt,
                )
              : null),
    );
  }
}

/// 收敛段共用节标题：图标 + 标题 + 一句语义提示（提示承担 Flame 语义、
/// 采纳去向等自解释文案——「小组 journey 自解释」验收的落点之一）。
class _HubSectionHeader extends StatelessWidget {
  const _HubSectionHeader({
    required this.icon,
    required this.title,
    required this.hint,
  });

  final IconData icon;
  final String title;
  final String hint;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: DS.brandPrimary),
              const SizedBox(width: DS.sm),
              Text(
                title,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            hint,
            style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textSecondary),
          ),
        ],
      );
}

class _CommunityHero extends StatefulWidget {
  const _CommunityHero({required this.directoryAsync});

  final AsyncValue<GroupDirectoryInfo> directoryAsync;

  @override
  State<_CommunityHero> createState() => _CommunityHeroState();
}

class _CommunityHeroState extends State<_CommunityHero> {
  static const _collapsedPrefsKey = 'community_group_entry_collapsed_v1';
  bool _collapsed = false;

  @override
  void initState() {
    super.initState();
    unawaited(_loadCollapsed());
  }

  Future<void> _loadCollapsed() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _collapsed = prefs.getBool(_collapsedPrefsKey) ?? false;
    });
  }

  Future<void> _toggleCollapsed() async {
    final prefs = await SharedPreferences.getInstance();
    final next = !_collapsed;
    await prefs.setBool(_collapsedPrefsKey, next);
    if (!mounted) return;
    setState(() {
      _collapsed = next;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    final directory = widget.directoryAsync.valueOrNull;
    final tags = directory?.availableTags.take(6).toList() ?? const <String>[];

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.accent,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  gradient: LinearGradient(
                    colors: [
                      DS.brandPrimary,
                      DS.warning.withValues(alpha: 0.88),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Icon(Icons.hub_outlined, color: DS.neutral0),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.communityGroupEntry,
                      style: theme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Text(
                      directory == null
                          ? context.l10n.communityBrowseOrCreate
                          : context.l10n
                              .communityPublicGroupsCount(directory.totalCount),
                      style: theme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              SparkleButton(
                label: _collapsed
                    ? context.l10n.communityExpand
                    : context.l10n.communityCollapse,
                variant: ButtonVariant.ghost,
                size: ButtonSize.small,
                onPressed: _toggleCollapsed,
              ),
            ],
          ),
          if (!_collapsed) ...[
            const SizedBox(height: 12),
            Text(
              context.l10n.communityDiscoverCampusGroups,
              style: theme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Text(
              directory == null
                  ? context.l10n.communityDiscoverBrowseHint
                  : context.l10n.communityDiscoverFilterHint,
              style: theme.bodyMedium?.copyWith(color: DS.textSecondary),
            ),
            if (tags.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: tags
                    .map(
                      (tag) => SemanticPill(
                        label: tag,
                        tone: PillTone.brand,
                        dense: true,
                      ),
                    )
                    .toList(),
              ),
            ],
            const SizedBox(height: 12),
          ] else
            const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: SparkleButton.primary(
                  label: context.l10n.communityBrowseGroups,
                  icon: const Icon(Icons.travel_explore_outlined),
                  onPressed: () => context.push('/community/groups/discover'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: SparkleButton(
                  label: context.l10n.communityCreateGroup,
                  variant: ButtonVariant.secondary,
                  icon: const Icon(Icons.add_circle_outline),
                  onPressed: () => context.push('/community/groups/create'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RecommendationsSection extends ConsumerWidget {
  const _RecommendationsSection({required this.state});

  final AsyncValue<List<GroupRecommendationItem>> state;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(context.l10n.communityRecommendedForYou,
                  style: Theme.of(context).textTheme.titleMedium,),
              const Spacer(),
              SparkleButton(
                label: context.l10n.communityViewAll,
                variant: ButtonVariant.ghost,
                size: ButtonSize.small,
                onPressed: () => context.push('/community/groups/discover'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          state.when(
            data: (items) {
              if (items.isEmpty) {
                return const SizedBox.shrink();
              }
              return SizedBox(
                height: 200,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 12),
                  itemBuilder: (context, index) {
                    final item = items[index];
                    return SizedBox(
                      width: 292,
                      child: GroupRecommendationCard(
                        recommendation: item,
                        onTap: () =>
                            context.push('/community/groups/${item.group.id}'),
                        onJoin: () {
                          unawaited(
  ref
                                .read(groupRecommendationsProvider.notifier)
                                .join(item.group.id),
                          );
                          ref.invalidate(myGroupsProvider);
                        },
                        onDismiss: () {
                          unawaited(
  ref
                                .read(groupRecommendationsProvider.notifier)
                                .dismiss(item.group.id),
                          );
                        },
                      ),
                    );
                  },
                ),
              );
            },
            loading: () => SizedBox(
              height: 200,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: 2,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (_, __) => Shimmer.fromColors(
                  baseColor: DS.surfaceOverlay,
                  highlightColor: DS.surfacePrimary,
                  child: Container(
                    width: 292,
                    decoration: BoxDecoration(
                      color: DS.surfaceOverlay,
                      borderRadius: BorderRadius.circular(24),
                    ),
                  ),
                ),
              ),
            ),
            error: (_, __) => Text(
              context.l10n.communityRecommendLoadError,
              style: TextStyle(color: DS.textSecondary),
            ),
          ),
        ],
      );
}

class _MyGroupsSection extends ConsumerWidget {
  const _MyGroupsSection({required this.state});

  final AsyncValue<List<GroupListItem>> state;

  @override
  Widget build(BuildContext context, WidgetRef ref) => state.when(
        data: (groups) {
          if (groups.isEmpty) {
            return CompactEmptyState(
              message: context.l10n.communityNoGroupsYet,
              icon: Icons.groups_outlined,
              actionText: context.l10n.communityDiscoverGroups,
              onAction: () => context.push('/community/groups/discover'),
            );
          }
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(context.l10n.communityMyGroups,
                      style: Theme.of(context).textTheme.titleMedium,),
                  const Spacer(),
                  SparkleButton(
                    label: context.l10n.communityViewAllGroups,
                    variant: ButtonVariant.ghost,
                    size: ButtonSize.small,
                    onPressed: () => context.push('/community/groups'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              ...List.generate(groups.length > 4 ? 4 : groups.length, (index) {
                final group = groups[index];
                return Padding(
                  padding: EdgeInsets.only(
                    bottom: index == (groups.length > 4 ? 3 : groups.length - 1)
                        ? 0
                        : 12,
                  ),
                  child: _JoinedGroupTile(group: group),
                );
              }),
              if (groups.length > 4) ...[
                const SizedBox(height: 12),
                Text(
                  context.l10n.communityMoreGroupsFolded(groups.length - 4),
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: DS.fontSizeSm,
                  ),
                ),
              ],
            ],
          );
        },
        loading: () => const SparkleListSkeleton(),
        // COMMUNITY-401: the raw DioException text (401 textbook dump with a
        // mozilla link) used to be interpolated verbatim here. Humanize via
        // UserFacingError (SPEC-C precedent) and give the section a visible
        // tap-to-retry so a transient auth/network failure can recover.
        error: (error, _) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.communityMyGroupsLoadError(
                UserFacingError.from(error),
              ),
              style: TextStyle(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing8),
            CompactErrorCard(
              onRetry: () => ref.invalidate(myGroupsProvider),
            ),
          ],
        ),
      );
}

class _JoinedGroupTile extends StatelessWidget {
  const _JoinedGroupTile({required this.group});

  final GroupListItem group;

  @override
  Widget build(BuildContext context) {
    final roleLabel = switch (group.myRole) {
      GroupRole.owner => context.l10n.communityRoleOwner,
      GroupRole.admin => context.l10n.communityRoleAdmin,
      GroupRole.member => context.l10n.communityRoleMember,
      null => context.l10n.communityRolePublic,
    };

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      // Tap goes directly to chat — the primary action for joined groups
      onTap: () => context.push('/chat/group/${group.id}'),
      child: ListTile(
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        leading: Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            color: group.isSprint
                ? DS.warning.withValues(alpha: 0.16)
                : DS.brandPrimary.withValues(alpha: 0.12),
          ),
          child: Icon(
            group.isSprint ? Icons.timer_outlined : Icons.groups_2_outlined,
            color: DS.textPrimary,
          ),
        ),
        title: Text(group.name),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (group.description != null && group.description!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  group.description!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            const SizedBox(height: 6),
            Text(
              context.l10n.communityGroupSubtitle(
                  roleLabel, group.memberCount, group.todayCheckinCount,),
              style: TextStyle(color: DS.textSecondary, fontSize: 12),
            ),
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}
