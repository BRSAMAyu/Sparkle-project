import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/domain/community/community_models.dart';
import 'package:timeago/timeago.dart' as timeago;

class FeedPostCard extends StatelessWidget {
  final Post post;
  final VoidCallback? onLike;

  const FeedPostCard({required this.post, super.key, this.onLike});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppDesignTokens.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppDesignTokens.border.withOpacity(0.3),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 20,
                backgroundColor: AppDesignTokens.primaryBase,
                backgroundImage: post.user.avatarUrl != null
                    ? NetworkImage(post.user.avatarUrl!)
                    : null,
                child: post.user.avatarUrl == null
                    ? Text(post.user.username[0].toUpperCase())
                    : null,
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    post.user.username,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                  Text(
                    timeago.format(post.createdAt),
                    style: TextStyle(
                      color: Colors.grey[400],
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              const Spacer(),
              if (post.isOptimistic)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppDesignTokens.primaryBase.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Row(
                    children: [
                      SizedBox(
                        width: 12,
                        height: 12,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      SizedBox(width: 4),
                      Text(
                        'Posting...',
                        style: TextStyle(
                          color: AppDesignTokens.primaryBase,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            post.content,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              height: 1.4,
            ),
          ),
          if (post.imageUrls != null && post.imageUrls!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.top(12),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  post.imageUrls!.first,
                  fit: BoxFit.cover,
                  width: double.infinity,
                  height: 200,
                  errorBuilder: (ctx, err, stack) => Container(
                    height: 200,
                    color: Colors.grey[800],
                    child: const Center(child: Icon(Icons.broken_image)),
                  ),
                ),
              ),
            ),
          const SizedBox(height: 16),
          Row(
            children: [
              _ActionButton(
                icon: Icons.favorite_border,
                label: '${post.likeCount}',
                onTap: onLike,
              ),
              const SizedBox(width: 24),
              const _ActionButton(
                icon: Icons.chat_bubble_outline,
                label: 'Comment',
              ),
              const Spacer(),
              if (post.topic != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppDesignTokens.secondaryBase.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '#${post.topic}',
                    style: const TextStyle(
                      color: AppDesignTokens.secondaryBase,
                      fontSize: 12,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  const _ActionButton({required this.icon, required this.label, this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Row(
        children: [
          Icon(icon, color: Colors.grey[400], size: 20),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: Colors.grey[400],
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }
}
