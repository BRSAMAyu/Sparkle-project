import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';

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
    final zh = I18nService.instance.isChinese;
    final title = isOwner
        ? (zh ? '你看到完整视图' : 'You see the full view')
        : (zh ? '伙伴只看到摘要' : 'Partner sees summary only');

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
              '${zh ? '已隐藏' : 'Hidden'}：${redactedFields.join('、')}',
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
