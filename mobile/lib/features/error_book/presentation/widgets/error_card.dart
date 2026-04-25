import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/presentation/widgets/subject_chips.dart';

typedef KnowledgeNodeTap = void Function(String nodeId, double? masteryDelta);

/// 错题卡片组件
///
/// 设计原则：
/// 1. 信息层次清晰：题目摘要 > 状态标签 > 元信息
/// 2. 交互明确：整卡可点击查看详情，左滑删除
/// 3. 视觉反馈：掌握度用进度条和颜色体现
class ErrorCard extends StatelessWidget {
  const ErrorCard({
    required this.error,
    super.key,
    this.onTap,
    this.onDelete,
    this.onKnowledgeNodeTap,
    this.showReviewStatus = true,
  });
  final ErrorRecord error;
  final VoidCallback? onTap;
  final VoidCallback? onDelete;
  final KnowledgeNodeTap? onKnowledgeNodeTap;
  final bool showReviewStatus;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final now = DateTime.now();
    final needReview =
        error.nextReviewAt != null && error.nextReviewAt!.isBefore(now);
    final affectedNode = _affectedKnowledgeLink(error);

    return Dismissible(
      key: Key(error.id),
      direction: onDelete != null
          ? DismissDirection.endToStart
          : DismissDirection.none,
      confirmDismiss: onDelete != null
          ? (_) async => showDialog<bool>(
                context: context,
                builder: (context) => AlertDialog(
                  title: Text(context.l10n.errorBookDeleteConfirmTitle),
                  content: Text(context.l10n.errorBookDeleteConfirmMessage),
                  actions: [
                    SparkleButton.ghost(
                      onPressed: () => Navigator.of(context).pop(false),
                      label: context.l10n.cancel,
                    ),
                    SparkleButton(
                      onPressed: () => Navigator.of(context).pop(true),
                      variant: ButtonVariant.destructive,
                      label: context.l10n.commonDelete,
                    ),
                  ],
                ),
              )
          : null,
      onDismissed: (_) => onDelete?.call(),
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: DS.spacing16),
        color: DS.semanticError,
        child: Icon(Icons.delete, color: DS.onBrandPrimary),
      ),
      child: Card(
        margin: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () {
            unawaited(
              SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
            );
            onTap?.call();
          },
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 头部：科目标签 + 状态标签
                Row(
                  children: [
                    SubjectChip(subjectCode: error.subject, compact: true),
                    const SizedBox(width: DS.spacing8),
                    if (error.chapter != null && error.chapter!.isNotEmpty)
                      Expanded(
                        child: Text(
                          error.chapter!,
                          style: theme.textTheme.labelSmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    const Spacer(),
                    if (needReview && showReviewStatus)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.error.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(
                            color:
                                theme.colorScheme.error.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Text(
                          context.l10n.errorBookTabNeedReview,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: DS.fontWeightMedium,
                            color: theme.colorScheme.error,
                          ),
                        ),
                      ),
                    if (error.difficulty != null)
                      Padding(
                        padding: const EdgeInsets.only(left: DS.spacing8),
                        child: Row(
                          children: List.generate(
                            5,
                            (index) => Icon(
                              index < error.difficulty!
                                  ? Icons.star
                                  : Icons.star_border,
                              size: 12,
                              color: DS.semanticWarning,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: DS.spacing12),

                // 题目摘要（限制3行）
                Text(
                  error.questionText,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightMedium,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
                if (affectedNode != null) ...[
                  const SizedBox(height: DS.spacing10),
                  _AffectedKnowledgeTag(
                    link: affectedNode,
                    masteryDelta: error.masteryDelta,
                    onTap: onKnowledgeNodeTap == null
                        ? null
                        : () {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.selection,
                              ),
                            );
                            onKnowledgeNodeTap!(
                              affectedNode.nodeId,
                              error.masteryDelta,
                            );
                          },
                  ),
                ],
                const SizedBox(height: DS.spacing12),

                // 掌握度进度条
                if (showReviewStatus) ...[
                  Row(
                    children: [
                      Expanded(
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: error.masteryLevel,
                            minHeight: 6,
                            backgroundColor:
                                theme.colorScheme.surfaceContainerHighest,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              _getMasteryColor(error.masteryLevel),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      Text(
                        '${(error.masteryLevel * 100).toInt()}%',
                        style: theme.textTheme.labelSmall?.copyWith(
                          fontWeight: DS.fontWeightSemibold,
                          color: _getMasteryColor(error.masteryLevel),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing12),
                ],

                // 底部元信息
                Wrap(
                  spacing: DS.spacing16,
                  runSpacing: DS.spacing6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    _MetaInfoItem(
                      icon: Icons.replay,
                      label: context.l10n.errorBookReviewCount(
                        error.reviewCount,
                      ),
                      color: theme.colorScheme.onSurfaceVariant,
                      textStyle: theme.textTheme.labelSmall,
                    ),
                    _MetaInfoItem(
                      icon: Icons.access_time,
                      label: _formatTime(context, error.createdAt),
                      color: theme.colorScheme.onSurfaceVariant,
                      textStyle: theme.textTheme.labelSmall,
                    ),
                    if (error.latestAnalysis != null)
                      _MetaInfoItem(
                        icon: Icons.psychology,
                        label: context.l10n.errorBookAIAnalyzed,
                        color: theme.colorScheme.primary,
                        textStyle: theme.textTheme.labelSmall?.copyWith(
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  KnowledgeLink? _affectedKnowledgeLink(ErrorRecord error) {
    final affectedNodeId = error.affectedNodeId;
    if (affectedNodeId != null && affectedNodeId.isNotEmpty) {
      for (final link in error.knowledgeLinks) {
        if (link.nodeId == affectedNodeId) {
          return link;
        }
      }
      return KnowledgeLink(nodeId: affectedNodeId, nodeName: '知识节点');
    }

    for (final link in error.knowledgeLinks) {
      if (link.isPrimary) {
        return link;
      }
    }
    return error.knowledgeLinks.isNotEmpty ? error.knowledgeLinks.first : null;
  }

  Color _getMasteryColor(double mastery) {
    if (mastery >= 0.8) return DS.semanticSuccess;
    if (mastery >= 0.5) return DS.semanticWarning;
    return DS.semanticError;
  }

  String _formatTime(BuildContext context, DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);
    final l10n = context.l10n;

    if (difference.inDays == 0) {
      if (difference.inHours == 0) {
        return l10n.errorBookTimeAgoMinutes(difference.inMinutes);
      }
      return l10n.errorBookTimeAgoHours(difference.inHours);
    } else if (difference.inDays < 7) {
      return l10n.errorBookTimeAgoDays(difference.inDays);
    } else {
      return DateFormat('MM-dd').format(time);
    }
  }
}

class _MetaInfoItem extends StatelessWidget {
  const _MetaInfoItem({
    required this.icon,
    required this.label,
    required this.color,
    required this.textStyle,
  });

  final IconData icon;
  final String label;
  final Color color;
  final TextStyle? textStyle;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: color,
          ),
          const SizedBox(width: DS.spacing4),
          Text(
            label,
            style: textStyle?.copyWith(color: color),
          ),
        ],
      );
}

class _AffectedKnowledgeTag extends StatelessWidget {
  const _AffectedKnowledgeTag({
    required this.link,
    required this.masteryDelta,
    this.onTap,
  });

  final KnowledgeLink link;
  final double? masteryDelta;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final delta = masteryDelta;
    final hasDrop = delta != null && delta < 0;
    final labelColor =
        hasDrop ? theme.colorScheme.error : theme.colorScheme.primary;
    final backgroundColor = labelColor.withValues(alpha: 0.1);

    return Align(
      alignment: Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width - DS.spacing64,
        ),
        child: Material(
          color: backgroundColor,
          borderRadius: BorderRadius.circular(6),
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(6),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing8,
                vertical: DS.spacing4,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.hub_outlined,
                    size: 14,
                    color: labelColor,
                  ),
                  const SizedBox(width: DS.spacing4),
                  Flexible(
                    child: Text(
                      link.nodeName,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: labelColor,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (hasDrop) ...[
                    const SizedBox(width: DS.spacing4),
                    Icon(
                      Icons.trending_down_rounded,
                      size: 14,
                      color: labelColor,
                    ),
                    Text(
                      delta.toStringAsFixed(delta.abs() >= 1 ? 0 : 1),
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: labelColor,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 错题简化卡片（用于复习页面）
class ErrorCardCompact extends StatelessWidget {
  const ErrorCardCompact({
    required this.error,
    super.key,
    this.onTap,
  });
  final ErrorRecord error;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing6,
      ),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing12),
          child: Row(
            children: [
              SubjectChip(subjectCode: error.subject, compact: true),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Text(
                  error.questionText,
                  style: theme.textTheme.bodyMedium,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Icon(
                Icons.chevron_right,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
