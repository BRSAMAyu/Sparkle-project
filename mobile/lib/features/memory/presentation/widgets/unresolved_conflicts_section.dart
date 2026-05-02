import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class UnresolvedConflictsSection extends StatelessWidget {
  const UnresolvedConflictsSection({
    super.key,
    this.items = const [],
    this.processingIds = const {},
    this.onSelectLeft,
    this.onSelectRight,
    this.onSelectNone,
  });

  final List<UnresolvedConflictItem> items;
  final Set<String> processingIds;
  final Future<void> Function(UnresolvedConflictItem)? onSelectLeft;
  final Future<void> Function(UnresolvedConflictItem)? onSelectRight;
  final Future<void> Function(UnresolvedConflictItem)? onSelectNone;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(DS.md, DS.md, DS.md, DS.sm),
          child: Text(
            I18nService.instance.isChinese ? '冲突记录' : 'Conflict Records',
            style: DS.labelLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ),
        ...items.map(
          (c) => Card(
            margin: const EdgeInsets.symmetric(horizontal: DS.md, vertical: DS.xs),
            child: Padding(
              padding: const EdgeInsets.all(DS.sm),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(c.conflictKey, style: DS.bodySmall),
                  Text(
                    '${c.leftCandidate.summary} vs ${c.rightCandidate.summary}',
                    style: DS.labelSmall.copyWith(color: DS.textSecondary),
                  ),
                  const SizedBox(height: DS.xs),
                  if (processingIds.contains(c.id))
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  else
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed: () => onSelectLeft?.call(c),
                          child: const Text('A'),
                        ),
                        TextButton(
                          onPressed: () => onSelectRight?.call(c),
                          child: const Text('B'),
                        ),
                        TextButton(
                          onPressed: () => onSelectNone?.call(c),
                          child: Text(context.l10n.memSkip),
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
