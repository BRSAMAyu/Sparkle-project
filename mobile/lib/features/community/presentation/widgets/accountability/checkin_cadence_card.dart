import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';

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
    final formattedTime = DateFormat('MM/dd HH:mm').format(nextCheckInAt);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '伙伴打卡节奏',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              '$cadenceDays 天一次，下一次提醒是 $formattedTime',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (milestoneLabel != null) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                '绑定里程碑：$milestoneLabel',
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
