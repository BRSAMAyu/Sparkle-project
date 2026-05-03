import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

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
    final zh = I18nService.instance.isChinese;
    final formattedTime = DateFormat('MM/dd HH:mm').format(nextCheckInAt);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.communityPartnerCheckinCadence,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              zh ? '$cadenceDays 天一次，下一次提醒是 $formattedTime' : 'Every $cadenceDays days, next reminder at $formattedTime',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (milestoneLabel != null) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                zh ? '绑定里程碑：$milestoneLabel' : 'Milestone: $milestoneLabel',
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
