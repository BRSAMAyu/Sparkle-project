import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/display/lexicon/date_formatting.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/memory_models.dart';


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
            context.l10n.auto_pendingcommitments,
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
                          // S2 例2：截止时间经唯一格式化入口人话化，禁毫秒直出。
                          '${context.l10n.displayDueLabel}: '
                          '${formatSparkleDateTime(c.dueAt, context.l10n)}',
                          style:
                              DS.labelSmall.copyWith(color: DS.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  if (processingIds.contains(c.id))
                    LoadingIndicator.circular(
                        size: 16,
                        strokeWidth: 2,
                        liveRegion: false,
                    )
                  else ...[
                    // 乙式（A11Y-BATCH5）：tooltip+Icon semanticLabel 同键单节点。
                    IconButton(
                      tooltip: context.l10n.memoryCommitmentResolve,
                      onPressed: () => onResolve?.call(c),
                      icon: Icon(
                        Icons.check,
                        size: 16,
                        semanticLabel: context.l10n.memoryCommitmentResolve,
                      ),
                    ),
                    IconButton(
                      tooltip: context.l10n.memoryCommitmentDismiss,
                      onPressed: () => onDismiss?.call(c),
                      icon: Icon(
                        Icons.close,
                        size: 16,
                        semanticLabel: context.l10n.memoryCommitmentDismiss,
                      ),
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
