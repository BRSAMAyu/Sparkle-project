import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/user_state_models.dart';

class WorkingMemoryCard extends StatelessWidget {
  const WorkingMemoryCard({required this.snapshot, super.key});

  final UserStateFieldEnvelope<Stage35WorkingMemorySnapshot>? snapshot;

  @override
  Widget build(BuildContext context) {
    final items = snapshot?.value.items ?? const <Stage35WorkingMemoryItem>[];
    return GraphiteCardSurface(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.userWorkingMemory,
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.userWorkingMemoryHint,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing12),
            if (items.isEmpty)
              Text(
                context.l10n.userWorkingMemoryEmpty,
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              ),
            if (items.isNotEmpty)
              ...items.take(3).map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing10),
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(DS.spacing12),
                        decoration: BoxDecoration(
                          color: DS.surfaceSecondary,
                          borderRadius: DS.borderRadius16,
                        ),
                          child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item.summary,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: DS.bodyMedium.copyWith(
                                color: DS.textPrimary,
                                fontWeight: DS.fontWeightSemibold,
                              ),
                            ),
                            const SizedBox(height: DS.spacing6),
                            Text(
                              _buildMeta(context, item),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: DS.bodySmall.copyWith(
                                color: DS.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
          ],
        ),
      ),
    );
  }

  String _buildMeta(BuildContext context, Stage35WorkingMemoryItem item) {
    final parts = <String>[
      item.subjectType,
      context.l10n.workMemMentioned(item.mentionCount),
      if (item.consolidated)
        context.l10n.workMemConsolidated
      else
        context.l10n.workMemStillInForeground,
    ];
    if (item.lastSeenAt != null) {
      parts.add(DateFormat(context.l10n.workMemDateFormat)
          .format(item.lastSeenAt!));
    }
    return parts.join(' · ');
  }
}
