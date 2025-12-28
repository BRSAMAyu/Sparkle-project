import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';

class PrivateChatBubble extends ConsumerStatefulWidget {

  const PrivateChatBubble({required this.message, super.key});
  final PrivateMessageInfo message;

  @override
  ConsumerState<PrivateChatBubble> createState() => _PrivateChatBubbleState();
}

class _PrivateChatBubbleState extends ConsumerState<PrivateChatBubble> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.5),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );

    _controller.forward();
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
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
          child: Row(
            mainAxisAlignment: isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isMe) ...[
                _buildAvatar(widget.message.sender),
                const SizedBox(width: DS.sm),
              ],
              Flexible(
                child: Column(
                  crossAxisAlignment: isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                  children: [
                    _buildContent(context, isMe),
                    const SizedBox(height: 2),
                     if (isMe && widget.message.isRead)
                      Text(brandPrimary),,,),
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
    );
  }

  Widget _buildContent(BuildContext context, bool isMe) {
    // Private chat mostly text for now
    switch (widget.message.messageType) {
      case MessageType.text:
      default:
        return _buildTextBubble(context, isMe);
    }
  }

  Widget _buildTextBubble(BuildContext context, bool isMe) => Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: isMe ? AppDesignTokens.primaryBase : DS.brandPrimary,
        borderRadius: BorderRadius.only(
          topLeft: const Radius.circular(16),
          topRight: const Radius.circular(16),
          bottomLeft: isMe ? const Radius.circular(16) : const Radius.circular(4),
          bottomRight: isMe ? const Radius.circular(4) : const Radius.circular(16),
        ),
        boxShadow: isMe 
            ? [BoxShadow(color: AppDesignTokens.primaryBase.withValues(alpha: 0.3), blurRadius: 8, offset: const Offset(0, 4))] 
            : AppDesignTokens.shadowSm,
        border: isMe ? null : Border.all(color: AppDesignTokens.neutral100),
      ),
      child: Text(
        widget.message.content ?? '',
        style: TextStyle(
          color: isMe ? DS.brandPrimary : AppDesignTokens.neutral900,
          fontSize: 16,
          height: 1.4,
        ),
      ),
    );

  Widget _buildAvatar(UserBrief user) => DecoratedBox(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: DS.brandPrimary, width: 2),
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: CircleAvatar(
        radius: 16,
        backgroundImage: user.avatarUrl != null ? NetworkImage(user.avatarUrl!) : null,
        backgroundColor: AppDesignTokens.neutral200,
        child: user.avatarUrl == null
            ? Text(
                user.displayName.substring(0, 1).toUpperCase(),
                style: const TextStyle(fontSize: 12, color: AppDesignTokens.neutral600),
              )
            : null,
      ),
    );
}
