import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/user_state_models.dart';

class EngagementStateBadge extends StatelessWidget {
  const EngagementStateBadge({required this.state, super.key});

  final UserStateFieldEnvelope<Stage35EngagementState>? state;

  @override
  Widget build(BuildContext context) {
    final value = state?.value;
    return GraphiteCardSurface(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.userEngagementState,
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                _StatusChip(
                    label: context.l10n.engageSessions7d(value?.sessionCount7d ?? 0)),
                _StatusChip(
                    label: context.l10n.engageDayStreak(value?.streak ?? 0)),
                _StatusChip(
                  label: value?.lastActiveAt != null
                      ? context.l10n.engageLastActive(DateFormat(context.l10n.engageDateFormat).format(value!.lastActiveAt!))
                      : context.l10n.userNoRecentActivity,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: isDark
            ? DS.success.withValues(alpha: 0.12)
            : const Color(0xFFEAF2E8),
        borderRadius: DS.borderRadius20,
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: DS.bodySmall.copyWith(
          color: DS.textPrimary,
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    );
  }
}
