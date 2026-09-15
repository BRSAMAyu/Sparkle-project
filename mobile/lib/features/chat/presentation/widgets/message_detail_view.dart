import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';

/// 消息详情放大视图
/// 全屏显示消息内容，支持滚动和复制
class MessageDetailView extends StatefulWidget {
  const MessageDetailView({
    required this.message,
    required this.heroTag,
    super.key,
  });

  final ChatMessageModel message;
  final String heroTag;

  @override
  State<MessageDetailView> createState() => _MessageDetailViewState();
}

class _MessageDetailViewState extends State<MessageDetailView> {
  final ScrollController _scrollController = ScrollController();
  bool _hasScrolledToBottom = false;
  bool _canScroll = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_updateScrollAffordance);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_updateScrollAffordance);
    _scrollController.dispose();
    super.dispose();
  }

  void _updateScrollAffordance() {
    if (!_scrollController.hasClients) {
      return;
    }
    final position = _scrollController.position;
    final canScroll = position.maxScrollExtent > 1;
    final hasScrolledToBottom =
        !canScroll || position.pixels >= position.maxScrollExtent - 1;
    if (canScroll != _canScroll ||
        hasScrolledToBottom != _hasScrolledToBottom) {
      setState(() {
        _canScroll = canScroll;
        _hasScrolledToBottom = hasScrolledToBottom;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isUserMessage = widget.message.role == MessageRole.user;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _updateScrollAffordance();
      }
    });

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          // Backdrop blur
          Positioned.fill(
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
              child: Container(
                color: DS.overlay30.withValues(alpha: 0.4),
              ),
            ),
          ),
          GestureDetector(
            // Tap background to close
            onTap: () => Navigator.of(context).pop(),
            onVerticalDragEnd: (details) {
              // Only dismiss when at scroll top with sufficient velocity
              final velocity = details.primaryVelocity ?? 0;
              final atTop = !_scrollController.hasClients ||
                  _scrollController.offset <= 0;
              if (atTop && velocity > 300) {
                Navigator.of(context).pop();
              }
            },
            child: ColoredBox(
              color: Colors.transparent,
              child: GestureDetector(
                // Prevent content area from closing on tap
                onTap: () {},
                child: SafeArea(
                  child: Center(
                    child: Container(
                      margin: const EdgeInsets.symmetric(
                        horizontal: DS.md,
                        vertical: DS.lg,
                      ),
                      constraints: BoxConstraints(
                        maxHeight: MediaQuery.of(context).size.height * 0.88,
                      ),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surface,
                        borderRadius: BorderRadius.circular(DS.radius20),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.15),
                            blurRadius: 30,
                            offset: const Offset(0, 15),
                          ),
                        ],
                        border: Border.all(
                          color: DS.borderSubtle.withValues(alpha: 0.5),
                        ),
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // Header
                          _buildHeader(context, isUserMessage),

                          // Scrollable content
                          Flexible(
                            child: Hero(
                              tag: widget.heroTag,
                              child: Material(
                                color: Colors.transparent,
                                child: Stack(
                                  children: [
                                    NotificationListener<ScrollNotification>(
                                      onNotification: (_) {
                                        _updateScrollAffordance();
                                        return false;
                                      },
                                      child: SingleChildScrollView(
                                        controller: _scrollController,
                                        padding: const EdgeInsets.only(
                                          left: DS.lg,
                                          right: DS.lg,
                                          top: DS.md,
                                          bottom: 28,
                                        ),
                                        child: _buildContent(
                                          context,
                                          isUserMessage,
                                        ),
                                      ),
                                    ),
                                    // Bottom gradient — visible until scrolled to bottom
                                    if (_canScroll && !_hasScrolledToBottom)
                                      Positioned(
                                        bottom: 0,
                                        left: 0,
                                        right: 0,
                                        height: 32,
                                        child: DecoratedBox(
                                          decoration: BoxDecoration(
                                            gradient: LinearGradient(
                                              begin: Alignment.topCenter,
                                              end: Alignment.bottomCenter,
                                              colors: [
                                                Theme.of(context)
                                                    .colorScheme
                                                    .surface
                                                    .withValues(alpha: 0),
                                                Theme.of(context)
                                                    .colorScheme
                                                    .surface,
                                              ],
                                            ),
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            ),
                          ),

                          // Bottom actions
                          _buildActions(context),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context, bool isUserMessage) {
    final roleColor = isUserMessage ? DS.primaryBase : DS.secondaryBase;
    final roleTextColor = DS.onBrandPrimary;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.lg,
        vertical: DS.md,
      ),
      decoration: BoxDecoration(
        color: DS.surfaceTertiary.withValues(alpha: 0.4),
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(DS.radius20),
        ),
      ),
      child: Row(
        children: [
          // Role badge
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.sm,
              vertical: DS.xs,
            ),
            decoration: BoxDecoration(
              color: roleColor,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isUserMessage ? Icons.person : Icons.smart_toy,
                  size: 16,
                  color: roleTextColor,
                ),
                const SizedBox(width: 4),
                Text(
                  isUserMessage
                      ? context.l10n.chatLabelMe
                      : context.l10n.chatLabelAssistant,
                  style: TextStyle(
                    color: roleTextColor,
                    fontSize: 12,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(width: DS.sm),

          // Timestamp
          Text(
            DateFormat('MM/dd HH:mm').format(widget.message.createdAt),
            style: TextStyle(
              color: DS.textSecondary,
              fontSize: 12,
            ),
          ),

          const SizedBox(width: DS.sm),

          // Character count
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.sm,
              vertical: DS.xs,
            ),
            decoration: BoxDecoration(
              color: DS.surfaceTertiary.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '${widget.message.content.length} ${context.l10n.chatCharacters}',
              style: TextStyle(
                color: DS.textTertiary,
                fontSize: 11,
              ),
            ),
          ),

          const Spacer(),

          // Close button
          Semantics(
            button: true,
            label: 'Chat message detail view control 2',
            child: SparkleIconButton(
              icon: const Icon(Icons.close, size: DS.iconSizeSm),
              onPressed: () => Navigator.of(context).pop(),
              semanticLabel: context.l10n.close,
              variant: ButtonVariant.ghost,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(BuildContext context, bool isUserMessage) {
    if (widget.message.content.isEmpty) {
      return Center(
        child: Text(
          context.l10n.chatNoContent,
          style: TextStyle(
            color: DS.textTertiary,
            fontSize: 14,
          ),
        ),
      );
    }

    if (isUserMessage) {
      return SelectableText(
        widget.message.content,
        style: TextStyle(
          fontSize: 16,
          height: 1.6,
          color: DS.textPrimary,
          fontFamilyFallback: sparkleFontFallback,
        ),
      );
    }

    return SparkleMarkdown(
      content: widget.message.content,
      textColor: DS.textPrimary,
      codeBackgroundColor: DS.surfaceTertiary.withValues(alpha: 0.35),
      linkColor: DS.primaryBase,
      selectable: true,
      contentRole: SparkleMarkdownRole.chatBubble,
    );
  }

  Widget _buildActions(BuildContext context) {
    final charCount = widget.message.content.length;
    final wordCount = widget.message.content.trim().isEmpty
        ? 0
        : widget.message.content.trim().split(RegExp(r'\s+')).length;

    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.surfaceTertiary.withValues(alpha: 0.4),
        borderRadius: const BorderRadius.vertical(
          bottom: Radius.circular(DS.radius20),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.only(bottom: DS.sm),
            child: Text(
              '$charCount ${context.l10n.chatCharacters} · $wordCount ${context.l10n.chatWords}',
              style: TextStyle(
                fontSize: 12,
                color: DS.textTertiary,
              ),
            ),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _ActionButton(
                icon: Icons.copy,
                label: context.l10n.chatCopy,
                onPressed: () async {
                  await Clipboard.setData(
                    ClipboardData(text: widget.message.content),
                  );
                  if (!context.mounted) return;
                  AppFeedback.success(
                    context,
                    context.l10n.chatCopiedToClipboard,
                  );
                },
              ),
              _ActionButton(
                icon: Icons.share,
                label: context.l10n.chatShare,
                onPressed: () async {
                  await SharePlus.instance.share(
                    ShareParams(text: widget.message.content),
                  );
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final Future<void> Function() onPressed;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: 'Chat message detail view control 3',
        child: InkWell(
          onTap: () async {
            await SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
            await onPressed();
          },
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.lg,
              vertical: DS.sm,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  icon,
                  size: 24,
                  color: DS.textSecondary,
                ),
                const SizedBox(height: 4),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 12,
                    color: DS.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}
