import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';

/// 消息详情放大视图
/// 全屏显示消息内容，支持滚动和复制
class MessageDetailView extends StatelessWidget {
  const MessageDetailView({
    required this.message,
    required this.heroTag,
    super.key,
  });

  final ChatMessageModel message;
  final String heroTag;

  @override
  Widget build(BuildContext context) {
    final isUserMessage = message.role == MessageRole.user;

    return Scaffold(
      backgroundColor: DS.overlay30.withValues(alpha: 0),
      body: Dismissible(
        key: Key('message_detail_${message.id}'),
        direction: DismissDirection.vertical,
        onDismissed: (_) => Navigator.of(context).pop(),
        child: Semantics(
          button: true,
          label: 'Chat message detail view control 1',
          child: GestureDetector(
            // 点击背景关闭
            onTap: () => Navigator.of(context).pop(),
            child: ColoredBox(
              color: DS.textPrimary.withValues(alpha: 0.5),
              child: GestureDetector(
                // 阻止点击内容区域时关闭
                onTap: () {},
                child: SafeArea(
                  child: Center(
                    child: Container(
                      margin: const EdgeInsets.symmetric(
                        horizontal: DS.md,
                        vertical: DS.lg,
                      ),
                      constraints: BoxConstraints(
                        maxHeight: MediaQuery.of(context).size.height * 0.92,
                      ),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surface,
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [
                          BoxShadow(
                            color: DS.textPrimary.withValues(alpha: 0.3),
                            blurRadius: 20,
                            offset: const Offset(0, 10),
                          ),
                        ],
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // 顶部工具栏
                          _buildHeader(context, isUserMessage),

                          // 内容区域（可滚动）
                          Flexible(
                            child: Hero(
                              tag: heroTag,
                              child: Material(
                                color: DS.overlay30.withValues(alpha: 0),
                                child: SingleChildScrollView(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: DS.lg,
                                    vertical: DS.md,
                                  ),
                                  child: _buildContent(context, isUserMessage),
                                ),
                              ),
                            ),
                          ),

                          // 底部操作栏
                          _buildActions(context),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
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
        color: DS.surfaceTertiary.withValues(alpha: 0.35),
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(20),
        ),
      ),
      child: Row(
        children: [
          // 发送者标识
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

          // 时间戳
          Text(
            DateFormat('MM/dd HH:mm').format(message.createdAt),
            style: TextStyle(
              color: DS.textSecondary,
              fontSize: 12,
            ),
          ),

          const SizedBox(width: DS.sm),

          // 字数统计
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
              '${message.content.length} ${context.l10n.chatCharacters}',
              style: TextStyle(
                color: DS.textTertiary,
                fontSize: 11,
              ),
            ),
          ),

          const Spacer(),

          // 关闭按钮
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
    if (message.content.isEmpty) {
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

    // 用户消息使用纯文本
    if (isUserMessage) {
      return SelectableText(
        message.content,
        style: TextStyle(
          fontSize: 16,
          height: 1.6,
          color: DS.textPrimary,
          fontFamilyFallback: sparkleFontFallback,
        ),
      );
    }

    return SparkleMarkdown(
      content: message.content,
      textColor: DS.textPrimary,
      codeBackgroundColor: DS.surfaceTertiary.withValues(alpha: 0.35),
      linkColor: DS.primaryBase,
      selectable: true,
      contentRole: SparkleMarkdownRole.chatBubble,
    );
  }

  Widget _buildActions(BuildContext context) {
    final charCount = message.content.length;
    final wordCount = message.content.trim().isEmpty
        ? 0
        : message.content.trim().split(RegExp(r'\s+')).length;

    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.surfaceTertiary.withValues(alpha: 0.35),
        borderRadius: const BorderRadius.vertical(
          bottom: Radius.circular(20),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 字数统计
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
          // 操作按钮
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              // 复制按钮
              _ActionButton(
                icon: Icons.copy,
                label: context.l10n.chatCopy,
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: message.content));
                  if (!context.mounted) return;
                  AppFeedback.success(
                    context,
                    context.l10n.chatCopiedToClipboard,
                  );
                },
              ),

              // 分享按钮
              _ActionButton(
                icon: Icons.share,
                label: context.l10n.chatShare,
                onPressed: () async {
                  await SharePlus.instance.share(
                    ShareParams(text: message.content),
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
          onTap: () => unawaited(onPressed()),
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
