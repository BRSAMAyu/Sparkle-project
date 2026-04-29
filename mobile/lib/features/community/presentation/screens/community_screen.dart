import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/scroll_edge_haptics.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/presentation/providers/community_providers.dart';
import 'package:sparkle/features/community/presentation/widgets/feed_post_card.dart';

/// Selected feed filter index (0 = Global, 1 = My Squad, 2 = Following)
final _communityFeedFilterProvider = StateProvider<int>((ref) => 0);

class CommunityScreen extends ConsumerWidget {
  const CommunityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feedState = ref.watch(feedProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      safeArea: false,
      floatingActionButton: SparkleIconButton(
        icon: const Icon(Icons.edit),
        onPressed: () {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
          context.push(CommunityRoutes.postsCreate);
        },
      ),
      child: SafeArea(
        child: ContentConstraint(
          child: RefreshIndicator(
            onRefresh: () => ref.read(feedProvider.notifier).refresh(),
            color: DS.primaryBase,
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
                        return _buildHeader(context, ref);
                      }
                      final post = posts[index - 1];
                      return SparkleStaggerItem(
                        index: index - 1,
                        child: FeedPostCard(post: post),
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
                      onPressed: () =>
                          ref.read(feedProvider.notifier).refresh(),
                    ),
                  ],
                ),
              ),
              loading: () => Center(
                child: CircularProgressIndicator(color: DS.primaryBase),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, WidgetRef ref) {
    final selectedIndex = ref.watch(_communityFeedFilterProvider);
    const filters = ['Global Feed', 'My Squad', 'Goal Mates', 'Following'];
    return Padding(
      padding: const EdgeInsets.all(DS.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.communityCommunity,
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: DS.textPrimary,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: DS.sm),
          Text(
            'Discover what others are learning',
            style: TextStyle(
              fontSize: 14,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.lg),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (int i = 0; i < filters.length; i++) ...[
                  _FilterChip(
                    label: filters[i],
                    isSelected: selectedIndex == i,
                    onTap: () {
                      ref.read(_communityFeedFilterProvider.notifier).state = i;
                      ref.read(feedProvider.notifier).refresh();
                    },
                  ),
                  if (i < filters.length - 1) const SizedBox(width: DS.sm),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, WidgetRef ref) => ScrollEdgeHaptics(
        child: ListView(
          children: [
            _buildHeader(context, ref),
            // UX-009: Goal-focused section showing accountability & common mistakes
            const _GoalFocusSection(),
            const SizedBox(height: DS.spacing64),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
              child: EmptyState(
                title: 'No community spark yet',
                description:
                    'Share a plan, insight, or small win to start the first conversation here.',
                icon: Icons.forum_outlined,
                actionText: 'Share a post',
                onAction: () {
                  unawaited(
                    SensoryFeedbackService.emit(
                      SensoryFeedbackEvent.confirm,
                    ),
                  );
                  context.push(CommunityRoutes.postsCreate);
                },
                customAction: SparkleButton.ghost(
                  label: 'Refresh feed',
                  onPressed: () => ref.read(feedProvider.notifier).refresh(),
                ),
              ),
            ),
          ],
        ),
      );
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({required this.label, required this.isSelected, required this.onTap});
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
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ),
      );
}

/// UX-009: Goal-focused section surfacing accountability partners,
/// cohort common mistakes, and resource quality from peers.
class _GoalFocusSection extends StatelessWidget {
  const _GoalFocusSection();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: DS.md),
          Row(
            children: [
              Icon(Icons.track_changes_rounded, size: 18, color: DS.brandPrimary),
              const SizedBox(width: DS.sm),
              Text(
                'Goal Focus',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.md),
          _GoalFocusCard(
            icon: Icons.people_outline_rounded,
            title: 'Accountability Partners',
            subtitle: 'Pair up with peers pursuing similar goals',
            onTap: () => context.push(CommunityRoutes.accountability),
          ),
          const SizedBox(height: DS.sm),
          _GoalFocusCard(
            icon: Icons.school_outlined,
            title: 'Common Mistakes',
            subtitle: 'See what others struggled with on the same topics',
            onTap: () => context.push(CommunityRoutes.errorInsights),
          ),
          const SizedBox(height: DS.sm),
          _GoalFocusCard(
            icon: Icons.star_outline_rounded,
            title: 'Top Resources',
            subtitle: 'Highest-rated materials from your cohort',
            onTap: () => context.push(CommunityRoutes.topResources),
          ),
        ],
      ),
    );
  }
}

class _GoalFocusCard extends StatelessWidget {
  const _GoalFocusCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
          borderRadius: BorderRadius.circular(DS.radiusMd),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: DS.brandPrimary12,
                borderRadius: BorderRadius.circular(DS.radiusSm),
              ),
              child: Icon(icon, size: 20, color: DS.brandPrimary),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: DS.textPrimary,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: TextStyle(fontSize: 12, color: DS.textSecondary),
                  ),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded, color: DS.textTertiary),
          ],
        ),
      ),
    );
  }
}