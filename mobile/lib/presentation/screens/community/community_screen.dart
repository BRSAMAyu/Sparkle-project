import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
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
        backgroundColor: AppDesignTokens.primaryBase,
        child: const Icon(Icons.edit),
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () => ref.read(feedProvider.notifier).refresh(),
          color: AppDesignTokens.primaryBase,
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
                  const Icon(Icons.error_outline, size: 48, color: AppDesignTokens.error),
                  const SizedBox(height: 16),
                  Text(
                    'Failed to load feed',
                    style: TextStyle(color: Colors.grey[300]),
                  ),
                  TextButton(
                    onPressed: () => ref.read(feedProvider.notifier).refresh(),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
            loading: () => const Center(
              child: CircularProgressIndicator(color: AppDesignTokens.primaryBase),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Community',
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: Colors.white,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Discover what others are learning',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[400],
            ),
          ),
          const SizedBox(height: 16),
          // Filter Tabs (Placeholder)
          const SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _FilterChip(label: 'Global Feed', isSelected: true),
                SizedBox(width: 8),
                _FilterChip(label: 'My Squad', isSelected: false),
                SizedBox(width: 8),
                _FilterChip(label: 'Following', isSelected: false),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return ListView(
      children: [
        _buildHeader(context),
        const SizedBox(height: 100),
        const Center(
          child: Column(
            children: [
              Icon(Icons.forum_outlined, size: 64, color: Colors.white24),
              SizedBox(height: 16),
              Text(
                'No posts yet',
                style: TextStyle(color: Colors.white54, fontSize: 18),
              ),
              SizedBox(height: 8),
              Text(
                'Be the first to share something!',
                style: TextStyle(color: Colors.white24),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool isSelected;

  const _FilterChip({required this.label, required this.isSelected});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: isSelected ? AppDesignTokens.primaryBase : Colors.white10,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isSelected ? AppDesignTokens.primaryBase : Colors.white24,
        ),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isSelected ? Colors.white : Colors.white70,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        ),
      ),
    );
  }
}