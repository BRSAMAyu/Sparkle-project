import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/models/user_state_models.dart';

class ForesightCard extends StatelessWidget {
  const ForesightCard({required this.hint, super.key});

  final UserStateFieldEnvelope<ForesightHintSummaryItem>? hint;

  @override
  Widget build(BuildContext context) {
    final value = hint?.value;
    final confidenceItems =
        value?.attractorConfidences ?? const <ForesightConfidenceItem>[];

    return GraphiteCardSurface(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.userForesightHint,
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              (value?.hintText ?? '').isEmpty
                  ? context.l10n.userForesightEmpty
                  : value!.hintText!,
              style: DS.bodyMedium.copyWith(color: DS.textPrimary),
            ),
            if (value?.generatedAt != null ||
                (value?.deviationCount ?? 0) > 0) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                [
                  if ((value?.deviationCount ?? 0) > 0)
                    '偏离 ${value!.deviationCount} 个',
                  if (value?.generatedAt != null)
                    DateFormat('M月d日 HH:mm').format(value!.generatedAt!),
                ].join(' · '),
                style: DS.bodySmall.copyWith(color: DS.textSecondary),
              ),
            ],
            if (confidenceItems.isNotEmpty) ...[
              const SizedBox(height: DS.spacing10),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: confidenceItems
                    .take(3)
                    .map(
                      (item) => Chip(
                        label: Text(
                          '${_labelForDim(item.dim)} ${item.confidence.toStringAsFixed(2)}',
                        ),
                      ),
                    )
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _labelForDim(String dim) {
    switch (dim) {
      case 'execution_stability':
        return context.l10n.userStabilityScore;
      case 'schedule_fit':
        return context.l10n.userRhythmFit;
      case 'overload_risk':
        return context.l10n.userOverloadRisk;
      default:
        return dim;
    }
  }
}
