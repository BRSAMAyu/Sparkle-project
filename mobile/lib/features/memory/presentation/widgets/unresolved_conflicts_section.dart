import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';

class UnresolvedConflictsSection extends StatelessWidget {
  const UnresolvedConflictsSection({
    super.key,
    required this.items,
    required this.processingIds,
    required this.onSelectLeft,
    required this.onSelectRight,
    required this.onSelectNone,
  });

  final List<UnresolvedConflictItem> items;
  final Set<String> processingIds;
  final Future<void> Function(UnresolvedConflictItem item) onSelectLeft;
  final Future<void> Function(UnresolvedConflictItem item) onSelectRight;
  final Future<void> Function(UnresolvedConflictItem item) onSelectNone;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '待你确认',
          style:
              TextStyle(fontSize: DS.fontSizeLg, fontWeight: DS.fontWeightBold),
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
                  _ConflictCandidateCard(
                    title: '候选 A',
                    candidate: item.leftCandidate,
                  ),
                  const SizedBox(height: DS.sm),
                  _ConflictCandidateCard(
                    title: '候选 B',
                    candidate: item.rightCandidate,
                  ),
                  const SizedBox(height: DS.sm),
                  Wrap(
                    spacing: DS.sm,
                    runSpacing: DS.sm,
                    children: [
                      SparkleButton.ghost(
                        label: processingIds.contains(item.id) ? '处理中' : '选 A',
                        onPressed: processingIds.contains(item.id)
                            ? () {}
                            : () => onSelectLeft(item),
                      ),
                      SparkleButton.ghost(
                        label: processingIds.contains(item.id) ? '处理中' : '选 B',
                        onPressed: processingIds.contains(item.id)
                            ? () {}
                            : () => onSelectRight(item),
                      ),
                      SparkleButton.ghost(
                        label: processingIds.contains(item.id) ? '处理中' : '都不对',
                        onPressed: processingIds.contains(item.id)
                            ? () {}
                            : () => onSelectNone(item),
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

class _ConflictCandidateCard extends StatelessWidget {
  const _ConflictCandidateCard({
    required this.title,
    required this.candidate,
  });

  final String title;
  final UnresolvedConflictCandidate candidate;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.sm),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(DS.radius12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: DS.fontWeightBold)),
            const SizedBox(height: DS.xs),
            Text(candidate.summary),
            const SizedBox(height: DS.xs),
            Text(
              'evidence_token: ${candidate.evidenceToken ?? '无'}',
              style:
                  TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
            ),
          ],
        ),
      );
}
