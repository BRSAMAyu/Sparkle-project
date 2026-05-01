import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class AchievementShareCardFactory {
  static Widget fromPayload(
    UniversalSharePayload payload, {
    bool isCompact = false,
    VoidCallback? onTap,
  }) {
    final metadata = payload.metadata ?? const <String, dynamic>{};
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.all(isCompact ? DS.spacing10 : DS.spacing12),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFFFFF4D6),
              Color(0xFFFFE2A8),
            ],
          ),
          borderRadius: DS.borderRadius16,
          border: Border.all(
            color: const Color(0xFFF0C676).withValues(alpha: 0.6),
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
                    color: DS.neutral0.withValues(alpha: 0.75),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.workspace_premium_rounded,
                    color: Color(0xFFB8860B),
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
                      color: const Color(0xFF3A2A10),
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
                  color: Color(0xFF6F5A34),
                  height: 1.35,
                ),
              ),
            ],
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing6,
              runSpacing: DS.spacing6,
              children: [
                _chip(S.communityShareRarity,
                    metadata['rarity']?.toString() ?? '荣耀'),
                if (metadata['unlocked_count'] != null)
                  _chip(S.communityShareUnlocked,
                      '${metadata['unlocked_count']}'),
                if (metadata['flame_level'] != null)
                  _chip(S.communityShareLevel, 'Lv.${metadata['flame_level']}'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  static Widget _chip(String label, String value) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.neutral0.withValues(alpha: 0.66),
          borderRadius: DS.borderRadius12,
        ),
        child: Text(
          '$label · $value',
          style: DS.labelSmall.copyWith(
            color: const Color(0xFF5A4318),
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
      );
}
