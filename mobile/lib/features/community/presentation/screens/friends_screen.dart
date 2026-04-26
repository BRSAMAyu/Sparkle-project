import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/utils/accountability_invite_flow.dart';
import 'package:sparkle/features/community/presentation/widgets/friends_hub_view.dart';
import 'package:sparkle/features/community/presentation/widgets/recommendation_feedback_widgets.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class FriendsScreen extends StatelessWidget {
  const FriendsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return DefaultTabController(
      length: 2,
      child: SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(l10n.community),
          bottom: TabBar(
            tabs: [
              Tab(text: l10n.languageChinese == '简体中文' ? '我的好友' : 'My Friends'),
              Tab(text: l10n.languageChinese == '简体中文' ? '好友请求' : 'Requests'),
            ],
          ),
        ),
        child: const ContentConstraint(
          child: TabBarView(
            children: [
              SparkleStaggerItem(index: 0, child: _MyFriendsTab()),
              SparkleStaggerItem(index: 1, child: _PendingRequestsTab()),
            ],
          ),
        ),
      ),
    );
  }
}

class FriendRequestsScreen extends StatelessWidget {
  const FriendRequestsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop()
              ? context.pop()
              : context.go(CommunityRoutes.home),
        ),
        title: Text(l10n.languageChinese == '简体中文' ? '好友请求' : 'Requests'),
      ),
      child: const ContentConstraint(
        child: SparkleStaggerItem(index: 0, child: _PendingRequestsTab()),
      ),
    );
  }
}

class FriendsDiscoverScreen extends StatelessWidget {
  const FriendsDiscoverScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop()
              ? context.pop()
              : context.go(CommunityRoutes.home),
        ),
        title: Text(
          l10n.languageChinese == '简体中文' ? '发现好友' : 'Discover Friends',
        ),
      ),
      child: const ContentConstraint(
        child: SparkleStaggerItem(index: 0, child: _RecommendationsTab()),
      ),
    );
  }
}

class _MyFriendsTab extends ConsumerWidget {
  const _MyFriendsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) => const FriendsHubView(
        padding: EdgeInsets.fromLTRB(16, 16, 16, 24),
      );

  // ignore: unused_element
  void _showFriendContextMenu(
    BuildContext context,
    WidgetRef ref,
    FriendshipInfo friendInfo,
  ) {
    final friend = friendInfo.friend;
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: Colors.transparent,
        builder: (ctx) => Container(
          decoration: BoxDecoration(
            color: Theme.of(ctx).scaffoldBackgroundColor,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Header with user info
                Padding(
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: Row(
                    children: [
                      CircleAvatar(
                        backgroundImage: friend.avatarUrl != null
                            ? NetworkImage(friend.avatarUrl!)
                            : null,
                        child: friend.avatarUrl == null
                            ? Text(friend.displayName[0])
                            : null,
                      ),
                      const SizedBox(width: DS.spacing12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              friend.displayName,
                              style: DS.titleLarge
                                  .copyWith(fontWeight: FontWeight.bold),
                            ),
                            Text(
                              'Lv.${friend.flameLevel}',
                              style: DS.bodySmall
                                  .copyWith(color: DS.brandPrimaryConst),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1),
                // Delete friend option
                ListTile(
                  leading: Icon(Icons.person_remove, color: DS.neutral600),
                  title: const Text('删除好友'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _handleDeleteFriend(context, ref, friendInfo);
                  },
                ),
                // Block user option
                ListTile(
                  leading: Icon(Icons.block, color: DS.error),
                  title: Text('拉黑用户', style: TextStyle(color: DS.error)),
                  onTap: () {
                    Navigator.pop(ctx);
                    _handleBlockUser(context, ref, friendInfo);
                  },
                ),
                // Blocked users management
                ListTile(
                  leading: Icon(Icons.block_outlined, color: DS.neutral600),
                  title: const Text('黑名单管理'),
                  onTap: () {
                    Navigator.pop(ctx);
                    context.push(CommunityRoutes.blockedUsers);
                  },
                ),
                const SizedBox(height: DS.spacing8),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _handleDeleteFriend(
    BuildContext context,
    WidgetRef ref,
    FriendshipInfo friendInfo,
  ) async {
    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('删除好友'),
        content: Text('确定要删除好友 ${friendInfo.friend.displayName} 吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: DS.error),
            child: const Text('删除'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        await ref.read(friendsProvider.notifier).deleteFriend(friendInfo.id);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.success('已删除 ${friendInfo.friend.displayName}'),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.error('删除失败: $e'),
          );
        }
      }
    }
  }

  Future<void> _handleBlockUser(
    BuildContext context,
    WidgetRef ref,
    FriendshipInfo friendInfo,
  ) async {
    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('拉黑用户'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('拉黑 ${friendInfo.friend.displayName} 后:'),
            const SizedBox(height: 8),
            Row(
              children: [
                Container(
                  width: 5,
                  height: 5,
                  margin: const EdgeInsets.only(right: 8),
                  decoration: BoxDecoration(
                    color: DS.textPrimary,
                    shape: BoxShape.circle,
                  ),
                ),
                const Expanded(child: Text('从好友列表移除')),
              ],
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Container(
                  width: 5,
                  height: 5,
                  margin: const EdgeInsets.only(right: 8),
                  decoration: BoxDecoration(
                    color: DS.textPrimary,
                    shape: BoxShape.circle,
                  ),
                ),
                const Expanded(child: Text('无法发送消息给你')),
              ],
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Container(
                  width: 5,
                  height: 5,
                  margin: const EdgeInsets.only(right: 8),
                  decoration: BoxDecoration(
                    color: DS.textPrimary,
                    shape: BoxShape.circle,
                  ),
                ),
                const Expanded(child: Text('无法发送好友请求')),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: DS.error),
            child: const Text('拉黑'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        await ref
            .read(friendsProvider.notifier)
            .blockUser(friendInfo.friend.id);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.success('已拉黑 ${friendInfo.friend.displayName}'),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.error('拉黑失败: $e'),
          );
        }
      }
    }
  }
}

class _PendingRequestsTab extends ConsumerWidget {
  const _PendingRequestsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requestsState = ref.watch(pendingRequestsProvider);
    final overviewAsync = ref.watch(accountabilityOverviewProvider);

    return requestsState.when(
      data: (requests) {
        final pendingPartnerships =
            overviewAsync.valueOrNull?.pendingPartnerships ??
                const <AccountabilityPartnershipInfo>[];
        if (requests.isEmpty && pendingPartnerships.isEmpty) {
          return const Center(child: Text('当前没有待处理的好友请求或伙伴邀请'));
        }
        return RefreshIndicator(
          onRefresh: () async {
            await ref.read(pendingRequestsProvider.notifier).refresh();
            await ref.read(myPartnershipsProvider.notifier).load();
            ref.invalidate(accountabilityOverviewProvider);
          },
          child: ListView.builder(
            itemCount: requests.length + pendingPartnerships.length + 2,
            padding: const EdgeInsets.all(DS.lg),
            itemBuilder: (context, index) {
              if (index == 0) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: DS.md),
                  child: Text(
                    '好友请求',
                    style: DS.titleLarge.copyWith(fontWeight: FontWeight.bold),
                  ),
                );
              }
              if (index <= requests.length) {
                final request = requests[index - 1];
                final user = request.friend;
                return Card(
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundImage: user.avatarUrl != null
                          ? NetworkImage(user.avatarUrl!)
                          : null,
                      child: user.avatarUrl == null
                          ? Text(user.displayName[0])
                          : null,
                    ),
                    title: Text(user.displayName),
                    subtitle: const Text('希望先和你建立好友关系'),
                    onTap: () => context.push(
                      '/community/users/${user.id}?name=${Uri.encodeComponent(user.displayName)}',
                    ),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SparkleIconButton(
                          variant: ButtonVariant.ghost,
                          size: 36,
                          icon: Icon(Icons.check, color: DS.success),
                          onPressed: () {
                            ref
                                .read(pendingRequestsProvider.notifier)
                                .respondToRequest(request.id, true);
                            ref.read(friendsProvider.notifier).refresh();
                          },
                        ),
                        SparkleIconButton(
                          variant: ButtonVariant.ghost,
                          size: 36,
                          icon: Icon(Icons.close, color: DS.error),
                          onPressed: () {
                            ref
                                .read(pendingRequestsProvider.notifier)
                                .respondToRequest(request.id, false);
                          },
                        ),
                      ],
                    ),
                  ),
                );
              }
              if (index == requests.length + 1) {
                return Padding(
                  padding: const EdgeInsets.only(top: DS.lg, bottom: DS.md),
                  child: Text(
                    '责任伙伴邀请',
                    style: DS.titleLarge.copyWith(fontWeight: FontWeight.bold),
                  ),
                );
              }
              final partnership =
                  pendingPartnerships[index - requests.length - 2];
              final partner = partnership.initiator ?? partnership.partner;
              return Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundImage: partner?.avatarUrl != null
                        ? NetworkImage(partner!.avatarUrl!)
                        : null,
                    child: partner?.avatarUrl == null
                        ? Text((partner?.displayName ?? '伙')[0])
                        : null,
                  ),
                  title: Text(partner?.displayName ?? '责任伙伴邀请'),
                  subtitle: Text(partnership.initiatorGoal),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        size: 36,
                        icon: Icon(Icons.check, color: DS.success),
                        onPressed: () async {
                          try {
                            final repo =
                                ref.read(accountabilityRepositoryProvider);
                            final resolution =
                                await acceptAccountabilityInviteWithRefresh(
                              repository: repo,
                              partnershipId: partnership.id,
                              reloadPartnerships: () => ref
                                  .read(myPartnershipsProvider.notifier)
                                  .load(),
                              refreshPendingRequests: () => ref
                                  .read(pendingRequestsProvider.notifier)
                                  .refresh(),
                              invalidateOverview: () => ref
                                  .invalidate(accountabilityOverviewProvider),
                            );
                            if (!context.mounted) return;
                            AppFeedback.success(context, '已接受责任伙伴邀请！');
                            context.go(resolution.route);
                          } catch (e) {
                            if (context.mounted) {
                              final message =
                                  normalizeAccountabilityInviteError(e);
                              final hasActiveCoreConflict = message.contains(
                                  'already has a core accountability partner');
                              if (hasActiveCoreConflict) {
                                final route =
                                    await resolveExistingAccountabilityRouteOnConflict(
                                  ref.read(accountabilityRepositoryProvider),
                                );
                                AppFeedback.info(
                                  context,
                                  '你当前已经有核心责任伙伴，先进入现有工作台继续协作。',
                                );
                                if (route != null) {
                                  context.go(route);
                                  return;
                                }
                              }
                              AppFeedback.error(context, message);
                            }
                          }
                        },
                      ),
                      SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        size: 36,
                        icon: Icon(Icons.close, color: DS.error),
                        onPressed: () async {
                          try {
                            await declineAccountabilityInviteWithRefresh(
                              repository:
                                  ref.read(accountabilityRepositoryProvider),
                              partnershipId: partnership.id,
                              reloadPartnerships: () => ref
                                  .read(myPartnershipsProvider.notifier)
                                  .load(),
                              refreshPendingRequests: () => ref
                                  .read(pendingRequestsProvider.notifier)
                                  .refresh(),
                              invalidateOverview: () => ref
                                  .invalidate(accountabilityOverviewProvider),
                            );
                            if (context.mounted) {
                              AppFeedback.info(context, '已拒绝邀请');
                            }
                          } catch (e) {
                            if (context.mounted) {
                              final message =
                                  normalizeAccountabilityInviteError(e);
                              AppFeedback.error(context, message);
                            }
                          }
                        },
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: LoadingIndicator()),
      error: (e, s) => Center(
        child: CustomErrorWidget.page(
          context: context,
          message: e.toString(),
          onRetry: () => ref.read(pendingRequestsProvider.notifier).refresh(),
        ),
      ),
    );
  }
}

class _RecommendationsTab extends ConsumerWidget {
  const _RecommendationsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recommendationsState = ref.watch(friendRecommendationsProvider);
    final strategy = ref.watch(friendRecommendationStrategyProvider);
    final promptsState = ref.watch(recommendationFeedbackPromptsProvider);
    final insightsState = ref.watch(recommendationFeedbackInsightsProvider);
    final friendPrompts = (promptsState.valueOrNull ?? const [])
        .where((prompt) => prompt.itemType == RecommendationItemType.friend)
        .toList();
    final friendInsight = (insightsState.valueOrNull ?? const [])
        .where((insight) => insight.itemType == RecommendationItemType.friend)
        .cast<RecommendationFeedbackInsight?>()
        .firstWhere((insight) => insight != null, orElse: () => null);

    return recommendationsState.when(
      data: (recommendations) => RefreshIndicator(
        onRefresh: () =>
            ref.read(friendRecommendationsProvider.notifier).refresh(),
        child: ListView(
          padding: const EdgeInsets.all(DS.lg),
          children: [
            Text(
              '责任伙伴匹配',
              style: DS.titleLarge.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: DS.xs),
            Text(
              '系统会结合公开画像、学习主题、社群重合度与责任伙伴状态，优先推荐适合作为核心责任伙伴的人。',
              style: DS.bodyMedium.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.md),
            Wrap(
              spacing: DS.sm,
              runSpacing: DS.sm,
              children: FriendMatchStrategy.values.map((item) {
                final selected = strategy == item;
                return FilterChip(
                  label: Text(_strategyLabel(item)),
                  selected: selected,
                  onSelected: (_) {
                    ref
                        .read(friendRecommendationStrategyProvider.notifier)
                        .state = item;
                    ref
                        .read(friendRecommendationsProvider.notifier)
                        .setStrategy(item);
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: DS.md),
            Container(
              padding: const EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: BorderRadius.circular(DS.borderRadiusLG),
                border: Border.all(color: DS.neutral200),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.privacy_tip_outlined,
                    size: 18,
                    color: DS.brandPrimaryConst,
                  ),
                  const SizedBox(width: DS.sm),
                  Expanded(
                    child: Text(
                      '仅展示允许公开发现的用户，推荐理由来自可解释的画像摘要，不会暴露私密原始数据。',
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ),
                ],
              ),
            ),
            if (friendPrompts.isNotEmpty) ...[
              const SizedBox(height: DS.md),
              Text(
                '待你校准',
                style: DS.titleLarge.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: DS.xs),
              Text(
                '分阶段反馈会直接调整你后续的好友与责任伙伴匹配。',
                style: DS.bodySmall.copyWith(color: DS.textSecondary),
              ),
              const SizedBox(height: DS.sm),
              ...friendPrompts.take(2).map(
                    (prompt) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.sm),
                      child: RecommendationFeedbackPromptCard(
                        prompt: prompt,
                        onRespond: () => _handlePromptFeedback(
                          context,
                          ref,
                          prompt,
                        ),
                      ),
                    ),
                  ),
            ],
            if (friendInsight != null && friendInsight.recentFeedbackCount > 0)
              Padding(
                padding: const EdgeInsets.only(top: DS.md),
                child: RecommendationFeedbackInsightCard(
                  insight: friendInsight,
                ),
              ),
            const SizedBox(height: DS.md),
            if (recommendations.isEmpty)
              const EmptyState(
                icon: Icons.people_outline,
                title: '暂时没有合适候选人',
                description: '换个匹配策略或稍后刷新，我们会持续根据最新画像和社群活跃度更新推荐。',
              )
            else
              ...recommendations.map(
                (rec) => Padding(
                  padding: const EdgeInsets.only(bottom: DS.md),
                  child: _RecommendationCard(
                    recommendation: rec,
                    onPrimaryAction: () =>
                        _handlePrimaryAction(context, ref, rec),
                    onDismiss: () => _dismissRecommendation(context, ref, rec),
                    onFeedback: () => _handleInlineFeedback(context, ref, rec),
                  ),
                ),
              ),
          ],
        ),
      ),
      loading: () => const Center(child: LoadingIndicator()),
      error: (e, s) => Center(
        child: CustomErrorWidget.page(
          context: context,
          message: e.toString(),
          onRetry: () =>
              ref.read(friendRecommendationsProvider.notifier).refresh(),
        ),
      ),
    );
  }

  Future<void> _handlePromptFeedback(
    BuildContext context,
    WidgetRef ref,
    RecommendationFeedbackPrompt prompt,
  ) async {
    final draft = await showRecommendationFeedbackSheet(
      context: context,
      itemType: RecommendationItemType.friend,
      prompt: prompt,
      user: prompt.user,
      strategy: prompt.strategy,
      target: prompt.target,
    );
    if (draft == null) return;

    await _submitFriendFeedback(
      context,
      ref,
      targetUserId: prompt.user?.id ?? prompt.itemId,
      strategy: _parseStrategy(prompt.strategy),
      target: _parseTarget(prompt.target),
      action: _friendActionFromTrigger(prompt.triggerAction),
      source: 'friends_prompt',
      draft: draft,
    );
  }

  Future<void> _handleInlineFeedback(
    BuildContext context,
    WidgetRef ref,
    FriendRecommendation recommendation,
  ) async {
    final draft = await showRecommendationFeedbackSheet(
      context: context,
      itemType: RecommendationItemType.friend,
      user: recommendation.user,
      strategy: recommendation.strategy,
      target: recommendation.target,
    );
    if (draft == null) return;

    await _submitFriendFeedback(
      context,
      ref,
      targetUserId: recommendation.user.id,
      strategy: _parseStrategy(recommendation.strategy),
      target: _parseTarget(recommendation.target),
      action: 'view',
      source: 'friends_card_feedback',
      draft: draft,
      score: recommendation.matchScore,
    );
  }

  Future<void> _submitFriendFeedback(
    BuildContext context,
    WidgetRef ref, {
    required String targetUserId,
    required FriendMatchStrategy strategy,
    required FriendRecommendationTarget target,
    required String action,
    required String source,
    required RecommendationFeedbackDraft draft,
    double? score,
  }) async {
    try {
      await ref
          .read(communityRepositoryProvider)
          .sendFriendRecommendationFeedback(
            targetUserId: targetUserId,
            strategy: strategy,
            target: target,
            action: action,
            source: source,
            score: score,
            promptId: draft.promptId,
            stage: draft.stage,
            questionnaireVersion: 1,
            overallScore: draft.overallScore,
            relevanceScore: draft.relevanceScore,
            explanationScore: draft.explanationScore,
            actionabilityScore: draft.actionabilityScore,
            similarityScore: draft.similarityScore,
            complementaryScore: draft.complementaryScore,
            comfortScore: draft.comfortScore,
            selectedIssues: draft.selectedIssues,
            selectedStrengths: draft.selectedStrengths,
            freeText: draft.freeText,
          );
      ref.invalidate(recommendationFeedbackPromptsProvider);
      ref.invalidate(recommendationFeedbackInsightsProvider);
      ref.invalidate(friendRecommendationsProvider);
      if (context.mounted) {
        AppFeedback.success(context, '反馈已提交，后续推荐会更贴近你的偏好');
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, '提交失败: $e');
      }
    }
  }

  Future<void> _dismissRecommendation(
    BuildContext context,
    WidgetRef ref,
    FriendRecommendation recommendation,
  ) async {
    try {
      await ref
          .read(friendRecommendationsProvider.notifier)
          .dismiss(recommendation);
      if (context.mounted) {
        AppFeedback.info(context, '已隐藏这条推荐');
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, '操作失败: $e');
      }
    }
  }

  Future<void> _handlePrimaryAction(
    BuildContext context,
    WidgetRef ref,
    FriendRecommendation recommendation,
  ) async {
    try {
      if (recommendation.canInviteAccountability) {
        final invited = await _showAccountabilityInvite(
          context,
          ref,
          recommendation.user,
        );
        if (invited) {
          await ref
              .read(friendRecommendationsProvider.notifier)
              .recordAccountabilityInvite(recommendation);
        }
        return;
      }
      if (!recommendation.isExistingFriend) {
        await ref
            .read(friendRecommendationsProvider.notifier)
            .sendRequest(recommendation);
        if (context.mounted) {
          AppFeedback.success(context, '好友请求已发送');
        }
        return;
      }
      if (context.mounted) {
        unawaited(
          context.pushNamed(
            'userProfile',
            pathParameters: {'id': recommendation.user.id},
            queryParameters: {'name': recommendation.user.displayName},
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, '操作失败: $e');
      }
    }
  }

  Future<bool> _showAccountabilityInvite(
    BuildContext context,
    WidgetRef ref,
    UserBrief user,
  ) async {
    final goalController = TextEditingController();
    var checkInDays = 1;

    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          title: const Text('发起责任伙伴邀请'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '邀请 ${user.displayName} 成为你的责任伙伴',
                style: TextStyle(color: DS.textSecondary, fontSize: 13),
              ),
              const SizedBox(height: DS.spacing16),
              TextField(
                controller: goalController,
                decoration: const InputDecoration(
                  labelText: '我的目标',
                  hintText: '例如：每天学习英语 30 分钟',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
              ),
              const SizedBox(height: DS.spacing16),
              const Text(
                '打卡频率:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: DS.xs),
              Wrap(
                spacing: DS.sm,
                children: [1, 2, 3, 7].map((d) {
                  final selected = checkInDays == d;
                  return FilterChip(
                    label: Text(d == 1 ? '每天' : '每 $d 天'),
                    selected: selected,
                    onSelected: (_) => setState(() => checkInDays = d),
                  );
                }).toList(),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('发送邀请'),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true) return false;
    final goal = goalController.text.trim();
    if (goal.isEmpty) {
      if (context.mounted) AppFeedback.info(context, '请填写目标');
      return false;
    }

    await ref.read(myPartnershipsProvider.notifier).requestPartnership(
          partnerId: user.id,
          initiatorGoal: goal,
          checkInDays: checkInDays,
        );
    ref.invalidate(accountabilityOverviewProvider);
    if (context.mounted) {
      AppFeedback.success(context, '责任伙伴邀请已发送！');
    }
    return true;
  }

  String _strategyLabel(FriendMatchStrategy strategy) {
    switch (strategy) {
      case FriendMatchStrategy.compatibility:
        return '契合度';
      case FriendMatchStrategy.complementary:
        return '互补型';
    }
  }

  FriendMatchStrategy _parseStrategy(String? raw) =>
      FriendMatchStrategy.values.firstWhere(
        (item) => item.name == raw,
        orElse: () => FriendMatchStrategy.compatibility,
      );

  FriendRecommendationTarget _parseTarget(String? raw) =>
      FriendRecommendationTarget.values.firstWhere(
        (item) => item.name == raw,
        orElse: () => FriendRecommendationTarget.accountability,
      );

  String _friendActionFromTrigger(String trigger) {
    if (trigger.contains('accountability_invite')) {
      return 'accountability_invite';
    }
    if (trigger.contains('friend_request')) {
      return 'friend_request';
    }
    if (trigger.contains('dismiss')) {
      return 'dismiss';
    }
    return 'view';
  }
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({
    required this.recommendation,
    required this.onPrimaryAction,
    required this.onDismiss,
    required this.onFeedback,
  });

  final FriendRecommendation recommendation;
  final VoidCallback onPrimaryAction;
  final VoidCallback onDismiss;
  final VoidCallback onFeedback;

  @override
  Widget build(BuildContext context) {
    final accentColor = recommendation.canInviteAccountability
        ? DS.brandPrimaryConst
        : DS.warning;
    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        gradient: LinearGradient(
          colors: recommendation.canInviteAccountability
              ? [
                  DS.brandPrimary.withValues(alpha: 0.12),
                  DS.brandPrimary.withValues(alpha: 0.04),
                ]
              : [
                  DS.warning.withValues(alpha: 0.12),
                  DS.surfaceSecondary,
                ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(
          color: recommendation.canInviteAccountability
              ? DS.brandPrimary.withValues(alpha: 0.25)
              : DS.warning.withValues(alpha: 0.25),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                radius: 24,
                backgroundImage: recommendation.user.avatarUrl != null
                    ? NetworkImage(recommendation.user.avatarUrl!)
                    : null,
                child: recommendation.user.avatarUrl == null
                    ? Text(recommendation.user.displayName[0])
                    : null,
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            recommendation.user.displayName,
                            style: DS.titleLarge
                                .copyWith(fontWeight: FontWeight.bold),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: DS.sm,
                            vertical: DS.xs,
                          ),
                          decoration: BoxDecoration(
                            color: accentColor.withValues(alpha: 0.12),
                            borderRadius: DS.borderRadiusFull,
                          ),
                          child: Text(
                            '${(recommendation.matchScore * 100).round()}%',
                            style: DS.labelSmall.copyWith(
                              color: accentColor,
                              fontWeight: DS.fontWeightBold,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.xs),
                    Text(
                      recommendation.summary ?? '适合作为下一位学习搭子',
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ],
                ),
              ),
              IconButton(
                onPressed: onDismiss,
                icon: const Icon(Icons.close),
                tooltip: '隐藏',
              ),
            ],
          ),
          const SizedBox(height: DS.sm),
          Wrap(
            spacing: DS.sm,
            runSpacing: DS.sm,
            children: [
              _RecommendationBadge(
                label: recommendation.canInviteAccountability
                    ? '可直接邀请伙伴'
                    : recommendation.isExistingFriend
                        ? '已是好友'
                        : '先加好友',
                color: accentColor,
              ),
              _RecommendationBadge(
                label: recommendation.strategy == 'complementary'
                    ? '互补推荐'
                    : '契合推荐',
                color: DS.info,
              ),
            ],
          ),
          const SizedBox(height: DS.sm),
          ...recommendation.matchReasons.map(
            (reason) => Padding(
              padding: const EdgeInsets.only(bottom: DS.xs),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.auto_awesome,
                    size: 16,
                    color: accentColor,
                  ),
                  const SizedBox(width: DS.xs),
                  Expanded(
                    child: Text(
                      reason,
                      style: DS.bodySmall,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: DS.sm),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: onPrimaryAction,
                  child: Text(_primaryActionLabel(recommendation)),
                ),
              ),
              const SizedBox(width: DS.sm),
              OutlinedButton(
                onPressed: onFeedback,
                child: const Text('评价推荐'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _primaryActionLabel(FriendRecommendation recommendation) {
    if (recommendation.canInviteAccountability) {
      return '发起责任伙伴';
    }
    if (!recommendation.isExistingFriend) {
      return '先加好友';
    }
    return '查看详情';
  }
}

class _RecommendationBadge extends StatelessWidget {
  const _RecommendationBadge({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.sm,
          vertical: DS.xs,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: DS.borderRadiusFull,
        ),
        child: Text(
          label,
          style: DS.labelSmall.copyWith(
            color: color,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

/// 责任伙伴入口卡片（显示在好友列表顶部）
// ignore: unused_element
class _AccountabilityPartnersCard extends StatelessWidget {
  const _AccountabilityPartnersCard({required this.partnershipsState});

  final AsyncValue<List<AccountabilityPartnershipInfo>> partnershipsState;

  @override
  Widget build(BuildContext context) => partnershipsState.when(
        loading: _buildSkeleton,
        error: (_, __) => Padding(
          padding:
              const EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.sm),
          child: Text(
            '互督伙伴加载失败',
            style: TextStyle(fontSize: DS.fontSizeSm, color: DS.textSecondary),
          ),
        ),
        data: (partnerships) {
          final activeCount = partnerships
              .where((p) => p.status == AccountabilityStatus.active)
              .length;
          final pendingCount = partnerships
              .where((p) => p.status == AccountabilityStatus.pending)
              .length;

          return GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            margin: const EdgeInsets.fromLTRB(DS.lg, DS.lg, DS.lg, DS.sm),
            onTap: () => context.push(CommunityRoutes.accountability),
            child: Row(
              children: [
                // 图标
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(DS.borderRadiusMD),
                  ),
                  child: Icon(
                    Icons.handshake_outlined,
                    color: DS.brandPrimaryConst,
                  ),
                ),
                const SizedBox(width: DS.md),
                // 文字
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '我的责任伙伴',
                        style: DS.titleLarge.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: DS.xs),
                      Text(
                        _buildSubtitle(activeCount, pendingCount),
                        style: DS.bodySmall.copyWith(color: DS.textSecondary),
                      ),
                    ],
                  ),
                ),
                // 箭头
                Icon(Icons.chevron_right, color: DS.neutral400),
              ],
            ),
          );
        },
      );

  String _buildSubtitle(int active, int pending) {
    if (active == 0 && pending == 0) {
      return '点击添加责任伙伴，互相监督成长';
    }
    final parts = <String>[];
    if (active > 0) parts.add('$active 位进行中');
    if (pending > 0) parts.add('$pending 位待确认');
    return parts.join(' · ');
  }

  Widget _buildSkeleton() => Container(
        margin: const EdgeInsets.fromLTRB(DS.lg, DS.lg, DS.lg, DS.sm),
        height: 80,
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(DS.borderRadiusMD),
        ),
      );
}
