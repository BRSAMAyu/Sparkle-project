import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class BottleneckCard extends StatelessWidget {
  const BottleneckCard({required this.data, super.key});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final bottlenecks = (data['bottlenecks'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.l10n.chatBottleneckPriority,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
        ),
        const SizedBox(height: DS.spacing12),
        ...bottlenecks.map(
          (item) => Container(
            margin: const EdgeInsets.only(bottom: DS.spacing10),
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfaceSecondary,
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 10,
                  height: 10,
                  margin: const EdgeInsets.only(top: 6),
                  decoration: BoxDecoration(
                    color: _severityColor(item['severity']?.toString()),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item['description']?.toString() ?? '',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              fontWeight: DS.fontWeightSemibold,
                              color: DS.textPrimary,
                            ),
                      ),
                      const SizedBox(height: DS.spacing6),
                      Text(
                        item['specific_risk']?.toString() ?? '',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.45,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Color _severityColor(String? severity) {
    switch ((severity ?? '').toLowerCase()) {
      case 'high':
        return DS.error;
      case 'medium':
        return DS.warning;
      default:
        return DS.success;
    }
  }
}
