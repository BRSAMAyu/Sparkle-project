import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../widgets/subject_chips.dart';
import '../widgets/analysis_card.dart';
import '../../data/providers/error_book_provider.dart';
import '../../data/models/error_record.dart';

/// 错题详情页面
///
/// 设计原则：
/// 1. 信息完整：展示题目、答案、分析、关联知识点、复习记录
/// 2. 操作便捷：编辑、删除、重新分析、开始复习
/// 3. 视觉清晰：分段展示，关键信息突出
class ErrorDetailScreen extends ConsumerWidget {
  final String errorId;

  const ErrorDetailScreen({
    super.key,
    required this.errorId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final errorAsync = ref.watch(errorDetailProvider(errorId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('错题详情'),
        actions: [
          // 编辑按钮
          errorAsync.whenOrNull(
            data: (error) => IconButton(
              icon: const Icon(Icons.edit_outlined),
              tooltip: '编辑',
              onPressed: () => _navigateToEdit(context, error),
            ),
          ) ?? const SizedBox.shrink(),
          // 更多操作
          errorAsync.whenOrNull(
            data: (error) => PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert),
              onSelected: (value) {
                switch (value) {
                  case 'reanalyze':
                    _reanalyze(context, ref, error);
                    break;
                  case 'delete':
                    _confirmDelete(context, ref, error);
                    break;
                }
              },
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'reanalyze',
                  child: Row(
                    children: [
                      Icon(Icons.psychology_outlined),
                      SizedBox(width: 12),
                      Text('重新分析'),
                    ],
                  ),
                ),
                const PopupMenuItem(
                  value: 'delete',
                  child: Row(
                    children: [
                      Icon(Icons.delete_outline, color: Colors.red),
                      SizedBox(width: 12),
                      Text('删除错题', style: TextStyle(color: Colors.red)),
                    ],
                  ),
                ),
              ],
            ),
          ) ?? const SizedBox.shrink(),
        ],
      ),
      body: errorAsync.when(
        data: (error) => _buildDetailContent(context, ref, error),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => _buildErrorState(context, ref, error.toString()),
      ),
      bottomNavigationBar: errorAsync.whenOrNull(
        data: (error) => _buildBottomBar(context, ref, error),
      ),
    );
  }

  Widget _buildDetailContent(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) {
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 80),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 科目和元数据
          _buildMetadataSection(context, error),

          const Divider(height: 1),

          // 题目内容
          _buildQuestionSection(context, error),

          const Divider(height: 1),

          // 答案对比
          _buildAnswerSection(context, error),

          const Divider(height: 1),

          // AI 分析
          if (error.latestAnalysis != null) ...[
            _buildAnalysisSection(context, error),
            const Divider(height: 1),
          ],

          // 关联知识点
          if (error.knowledgeLinks.isNotEmpty) ...[
            _buildKnowledgeSection(context, error),
            const Divider(height: 1),
          ],

          // 复习统计
          _buildReviewStatsSection(context, error),
        ],
      ),
    );
  }

  Widget _buildMetadataSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 科目徽章
          Row(
            children: [
              SubjectChip(subjectCode: error.subject),
              if (error.chapter != null) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceVariant,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.folder_outlined,
                        size: 14,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        error.chapter!,
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const Spacer(),
              // 掌握度
              _buildMasteryBadge(theme, error.masteryLevel),
            ],
          ),
          const SizedBox(height: 12),

          // 创建时间
          Row(
            children: [
              Icon(
                Icons.access_time,
                size: 14,
                color: theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 4),
              Text(
                '创建于 ${_formatDateTime(error.createdAt)}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMasteryBadge(ThemeData theme, double mastery) {
    final color = mastery >= 0.8
        ? Colors.green
        : mastery >= 0.5
            ? Colors.orange
            : Colors.red;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            mastery >= 0.8
                ? Icons.star
                : mastery >= 0.5
                    ? Icons.star_half
                    : Icons.star_outline,
            size: 16,
            color: color,
          ),
          const SizedBox(width: 4),
          Text(
            '掌握度 ${(mastery * 100).toInt()}%',
            style: theme.textTheme.labelMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuestionSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '题目内容',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceVariant.withOpacity(0.5),
              borderRadius: BorderRadius.circular(12),
            ),
            child: SelectableText(
              error.questionText,
              style: theme.textTheme.bodyLarge?.copyWith(
                height: 1.6,
              ),
            ),
          ),
          if (error.questionImageUrl != null) ...[
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.network(
                error.questionImageUrl!,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stack) => Container(
                  padding: const EdgeInsets.all(16),
                  color: theme.colorScheme.errorContainer,
                  child: Row(
                    children: [
                      Icon(
                        Icons.broken_image_outlined,
                        color: theme.colorScheme.error,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '图片加载失败',
                        style: TextStyle(color: theme.colorScheme.error),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAnswerSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '答案对比',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),

          // 你的答案
          _buildAnswerCard(
            context: context,
            label: '你的答案',
            content: error.userAnswer,
            icon: Icons.edit_outlined,
            color: theme.colorScheme.error,
            isCorrect: false,
          ),
          const SizedBox(height: 12),

          // 正确答案
          _buildAnswerCard(
            context: context,
            label: '正确答案',
            content: error.correctAnswer,
            icon: Icons.check_circle_outline,
            color: Colors.green,
            isCorrect: true,
          ),
        ],
      ),
    );
  }

  Widget _buildAnswerCard({
    required BuildContext context,
    required String label,
    required String content,
    required IconData icon,
    required Color color,
    required bool isCorrect,
  }) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withOpacity(0.2),
          width: 1.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: color),
              const SizedBox(width: 6),
              Text(
                label,
                style: theme.textTheme.titleSmall?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SelectableText(
            content,
            style: theme.textTheme.bodyMedium?.copyWith(
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalysisSection(BuildContext context, ErrorRecord error) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.psychology,
                size: 20,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                'AI 智能分析',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const Spacer(),
              Text(
                _formatDateTime(error.latestAnalysis!.analyzedAt),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          AnalysisCard(analysis: error.latestAnalysis!),
        ],
      ),
    );
  }

  Widget _buildKnowledgeSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.auto_graph,
                size: 20,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                '关联知识点',
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: error.knowledgeLinks.map((link) {
              return ActionChip(
                avatar: const Icon(Icons.timeline, size: 16),
                label: Text(link.nodeName),
                tooltip: '跳转到知识星图',
                onPressed: () {
                  // TODO: 导航到知识星图对应节点
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('跳转到知识点: ${link.nodeName}'),
                      behavior: SnackBarBehavior.floating,
                    ),
                  );
                },
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildReviewStatsSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '复习统计',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildStatCard(
                  context: context,
                  label: '复习次数',
                  value: error.reviewCount.toString(),
                  icon: Icons.repeat,
                  color: Colors.blue,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildStatCard(
                  context: context,
                  label: '掌握度',
                  value: '${(error.masteryLevel * 100).toInt()}%',
                  icon: Icons.trending_up,
                  color: error.masteryLevel >= 0.8
                      ? Colors.green
                      : error.masteryLevel >= 0.5
                          ? Colors.orange
                          : Colors.red,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (error.lastReviewedAt != null)
            _buildInfoRow(
              context,
              '上次复习',
              _formatDateTime(error.lastReviewedAt!),
              Icons.history,
            ),
          if (error.nextReviewAt != null) ...[
            const SizedBox(height: 8),
            _buildInfoRow(
              context,
              '下次复习',
              _formatDateTime(error.nextReviewAt!),
              Icons.event,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatCard({
    required BuildContext context,
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withOpacity(0.3),
        ),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 8),
          Text(
            value,
            style: theme.textTheme.headlineSmall?.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(
    BuildContext context,
    String label,
    String value,
    IconData icon,
  ) {
    final theme = Theme.of(context);

    return Row(
      children: [
        Icon(
          icon,
          size: 16,
          color: theme.colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: 8),
        Text(
          '$label: ',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        Text(
          value,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Widget _buildBottomBar(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) {
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 10,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: FilledButton.icon(
          onPressed: () => _startReview(context, ref, error),
          icon: const Icon(Icons.play_circle_outline),
          label: const Text('开始复习'),
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
            textStyle: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildErrorState(BuildContext context, WidgetRef ref, String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            size: 80,
            color: Colors.red,
          ),
          const SizedBox(height: 16),
          const Text(
            '加载失败',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            error,
            style: const TextStyle(
              fontSize: 14,
              color: Colors.grey,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: () {
              ref.invalidate(errorDetailProvider(errorId));
            },
            icon: const Icon(Icons.refresh),
            label: const Text('重试'),
          ),
        ],
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final diff = now.difference(dateTime);

    if (diff.inDays == 0) {
      if (diff.inHours == 0) {
        if (diff.inMinutes == 0) {
          return '刚刚';
        }
        return '${diff.inMinutes} 分钟前';
      }
      return '${diff.inHours} 小时前';
    } else if (diff.inDays == 1) {
      return '昨天';
    } else if (diff.inDays < 7) {
      return '${diff.inDays} 天前';
    } else {
      return '${dateTime.year}-${dateTime.month.toString().padLeft(2, '0')}-${dateTime.day.toString().padLeft(2, '0')}';
    }
  }

  void _navigateToEdit(BuildContext context, ErrorRecord error) {
    // TODO: 实现编辑功能
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('编辑功能开发中...'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _reanalyze(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) async {
    // TODO: 调用重新分析 API
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Row(
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            ),
            SizedBox(width: 12),
            Text('AI 正在重新分析...'),
          ],
        ),
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _confirmDelete(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认删除'),
        content: const Text('删除后将无法恢复，是否继续？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: Colors.red,
            ),
            child: const Text('删除'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        await ref.read(errorOperationsProvider.notifier).deleteError(error.id);

        if (context.mounted) {
          Navigator.of(context).pop(true); // 返回列表页
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('删除成功'),
              backgroundColor: Colors.green,
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('删除失败: ${e.toString()}'),
              backgroundColor: Colors.red,
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      }
    }
  }

  void _startReview(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) {
    // TODO: 导航到复习页面
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('复习功能开发中...'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
