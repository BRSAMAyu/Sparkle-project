import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/domain/community/community_models.dart';
import 'package:timeago/timeago.dart' as timeago;

class FeedPostCard extends StatelessWidget {

  FeedPostCard({required this.post, super.key, this.onLike});
  final Post post;
  final VoidCallback? onLike;

  @override
  Widget build(BuildContext context) => Container(
      margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: DS.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: DS.border.withOpacity(0.3),
        ),
        boxShadow: [
          BoxShadow(
            color: DS.brandPrimary.withOpacity(0.1),
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
                backgroundColor: DS.primaryBase,
                backgroundImage: post.user.avatarUrl != null
                    ? NetworkImage(post.user.avatarUrl!)
                    : null,
                child: post.user.avatarUrl == null
                    ? Text(post.user.username[0].toUpperCase())
                    : null,
              ),
              SizedBox(width: DS.md),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    post.user.username,
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                  Text(
                    timeago.format(post.createdAt),
                    style: TextStyle(
                      color: DS.brandPrimary400,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              Spacer(),
              if (post.isOptimistic)
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: DS.primaryBase.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 12,
                        height: 12,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      SizedBox(width: DS.xs),
                      Text(
                        'Posting...',
                        style: TextStyle(
                          color: DS.primaryBase,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          SizedBox(height: DS.md),
          Text(
            post.content,
            style: TextStyle(
              color: DS.brandPrimaryConst,
              fontSize: 15,
              height: 1.4,
            ),
          ),
          if (post.imageUrls != null && post.imageUrls!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  post.imageUrls!.first,
                  fit: BoxFit.cover,
                  width: double.infinity,
                  height: 200,
                  errorBuilder: (ctx, err, stack) => Container(
                    height: 200,
                    color: DS.brandPrimary800,
                    child: Center(child: Icon(Icons.broken_image)),
                  ),
                ),
              ),
            ),
          SizedBox(height: DS.lg),
          Row(
            children: [
              _ActionButton(
                icon: Icons.favorite_border,
                label: '${post.likeCount}',
                onTap: onLike,
              ),
              SizedBox(width: DS.xl),
              const _ActionButton(
                icon: Icons.chat_bubble_outline,
                label: 'Comment',
              ),
              Spacer(),
              if (post.topic != null)
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: DS.secondaryBase.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '#${post.topic}',
                    style: TextStyle(
                      color: DS.secondaryBase,
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

class _ActionButton extends StatelessWidget {

  const _ActionButton({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
      onTap: onTap,
      child: Row(
        children: [
          Icon(icon, color: DS.brandPrimary400, size: 20),
          SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: DS.brandPrimary400,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
}
