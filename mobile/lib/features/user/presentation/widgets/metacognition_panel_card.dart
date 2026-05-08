import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class MetacognitionPanelCard extends StatefulWidget {
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
  State<MetacognitionPanelCard> createState() => _MetacognitionPanelCardState();
}

class _MetacognitionPanelCardState extends State<MetacognitionPanelCard> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardCount = widget.cards.length;

    return GraphiteCardSurface(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                GestureDetector(
                  onTap: () => setState(() => _isExpanded = !_isExpanded),
                  child: Container(
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
                ),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: GestureDetector(
                    onTap: () => setState(() => _isExpanded = !_isExpanded),
                    behavior: HitTestBehavior.opaque,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                context.l10n.userMetacognition,
                                style: DS.titleMedium.copyWith(
                                  color: DS.textPrimary,
                                  fontWeight: DS.fontWeightBold,
                                ),
                              ),
                            ),
                            const SizedBox(width: DS.spacing8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.spacing8,
                                vertical: DS.spacing2,
                              ),
                              decoration: BoxDecoration(
                                color: isDark
                                    ? DS.success.withValues(alpha: 0.16)
                                    : const Color(0xFFE0EBE3),
                                borderRadius: DS.borderRadius12,
                              ),
                              child: Text(
                                '$cardCount',
                                style: DS.labelSmall.copyWith(
                                  color: isDark
                                      ? DS.success
                                      : const Color(0xFF4A7A58),
                                  fontWeight: DS.fontWeightBold,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: DS.spacing2),
                        Text(
                          context.l10n.userMetacognitionHint,
                          style: DS.bodySmall.copyWith(color: DS.textSecondary),
                        ),
                        if ((widget.profileDimensionCount ?? 0) > 0) ...[
                          const SizedBox(height: DS.spacing4),
                          Text(
                            context.l10n.metacogDimensionsObserved(widget.profileDimensionCount!),
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
                ),
                Semantics(
                  button: true,
                  label: _isExpanded
                      ? 'Collapse metacognition panel'
                      : 'Expand metacognition panel',
                  child: AnimatedRotation(
                    turns: _isExpanded ? 0.5 : 0,
                    duration: DS.quick,
                    child: IconButton(
                      onPressed: () => setState(() => _isExpanded = !_isExpanded),
                      icon: Icon(
                        Icons.expand_more_rounded,
                        color: DS.textSecondary,
                      ),
                    ),
                  ),
                ),
                IconButton(
                  tooltip: context.l10n.userHidePanel,
                  onPressed: widget.onHide,
                  icon: const Icon(Icons.visibility_off_outlined),
                ),
              ],
            ),
            AnimatedCrossFade(
              firstChild: const SizedBox(width: double.infinity),
              secondChild: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: DS.spacing12),
                  ...widget.cards.map((c) => _buildCard(c, isDark)),
                  if (widget.generatedAt != null && widget.generatedAt!.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing8),
                    Text(
                      context.l10n.metacogUpdatedAt(widget.generatedAt!),
                      style: DS.labelSmall.copyWith(color: DS.textTertiary),
                    ),
                  ],
                ],
              ),
              crossFadeState: _isExpanded
                  ? CrossFadeState.showSecond
                  : CrossFadeState.showFirst,
              duration: DS.quick,
            ),
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
            Text(
              body,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: DS.bodyMedium.copyWith(color: DS.textPrimary),
            ),
            if (trendText.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                trendText,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: DS.bodySmall.copyWith(color: toneColor),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
