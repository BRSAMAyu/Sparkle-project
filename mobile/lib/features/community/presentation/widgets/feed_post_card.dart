import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/sparkle_network_image.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:timeago/timeago.dart' as timeago;

class FeedPostCard extends StatelessWidget {
  const FeedPostCard({
    required this.post,
    super.key,
    this.onLike,
    this.onComment,
    this.onDelete,
    this.currentUserId,
  });
  final Post post;
  final VoidCallback? onLike;
  final VoidCallback? onComment;
  final VoidCallback? onDelete;
  final String? currentUserId;

  bool get _isOwner =>
      currentUserId != null && post.userId == currentUserId;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      explicitChildNodes: true,
      label: '${post.user.username}. ${post.content}',
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              DS.surfacePrimary,
              Color.lerp(DS.surfaceSecondary, DS.brandPrimary, 0.03) ??
                  DS.surfaceSecondary,
            ],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: DS.border.withValues(alpha: 0.4),
          ),
          boxShadow: [
            BoxShadow(
              color: DS.textPrimary.withValues(alpha: 0.06),
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Semantics(
                        image: true,
                        label: '${post.user.username} avatar',
                        child: CircleAvatar(
                          radius: 16,
                          backgroundColor: DS.avatarFallbackBackground,
                          backgroundImage: post.user.avatarUrl != null
                              ? CachedNetworkImageProvider(post.user.avatarUrl!)
                              : null,
                          child: post.user.avatarUrl == null
                              ? Text(
                                  post.user.username[0].toUpperCase(),
                                  style: TextStyle(
                                    color: DS.avatarFallbackForeground,
                                  ),
                                )
                              : null,
                        ),
                      ),
                      const SizedBox(width: DS.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              post.user.username,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: DS.textPrimary,
                                fontWeight: DS.fontWeightBold,
                                fontSize: 16,
                              ),
                            ),
                            Text(
                              timeago.format(post.createdAt),
                              style: TextStyle(
                                color: DS.textSecondary,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.sm),
                if (post.isOptimistic)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: DS.info.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: DS.info.withValues(alpha: 0.22),
                      ),
                    ),
                    child: Row(
                      children: [
                        const SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        const SizedBox(width: DS.xs),
                        Text(
                          'Posting...',
                          style: TextStyle(
                            color: DS.info,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
            const SizedBox(height: DS.sm),
            _ExpandableText(
              text: post.content,
              style: TextStyle(
                color: DS.textPrimary,
                fontSize: 15,
                height: 1.4,
              ),
            ),
            if (post.imageUrls != null && post.imageUrls!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: SparkleNetworkImage(
                  imageUrl: post.imageUrls!.first,
                  width: double.infinity,
                  height: 200,
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            const SizedBox(height: DS.md),
            Wrap(
              spacing: DS.lg,
              runSpacing: DS.sm,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                _ActionButton(
                  icon: post.isLiked ? Icons.favorite : Icons.favorite_border,
                  label: '${post.likeCount}',
                  semanticLabel: context.l10n.communityLikesCount(
                    post.likeCount,
                  ),
                  color: post.isLiked ? DS.error : null,
                  onTap: onLike,
                ),
                _ActionButton(
                  icon: Icons.chat_bubble_outline,
                  label: context.l10n.communityCommentLabel,
                  semanticLabel: context.l10n.communityCommentLabel,
                  onTap: onComment ??
                      () {
                        AppFeedback.info(
                          context,
                          context.l10n.communityCommentsComingSoon,
                        );
                      },
                ),
                _ActionButton(
                  icon: Icons.share_outlined,
                  label: context.l10n.communityShareLabel,
                  semanticLabel: context.l10n.communityShareLabel,
                  onTap: () {
                    final buffer = StringBuffer(post.content);
                    if (post.topic != null && post.topic!.isNotEmpty) {
                      buffer.write(' #${post.topic}');
                    }
                    Clipboard.setData(ClipboardData(text: buffer.toString()));
                    AppFeedback.success(
                      context,
                      context.l10n.communityCopiedToClipboard,
                    );
                  },
                ),
                if (_isOwner && onDelete != null)
                  _ActionButton(
                    icon: Icons.delete_outline,
                    label: context.l10n.communityDeleteLabel,
                    semanticLabel: context.l10n.communityDeleteLabel,
                    color: DS.error,
                    onTap: onDelete,
                  ),
                if (post.topic != null)
                  Semantics(
                    label: '#${post.topic}',
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 32),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: DS.secondaryBase.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: DS.secondaryBase.withValues(alpha: 0.22),
                        ),
                      ),
                      child: ExcludeSemantics(
                        child: Text(
                          '#${post.topic}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: DS.secondaryBase,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.label,
    this.activeIcon,
    this.color,
    this.semanticLabel,
    this.onTap,
  });
  final IconData icon;
  final IconData? activeIcon;
  final String label;
  final Color? color;
  final String? semanticLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => ConstrainedBox(
        constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
        child: SparklePressable(
          onTap: onTap,
          feedbackEvent: SensoryFeedbackEvent.selection,
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
          semanticLabel: semanticLabel ?? label,
          child: ExcludeSemantics(
            child: Row(
              children: [
                Icon(
                  activeIcon ?? icon,
                  color: color ?? DS.textSecondary,
                  size: 20,
                ),
                const SizedBox(width: 6),
                Text(
                  label,
                  style: TextStyle(
                    color: color ?? DS.textSecondary,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _ExpandableText extends StatefulWidget {
  const _ExpandableText({required this.text, this.style});
  final String text;
  final TextStyle? style;

  @override
  State<_ExpandableText> createState() => _ExpandableTextState();
}

class _ExpandableTextState extends State<_ExpandableText> {
  bool _expanded = false;
  bool _overflows = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final textPainter = TextPainter(
              text: TextSpan(text: widget.text, style: widget.style),
              maxLines: 4,
              textDirection: Directionality.of(context),
            )..layout(maxWidth: constraints.maxWidth);
            final overflows = textPainter.didExceedMaxLines;
            if (overflows != _overflows) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                if (mounted) setState(() => _overflows = overflows);
              });
            }
            return AnimatedSize(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
              alignment: Alignment.topLeft,
              child: Text(
                widget.text,
                maxLines: _expanded ? null : 4,
                overflow: _expanded ? TextOverflow.visible : TextOverflow.ellipsis,
                style: widget.style,
              ),
            );
          },
        ),
        if (_overflows)
          GestureDetector(
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                _expanded
                    ? context.l10n.communityShowLess
                    : context.l10n.communityShowMore,
                style: TextStyle(
                  color: DS.brandPrimary,
                  fontSize: 13,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ),
          ),
      ],
    );
  }
}
