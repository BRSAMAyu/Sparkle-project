import 'package:flutter/material.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';

/// AI 分析结果卡片
///
/// 设计原则：
/// 1. 信息分段展示：错因 > 正确思路 > 易错点 > 建议
/// 2. 视觉层次：使用图标和颜色区分不同类型的信息
/// 3. 可操作性：关联知识点可点击跳转
class AnalysisCard extends StatelessWidget {

  const AnalysisCard({
    super.key,
    required this.analysis,
    this.knowledgeLinks = const [],
    this.onKnowledgeTap,
    this.onReAnalyze,
  });
  final ErrorAnalysis analysis;
  final List<KnowledgeLink> knowledgeLinks;
  final VoidCallback? onKnowledgeTap;
  final VoidCallback? onReAnalyze;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题栏
            Row(
              children: [
                Icon(
                  Icons.psychology,
                  color: theme.colorScheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'AI 分析',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                // 错因类型标签
                _ErrorTypeChip(
                  errorType: analysis.errorType,
                  label: analysis.errorTypeLabel,
                ),
                if (onReAnalyze != null) ...[
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.refresh, size: 20),
                    onPressed: onReAnalyze,
                    tooltip: '重新分析',
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 16),

            // 错误原因
            _buildSection(
              context,
              icon: Icons.error_outline,
              iconColor: Colors.red,
              title: '错误原因',
              content: analysis.rootCause,
            ),
            const SizedBox(height: 16),

            // 正确思路
            _buildSection(
              context,
              icon: Icons.lightbulb_outline,
              iconColor: Colors.amber,
              title: '正确思路',
              content: analysis.correctApproach,
            ),

            // 易错点提醒
            if (analysis.similarTraps.isNotEmpty) ...[
              const SizedBox(height: 16),
              _buildListSection(
                context,
                icon: Icons.warning_amber_rounded,
                iconColor: Colors.orange,
                title: '类似易错点',
                items: analysis.similarTraps,
              ),
            ],

            const SizedBox(height: 16),

            // 学习建议
            _buildSection(
              context,
              icon: Icons.school_outlined,
              iconColor: Colors.blue,
              title: '学习建议',
              content: analysis.studySuggestion,
            ),

            // 关联知识点
            if (knowledgeLinks.isNotEmpty) ...[
              const SizedBox(height: 20),
              const Divider(),
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(
                    Icons.account_tree_outlined,
                    size: 16,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '关联知识点',
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: knowledgeLinks.map((link) => ActionChip(
                    avatar: link.isPrimary
                        ? Icon(
                            Icons.star,
                            size: 16,
                            color: theme.colorScheme.primary,
                          )
                        : null,
                    label: Text(link.nodeName),
                    onPressed: onKnowledgeTap,
                    backgroundColor: link.isPrimary
                        ? theme.colorScheme.primaryContainer
                        : theme.colorScheme.surfaceVariant,
                  )).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSection(
    BuildContext context, {
    required IconData icon,
    required Color iconColor,
    required String title,
    required String content,
  }) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 18, color: iconColor),
            const SizedBox(width: 6),
            Text(
              title,
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: iconColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: iconColor.withOpacity(0.05),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: iconColor.withOpacity(0.2),
            ),
          ),
          child: Text(
            content,
            style: theme.textTheme.bodyMedium?.copyWith(
              height: 1.5,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildListSection(
    BuildContext context, {
    required IconData icon,
    required Color iconColor,
    required String title,
    required List<String> items,
  }) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 18, color: iconColor),
            const SizedBox(width: 6),
            Text(
              title,
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: iconColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: iconColor.withOpacity(0.05),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: iconColor.withOpacity(0.2),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: items.map((item) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '• ',
                      style: TextStyle(
                        color: iconColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Expanded(
                      child: Text(
                        item,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                ),
              )).toList(),
          ),
        ),
      ],
    );
  }
}

/// 错因类型标签
class _ErrorTypeChip extends StatelessWidget {

  const _ErrorTypeChip({
    required this.errorType,
    required this.label,
  });
  final String errorType;
  final String label;

  @override
  Widget build(BuildContext context) {
    final color = _getErrorTypeColor(errorType);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Color _getErrorTypeColor(String type) {
    switch (type) {
      case 'concept_confusion':
        return Colors.purple;
      case 'calculation_error':
        return Colors.orange;
      case 'reading_careless':
        return Colors.amber;
      case 'knowledge_gap':
        return Colors.red;
      case 'method_wrong':
        return Colors.blue;
      case 'logic_error':
        return Colors.indigo;
      case 'memory_lapse':
        return Colors.teal;
      case 'time_pressure':
        return Colors.deepOrange;
      default:
        return Colors.grey;
    }
  }
}

/// AI 分析加载占位符
class AnalysisLoadingPlaceholder extends StatelessWidget {
  const AnalysisLoadingPlaceholder({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              children: [
                SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      theme.colorScheme.primary,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  'AI 正在分析中...',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              '正在分析错题原因、生成学习建议并关联知识点，预计需要 3-5 秒',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
