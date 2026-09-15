import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class TraitsPriorCard extends StatelessWidget {
  const TraitsPriorCard({
    super.key,
    required this.traits,
    this.helperText = '',
  });

  final List<Map<String, dynamic>> traits;
  final String helperText;

  static List<Map<String, dynamic>> fromProfileContext(
    Map<String, dynamic> profileContext,
  ) {
    final userInsightState =
        profileContext['user_insight_state'] as Map<String, dynamic>? ?? const {};
    final traitsPrior =
        userInsightState['traits_prior'] as Map<String, dynamic>? ?? const {};
    final items = <Map<String, dynamic>>[];
    for (final entry in traitsPrior.entries) {
      final value = entry.value;
      if (value is! Map<String, dynamic>) continue;
      final confidence = (value['confidence'] as num?)?.toDouble() ?? 0.0;
      if (confidence < 0.1) continue;
      items.add({
        'dim': entry.key,
        'value': (value['value'] as num?)?.toDouble() ?? 0.0,
        'confidence': confidence,
        'source': value['source']?.toString() ?? 'merged',
      });
    }
    return items;
  }

  @override
  Widget build(BuildContext context) {
    if (traits.isEmpty) return const SizedBox.shrink();

    return GraphiteCardSurface(
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.userTraitsLongTerm,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            helperText,
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: DS.spacing12),
          ...traits.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: Row(
                children: [
                  Expanded(
                    child: Text(_labelFor(context, item['dim']?.toString() ?? '')),
                  ),
                  Text(
                    _summaryForValue(context, (item['value'] as num?)?.toDouble() ?? 0.0),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Text(
                    '${(((item['confidence'] as num?)?.toDouble() ?? 0.0) * 100).round()}%',
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  static String _labelFor(BuildContext context, String dim) {
    switch (dim) {
      case 'openness':
        return context.l10n.userTraitOpenness;
      case 'conscientiousness':
        return context.l10n.userTraitConscientiousness;
      case 'extraversion':
        return context.l10n.userTraitExtraversion;
      case 'agreeableness':
        return context.l10n.userTraitAgreeableness;
      case 'neuroticism':
        return context.l10n.userTraitNeuroticism;
      default:
        return dim;
    }
  }

  static String _summaryForValue(BuildContext context, double value) {
    if (value >= 0.35) return context.l10n.userTraitLevelHigh;
    if (value <= -0.35) return context.l10n.userTraitLevelLow;
    return context.l10n.userTraitLevelNeutral;
  }
}
