import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:url_launcher/url_launcher.dart';

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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isUserMessage = message.role == MessageRole.user;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: GestureDetector(
        // 点击背景关闭
        onTap: () => Navigator.of(context).pop(),
        child: Container(
          color: Colors.black.withValues(alpha: 0.5),
          child: GestureDetector(
            // 阻止点击内容区域时关闭
            onTap: () {},
            child: SafeArea(
              child: Center(
                child: Container(
                  margin: const EdgeInsets.symmetric(
                    horizontal: DS.lg,
                    vertical: DS.xl * 2,
                  ),
                  constraints: BoxConstraints(
                    maxHeight: MediaQuery.of(context).size.height * 0.85,
                  ),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surface,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.3),
                        blurRadius: 20,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // 顶部工具栏
                      _buildHeader(context, isUserMessage, isDark),

                      // 内容区域（可滚动）
                      Flexible(
                        child: Hero(
                          tag: heroTag,
                          child: Material(
                            color: Colors.transparent,
                            child: SingleChildScrollView(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.lg,
                                vertical: DS.md,
                              ),
                              child: _buildContent(context, isUserMessage, isDark),
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
    );
  }

  Widget _buildHeader(BuildContext context, bool isUserMessage, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.lg,
        vertical: DS.md,
      ),
      decoration: BoxDecoration(
        color: isDark
            ? Colors.white.withValues(alpha: 0.05)
            : Colors.black.withValues(alpha: 0.02),
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
              color: isUserMessage ? DS.primaryBase : DS.secondaryBase,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isUserMessage ? Icons.person : Icons.smart_toy,
                  size: 16,
                  color: Colors.white,
                ),
                const SizedBox(width: 4),
                Text(
                  isUserMessage ? '我' : 'AI助手',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
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
              color: isDark ? Colors.white60 : Colors.black54,
              fontSize: 12,
            ),
          ),

          const Spacer(),

          // 关闭按钮
          IconButton(
            icon: const Icon(Icons.close, size: 20),
            onPressed: () => Navigator.of(context).pop(),
            tooltip: '关闭',
            visualDensity: VisualDensity.compact,
          ),
        ],
      ),
    );
  }

  Widget _buildContent(BuildContext context, bool isUserMessage, bool isDark) {
    if (message.content.isEmpty) {
      return Center(
        child: Text(
          '无内容',
          style: TextStyle(
            color: isDark ? Colors.white38 : Colors.black38,
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
          color: isDark ? Colors.white : Colors.black87,
        ),
      );
    }

    // AI消息使用Markdown渲染
    return MarkdownBody(
      data: message.content,
      selectable: true,
      styleSheet: MarkdownStyleSheet(
        p: TextStyle(
          fontSize: 16,
          height: 1.6,
          color: isDark ? Colors.white : Colors.black87,
        ),
        h1: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.bold,
          color: isDark ? Colors.white : Colors.black87,
          height: 1.4,
        ),
        h2: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
          color: isDark ? Colors.white : Colors.black87,
          height: 1.4,
        ),
        h3: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: isDark ? Colors.white : Colors.black87,
          height: 1.4,
        ),
        code: TextStyle(
          fontSize: 14,
          backgroundColor: isDark
              ? Colors.white.withValues(alpha: 0.1)
              : Colors.black.withValues(alpha: 0.05),
          color: DS.primaryBase,
          fontFamily: 'monospace',
        ),
        codeblockDecoration: BoxDecoration(
          color: isDark
              ? Colors.white.withValues(alpha: 0.05)
              : Colors.black.withValues(alpha: 0.03),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isDark
                ? Colors.white.withValues(alpha: 0.1)
                : Colors.black.withValues(alpha: 0.1),
          ),
        ),
        blockquote: TextStyle(
          color: isDark ? Colors.white70 : Colors.black54,
          fontStyle: FontStyle.italic,
        ),
        blockquoteDecoration: BoxDecoration(
          color: isDark
              ? Colors.white.withValues(alpha: 0.05)
              : Colors.black.withValues(alpha: 0.03),
          borderRadius: BorderRadius.circular(4),
          border: Border(
            left: BorderSide(
              color: DS.primaryBase,
              width: 3,
            ),
          ),
        ),
        listBullet: TextStyle(
          color: isDark ? Colors.white : Colors.black87,
        ),
        a: TextStyle(
          color: DS.primaryBase,
          decoration: TextDecoration.underline,
        ),
      ),
      onTapLink: (text, href, title) {
        if (href != null) {
          launchUrl(Uri.parse(href), mode: LaunchMode.externalApplication);
        }
      },
    );
  }

  Widget _buildActions(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? Colors.white.withValues(alpha: 0.05)
            : Colors.black.withValues(alpha: 0.02),
        borderRadius: const BorderRadius.vertical(
          bottom: Radius.circular(20),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          // 复制按钮
          _ActionButton(
            icon: Icons.copy,
            label: '复制',
            onPressed: () {
              Clipboard.setData(ClipboardData(text: message.content));
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('已复制到剪贴板'),
                  behavior: SnackBarBehavior.floating,
                  duration: Duration(seconds: 1),
                ),
              );
            },
          ),

          // 分享按钮（可选，预留）
          // _ActionButton(
          //   icon: Icons.share,
          //   label: '分享',
          //   onPressed: () {
          //     // TODO: 实现分享功能
          //   },
          // ),
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
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return InkWell(
      onTap: onPressed,
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
              color: isDark ? Colors.white70 : Colors.black54,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: isDark ? Colors.white70 : Colors.black54,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
