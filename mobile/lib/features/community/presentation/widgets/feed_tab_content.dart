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
import 'package:sparkle/features/community/presentation/widgets/comment_bottom_sheet.dart';
import 'package:sparkle/features/community/presentation/widgets/feed_post_card.dart';

/// Feed filter index (0 = Global, 1 = My Squad, 2 = Goal Mates, 3 = Following)
final communityFeedFilterProvider = StateProvider<int>((ref) => 0);

/// Extracted feed body content — used both standalone (CommunityScreen) and
/// embedded in the CommunityMainScreen 3-tab shell.
class FeedTabContent extends ConsumerStatefulWidget {
  const FeedTabContent({super.key, this.onCreatePost});

  final VoidCallback? onCreatePost;

  @override
  ConsumerState<FeedTabContent> createState() => _FeedTabContentState();
}

class _FeedTabContentState extends ConsumerState<FeedTabContent> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref.read(feedProvider.notifier).loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
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
                controller: _scrollController,
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
                      onComment: () => showCommentSheet(
                        context,
                        ref,
                        post.id,
                        postContent: post.content,
                      ),
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
    final l10n = context.l10n;
    final filters = [
      l10n.communityFeedGlobal,
      l10n.communityFeedMySquad,
      l10n.communityFeedGoalMates,
      l10n.communityFeedFollowing,
    ];
    const scopes = [null, 'squad', 'goal_mates', 'following'];
    return Padding(
      padding: const EdgeInsets.fromLTRB(DS.lg, DS.lg, DS.lg, DS.sm),
      child: SingleChildScrollView(
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
    );
  }

  Widget _buildEmptyState(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    return ScrollEdgeHaptics(
      child: ListView(
        children: [
          _buildFilterHeader(context, ref),
          const SizedBox(height: DS.spacing64),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
            child: EmptyState(
              title: l10n.communityNoCommunitySpark,
              description: l10n.communityNoCommunitySparkDesc,
              icon: Icons.forum_outlined,
              actionText: l10n.communitySharePost,
              onAction: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
                );
                if (widget.onCreatePost != null) {
                  widget.onCreatePost!();
                } else {
                  unawaited(context.push(CommunityRoutes.postsCreate));
                }
              },
              customAction: SparkleButton.ghost(
                label: l10n.communityRefreshFeed,
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
