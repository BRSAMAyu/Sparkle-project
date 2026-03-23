import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 胶囊生成预览卡片
///
/// 根据用户偏好显示预计生成的胶囊信息:
/// - 预计生成数量 (1-5个)
/// - 深度级别 (浅度/中度/深度)
/// - 使用模型名称
class CapsuleGenerationPreview extends StatelessWidget {
  const CapsuleGenerationPreview({
    required this.depthPreference,
    required this.curiosityPreference,
    super.key,
  });

  final double depthPreference;
  final double curiosityPreference;

  /// 根据深度偏好获取深度级别与预估模型
  (String Function(BuildContext) label, String model) get _depthLevel {
    if (depthPreference < 0.3) {
      return ((context) => context.l10n.capsuleDepthShallow, 'GLM-4.5 Air Batch');
    }
    if (depthPreference < 0.72) {
      return ((context) => context.l10n.capsuleDepthMedium, 'GLM-4.6 Batch');
    }
    if (curiosityPreference >= 0.8) {
      return ((context) => context.l10n.capsuleDepthDeep, 'GLM-4.7 Thinking');
    }
    return ((context) => context.l10n.capsuleDepthDeep, 'GLM-4.7');
  }

  /// 根据好奇心偏好计算预计生成数量
  int get _expectedCount {
    if (curiosityPreference < 0.3) {
      return 1;
    } else if (curiosityPreference < 0.7) {
      return 3;
    } else {
      return 5;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final (depthLabelBuilder, modelName) = _depthLevel;
    final depthLabel = depthLabelBuilder(context);
    final expectedCount = _expectedCount;

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 360;
        return Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color: isDark ? DS.neutral700 : DS.neutral300,
            ),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color.alphaBlend(
                  DS.primaryBase.withValues(alpha: isDark ? 0.12 : 0.08),
                  isDark ? DS.surfaceTertiary : DS.surfaceSecondary,
                ),
                isDark ? DS.surfaceSecondary : DS.surfacePrimaryElevated,
              ],
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.auto_awesome_outlined,
                    color: DS.primaryBase,
                    size: 20,
                  ),
                  const SizedBox(width: DS.sm),
                  Expanded(
                    child: Text(
                      context.l10n.capsuleGenerationPreviewTitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: DS.textPrimary,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),
              compact
                  ? Column(
                      children: [
                        _buildPreviewMetricCard(
                          context,
                          icon: Icons.library_books_outlined,
                          label:
                              context.l10n.capsuleGenerationPreviewCountLabel,
                          value: context.l10n.capsuleGenerationPreviewCount(
                            expectedCount,
                          ),
                          color: DS.info,
                        ),
                        const SizedBox(height: DS.spacing12),
                        _buildPreviewMetricCard(
                          context,
                          icon: Icons.timeline_outlined,
                          label:
                              context.l10n.capsuleGenerationPreviewDepthLabel,
                          value: depthLabel,
                          color: DS.warning,
                        ),
                        const SizedBox(height: DS.spacing12),
                        _buildPreviewMetricCard(
                          context,
                          icon: Icons.psychology_outlined,
                          label:
                              context.l10n.capsuleGenerationPreviewModelLabel,
                          value: modelName,
                          color: DS.success,
                        ),
                      ],
                    )
                  : Wrap(
                      spacing: DS.spacing12,
                      runSpacing: DS.spacing12,
                      children: [
                        _buildPreviewMetricCard(
                          context,
                          icon: Icons.library_books_outlined,
                          label:
                              context.l10n.capsuleGenerationPreviewCountLabel,
                          value: context.l10n.capsuleGenerationPreviewCount(
                            expectedCount,
                          ),
                          color: DS.info,
                        ),
                        _buildPreviewMetricCard(
                          context,
                          icon: Icons.timeline_outlined,
                          label:
                              context.l10n.capsuleGenerationPreviewDepthLabel,
                          value: depthLabel,
                          color: DS.warning,
                        ),
                        _buildPreviewMetricCard(
                          context,
                          icon: Icons.psychology_outlined,
                          label:
                              context.l10n.capsuleGenerationPreviewModelLabel,
                          value: modelName,
                          color: DS.success,
                        ),
                      ],
                    ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildPreviewMetricCard(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      width: 160,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: color.withValues(alpha: isDark ? 0.22 : 0.16),
        ),
        color: Color.alphaBlend(
          color.withValues(alpha: isDark ? 0.12 : 0.08),
          isDark ? DS.surfacePrimaryElevated : DS.surfaceSecondary,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
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
          const SizedBox(height: DS.spacing10),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            value,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: DS.textPrimary,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
