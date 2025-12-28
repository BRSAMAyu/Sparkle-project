import 'package:flutter/material.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

/// 空状态场景类型
enum EmptyStateType {
  noTasks, // 无任务
  noChats, // 无聊天记录
  noPlans, // 无计划
  noErrors, // 无错题
  noResults, // 无搜索结果
  general, // 通用空状态
}

/// 空状态组件
///
/// 用于显示列表为空、搜索无结果等场景
class EmptyState extends StatelessWidget {

  const EmptyState({
    super.key,
    this.type = EmptyStateType.general,
    this.title,
    this.description,
    this.icon,
    this.actionText,
    this.onAction,
    this.customAction,
    this.showIcon = true,
  });

  /// 无任务空状态
  factory EmptyState.noTasks({
    Key? key,
    VoidCallback? onCreateTask,
  }) => EmptyState(
      key: key,
      type: EmptyStateType.noTasks,
      title: '还没有任务',
      description: '创建您的第一个学习任务，开启高效学习之旅',
      icon: Icons.task_alt_rounded,
      actionText: '创建任务',
      onAction: onCreateTask,
    );

  /// 无聊天记录空状态
  factory EmptyState.noChats({
    Key? key,
    VoidCallback? onStartChat,
  }) => EmptyState(
      key: key,
      type: EmptyStateType.noChats,
      title: '我是你的 AI 导师 Sparkle',
      description: '有什么可以帮你？',
      icon: Icons.chat_bubble_outline_rounded,
      actionText: '开始对话',
      onAction: onStartChat,
    );

  /// 无计划空状态
  factory EmptyState.noPlans({
    Key? key,
    VoidCallback? onCreatePlan,
  }) => EmptyState(
      key: key,
      type: EmptyStateType.noPlans,
      title: '还没有学习计划',
      description: '制定学习计划，让AI帮您规划学习路线',
      icon: Icons.calendar_today_rounded,
      actionText: '创建计划',
      onAction: onCreatePlan,
    );

  /// 无错题空状态
  factory EmptyState.noErrors({
    Key? key,
  }) => EmptyState(
      key: key,
      type: EmptyStateType.noErrors,
      title: '太棒了！',
      description: '您还没有错题记录，继续保持',
      icon: Icons.emoji_events_rounded,
    );

  /// 无搜索结果空状态
  factory EmptyState.noResults({
    Key? key,
    String? searchQuery,
  }) => EmptyState(
      key: key,
      type: EmptyStateType.noResults,
      title: '没有找到结果',
      description: searchQuery != null ? '没有找到与"$searchQuery"相关的内容' : '请尝试其他搜索关键词',
      icon: Icons.search_off_rounded,
    );
  /// 空状态类型
  final EmptyStateType type;

  /// 标题
  final String? title;

  /// 描述
  final String? description;

  /// 图标
  final IconData? icon;

  /// 操作按钮文本
  final String? actionText;

  /// 操作按钮回调
  final VoidCallback? onAction;

  /// 自定义操作按钮
  final Widget? customAction;

  /// 是否显示图标
  final bool showIcon;

  String _getDefaultTitle() {
    switch (type) {
      case EmptyStateType.noTasks:
        return '还没有任务';
      case EmptyStateType.noChats:
        return '还没有对话';
      case EmptyStateType.noPlans:
        return '还没有学习计划';
      case EmptyStateType.noErrors:
        return '太棒了！';
      case EmptyStateType.noResults:
        return '没有找到结果';
      case EmptyStateType.general:
        return '暂无数据';
    }
  }

  String _getDefaultDescription() {
    switch (type) {
      case EmptyStateType.noTasks:
        return '创建您的第一个学习任务';
      case EmptyStateType.noChats:
        return '开始与AI助手对话';
      case EmptyStateType.noPlans:
        return '制定您的学习计划';
      case EmptyStateType.noErrors:
        return '您还没有错题记录';
      case EmptyStateType.noResults:
        return '请尝试其他搜索关键词';
      case EmptyStateType.general:
        return '这里还没有内容';
    }
  }

  IconData _getDefaultIcon() {
    switch (type) {
      case EmptyStateType.noTasks:
        return Icons.task_alt_rounded;
      case EmptyStateType.noChats:
        return Icons.chat_bubble_outline_rounded;
      case EmptyStateType.noPlans:
        return Icons.calendar_today_rounded;
      case EmptyStateType.noErrors:
        return Icons.emoji_events_rounded;
      case EmptyStateType.noResults:
        return Icons.search_off_rounded;
      case EmptyStateType.general:
        return Icons.inbox_rounded;
    }
  }

  Color _getIconColor() {
    switch (type) {
      case EmptyStateType.noErrors:
        return AppDesignTokens.success;
      case EmptyStateType.noResults:
        return AppDesignTokens.warning;
      default:
        return AppDesignTokens.primaryBase;
    }
  }

  LinearGradient _getIconGradient() {
    switch (type) {
      case EmptyStateType.noErrors:
        return AppDesignTokens.successGradient;
      case EmptyStateType.noResults:
        return AppDesignTokens.warningGradient;
      default:
        return AppDesignTokens.primaryGradient;
    }
  }

  @override
  Widget build(BuildContext context) => Center(
      child: Padding(
        padding: const EdgeInsets.all(AppDesignTokens.spacing32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            // 图标
            if (showIcon) _buildIcon(),
            if (showIcon) const SizedBox(height: AppDesignTokens.spacing24),
            // 标题
            Text(
              title ?? _getDefaultTitle(),
              style: TextStyle(
                fontSize: AppDesignTokens.fontSize2xl,
                fontWeight: AppDesignTokens.fontWeightBold,
                color: context.colors.textPrimary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppDesignTokens.spacing12),
            // 描述
            Text(
              description ?? _getDefaultDescription(),
              style: const TextStyle(
                fontSize: AppDesignTokens.fontSizeBase,
                color: AppDesignTokens.neutral600,
                height: AppDesignTokens.lineHeightNormal,
              ),
              textAlign: TextAlign.center,
            ),
            // 操作按钮
            if (customAction != null || (actionText != null && onAction != null)) ...[
              const SizedBox(height: AppDesignTokens.spacing32),
              customAction ??
                  CustomButton.primary(
                    text: actionText!,
                    onPressed: onAction,
                    icon: _getActionIcon(),
                  ),
            ],
          ],
        ),
      ),
    );

  Widget _buildIcon() => Container(
      width: 120.0,
      height: 120.0,
      decoration: BoxDecoration(
        gradient: _getIconGradient(),
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: _getIconColor().withValues(alpha: 0.2),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Icon(
        icon ?? _getDefaultIcon(),
        size: AppDesignTokens.iconSize3xl,
        color: DS.brandPrimary,
      ),
    );

  IconData? _getActionIcon() {
    switch (type) {
      case EmptyStateType.noTasks:
        return Icons.add_rounded;
      case EmptyStateType.noChats:
        return Icons.chat_rounded;
      case EmptyStateType.noPlans:
        return Icons.add_rounded;
      default:
        return null;
    }
  }
}

/// 紧凑型空状态
///
/// 用于列表中的空状态展示，占用空间更小
class CompactEmptyState extends StatelessWidget {

  const CompactEmptyState({
    required this.message, super.key,
    this.icon,
    this.onAction,
    this.actionText,
  });
  final String message;
  final IconData? icon;
  final VoidCallback? onAction;
  final String? actionText;

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(AppDesignTokens.spacing24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Container(
              width: 64.0,
              height: 64.0,
              decoration: const BoxDecoration(
                color: AppDesignTokens.neutral100,
                shape: BoxShape.circle,
              ),
              child: Icon(
                icon,
                size: AppDesignTokens.iconSizeLg,
                color: AppDesignTokens.neutral400,
              ),
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
          ],
          Text(
            message,
            style: const TextStyle(
              fontSize: AppDesignTokens.fontSizeBase,
              color: AppDesignTokens.neutral600,
            ),
            textAlign: TextAlign.center,
          ),
          if (onAction != null && actionText != null) ...[
            const SizedBox(height: AppDesignTokens.spacing16),
            CustomButton.text(
              text: actionText!,
              onPressed: onAction,
              size: ButtonSize.small,
            ),
          ],
        ],
      ),
    );
}
