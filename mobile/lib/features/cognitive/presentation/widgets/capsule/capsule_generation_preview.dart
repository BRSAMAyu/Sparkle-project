import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 胶囊生成预览卡片
///
/// 根据用户偏好显示预计生成的胶囊信息:
/// - 预计生成数量 (1-5个)
/// - 深度级别 (浅度⚡/中度💡/深度🔬)
/// - 使用模型名称
class CapsuleGenerationPreview extends StatelessWidget {
  const CapsuleGenerationPreview({
    required this.depthPreference,
    required this.curiosityPreference,
    super.key,
  });

  final double depthPreference;
  final double curiosityPreference;

  /// 根据深度偏好获取深度级别
  (String Function(BuildContext) label, String emoji, String model) get _depthLevel {
    if (depthPreference < 0.3) {
      return ((context) => context.l10n.capsuleDepthShallow, '⚡', 'MIMO');
    } else if (depthPreference < 0.7) {
      return ((context) => context.l10n.capsuleDepthMedium, '💡', 'GLM-4.7');
    } else {
      return ((context) => context.l10n.capsuleDepthDeep, '🔬', 'DeepSeek R1');
    }
  }

  /// 根据好奇心偏好计算预计生成数量
  int get _expectedCount {
    if (curiosityPreference < 0.3) {
      return 1;
    } else if (curiosityPreference < 0.7) {
      return 2;
    } else {
      return 3;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final (depthLabelBuilder, depthEmoji, modelName) = _depthLevel;
    final depthLabel = depthLabelBuilder(context);
    final expectedCount = _expectedCount;

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: isDark ? DS.surfaceTertiary : DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: isDark ? DS.neutral700 : DS.neutral300,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题行
          Row(
            children: [
              Icon(
                Icons.auto_awesome_outlined,
                color: DS.primaryBase,
                size: 20,
              ),
              const SizedBox(width: DS.sm),
              Text(
                context.l10n.capsuleGenerationPreviewTitle,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: isDark ? DS.textPrimary : DS.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),

          // 预计生成数量
          _buildPreviewRow(
            context,
            icon: Icons.library_books_outlined,
            label: context.l10n.capsuleGenerationPreviewCountLabel,
            value: context.l10n.capsuleGenerationPreviewCount(expectedCount),
            color: DS.info,
          ),
          const SizedBox(height: DS.md),

          // 深度级别
          _buildPreviewRow(
            context,
            icon: Icons.timeline_outlined,
            label: context.l10n.capsuleGenerationPreviewDepthLabel,
            value: '$depthEmoji $depthLabel',
            color: DS.warning,
          ),
          const SizedBox(height: DS.md),

          // 使用模型
          _buildPreviewRow(
            context,
            icon: Icons.psychology_outlined,
            label: context.l10n.capsuleGenerationPreviewModelLabel,
            value: modelName,
            color: DS.success,
          ),
        ],
      ),
    );
  }

  Widget _buildPreviewRow(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(DS.sm),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.15),
            borderRadius: DS.borderRadius8,
          ),
          child: Icon(
            icon,
            size: 18,
            color: color,
          ),
        ),
        const SizedBox(width: DS.md),
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              color: isDark ? DS.textSecondary : DS.textSecondary,
            ),
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: isDark ? DS.textPrimary : DS.textPrimary,
          ),
        ),
      ],
    );
  }
}
