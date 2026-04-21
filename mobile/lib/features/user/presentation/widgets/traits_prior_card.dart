import 'package:flutter/material.dart';

class TraitsPriorCard extends StatelessWidget {
  const TraitsPriorCard({
    super.key,
    required this.traits,
    this.helperText = '基于历史观察，可随时调整',
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

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '长期倾向',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              helperText,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            ...traits.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(_labelFor(item['dim']?.toString() ?? '')),
                    ),
                    Text(
                      _summaryForValue((item['value'] as num?)?.toDouble() ?? 0.0),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      '${(((item['confidence'] as num?)?.toDouble() ?? 0.0) * 100).round()}%',
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _labelFor(String dim) {
    switch (dim) {
      case 'openness':
        return '开放性';
      case 'conscientiousness':
        return '尽责性';
      case 'extraversion':
        return '外向倾向';
      case 'agreeableness':
        return '宜人性';
      case 'neuroticism':
        return '情绪波动敏感度';
      default:
        return dim;
    }
  }

  static String _summaryForValue(double value) {
    if (value >= 0.35) return '偏高';
    if (value <= -0.35) return '偏低';
    return '中性';
  }
}
