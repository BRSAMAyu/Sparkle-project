import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/goal/presentation/providers/goal_detail_provider.dart';
import 'package:sparkle/features/goal/presentation/widgets/goal_detail_l10n.dart';

class MinimumCriteriaCard extends StatelessWidget {
  const MinimumCriteriaCard({
    required this.criteria,
    required this.onConfirm,
    required this.onModify,
    super.key,
  });

  final MinimumAcceptanceCriteria criteria;
  final VoidCallback onConfirm;
  final VoidCallback onModify;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Semantics(
      container: true,
      label: l10n.goalDetailMinimumLine,
      child: Card(
        elevation: 0,
        color: colorScheme.surfaceContainerHighest,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: BorderSide(color: colorScheme.outlineVariant),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    criteria.isConfirmed
                        ? Icons.verified_outlined
                        : Icons.fact_check_outlined,
                    color: colorScheme.primary,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      l10n.goalDetailMinimumLine,
                      style: textTheme.titleMedium?.copyWith(
                        color: colorScheme.onSurface,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                criteria.isConfirmed
                    ? l10n.goalDetailConfirmedMinimum
                    : l10n.goalDetailSuggestedMinimum,
                style: textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              if (criteria.description.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(
                  criteria.description,
                  style: textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurface,
                  ),
                ),
              ],
              const SizedBox(height: 14),
              if (criteria.thresholds.isEmpty)
                Text(
                  l10n.goalDetailNoCriteria,
                  style: textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                )
              else
                Column(
                  children: [
                    for (final item in criteria.thresholds)
                      _CriteriaRow(threshold: item),
                  ],
                ),
              if (!criteria.isConfirmed) ...[
                const SizedBox(height: 14),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    FilledButton.icon(
                      onPressed: onConfirm,
                      icon: const Icon(Icons.check_rounded),
                      label: Text(l10n.goalDetailConfirm),
                    ),
                    OutlinedButton.icon(
                      onPressed: onModify,
                      icon: const Icon(Icons.edit_outlined),
                      label: Text(l10n.goalDetailModify),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _CriteriaRow extends StatelessWidget {
  const _CriteriaRow({required this.threshold});

  final CriteriaThreshold threshold;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final detail = [
      threshold.currentValue,
      threshold.threshold,
      threshold.unit,
    ].whereType<String>().where((value) => value.isNotEmpty).join(' / ');

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            threshold.met
                ? Icons.check_circle_rounded
                : Icons.radio_button_unchecked_rounded,
            size: 22,
            color: threshold.met ? colorScheme.primary : colorScheme.outline,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  threshold.label,
                  style: textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurface,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (detail.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    detail,
                    style: textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
