import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/presentation/widgets/chat/action_card.dart';
import 'package:sparkle/presentation/widgets/chat/agent_reasoning_bubble_v2.dart';
import 'package:sparkle/presentation/widgets/chat/ai_status_indicator.dart';
import 'package:url_launcher/url_launcher.dart';

class ChatBubble extends StatefulWidget {
  const ChatBubble({
    required this.message,
    super.key,
    this.showAvatar = true,
    this.currentUserId,
    this.onQuote,
    this.onRevoke,
    this.onActionConfirm,
    this.onActionDismiss,
  });
  final dynamic message; // ChatMessageModel or PrivateMessageInfo
  final bool showAvatar;
  final String? currentUserId;
  final Function(dynamic message)? onQuote;
  final Function(dynamic message)? onRevoke;
  final Function(WidgetPayload action)? onActionConfirm;
  final Function(WidgetPayload action)? onActionDismiss;

  @override
  State<ChatBubble> createState() => _ChatBubbleState();
}

class _ChatBubbleState extends State<ChatBubble> with TickerProviderStateMixin {
  late AnimationController _entryController;
  late Animation<double> _scale;
  late Animation<Offset> _position;

  bool _showHeart = false;
  bool _isPressed = false;

  @override
  void initState() {
    super.initState();
    _entryController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );

    _scale = Tween<double>(begin: 0.9, end: 1.0).animate(
      CurvedAnimation(parent: _entryController, curve: Curves.elasticOut),
    );

    _position = Tween<Offset>(
      begin: const Offset(0, 0.5),
      end: Offset.zero,
    ).animate(
        CurvedAnimation(parent: _entryController, curve: Curves.easeOutQuart),);

    _entryController.forward();
  }

  @override
  void dispose() {
    _entryController.dispose();
    super.dispose();
  }

  bool get _isUser {
    final myId = widget.currentUserId ?? 'me';
    var isUser = false;
    if (widget.message is ChatMessageModel) {
      isUser = (widget.message as ChatMessageModel).role == MessageRole.user;
    } else if (widget.message is PrivateMessageInfo) {
      final msg = widget.message as PrivateMessageInfo;
      isUser = msg.sender.id == myId;
    } else if (widget.message is MessageInfo) {
      final msg = widget.message as MessageInfo;
      isUser = msg.sender?.id == myId;
    }
    if (_isAgent) {
      return false;
    }
    return isUser;
  }

  bool get _isAgent {
    if (widget.message is PrivateMessageInfo) {
      return isPrivateAgentMessage(widget.message as PrivateMessageInfo);
    }
    if (widget.message is MessageInfo) {
      return isCommunityAgentMessage(widget.message as MessageInfo);
    }
    return false;
  }

  bool get _isRevoked {
    if (widget.message is MessageInfo) {
      return (widget.message as MessageInfo).isRevoked;
    }
    if (widget.message is PrivateMessageInfo) {
      return (widget.message as PrivateMessageInfo).isRevoked;
    }
    return false;
  }

  String get _content => (widget.message is ChatMessageModel)
      ? (widget.message as ChatMessageModel).content
      : (widget.message is PrivateMessageInfo)
          ? (widget.message as PrivateMessageInfo).content ?? ''
          : (widget.message as MessageInfo).content ?? '';

  DateTime get _createdAt => (widget.message is ChatMessageModel)
      ? (widget.message as ChatMessageModel).createdAt
      : (widget.message is PrivateMessageInfo)
          ? (widget.message as PrivateMessageInfo).createdAt
          : (widget.message as MessageInfo).createdAt;

  void _handleDoubleTap() {
    if (_isUser || _isRevoked || !mounted) return;
    setState(() => _showHeart = true);
    Future.delayed(const Duration(milliseconds: 1000), () {
      if (mounted) setState(() => _showHeart = false);
    });
  }

  void _showContextMenu(BuildContext context) {
    if (_isRevoked || !mounted) return;

    // Allow revocation within 24 hours for user messages
    final canRevoke =
        _isUser && DateTime.now().difference(_createdAt).inHours < 24;

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (widget.onQuote != null &&
                  widget.message is PrivateMessageInfo)
                ListTile(
                  leading: const Icon(Icons.format_quote_rounded),
                  title: const Text('引用'),
                  onTap: () {
                    if (mounted) {
                      Navigator.pop(context);
                      widget.onQuote!(widget.message);
                    }
                  },
                ),
              ListTile(
                leading: const Icon(Icons.copy_rounded),
                title: const Text('复制'),
                onTap: () {
                  Clipboard.setData(ClipboardData(text: _content));
                  if (mounted) {
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                          content: Text('已复制到剪贴板'),
                          duration: Duration(seconds: 1),),
                    );
                  }
                },
              ),
              if (canRevoke && widget.onRevoke != null)
                ListTile(
                  leading: Icon(Icons.undo_rounded, color: DS.error),
                  title: Text('撤销', style: TextStyle(color: DS.error)),
                  onTap: () {
                    if (mounted) {
                      Navigator.pop(context);
                      widget.onRevoke!(widget.message);
                    }
                  },
                ),
              const SizedBox(height: DS.sm),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isRevoked) return _buildRevokedPlaceholder();

    final isUser = _isUser;
    final timeStr = DateFormat('HH:mm').format(_createdAt);

    return SlideTransition(
      position: _position,
      child: ScaleTransition(
        scale: _scale,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 12.0),
          child: Column(
            children: [
              Row(
                mainAxisAlignment:
                    isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  if (!isUser && widget.showAvatar) _buildAvatar(false),
                  if (!isUser && !widget.showAvatar) const SizedBox(width: 44),
                  Flexible(
                    child: GestureDetector(
                      onDoubleTap: _handleDoubleTap,
                      onLongPress: () => _showContextMenu(context),
                      onTapDown: (_) {
                        if (mounted) setState(() => _isPressed = true);
                      },
                      onTapUp: (_) {
                        if (mounted) setState(() => _isPressed = false);
                      },
                      onTapCancel: () {
                        if (mounted) setState(() => _isPressed = false);
                      },
                      child: AnimatedScale(
                        scale: _isPressed ? 0.98 : 1.0,
                        duration: const Duration(milliseconds: 100),
                        curve: Curves.easeInOut,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            Column(
                              crossAxisAlignment: isUser
                                  ? CrossAxisAlignment.end
                                  : CrossAxisAlignment.start,
                              children: [
                                Container(
                                  margin: const EdgeInsets.symmetric(
                                    horizontal: 8.0,
                                  ),
                                  constraints: BoxConstraints(
                                    maxWidth:
                                        MediaQuery.of(context).size.width *
                                            0.72,
                                  ),
                                  child: MaterialStyler(
                                    material: isUser
                                        ? SparkleMaterial(
                                            backgroundGradient: LinearGradient(
                                              begin: Alignment.topLeft,
                                              end: Alignment.bottomRight,
                                              colors: [
                                                DS.brandPrimary,
                                                DS.brandPrimary
                                                    .withValues(alpha: 0.85),
                                              ],
                                            ),
                                            noiseOpacity: 0.0,
                                            shadows: [
                                              BoxShadow(
                                                color: DS.brandPrimary
                                                    .withValues(alpha: 0.2),
                                                blurRadius: 4,
                                                offset: const Offset(0, 2),
                                              ),
                                            ],
                                          )
                                        : AppMaterials.ceramic.copyWith(
                                            glowColor: context
                                                .sparkleColors.glowPrimary
                                                .withValues(alpha: 0.2),
                                          ),
                                    shapeBorder: ContinuousRectangleBorder(
                                      borderRadius: BorderRadius.circular(24),
                                    ),
                                    padding: const EdgeInsets.symmetric(
                                      vertical: 10,
                                      horizontal: 14,
                                    ),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        if (widget.message is PrivateMessageInfo &&
                                            (widget.message as PrivateMessageInfo)
                                                    .quotedMessage !=
                                                null)
                                          _buildQuoteArea(
                                              context,
                                              isUser,
                                              (widget.message as PrivateMessageInfo)
                                                  .quotedMessage!,),
                                        if (widget.message is ChatMessageModel &&
                                            (widget.message as ChatMessageModel)
                                                    .aiStatus !=
                                                null)
                                          Padding(
                                            padding: const EdgeInsets.only(
                                                bottom: 8.0,),
                                            child: AiStatusBubble(
                                                status: (widget.message
                                                        as ChatMessageModel)
                                                    .aiStatus!,),
                                          ),
                                        if (widget.message is ChatMessageModel &&
                                            (widget.message as ChatMessageModel)
                                                    .reasoningSteps !=
                                                null)
                                          Padding(
                                            padding: const EdgeInsets.only(
                                                bottom: 8.0,),
                                            child: AgentReasoningBubble(
                                              steps: (widget.message
                                                      as ChatMessageModel)
                                                  .reasoningSteps!,
                                              totalDurationMs:
                                                  _calculateReasoningDuration(
                                                      widget.message
                                                          as ChatMessageModel,),
                                            ),
                                          ),
                                        MarkdownBody(
                                          data: _content,
                                          styleSheet: _getMarkdownStyle(
                                              context, isUser,),
                                          onTapLink: (text, href, title) async {
                                            if (href == null) return;
                                            final uri = Uri.tryParse(href);
                                            if (uri == null) return;

                                            final scheme =
                                                uri.scheme.toLowerCase();
                                            const allowedSchemes = [
                                              'http',
                                              'https',
                                            ];
                                            if (!allowedSchemes
                                                .contains(scheme)) {
                                              return;
                                            }

                                            try {
                                              if (await canLaunchUrl(uri)) {
                                                await launchUrl(
                                                  uri,
                                                  mode: LaunchMode
                                                      .externalApplication,
                                                );
                                              }
                                            } catch (e) {
                                              debugPrint(
                                                  'Failed to launch URL: $e',);
                                            }
                                          },
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                                if (widget.message is ChatMessageModel &&
                                    (widget.message as ChatMessageModel)
                                            .widgets !=
                                        null)
                                  ...(widget.message as ChatMessageModel)
                                      .widgets!
                                      .map(
                                        (w) => Padding(
                                          padding: const EdgeInsets.only(
                                              top: 8.0, right: 8.0, left: 8.0,),
                                          child: ActionCard(
                                            action: w,
                                            onConfirm: widget.onActionConfirm !=
                                                    null
                                                ? () =>
                                                    widget.onActionConfirm!(w)
                                                : null,
                                            onDismiss: widget.onActionDismiss !=
                                                    null
                                                ? () =>
                                                    widget.onActionDismiss!(w)
                                                : null,
                                          ),
                                        ),
                                      ),
                              ],
                            ),
                            if (_showHeart) _buildHeartAnimation(),
                          ],
                        ),
                      ),
                    ),
                  ),
                  if (isUser && widget.showAvatar) _buildAvatar(true),
                  if (isUser && !widget.showAvatar) const SizedBox(width: 44),
                ],
              ),
              Padding(
                padding: EdgeInsets.only(
                  top: 4,
                  left: isUser ? 0 : 52,
                  right: isUser ? 52 : 0,
                ),
                child: Row(
                  mainAxisAlignment:
                      isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
                  children: [
                    if (isUser) _buildMessageStatus(),
                    const SizedBox(width: DS.xs),
                    Text(
                      timeStr,
                      style: TextStyle(fontSize: 10, color: DS.neutral500),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildQuoteArea(
          BuildContext context, bool isUser, PrivateMessageInfo msg,) =>
      Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          color: isUser
              ? context.sparkleColors.brandPrimary.withValues(alpha: 0.15)
              : context.sparkleColors.surfaceTertiary.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(8),
          border: Border(
              left: BorderSide(
                  color: isUser
                      ? context.sparkleColors.brandPrimary
                          .withValues(alpha: 0.7)
                      : context.sparkleColors.brandPrimary,
                  width: 3,),),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              msg.sender.displayName,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: isUser
                    ? context.sparkleColors.brandPrimary
                    : context.sparkleColors.brandPrimary,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              msg.content ?? '',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12,
                color: isUser
                    ? context.sparkleColors.brandPrimary.withValues(alpha: 0.9)
                    : context.sparkleColors.textSecondary,
              ),
            ),
          ],
        ),
      );

  Widget _buildRevokedPlaceholder() => Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text(
            _isUser ? '你撤回了一条消息' : '对方撤回了一条消息',
            style: TextStyle(
                fontSize: 12, color: context.sparkleColors.neutral400,),
          ),
        ),
      );

  Widget _buildMessageStatus() {
    if (widget.message is! PrivateMessageInfo) return const SizedBox.shrink();
    final msg = widget.message as PrivateMessageInfo;

    if (msg.isSending) {
      return const SizedBox(
          width: 12,
          height: 12,
          child: CircularProgressIndicator(strokeWidth: 1),);
    }
    if (msg.hasError) {
      return Icon(Icons.error_outline,
          color: context.sparkleColors.semanticError, size: 14,);
    }

    final isRead = msg.isRead || msg.readAt != null;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          isRead ? Icons.done_all_rounded : Icons.done_rounded,
          size: 14,
          color: isRead
              ? context.sparkleColors.semanticInfo
              : context.sparkleColors.neutral400,
        ),
        if (isRead)
          Padding(
            padding: const EdgeInsets.only(left: 2),
            child: Text('已读',
                style: TextStyle(
                    fontSize: 10, color: context.sparkleColors.semanticInfo,),),
          ),
      ],
    );
  }

  Widget _buildAvatar(bool isUser) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    String? avatarUrl;
    var initial = '?';

    if (_isAgent) {
      final agent = buildCommunityAgentUser();
      avatarUrl = agent.avatarUrl;
      initial = 'AI';
    } else if (widget.message is ChatMessageModel) {
      initial = isUser ? 'U' : 'AI';
    } else if (widget.message is PrivateMessageInfo) {
      final msg = widget.message as PrivateMessageInfo;
      avatarUrl = msg.sender.avatarUrl;
      initial = msg.sender.displayName[0].toUpperCase();
    } else if (widget.message is MessageInfo) {
      final msg = widget.message as MessageInfo;
      avatarUrl = msg.sender?.avatarUrl;
      initial = (msg.sender?.displayName ?? 'S')[0].toUpperCase();
    }

    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        gradient: isUser ? DS.primaryGradient : DS.secondaryGradient,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: (isUser
                    ? context.sparkleColors.brandPrimary
                    : context.sparkleColors.brandSecondary)
                .withValues(alpha: 0.2),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Center(
        child: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: isUser
                ? context.sparkleColors.brandPrimary
                : (isDark
                    ? context.sparkleColors.neutral200
                    : context.sparkleColors.brandPrimary),
            shape: BoxShape.circle,
          ),
          clipBehavior: Clip.antiAlias,
          child: avatarUrl != null
              ? Image.network(avatarUrl,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Center(child: Text(initial)),)
              : Center(
                  child: Text(initial,
                      style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: isUser ? Colors.white : Colors.white,),),),
        ),
      ),
    );
  }

  MarkdownStyleSheet _getMarkdownStyle(BuildContext context, bool isUser) =>
      MarkdownStyleSheet(
        p: TextStyle(
            color: isUser ? Colors.white : context.sparkleColors.textPrimary,
            fontSize: 16,
            height: 1.4,),
        h1: TextStyle(
            color: isUser ? Colors.white : context.sparkleColors.textPrimary,
            fontSize: 24,
            fontWeight: FontWeight.bold,),
        code: TextStyle(
            backgroundColor: isUser
                ? Colors.white.withValues(alpha: 0.2)
                : context.sparkleColors.surfaceTertiary,
            fontFamily: 'monospace',
            fontSize: 14,
            color:
                isUser ? Colors.white : context.sparkleColors.brandSecondary,),
        codeblockDecoration: BoxDecoration(
            color: isUser
                ? Colors.white.withValues(alpha: 0.1)
                : context.sparkleColors.surfaceTertiary,
            borderRadius: BorderRadius.circular(12),),
        a: TextStyle(
            color: isUser ? Colors.white : context.sparkleColors.brandPrimary,
            decoration: TextDecoration.underline,),
      );



  int? _calculateReasoningDuration(ChatMessageModel message) {
    if (message.reasoningSteps == null || message.reasoningSteps!.isEmpty) {
      return null;
    }

    // Calculate from first step to last completed step
    final firstStep = message.reasoningSteps!.first;
    final lastStep = message.reasoningSteps!.last;

    if (firstStep.createdAt != null && lastStep.completedAt != null) {
      return lastStep.completedAt!
          .difference(firstStep.createdAt!)
          .inMilliseconds;
    }

    // Fallback to summary parsing if available
    if (message.reasoningSummary != null) {
      final match =
          RegExp(r'(\d+(?:\.\d+)?)s').firstMatch(message.reasoningSummary!);
      if (match != null) {
        final seconds = double.tryParse(match.group(1)!);
        if (seconds != null) {
          return (seconds * 1000).toInt();
        }
      }
    }

    return null;
  }

  Widget _buildHeartAnimation() => TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.0, end: 1.0),
        duration: const Duration(milliseconds: 500),
        curve: Curves.elasticOut,
        builder: (context, value, child) => Transform.scale(
            scale: value,
            child: Icon(Icons.favorite, color: DS.error, size: 48, shadows: [
              Shadow(
                  blurRadius: 10,
                  color: DS.brandPrimary26,
                  offset: const Offset(0, 4),),
            ],),),
      );
}

class _MetaTag extends StatelessWidget {
  const _MetaTag({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 9,
            fontWeight: FontWeight.bold,
            color: color,
            fontFamily: 'monospace',
          ),
        ),
      );
}
