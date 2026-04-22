import 'package:flutter/material.dart';
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
              '前瞻提示',
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              (value?.hintText ?? '').isEmpty
                  ? '暂时还没有可展示的前瞻提示，后端会继续观察。'
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
        return '执行稳定度';
      case 'schedule_fit':
        return '节奏贴合';
      case 'overload_risk':
        return '过载风险';
      default:
        return dim;
    }
  }
}
