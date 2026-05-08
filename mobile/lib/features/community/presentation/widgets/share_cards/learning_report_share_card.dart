import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/universal_share_service.dart';

class LearningReportShareCardFactory {
  static Widget fromPayload(
    UniversalSharePayload payload, {
    bool isCompact = false,
    VoidCallback? onTap,
  }) {
    final metadata = payload.metadata ?? const <String, dynamic>{};
    return Builder(
      builder: (context) {
        final l10n = context.l10n;
        return GestureDetector(
          onTap: onTap,
          child: Container(
            padding: EdgeInsets.all(isCompact ? DS.spacing10 : DS.spacing12),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFFEAF3FF),
                  Color(0xFFDCE7FF),
                ],
              ),
              borderRadius: DS.borderRadius16,
              border: Border.all(
                color: const Color(0xFF8FB5F5).withValues(alpha: 0.58),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Container(
                      width: isCompact ? 34 : 40,
                      height: isCompact ? 34 : 40,
                      decoration: BoxDecoration(
                        color: DS.neutral0.withValues(alpha: 0.72),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(
                        Icons.insights_rounded,
                        color: Color(0xFF3F6FD9),
                      ),
                    ),
                    const SizedBox(width: DS.spacing10),
                    Expanded(
                      child: Text(
                        payload.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: isCompact ? DS.fontSizeSm : DS.fontSizeBase,
                          fontWeight: DS.fontWeightBold,
                          color: const Color(0xFF1B315C),
                          height: 1.15,
                        ),
                      ),
                    ),
                  ],
                ),
                if ((payload.subtitle ?? '').trim().isNotEmpty) ...[
                  const SizedBox(height: DS.spacing8),
                  Text(
                    payload.subtitle!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: Color(0xFF516B93),
                      height: 1.35,
                    ),
                  ),
                ],
                const SizedBox(height: DS.spacing10),
                Wrap(
                  spacing: DS.spacing6,
                  runSpacing: DS.spacing6,
                  children: [
                    if (metadata['active_plans'] != null)
                      _chip(l10n.communityShareActivePlans,
                          '${metadata['active_plans']}'),
                    if (metadata['unlocked_achievements'] != null)
                      _chip(l10n.communityShareAchievements,
                          '${metadata['unlocked_achievements']}'),
                    if (metadata['flame_brightness'] != null)
                      _chip(l10n.communityShareBrightness,
                          metadata['flame_brightness'].toString()),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  static Widget _chip(String label, String value) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.neutral0.withValues(alpha: 0.7),
          borderRadius: DS.borderRadius12,
        ),
        child: Text(
          '$label · $value',
          style: DS.labelSmall.copyWith(
            color: const Color(0xFF31507C),
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
      );
}
