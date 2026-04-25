import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';

class PendingCommitmentsSection extends StatelessWidget {
  const PendingCommitmentsSection({
    super.key,
    required this.items,
    required this.onResolve,
    required this.onDismiss,
    this.processingIds = const <String>{},
  });

  final List<PendingCommitmentItem> items;
  final Future<void> Function(PendingCommitmentItem item) onResolve;
  final Future<void> Function(PendingCommitmentItem item) onDismiss;
  final Set<String> processingIds;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '待跟进承诺',
          style: TextStyle(fontSize: DS.fontSizeLg, fontWeight: DS.fontWeightBold),
        ),
        const SizedBox(height: DS.sm),
        ...items.map(
          (item) => Card(
            margin: const EdgeInsets.only(bottom: DS.md),
            child: Padding(
              padding: const EdgeInsets.all(DS.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.summary, style: const TextStyle(fontWeight: DS.fontWeightSemibold)),
                  const SizedBox(height: DS.xs),
                  Text(
                    '到期时间 ${item.dueAt.year}-${item.dueAt.month.toString().padLeft(2, '0')}-${item.dueAt.day.toString().padLeft(2, '0')}',
                    style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
                  ),
                  const SizedBox(height: DS.sm),
                  Wrap(
                    spacing: DS.sm,
                    children: [
                      SparkleButton(
                        label: processingIds.contains(item.id) ? '处理中' : '已完成',
                        onPressed: processingIds.contains(item.id)
                            ? () {}
                            : () => onResolve(item),
                        disabled: processingIds.contains(item.id),
                        variant: ButtonVariant.ghost,
                      ),
                      SparkleButton.ghost(
                        label: '忽略',
                        onPressed: processingIds.contains(item.id)
                            ? () {}
                            : () => onDismiss(item),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
