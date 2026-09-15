import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/design_system.dart';

class IdiographicSummaryCard extends StatelessWidget {
  const IdiographicSummaryCard({
    super.key,
    required this.summaryLines,
    required this.disclaimerText,
  });

  final List<String> summaryLines;
  final String disclaimerText;

  static Map<String, dynamic>? fromProfileContext(
    Map<String, dynamic> profileContext,
  ) {
    final payload = profileContext['idiographic_summary'] as Map<String, dynamic>?;
    if (payload == null) return null;
    final mode = payload['mode']?.toString().trim().toLowerCase() ?? 'off';
    final confidence = (payload['confidence'] as num?)?.toDouble() ?? 0.0;
    final disclaimerText = payload['disclaimer_text']?.toString().trim() ?? '';
    if (mode != 'live' || confidence < 0.5 || disclaimerText.isEmpty) {
      return null;
    }
    final lines = (payload['top_associations'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .where((item) => item['displayed'] == true)
        .map((item) => item['rendered_text']?.toString().trim() ?? '')
        .where((text) => text.isNotEmpty)
        .take(3)
        .toList();
    if (lines.isEmpty) {
      return null;
    }
    return {
      'summaryLines': lines,
      'disclaimerText': disclaimerText,
    };
  }

  @override
  Widget build(BuildContext context) {
    return GraphiteCardSurface(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.userIdiographicObservations,
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing10),
            ...summaryLines.map(
              (line) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing8),
                child: Text(
                  line,
                  style: DS.bodyMedium.copyWith(color: DS.textPrimary),
                ),
              ),
            ),
            Text(
              disclaimerText,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}
