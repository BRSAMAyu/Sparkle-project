import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class MetacognitionPanelCard extends StatelessWidget {
  const MetacognitionPanelCard({
    required this.cards,
    required this.generatedAt,
    required this.onHide,
    this.profileDimensionCount,
    super.key,
  });

  final List<Map<String, dynamic>> cards;
  final String? generatedAt;
  final VoidCallback onHide;
  final int? profileDimensionCount;

  static Map<String, dynamic>? fromProfileContext(
    Map<String, dynamic> profileContext,
  ) {
    final payload =
        profileContext['metacognition_dashboard'] as Map<String, dynamic>?;
    if (payload == null) return null;
    final available = payload['available'] == true;
    final hidden = payload['hidden'] == true;
    final cards = (payload['cards'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    if (!available || hidden || cards.isEmpty) {
      return null;
    }
    return {'cards': cards, 'generatedAt': payload['generated_at']?.toString()};
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return GraphiteCardSurface(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing8),
                  decoration: BoxDecoration(
                    color: isDark
                        ? DS.success.withValues(alpha: 0.12)
                        : const Color(0xFFE8F1EA),
                    borderRadius: DS.borderRadius12,
                  ),
                  child: Icon(
                    Icons.insights_rounded,
                    color: isDark
                        ? DS.success
                        : const Color(0xFF4A7A58),
                    size: 18,
                  ),
                ),
                  const SizedBox(width: DS.spacing10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '自我认识',
                          style: DS.titleMedium.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        const SizedBox(height: DS.spacing2),
                        Text(
                          '这里只展示过去样本里的判断偏差，不给你贴标签。',
                          style: DS.bodySmall.copyWith(color: DS.textSecondary),
                        ),
                        if ((profileDimensionCount ?? 0) > 0) ...[
                          const SizedBox(height: DS.spacing4),
                          Text(
                            '已观察 ${profileDimensionCount!} 个元认知维度',
                            style: DS.labelSmall.copyWith(
                              color: isDark
                                  ? DS.success
                                  : const Color(0xFF4A7A58),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: '隐藏此面板',
                    onPressed: onHide,
                    icon: const Icon(Icons.visibility_off_outlined),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              ...cards.map((c) => _buildCard(c, isDark)),
              if (generatedAt != null && generatedAt!.isNotEmpty) ...[
                const SizedBox(height: DS.spacing8),
                Text(
                  '更新于 $generatedAt',
                  style: DS.labelSmall.copyWith(color: DS.textTertiary),
                ),
              ],
            ],
          ),
        ),
      );
  }

  Widget _buildCard(Map<String, dynamic> card, bool isDark) {
    final status = card['status']?.toString() ?? 'ready';
    final title = card['title']?.toString() ?? '';
    final body = card['body']?.toString() ?? '';
    final trendText = card['trend_text']?.toString() ?? '';
    final toneColor = status == 'insufficient'
        ? (isDark ? DS.warning : const Color(0xFF8A7C59))
        : (isDark ? DS.info : const Color(0xFF497179));

    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing10),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: Color.alphaBlend(
            toneColor.withValues(alpha: 0.08),
            DS.surfacePrimary,
          ),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: toneColor.withValues(alpha: 0.15)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: DS.labelLarge.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(body, style: DS.bodyMedium.copyWith(color: DS.textPrimary)),
            if (trendText.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(trendText, style: DS.bodySmall.copyWith(color: toneColor)),
            ],
          ],
        ),
      ),
    );
  }
}
