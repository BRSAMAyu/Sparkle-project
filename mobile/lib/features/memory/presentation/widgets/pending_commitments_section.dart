import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class PendingCommitmentsSection extends StatelessWidget {
  const PendingCommitmentsSection({
    super.key,
    this.items = const [],
    this.processingIds = const {},
    this.onResolve,
    this.onDismiss,
  });

  final List<PendingCommitmentItem> items;
  final Set<String> processingIds;
  final Future<void> Function(PendingCommitmentItem)? onResolve;
  final Future<void> Function(PendingCommitmentItem)? onDismiss;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(DS.md, DS.md, DS.md, DS.sm),
          child: Text(
            I18nService.instance.isChinese ? '待处理承诺' : 'Pending Commitments',
            style: DS.labelLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ),
        ...items.map(
          (c) => Card(
            margin:
                const EdgeInsets.symmetric(horizontal: DS.md, vertical: DS.xs),
            child: Padding(
              padding: const EdgeInsets.all(DS.sm),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(c.summary, style: DS.bodySmall),
                        Text(
                          I18nService.instance.isChinese
                              ? '截止: ${c.dueAt}'
                              : 'Due: ${c.dueAt}',
                          style:
                              DS.labelSmall.copyWith(color: DS.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  if (processingIds.contains(c.id))
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  else ...[
                    IconButton(
                      icon: const Icon(Icons.check, size: 16),
                      onPressed: () => onResolve?.call(c),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 16),
                      onPressed: () => onDismiss?.call(c),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
