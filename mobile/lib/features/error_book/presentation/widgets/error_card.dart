import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/presentation/widgets/subject_chips.dart';

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
    this.showReviewStatus = true,
  });
  final ErrorRecord error;
  final VoidCallback? onTap;
  final VoidCallback? onDelete;
  final bool showReviewStatus;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final now = DateTime.now();
    final needReview =
        error.nextReviewAt != null && error.nextReviewAt!.isBefore(now);

    return Dismissible(
      key: Key(error.id),
      direction: onDelete != null
          ? DismissDirection.endToStart
          : DismissDirection.none,
      confirmDismiss: onDelete != null
          ? (_) async => showDialog<bool>(
                context: context,
                builder: (context) => AlertDialog(
                  title: const Text('确认删除'),
                  content: const Text('删除后无法恢复，确定要删除这道错题吗？'),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(false),
                      child: const Text('取消'),
                    ),
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(true),
                      child:
                          const Text('删除', style: TextStyle(color: Colors.red)),
                    ),
                  ],
                ),
              )
          : null,
      onDismissed: (_) => onDelete?.call(),
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 16),
        color: Colors.red,
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      child: Card(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 头部：科目标签 + 状态标签
                Row(
                  children: [
                    SubjectChip(subjectCode: error.subject, compact: true),
                    const SizedBox(width: 8),
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
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.error.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(
                            color: theme.colorScheme.error.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Text(
                          '待复习',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w500,
                            color: theme.colorScheme.error,
                          ),
                        ),
                      ),
                    if (error.difficulty != null)
                      Padding(
                        padding: const EdgeInsets.only(left: 8),
                        child: Row(
                          children: List.generate(
                            5,
                            (index) => Icon(
                              index < error.difficulty!
                                  ? Icons.star
                                  : Icons.star_border,
                              size: 12,
                              color: Colors.amber,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 12),

                // 题目摘要（限制3行）
                Text(
                  error.questionText,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 12),

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
                      const SizedBox(width: 12),
                      Text(
                        '${(error.masteryLevel * 100).toInt()}%',
                        style: theme.textTheme.labelSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: _getMasteryColor(error.masteryLevel),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                ],

                // 底部元信息
                Row(
                  children: [
                    Icon(
                      Icons.replay,
                      size: 14,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '复习 ${error.reviewCount} 次',
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Icon(
                      Icons.access_time,
                      size: 14,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      _formatTime(error.createdAt),
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    if (error.latestAnalysis != null) ...[
                      const Spacer(),
                      Icon(
                        Icons.psychology,
                        size: 14,
                        color: theme.colorScheme.primary,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'AI已分析',
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: theme.colorScheme.primary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Color _getMasteryColor(double mastery) {
    if (mastery >= 0.8) return Colors.green;
    if (mastery >= 0.5) return Colors.orange;
    return Colors.red;
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);

    if (difference.inDays == 0) {
      if (difference.inHours == 0) {
        return '${difference.inMinutes}分钟前';
      }
      return '${difference.inHours}小时前';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}天前';
    } else {
      return DateFormat('MM-dd').format(time);
    }
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
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              SubjectChip(subjectCode: error.subject, compact: true),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  error.questionText,
                  style: theme.textTheme.bodyMedium,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
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
