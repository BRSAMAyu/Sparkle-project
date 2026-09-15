import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class PartnerVisibilityBanner extends StatelessWidget {
  const PartnerVisibilityBanner({
    required this.summary,
    super.key,
    this.isOwner = false,
    this.redactedFields = const [],
  });

  final String summary;
  final bool isOwner;
  final List<String> redactedFields;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final title = isOwner
        ? l10n.communityYouSeeFullView
        : l10n.communityPartnerSeesSummary;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(DS.borderRadiusMD),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.xs),
          Text(summary),
          if (redactedFields.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              '${l10n.communityHidden}: ${redactedFields.join('、')}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}
