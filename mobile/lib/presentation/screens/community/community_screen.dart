import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/providers/community_providers.dart';
import 'package:sparkle/presentation/screens/community/create_post_screen.dart';
import 'package:sparkle/presentation/widgets/community/feed_post_card.dart';

class CommunityScreen extends ConsumerWidget {
  const CommunityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feedState = ref.watch(feedProvider);

    return Scaffold(
      backgroundColor: Colors.transparent, // Background handled by parent scaffold/stack
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.of(context).push(
            MaterialPageRoute(builder: (ctx) => const CreatePostScreen()),
          );
        },
        backgroundColor: DS.primaryBase,
        child: const Icon(Icons.edit),
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () => ref.read(feedProvider.notifier).refresh(),
          color: DS.primaryBase,
          child: feedState.when(
            data: (posts) {
              if (posts.isEmpty) {
                return _buildEmptyState(context);
              }
              return ListView.builder(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.only(bottom: 80), // Space for FAB
                itemCount: posts.length + 1, // +1 for Header
                itemBuilder: (context, index) {
                  if (index == 0) {
                    return _buildHeader(context);
                  }
                  final post = posts[index - 1];
                  return FeedPostCard(post: post);
                },
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
                  SparkleButton.ghost(label: 'Retry', onPressed: () => ref.read(feedProvider.notifier).refresh()),
                ],
              ),
            ),
            loading: () => Center(
              child: CircularProgressIndicator(color: DS.primaryBase),
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
              color: DS.brandPrimaryConst,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: DS.sm),
          Text(
            'Discover what others are learning',
            style: TextStyle(
              fontSize: 14,
              color: DS.brandPrimary400,
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

  Widget _buildEmptyState(BuildContext context) => ListView(
      children: [
        _buildHeader(context),
        const SizedBox(height: 100),
        Center(
          child: Column(
            children: [
              Icon(Icons.forum_outlined, size: 64, color: DS.brandPrimary24),
              const SizedBox(height: DS.lg),
              Text(
                'No posts yet',
                style: TextStyle(color: DS.brandPrimary54, fontSize: 18),
              ),
              const SizedBox(height: DS.sm),
              Text(
                'Be the first to share something!',
                style: TextStyle(color: DS.brandPrimary24),
              ),
            ],
          ),
        ),
      ],
    );
}

class _FilterChip extends StatelessWidget {

  const _FilterChip({required this.label, required this.isSelected});
  final String label;
  final bool isSelected;

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: isSelected ? DS.primaryBase : DS.brandPrimary10,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isSelected ? DS.primaryBase : DS.brandPrimary24,
        ),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isSelected ? DS.brandPrimary : DS.brandPrimary70,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        ),
      ),
    );
}