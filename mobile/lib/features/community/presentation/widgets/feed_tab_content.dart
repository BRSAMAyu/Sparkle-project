import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/scroll_edge_haptics.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/presentation/providers/community_providers.dart';
import 'package:sparkle/features/community/presentation/widgets/feed_post_card.dart';

/// Feed filter index (0 = Global, 1 = My Squad, 2 = Goal Mates, 3 = Following)
final communityFeedFilterProvider = StateProvider<int>((ref) => 0);

/// Extracted feed body content — used both standalone (CommunityScreen) and
/// embedded in the CommunityMainScreen 3-tab shell.
class FeedTabContent extends ConsumerWidget {
  const FeedTabContent({super.key, this.onCreatePost});

  final VoidCallback? onCreatePost;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feedState = ref.watch(feedProvider);

    return ContentConstraint(
      child: SparkleRefreshIndicator(
        onRefresh: () => ref.read(feedProvider.notifier).refresh(),
        child: feedState.when(
          data: (posts) {
            if (posts.isEmpty) {
              return _buildEmptyState(context, ref);
            }
            return ScrollEdgeHaptics(
              child: ListView.builder(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.only(bottom: 80),
                itemCount: posts.length + 1,
                itemBuilder: (context, index) {
                  if (index == 0) {
                    return _buildFilterHeader(context, ref);
                  }
                  final post = posts[index - 1];
                  return SparkleStaggerItem(
                    index: index - 1,
                    child: FeedPostCard(
                      post: post,
                      onLike: () =>
                          ref.read(feedProvider.notifier).toggleLike(post.id),
                    ),
                  );
                },
              ),
            );
          },
          error: (err, stack) => Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline, size: 48, color: DS.error),
                const SizedBox(height: DS.lg),
                Text(
                  context.l10n.communityLoadFailedTitle,
                  style: TextStyle(color: DS.brandPrimary300),
                ),
                SparkleButton.ghost(
                  label: context.l10n.communityRetry,
                  onPressed: () => ref.read(feedProvider.notifier).refresh(),
                ),
              ],
            ),
          ),
          loading: () => const SparkleListSkeleton(count: 5),
        ),
      ),
    );
  }

  Widget _buildFilterHeader(BuildContext context, WidgetRef ref) {
    final selectedIndex = ref.watch(communityFeedFilterProvider);
    final isChinese = Localizations.localeOf(context).languageCode == 'zh';
    final filters = isChinese
        ? ['全局动态', '我的小队', '目标伙伴', '我的关注']
        : ['Global Feed', 'My Squad', 'Goal Mates', 'Following'];
    final descriptions = isChinese
        ? [
            '公开动态，只显示所有人可见的内容',
            '同小队成员的公开内容，好友内容仍尊重好友可见',
            '当前责任伙伴和目标同路人的动态',
            '已互相关注好友的动态',
          ]
        : [
            'Public posts that are visible to everyone',
            'Posts from squad members, with friend-only privacy preserved',
            'Updates from active accountability partners',
            'Posts from accepted friends',
          ];
    const scopes = [null, 'squad', 'goal_mates', 'following'];
    return Padding(
      padding: const EdgeInsets.fromLTRB(DS.lg, DS.lg, DS.lg, DS.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (int i = 0; i < filters.length; i++) ...[
                  _FilterChip(
                    label: filters[i],
                    isSelected: selectedIndex == i,
                    onTap: () {
                      ref.read(communityFeedFilterProvider.notifier).state = i;
                      unawaited(
                        ref.read(feedProvider.notifier).refresh(
                              scope: scopes[i],
                              clearScope: scopes[i] == null,
                            ),
                      );
                    },
                  ),
                  if (i < filters.length - 1) const SizedBox(width: DS.sm),
                ],
              ],
            ),
          ),
          const SizedBox(height: DS.sm),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 180),
            child: Text(
              descriptions[selectedIndex],
              key: ValueKey(selectedIndex),
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, WidgetRef ref) {
    final isChinese = Localizations.localeOf(context).languageCode == 'zh';
    return ScrollEdgeHaptics(
      child: ListView(
        children: [
          _buildFilterHeader(context, ref),
          const SizedBox(height: DS.spacing64),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
            child: EmptyState(
              title: isChinese ? '社区还没有火花' : 'No community spark yet',
              description: isChinese
                  ? '分享一个计划、洞察或小胜利，开始这里的第一次对话。'
                  : 'Share a plan, insight, or small win to start the first conversation here.',
              icon: Icons.forum_outlined,
              actionText: isChinese ? '发一条动态' : 'Share a post',
              onAction: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
                );
                if (onCreatePost != null) {
                  onCreatePost!();
                } else {
                  unawaited(context.push(CommunityRoutes.postsCreate));
                }
              },
              customAction: SparkleButton.ghost(
                label: isChinese ? '刷新动态' : 'Refresh feed',
                onPressed: () =>
                    unawaited(ref.read(feedProvider.notifier).refresh()),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => SparklePressable(
        onTap: onTap,
        feedbackEvent: SensoryFeedbackEvent.selection,
        padding: EdgeInsets.zero,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: isSelected
                ? DS.surfaceRoleColor(SparkleSurfaceRole.accent)
                : DS.surfaceRoleColor(SparkleSurfaceRole.panel),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: isSelected ? DS.brandPrimary : DS.borderSubtle,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: isSelected ? DS.textPrimary : DS.textSecondary,
              fontWeight: isSelected ? DS.fontWeightBold : FontWeight.normal,
            ),
          ),
        ),
      );
}
