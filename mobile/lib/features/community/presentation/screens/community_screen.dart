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
                        return _buildHeader(context);
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
                      'Failed to load feed',
                      style: TextStyle(color: DS.brandPrimary300),
                    ),
                    SparkleButton.ghost(
                      label: 'Retry',
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

  Widget _buildHeader(BuildContext context) => Padding(
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Community',
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
            // Filter Tabs (Placeholder)
            const SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _FilterChip(label: 'Global Feed', isSelected: true),
                  SizedBox(width: DS.sm),
                  _FilterChip(label: 'My Squad', isSelected: false),
                  SizedBox(width: DS.sm),
                  _FilterChip(label: 'Following', isSelected: false),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _buildEmptyState(BuildContext context, WidgetRef ref) => ScrollEdgeHaptics(
        child: ListView(
          children: [
            _buildHeader(context),
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
  const _FilterChip({required this.label, required this.isSelected});
  final String label;
  final bool isSelected;

  @override
  Widget build(BuildContext context) => SparklePressable(
        onTap: () {},
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
