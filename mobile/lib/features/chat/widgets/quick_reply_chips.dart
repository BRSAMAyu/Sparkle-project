import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';

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
    required this.onTap,
    super.key,
    this.enabled = true,
    this.customReplies,
  });
  final ValueChanged<String> onTap;
  final bool enabled;
  final List<QuickReply>? customReplies;

  /// 默认快捷回复列表
  static List<QuickReply> get defaultReplies {
    final l10n = I18nService.instance.l10n;
    return [
      QuickReply(
        id: 'today_plan',
        label: l10n.quickReplyTodayPlanLabel,
        message: l10n.quickReplyTodayPlanMessage,
        icon: Icons.today,
      ),
      QuickReply(
        id: 'review_plan',
        label: l10n.quickReplyReviewPlanLabel,
        message: l10n.quickReplyReviewPlanMessage,
        icon: Icons.schedule,
      ),
      QuickReply(
        id: 'start_focus',
        label: l10n.quickReplyStartFocusLabel,
        message: l10n.quickReplyStartFocusMessage,
        icon: Icons.timer,
      ),
      QuickReply(
        id: 'analyze_errors',
        label: l10n.quickReplyAnalyzeErrorsLabel,
        message: l10n.quickReplyAnalyzeErrorsMessage,
        icon: Icons.analytics,
      ),
      QuickReply(
        id: 'learning_progress',
        label: l10n.quickReplyLearningProgressLabel,
        message: l10n.quickReplyLearningProgressMessage,
        icon: Icons.trending_up,
      ),
    ];
  }

  /// 错题相关的快捷回复
  static List<QuickReply> get errorBookReplies {
    final l10n = I18nService.instance.l10n;
    return [
      QuickReply(
        id: 'add_error',
        label: l10n.quickReplyAddErrorLabel,
        message: l10n.quickReplyAddErrorMessage,
        icon: Icons.add_circle_outline,
      ),
      QuickReply(
        id: 'review_errors',
        label: l10n.quickReplyReviewErrorsLabel,
        message: l10n.quickReplyReviewErrorsMessage,
        icon: Icons.playlist_play,
      ),
      QuickReply(
        id: 'error_stats',
        label: l10n.quickReplyErrorStatsLabel,
        message: l10n.quickReplyErrorStatsMessage,
        icon: Icons.bar_chart,
      ),
      QuickReply(
        id: 'weak_subjects',
        label: l10n.quickReplyWeakSubjectsLabel,
        message: l10n.quickReplyWeakSubjectsMessage,
        icon: Icons.warning_amber,
      ),
    ];
  }

  /// 知识星图相关的快捷回复
  static List<QuickReply> get galaxyReplies {
    final l10n = I18nService.instance.l10n;
    return [
      QuickReply(
        id: 'explore_galaxy',
        label: l10n.quickReplyExploreGalaxyLabel,
        message: l10n.quickReplyExploreGalaxyMessage,
        icon: Icons.explore,
      ),
      QuickReply(
        id: 'add_knowledge',
        label: l10n.quickReplyAddKnowledgeLabel,
        message: l10n.quickReplyAddKnowledgeMessage,
        icon: Icons.add_circle,
      ),
      QuickReply(
        id: 'find_gaps',
        label: l10n.quickReplyFindGapsLabel,
        message: l10n.quickReplyFindGapsMessage,
        icon: Icons.search_off,
      ),
    ];
  }

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
    final color = reply.color ?? _resolveReplyColor(reply, theme);

    return Material(
      color: color.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        onTap: enabled ? onTap : null,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8 + DS.spacing6,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: color.withValues(alpha: 0.3),
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
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _resolveReplyColor(QuickReply reply, ThemeData theme) {
    switch (reply.id) {
      case 'today_plan':
        return DS.info;
      case 'review_plan':
        return DS.success;
      case 'start_focus':
        return DS.warning;
      case 'analyze_errors':
        return DS.error;
      case 'learning_progress':
        return DS.prismPurple;
      default:
        return theme.colorScheme.primary;
    }
  }
}

/// 快捷回复网格视图（备选方案）
///
/// 适合需要展示更多选项的场景
class QuickReplyGrid extends StatelessWidget {
  const QuickReplyGrid({
    required this.onTap,
    required this.replies,
    super.key,
    this.crossAxisCount = 2,
  });
  final ValueChanged<String> onTap;
  final List<QuickReply> replies;
  final int crossAxisCount;

  @override
  Widget build(BuildContext context) => GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.all(DS.spacing16),
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
          padding: const EdgeInsets.all(DS.spacing12),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                color.withValues(alpha: 0.1),
                color.withValues(alpha: 0.05),
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
                  fontWeight: DS.fontWeightSemibold,
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
    final l10n = I18nService.instance.l10n;
    final hour = DateTime.now().hour;
    if (hour < 6) {
      return l10n.quickReplyGreetingLateNight;
    } else if (hour < 12) {
      return l10n.quickReplyGreetingMorning;
    } else if (hour < 14) {
      return l10n.quickReplyGreetingNoon;
    } else if (hour < 18) {
      return l10n.quickReplyGreetingAfternoon;
    } else if (hour < 22) {
      return l10n.quickReplyGreetingEvening;
    } else {
      return l10n.quickReplyGreetingNight;
    }
  }
}
