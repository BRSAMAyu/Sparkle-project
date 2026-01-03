import 'package:flutter/material.dart';

/// 快捷回复选项数据类
class QuickReply {

  const QuickReply({
    required this.id,
    required this.label,
    required this.message,
    this.icon,
    this.color,
  });
  final String id;
  final String label;
  final String message;
  final IconData? icon;
  final Color? color;
}

/// 快捷回复按钮组
///
/// 设计原则：
/// 1. 降低输入成本：常用问题一键发送
/// 2. 引导探索：帮助新用户了解 AI 能做什么
/// 3. 情境化：根据当前状态显示不同的快捷回复
class QuickReplyChips extends StatelessWidget {

  const QuickReplyChips({
    super.key,
    required this.onTap,
    this.enabled = true,
    this.customReplies,
  });
  final Function(String message) onTap;
  final bool enabled;
  final List<QuickReply>? customReplies;

  /// 默认快捷回复列表
  static const List<QuickReply> defaultReplies = [
    QuickReply(
      id: 'today_plan',
      label: '今天该做什么',
      message: '根据我的任务和计划，今天应该做什么？',
      icon: Icons.today,
      color: Color(0xFF2196F3),
    ),
    QuickReply(
      id: 'review_plan',
      label: '帮我安排复习',
      message: '帮我安排今天的复习计划，重点复习哪些知识点？',
      icon: Icons.schedule,
      color: Color(0xFF4CAF50),
    ),
    QuickReply(
      id: 'start_focus',
      label: '开始专注',
      message: '我想开始一个 25 分钟的专注学习',
      icon: Icons.timer,
      color: Color(0xFFFF9800),
    ),
    QuickReply(
      id: 'analyze_errors',
      label: '分析错题',
      message: '帮我分析最近的错题，找出薄弱环节',
      icon: Icons.analytics,
      color: Color(0xFFF44336),
    ),
    QuickReply(
      id: 'learning_progress',
      label: '学习进度',
      message: '查看我这周的学习进度和完成情况',
      icon: Icons.trending_up,
      color: Color(0xFF9C27B0),
    ),
  ];

  /// 错题相关的快捷回复
  static const List<QuickReply> errorBookReplies = [
    QuickReply(
      id: 'add_error',
      label: '添加错题',
      message: '我要添加一道错题',
      icon: Icons.add_circle_outline,
    ),
    QuickReply(
      id: 'review_errors',
      label: '开始复习',
      message: '开始复习今天的错题',
      icon: Icons.playlist_play,
    ),
    QuickReply(
      id: 'error_stats',
      label: '错题统计',
      message: '查看我的错题统计数据',
      icon: Icons.bar_chart,
    ),
    QuickReply(
      id: 'weak_subjects',
      label: '薄弱科目',
      message: '分析我的薄弱科目和高频错误类型',
      icon: Icons.warning_amber,
    ),
  ];

  /// 知识星图相关的快捷回复
  static const List<QuickReply> galaxyReplies = [
    QuickReply(
      id: 'explore_galaxy',
      label: '探索星图',
      message: '查看我的知识星图',
      icon: Icons.explore,
    ),
    QuickReply(
      id: 'add_knowledge',
      label: '添加知识点',
      message: '添加新的知识点到星图',
      icon: Icons.add_circle,
    ),
    QuickReply(
      id: 'find_gaps',
      label: '找知识盲区',
      message: '帮我找出知识星图中的薄弱环节',
      icon: Icons.search_off,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final replies = customReplies ?? defaultReplies;

    if (replies.isEmpty) {
      return const SizedBox.shrink();
    }

    return SizedBox(
      height: 44,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: replies.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final reply = replies[index];
          return _QuickReplyChip(
            reply: reply,
            enabled: enabled,
            onTap: () => onTap(reply.message),
          );
        },
      ),
    );
  }
}

/// 快捷回复单个按钮
class _QuickReplyChip extends StatelessWidget {

  const _QuickReplyChip({
    required this.reply,
    required this.enabled,
    required this.onTap,
  });
  final QuickReply reply;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = reply.color ?? theme.colorScheme.primary;

    return Material(
      color: color.withOpacity(0.1),
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        onTap: enabled ? onTap : null,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: color.withOpacity(0.3),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (reply.icon != null) ...[
                Icon(
                  reply.icon,
                  size: 18,
                  color: color,
                ),
                const SizedBox(width: 6),
              ],
              Text(
                reply.label,
                style: theme.textTheme.labelLarge?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 快捷回复网格视图（备选方案）
///
/// 适合需要展示更多选项的场景
class QuickReplyGrid extends StatelessWidget {

  const QuickReplyGrid({
    super.key,
    required this.onTap,
    required this.replies,
    this.crossAxisCount = 2,
  });
  final Function(String message) onTap;
  final List<QuickReply> replies;
  final int crossAxisCount;

  @override
  Widget build(BuildContext context) => GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        childAspectRatio: 2.5,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
      ),
      itemCount: replies.length,
      itemBuilder: (context, index) {
        final reply = replies[index];
        return _QuickReplyCard(
          reply: reply,
          onTap: () => onTap(reply.message),
        );
      },
    );
}

class _QuickReplyCard extends StatelessWidget {

  const _QuickReplyCard({
    required this.reply,
    required this.onTap,
  });
  final QuickReply reply;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = reply.color ?? theme.colorScheme.primary;

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                color.withOpacity(0.1),
                color.withOpacity(0.05),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (reply.icon != null)
                Icon(
                  reply.icon,
                  size: 28,
                  color: color,
                ),
              if (reply.icon != null) const SizedBox(height: 6),
              Text(
                reply.label,
                style: theme.textTheme.labelLarge?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w600,
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 快捷回复管理器
///
/// 根据上下文自动选择合适的快捷回复列表
class QuickReplyManager {
  /// 根据当前页面/场景获取快捷回复列表
  static List<QuickReply> getRepliesForContext(String context) {
    switch (context) {
      case 'error_book':
        return QuickReplyChips.errorBookReplies;
      case 'galaxy':
        return QuickReplyChips.galaxyReplies;
      case 'home':
      default:
        return QuickReplyChips.defaultReplies;
    }
  }

  /// 根据时间获取个性化问候语
  static String getGreeting() {
    final hour = DateTime.now().hour;
    if (hour < 6) {
      return '深夜还在学习，注意休息哦 🌙';
    } else if (hour < 12) {
      return '早上好！今天要学什么？☀️';
    } else if (hour < 14) {
      return '中午好！午休后继续加油 ☀️';
    } else if (hour < 18) {
      return '下午好！保持专注 📚';
    } else if (hour < 22) {
      return '晚上好！今晚的学习计划是？🌆';
    } else {
      return '夜深了，早点休息吧 🌙';
    }
  }
}
