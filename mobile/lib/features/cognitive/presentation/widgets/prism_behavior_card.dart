import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';

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
      final type = PatternType.fromJson(p['pattern_type']);
      switch (type) {
        case PatternType.cognitive:
          cognitive.add(p);
        case PatternType.emotional:
          emotional.add(p);
        case PatternType.execution:
          execution.add(p);
        case PatternType.unknown:
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
                context.l10n.prismCognitivePatterns,
                cognitive,
                DS.prismBlue,
                Icons.psychology,
              ),
            ],

            // 情绪模式
            if (emotional.isNotEmpty) ...[
              _buildPatternSection(
                context,
                context.l10n.prismEmotionalPatterns,
                emotional,
                // V4-G03：prismPurple（=退役别名槽 brandSecondary）作文字/
                // 图标在 classic-light 玻璃/卡面仅 2.72–3.05:1；改
                // taskReflection 柔紫语义槽（B2-3a 定标，四档达标）。
                DS.taskReflection,
                Icons.sentiment_neutral,
              ),
            ],

            // 执行模式
            if (execution.isNotEmpty) ...[
              _buildPatternSection(
                context,
                context.l10n.prismExecutionPatterns,
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
                  Icon(
                    Icons.psychology_outlined,
                    // V4-G03：柔紫语义槽替换 brandSecondary（图形 ≥3:1）。
                    color: DS.taskReflection,
                  ),
                  const SizedBox(width: DS.sm),
                  Text(
                    context.l10n.prismTitle,
                    style: context.typo.labelLarge.copyWith(
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.sm),
              Text(
                message ?? context.l10n.prismNoData,
                style: TextStyle(color: DS.textSecondary),
              ),
              const SizedBox(height: DS.sm),
              Text(
                context.l10n.prismHint,
                style: TextStyle(
                  color: DS.textSecondary,
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
            child: Icon(
              Icons.diamond_outlined,
              color: DS.textOnPrimary,
              size: DS.iconSizeSm,
            ),
          ),
          const SizedBox(width: DS.sm),
          Text(
            context.l10n.prismTitle,
            style: context.typo.labelLarge.copyWith(
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
              // V4-G03 四风格复算：12sp 彩色标签对 0.1 tint 合成底在
              // classic 两档 ≤4.3:1；0.06 全档 ≥4.5:1（label 文字随色）。
              color: DS.taskReflection.withValues(alpha: 0.06),
              borderRadius: DS.borderRadius4,
            ),
            child: Text(
              context.l10n.prismTotalPatterns(count),
              style: TextStyle(
                color: DS.taskReflection,
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
                // V4-G03：分区标题文字走 textPrimary（classic-dark 下
                // success 系彩字对卡面仅 4.42:1 <4.5）；色相辨识由图标承担。
                style: TextStyle(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                  fontSize: DS.fontSizeSm,
                ),
              ),
              const SizedBox(width: DS.xs),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing6,
                  vertical: DS.spacing4 / 2,
                ),
                decoration: BoxDecoration(
                  // V4-G03：0.1→0.06（全档文字 ≥4.5），计数文字 textPrimary。
                  color: color.withValues(alpha: 0.06),
                  borderRadius: DS.borderRadius4,
                ),
                child: Text(
                  '${patterns.length}',
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.textPrimary,
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
                    horizontal: DS.spacing6,
                    vertical: DS.spacing4 / 2,
                  ),
                  decoration: BoxDecoration(
                    // V4-G03：0.12→0.06 + textPrimary（彩色 10sp 对 tint
                    // 合成底在 classic 两档 <4.2:1 且低于 12sp 字号下限）。
                    color: color.withValues(alpha: 0.06),
                    borderRadius: DS.borderRadius4,
                  ),
                  child: Text(
                    '${(confidenceScore * 100).toInt()}%',
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightMedium,
                    ),
                  ),
                ),
            ],
          ),
          if (description != null) ...[
            const SizedBox(height: DS.spacing4),
            Text(
              description,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: DS.textSecondary,
              ),
            ),
          ],
          if (solutionText != null) ...[
            const SizedBox(height: DS.spacing6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.lightbulb_outline,
                  size: 14,
                  // V4-G03：去 0.8 透明衰减（classic-light 对 tint 面图形
                  // 对比 <3:1），全色图标 ≥3:1。
                  color: color,
                ),
                const SizedBox(width: DS.spacing4),
                Expanded(
                  child: Text(
                    solutionText,
                    style: TextStyle(
                      // V4-G03：10/11sp 低于 12sp 辅助字号下限（DESIGN_SYSTEM
                      // 字阶合同），收敛 DS.fontSizeXs。
                      fontSize: DS.fontSizeXs,
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
