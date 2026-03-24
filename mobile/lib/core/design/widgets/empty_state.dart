import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

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
    this.searchQuery,
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
  }) =>
      EmptyState(
        key: key,
        type: EmptyStateType.noTasks,
        icon: Icons.task_alt_rounded,
        onAction: onCreateTask,
      );

  /// 无聊天记录空状态
  factory EmptyState.noChats({
    Key? key,
    VoidCallback? onStartChat,
  }) =>
      EmptyState(
        key: key,
        type: EmptyStateType.noChats,
        icon: Icons.chat_bubble_outline_rounded,
        onAction: onStartChat,
      );

  /// 无计划空状态
  factory EmptyState.noPlans({
    Key? key,
    VoidCallback? onCreatePlan,
  }) =>
      EmptyState(
        key: key,
        type: EmptyStateType.noPlans,
        icon: Icons.calendar_today_rounded,
        onAction: onCreatePlan,
      );

  /// 无错题空状态
  factory EmptyState.noErrors({
    Key? key,
  }) =>
      EmptyState(
        key: key,
        type: EmptyStateType.noErrors,
        icon: Icons.emoji_events_rounded,
      );

  /// 无搜索结果空状态
  factory EmptyState.noResults({
    Key? key,
    String? searchQuery,
  }) =>
      EmptyState(
        key: key,
        type: EmptyStateType.noResults,
        icon: Icons.search_off_rounded,
        searchQuery: searchQuery,
      );

  /// 空状态类型
  final EmptyStateType type;

  /// 标题
  final String? title;

  /// 描述
  final String? description;

  /// 搜索关键词
  final String? searchQuery;

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

  String _getDefaultTitle(BuildContext context) {
    final l10n = context.l10n;
    switch (type) {
      case EmptyStateType.noTasks:
        return l10n.emptyStateNoTasksTitle;
      case EmptyStateType.noChats:
        return l10n.emptyStateNoChatsTitle;
      case EmptyStateType.noPlans:
        return l10n.emptyStateNoPlansTitle;
      case EmptyStateType.noErrors:
        return l10n.emptyStateNoErrorsTitle;
      case EmptyStateType.noResults:
        return l10n.emptyStateNoResultsTitle;
      case EmptyStateType.general:
        return l10n.emptyStateGeneralTitle;
    }
  }

  String _getDefaultDescription(BuildContext context) {
    final l10n = context.l10n;
    switch (type) {
      case EmptyStateType.noTasks:
        return l10n.emptyStateNoTasksDescription;
      case EmptyStateType.noChats:
        return l10n.emptyStateNoChatsDescription;
      case EmptyStateType.noPlans:
        return l10n.emptyStateNoPlansDescription;
      case EmptyStateType.noErrors:
        return l10n.emptyStateNoErrorsDescription;
      case EmptyStateType.noResults:
        return searchQuery != null
            ? l10n.emptyStateNoResultsQuery(searchQuery!)
            : l10n.emptyStateNoResultsDescription;
      case EmptyStateType.general:
        return l10n.emptyStateGeneralDescription;
    }
  }

  String? _getDefaultActionText(BuildContext context) {
    final l10n = context.l10n;
    switch (type) {
      case EmptyStateType.noTasks:
        return l10n.taskAddNew;
      case EmptyStateType.noChats:
        return l10n.emptyStateStartChatAction;
      case EmptyStateType.noPlans:
        return l10n.emptyStateCreatePlanAction;
      case EmptyStateType.noErrors:
      case EmptyStateType.noResults:
      case EmptyStateType.general:
        return null;
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
        return DS.success;
      case EmptyStateType.noResults:
        return DS.warning;
      default:
        return DS.primaryBase;
    }
  }

  LinearGradient _getIconGradient() {
    switch (type) {
      case EmptyStateType.noErrors:
        return DS.successGradient;
      case EmptyStateType.noResults:
        return DS.warningGradient;
      default:
        return DS.primaryGradient;
    }
  }

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing32),
          child: Semantics(
            container: true,
            liveRegion: true,
            label: title ?? _getDefaultTitle(context),
            value: description ?? _getDefaultDescription(context),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (showIcon)
                    SparkleAttentionPulse(
                      active: !context.reduceMotion,
                      scaleRange: 0.014,
                      glowColor: _getIconColor(),
                      child: _buildIcon(),
                    ),
                  if (showIcon) const SizedBox(height: DS.spacing24),
                  Text(
                    title ?? _getDefaultTitle(context),
                    style: TextStyle(
                      fontSize: DS.fontSize2xl,
                      fontWeight: DS.fontWeightBold,
                      color: context.colors.textPrimary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: DS.spacing12),
                  Text(
                    description ?? _getDefaultDescription(context),
                    style: TextStyle(
                      fontSize: DS.fontSizeBase,
                      color: context.colors.textSecondary,
                      height: DS.lineHeightNormal,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  if (customAction != null ||
                      ((actionText ?? _getDefaultActionText(context)) != null &&
                          onAction != null)) ...[
                    const SizedBox(height: DS.spacing32),
                    customAction ??
                        CustomButton.primary(
                          text: actionText ?? _getDefaultActionText(context)!,
                          onPressed: onAction,
                          icon: _getActionIcon(),
                        ),
                  ],
                ],
              ),
            ),
          ),
        ),
      );

  Widget _buildIcon() => SizedBox(
        width: 128.0,
        height: 128.0,
        child: Stack(
          alignment: Alignment.center,
          children: [
            Positioned(
              top: 8,
              right: 10,
              child: Container(
                width: 18,
                height: 18,
                decoration: BoxDecoration(
                  color: _getIconColor().withValues(alpha: 0.18),
                  shape: BoxShape.circle,
                ),
              ),
            ),
            Positioned(
              bottom: 10,
              left: 6,
              child: Container(
                width: 14,
                height: 14,
                decoration: BoxDecoration(
                  color: _getIconColor().withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                ),
              ),
            ),
            Container(
              width: 108,
              height: 108,
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
            ),
            Container(
              width: 84,
              height: 84,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.12),
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.22),
                ),
              ),
              child: Icon(
                icon ?? _getDefaultIcon(),
                size: DS.iconSize3xl,
                color: DS.brandPrimaryConst,
              ),
            ),
          ],
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
    required this.message,
    super.key,
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
        padding: const EdgeInsets.all(DS.spacing24),
        child: Semantics(
          container: true,
          label: message,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Container(
                  width: 64.0,
                  height: 64.0,
                  decoration: BoxDecoration(
                    color: DS.neutral100,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    icon,
                    size: DS.iconSizeLg,
                    color: context.colors.textSecondary,
                  ),
                ),
                const SizedBox(height: DS.spacing16),
              ],
              Text(
                message,
                style: TextStyle(
                  fontSize: DS.fontSizeBase,
                  color: context.colors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
              if (onAction != null && actionText != null) ...[
                const SizedBox(height: DS.spacing16),
                CustomButton.text(
                  text: actionText!,
                  onPressed: onAction,
                  size: CustomButtonSize.small,
                ),
              ],
            ],
          ),
        ),
      );
}
