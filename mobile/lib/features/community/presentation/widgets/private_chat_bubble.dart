import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_tappable.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/widgets/share_cards/share_cards.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

class PrivateChatBubble extends ConsumerStatefulWidget {
  const PrivateChatBubble({required this.message, super.key});
  final PrivateMessageInfo message;

  @override
  ConsumerState<PrivateChatBubble> createState() => _PrivateChatBubbleState();
}

class _PrivateChatBubbleState extends ConsumerState<PrivateChatBubble>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: DS.motionDuration(SparkleMotionToken.standard),
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.5),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
    _scaleAnimation = Tween<double>(begin: 0.985, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );

    unawaited(_controller.forward());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final currentUser = ref.watch(currentUserProvider);
    final isMe = widget.message.sender.id == currentUser?.id;

    return SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: Padding(
            padding:
                const EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
            child: Row(
            mainAxisAlignment:
                isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isMe) ...[
                _buildAvatar(widget.message.sender),
                const SizedBox(width: DS.sm),
              ],
              Flexible(
                child: Column(
                  crossAxisAlignment:
                      isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                  children: [
                    _buildContent(context, isMe),
                    const SizedBox(height: 2),
                    if (isMe && widget.message.isRead)
                      Text(
                        'Read',
                        style: TextStyle(
                          fontSize: 10,
                          color: context.sparkleColors.textSecondary,
                        ),
                      ),
                  ],
                ),
              ),
              if (isMe) ...[
                const SizedBox(width: DS.sm),
                _buildAvatar(widget.message.sender),
              ],
            ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, bool isMe) {
    switch (widget.message.messageType) {
      case MessageType.taskShare:
        return _buildSharedResourceBubble(context, isMe);
      case MessageType.planShare:
        return _buildSharedResourceBubble(context, isMe);
      case MessageType.capsuleShare:
        return _buildSharedResourceBubble(context, isMe);
      case MessageType.prismShare:
        return _buildSharedResourceBubble(context, isMe);
      case MessageType.achievement:
        return _buildSharedResourceBubble(context, isMe);
      case MessageType.text:
      default:
        return _buildTextBubble(context, isMe);
    }
  }

  Widget _buildSharedResourceBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final contentType = _getContentTypeFromMessage(
      widget.message.messageType,
      data,
    );
    final sharedResourceId = data['shared_resource_id']?.toString();

    final payload = UniversalSharePayload(
      contentType: contentType,
      resourceId: data['resource_id'] as String? ??
          data['id'] as String? ??
          data['${contentType.stringValue}_id'] as String? ??
          data['achievement_id'] as String? ??
          '',
      title: data['resource_title'] as String? ??
          data['title'] as String? ??
          data['name'] as String? ??
          widget.message.content ??
          '',
      subtitle: data['resource_summary'] as String? ??
          data['subtitle'] as String? ??
          data['description'] as String?,
      metadata: data,
    );

    return _buildRichCardWrapper(
      isMe: isMe,
      onTap: () => _handleSharedResourceTap(payload),
      child: ShareCardFactory.fromPayload(
        payload,
        onTap: () => _handleSharedResourceTap(payload),
        sharedResourceId: sharedResourceId,
        onAdopt: sharedResourceId == null ||
                (contentType != ShareableContentType.planProgress &&
                    contentType != ShareableContentType.taskCompletion)
            ? null
            : () => _handleAdopt(
                  context,
                  sharedResourceId,
                  contentType == ShareableContentType.planProgress
                      ? 'plan'
                      : 'task',
                ),
      ),
    );
  }

  ShareableContentType _getContentTypeFromMessage(
    MessageType type,
    Map<String, dynamic> data,
  ) {
    if (type == MessageType.capsuleShare &&
        data['resource_type']?.toString() == 'knowledge_node') {
      return ShareableContentType.knowledgeNode;
    }
    return switch (type) {
      MessageType.taskShare => ShareableContentType.taskCompletion,
      MessageType.planShare => ShareableContentType.planProgress,
      MessageType.capsuleShare => ShareableContentType.capsule,
      MessageType.prismShare => ShareableContentType.cognitivePrism,
      MessageType.achievement => ShareableContentType.achievement,
      _ => ShareableContentType.taskCompletion,
    };
  }

  Widget _buildRichCardWrapper({
    required bool isMe,
    required Widget child,
    VoidCallback? onTap,
  }) =>
      SparkleTappable(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 260),
          decoration: BoxDecoration(
            color: isMe ? DS.chatBubbleUser : DS.chatBubbleOther,
            borderRadius: BorderRadius.circular(16),
            boxShadow: isMe
                ? [
                    BoxShadow(
                      color: DS.chatBubbleUser.withValues(alpha: 0.24),
                      blurRadius: 8,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : DS.shadowSm,
            border: isMe ? null : Border.all(color: DS.borderSubtle),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: child,
          ),
        ),
      );

  void _handleSharedResourceTap(UniversalSharePayload payload) {
    final deepLink = payload.deepLink;
    if (deepLink.isNotEmpty) {
      if (!DeepLinkService.handleDeepLink(context, deepLink)) {
        unawaited(UniversalShareService().copyDeepLink(deepLink));
        AppFeedback.info(context, '链接已复制');
      }
    }
  }

  Future<void> _handleAdopt(
    BuildContext context,
    String sharedResourceId,
    String fallbackResourceType,
  ) async {
    try {
      final result = await ref
          .read(communityShareRepositoryProvider)
          .adoptResource(sharedResourceId: sharedResourceId);
      if (!context.mounted) {
        return;
      }
      AppFeedback.success(context, '已采纳，跳转中...');
      final resourceType =
          result['resource_type']?.toString() ?? fallbackResourceType;
      final entityCard = result['entity_card'] is Map<String, dynamic>
          ? EntityCardPayload.fromRaw(
              {'entity_card': result['entity_card'] as Map<String, dynamic>},
              fallbackType: resourceType,
            )
          : null;
      final newId = result['new_resource_id']?.toString();
      final route = entityCard?.detailRoute ??
          (newId == null
              ? null
              : resourceType == 'plan'
                  ? '/plans/$newId'
                  : '/tasks/$newId');
      if (resourceType == 'plan') {
        unawaited(ref.read(planListProvider.notifier).refresh());
      } else if (resourceType == 'task') {
        unawaited(ref.read(taskListProvider.notifier).refreshTasks());
      }
      if (route != null && route.isNotEmpty) {
        unawaited(context.push(route));
      }
    } catch (e) {
      if (!context.mounted) {
        return;
      }
      AppFeedback.error(context, '采纳失败: $e');
    }
  }

  Widget _buildTextBubble(BuildContext context, bool isMe) => Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: isMe ? DS.chatBubbleUser : DS.chatBubbleOther,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft:
                isMe ? const Radius.circular(16) : const Radius.circular(4),
            bottomRight:
                isMe ? const Radius.circular(4) : const Radius.circular(16),
          ),
          boxShadow: isMe
              ? [
                  BoxShadow(
                      color: DS.chatBubbleUser.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 4),),
                ]
              : DS.shadowSm,
          border: isMe ? null : Border.all(color: DS.neutral100),
        ),
        child: SparkleMarkdown(
          content: widget.message.content ?? '',
          textColor: isMe ? DS.chatBubbleUserText : DS.chatBubbleOtherText,
          codeBackgroundColor:
              isMe ? Colors.white.withValues(alpha: 0.12) : DS.surfaceTertiary,
          linkColor: isMe ? Colors.white : DS.brandPrimary,
          contentRole: SparkleMarkdownRole.chatBubble,
        ),
      );

  Widget _buildAvatar(UserBrief user) => DecoratedBox(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: DS.brandPrimaryConst, width: 2),
          boxShadow: DS.shadowSm,
        ),
        child: CircleAvatar(
          radius: 16,
          backgroundImage:
              user.avatarUrl != null ? NetworkImage(user.avatarUrl!) : null,
          backgroundColor: DS.neutral200,
          child: user.avatarUrl == null
              ? Text(
                  user.displayName.substring(0, 1).toUpperCase(),
                  style: TextStyle(fontSize: 12, color: DS.neutral600),
                )
              : null,
        ),
      );
}
