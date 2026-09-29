import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 学习状态观察卡（D-07）——取代原 PredictiveInsightsCard 的 risk 面。
///
/// 诚实性红线（M-10 口径）：只渲染定性档位（低/中/高风险词）与建议，
/// 不渲染风险指数 x/100、置信度百分比等无定义分数/假精确面。
class RiskObservationCard extends StatelessWidget {
  const RiskObservationCard({required this.data, super.key});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final riskLevel = data['risk_level'] as String? ?? 'low';
    final suggestions = data['intervention_suggestions'] as List? ?? [];

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(DS.radius16)),
      child: Padding(
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    color: _getRiskColor(riskLevel).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(DS.radius8),
                  ),
                  child: Icon(
                    Icons.shield_outlined,
                    color: _getRiskColor(riskLevel),
                    size: 24,
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.insRiskAssessment,
                        style: const TextStyle(
                          fontSize: DS.fontSizeBase,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      Text(
                        context.l10n.insRiskSubtitle,
                        // V4-G05 副标题走 textSecondary（neutral500 在
                        // classic/dusk 3.08/4.13:1 <4.5:1）。
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getRiskColor(riskLevel).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(DS.radius12),
                  ),
                  child: Text(
                    _getRiskLevelText(riskLevel, context),
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      fontWeight: DS.fontWeightBold,
                      color: _getRiskColor(riskLevel),
                    ),
                  ),
                ),
              ],
            ),
            if (suggestions.isNotEmpty) ...[
              const SizedBox(height: DS.lg),
              Text(
                context.l10n.insAiSuggestions,
                style: const TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              ...suggestions.take(2).map(
                    (suggestion) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing4),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.lightbulb_outline,
                            color: DS.brandSecondary,
                            size: DS.iconSizeXs,
                          ),
                          const SizedBox(width: DS.spacing8),
                          Expanded(
                            child: Text(
                              suggestion.toString(),
                              style: const TextStyle(
                                fontSize: DS.fontSizeXs,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
            ],
          ],
        ),
      ),
    );
  }

  Color _getRiskColor(String level) {
    // V4-G05 风险语义色全强度：shade600（0.7 alpha 透明度压色）作徽章
    // 文本四风格 2.71–4.18:1（<4.5:1）、图标 classic 2.74:1（<3:1）；
    // 全强度在 0.1 tint 底上文本 4.66–7.05:1、图标 4.66–7.05:1。
    switch (level) {
      case 'low':
        return DS.success;
      case 'medium':
        return DS.brandPrimary;
      case 'high':
        return DS.error;
      default:
        return DS.brandPrimary;
    }
  }

  String _getRiskLevelText(String level, BuildContext context) {
    switch (level) {
      case 'low':
        return context.l10n.insRiskLow;
      case 'medium':
        return context.l10n.insRiskMedium;
      case 'high':
        return context.l10n.insRiskHigh;
      default:
        return context.l10n.insRiskUnknown;
    }
  }
}
