import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class AccountabilityCheckInCadenceCard extends StatelessWidget {
  const AccountabilityCheckInCadenceCard({
    required this.cadenceDays,
    required this.nextCheckInAt,
    super.key,
    this.milestoneLabel,
  });

  final int cadenceDays;
  final DateTime nextCheckInAt;
  final String? milestoneLabel;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final formattedTime = DateFormat('MM/dd HH:mm').format(nextCheckInAt);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.communityPartnerCheckinCadence,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              l10n.communityCadenceReminder(cadenceDays, formattedTime),
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (milestoneLabel != null) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                l10n.communityBoundMilestone(milestoneLabel!),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
