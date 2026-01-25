import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Prism 行为模式卡片 - 用于聊天界面展示工具返回的行为分析结果
///
/// 接收后端 `get_user_behavior_patterns` 工具返回的 widget_data
class PrismBehaviorCard extends StatelessWidget {
  const PrismBehaviorCard({
    required this.data,
    super.key,
  });

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final patterns = data['patterns'] as List<dynamic>? ?? [];
    final message = data['message'] as String?;

    // 空数据状态
    if (patterns.isEmpty) {
      return _buildEmptyState(context, message);
    }

    // 按类型分组
    final cognitive = <Map<String, dynamic>>[];
    final emotional = <Map<String, dynamic>>[];
    final execution = <Map<String, dynamic>>[];

    for (final p in patterns) {
      if (p is! Map<String, dynamic>) continue;
      final type = p['pattern_type'] as String? ?? '';
      switch (type) {
        case 'cognitive':
          cognitive.add(p);
        case 'emotional':
          emotional.add(p);
        case 'execution':
          execution.add(p);
      }
    }

    return Card(
      margin: const EdgeInsets.symmetric(vertical: DS.sm),
      shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius16),
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题
            _buildHeader(context, patterns.length),
            const Divider(height: DS.lg),

            // 认知模式
            if (cognitive.isNotEmpty) ...[
              _buildPatternSection(
                context,
                '认知模式',
                cognitive,
                DS.prismBlue,
                Icons.psychology,
              ),
            ],

            // 情绪模式
            if (emotional.isNotEmpty) ...[
              _buildPatternSection(
                context,
                '情绪模式',
                emotional,
                DS.prismPurple,
                Icons.sentiment_neutral,
              ),
            ],

            // 执行模式
            if (execution.isNotEmpty) ...[
              _buildPatternSection(
                context,
                '执行模式',
                execution,
                DS.prismGreen,
                Icons.run_circle_outlined,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, String? message) => Card(
        margin: const EdgeInsets.symmetric(vertical: DS.sm),
        shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius16),
        child: Padding(
          padding: const EdgeInsets.all(DS.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.psychology_outlined, color: DS.prismPurple),
                  const SizedBox(width: DS.sm),
                  Text(
                    '认知棱镜',
                    style: context.sparkleTypography.labelLarge.copyWith(
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.sm),
              Text(
                message ?? '暂无行为模式数据',
                style: TextStyle(color: DS.textSecondary),
              ),
              const SizedBox(height: DS.sm),
              Text(
                '继续学习后，认知棱镜会越来越准确地了解你的学习模式',
                style: TextStyle(
                  color: DS.textTertiary,
                  fontSize: DS.fontSizeSm,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ),
        ),
      );

  Widget _buildHeader(BuildContext context, int count) => Row(
        children: [
          Container(
            padding: const EdgeInsets.all(DS.sm),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [DS.prismBlue, DS.prismPurple],
              ),
              borderRadius: DS.borderRadius8,
            ),
            child: const Icon(
              Icons.diamond_outlined,
              color: Colors.white,
              size: DS.iconSizeSm,
            ),
          ),
          const SizedBox(width: DS.sm),
          Text(
            '认知棱镜',
            style: context.sparkleTypography.labelLarge.copyWith(
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.sm,
              vertical: DS.xs,
            ),
            decoration: BoxDecoration(
              color: DS.prismPurple.withValues(alpha: 0.1),
              borderRadius: DS.borderRadius4,
            ),
            child: Text(
              '共 $count 个模式',
              style: TextStyle(
                color: DS.prismPurple,
                fontSize: DS.fontSizeXs,
              ),
            ),
          ),
        ],
      );

  Widget _buildPatternSection(
    BuildContext context,
    String title,
    List<Map<String, dynamic>> patterns,
    Color color,
    IconData icon,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: DS.iconSizeSm, color: color),
              const SizedBox(width: DS.xs),
              Text(
                title,
                style: TextStyle(
                  color: color,
                  fontWeight: DS.fontWeightSemibold,
                  fontSize: DS.fontSizeSm,
                ),
              ),
              const SizedBox(width: DS.xs),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 6,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.1),
                  borderRadius: DS.borderRadius4,
                ),
                child: Text(
                  '${patterns.length}',
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: color,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.xs),
          ...patterns.map((p) => _buildPatternItem(context, p, color)),
          const SizedBox(height: DS.sm),
        ],
      );

  Widget _buildPatternItem(
    BuildContext context,
    Map<String, dynamic> pattern,
    Color color,
  ) {
    final patternName = pattern['pattern_name'] as String? ?? '';
    final description = pattern['description'] as String?;
    final solutionText = pattern['solution_text'] as String?;
    final confidenceScore = pattern['confidence_score'] as num?;

    return Container(
      margin: const EdgeInsets.only(bottom: DS.xs),
      padding: const EdgeInsets.all(DS.sm),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: DS.borderRadius8,
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  patternName,
                  style: TextStyle(
                    fontWeight: DS.fontWeightSemibold,
                    color: DS.textPrimary,
                  ),
                ),
              ),
              if (confidenceScore != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: DS.borderRadius4,
                  ),
                  child: Text(
                    '${(confidenceScore * 100).toInt()}%',
                    style: TextStyle(
                      fontSize: 10,
                      color: color,
                      fontWeight: DS.fontWeightMedium,
                    ),
                  ),
                ),
            ],
          ),
          if (description != null) ...[
            const SizedBox(height: 4),
            Text(
              description,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: DS.textSecondary,
              ),
            ),
          ],
          if (solutionText != null) ...[
            const SizedBox(height: 6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.lightbulb_outline,
                  size: 14,
                  color: color.withValues(alpha: 0.8),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    solutionText,
                    style: TextStyle(
                      fontSize: 11,
                      color: DS.textSecondary,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
