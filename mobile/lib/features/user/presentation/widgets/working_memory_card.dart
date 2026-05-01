import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/user_state_models.dart';
import 'package:sparkle/core/services/i18n_service.dart';

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
                              style: DS.bodyMedium.copyWith(
                                color: DS.textPrimary,
                                fontWeight: DS.fontWeightSemibold,
                              ),
                            ),
                            const SizedBox(height: DS.spacing6),
                            Text(
                              _buildMeta(item),
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

  String _buildMeta(Stage35WorkingMemoryItem item) {
    final parts = <String>[
      item.subjectType,
      '提及 ${item.mentionCount} 次',
      if (item.consolidated) S.userConsolidated else S.userStillInForeground,
    ];
    if (item.lastSeenAt != null) {
      parts.add(DateFormat('M月d日 HH:mm').format(item.lastSeenAt!));
    }
    return parts.join(' · ');
  }
}
