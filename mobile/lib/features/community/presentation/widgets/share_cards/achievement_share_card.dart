import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/visual_elements/presentation/shared/visual_element_palette.dart';

class AchievementShareCardFactory {
  static Widget fromPayload(
    UniversalSharePayload payload, {
    bool isCompact = false,
    VoidCallback? onTap,
  }) {
    final metadata = payload.metadata ?? const <String, dynamic>{};
    return Builder(
      builder: (context) {
        final l10n = context.l10n;
        final palette = VisualElementPalette.of(context);
        final provenance = metadata['earned_from']?.toString() ??
            metadata['equipped_title']?.toString();
        return GestureDetector(
          onTap: onTap,
          child: Container(
            padding: EdgeInsets.all(isCompact ? DS.spacing10 : DS.spacing12),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  palette.elevatedTint(palette.gold),
                  palette.elevatedTint(palette.cyan, 0.10),
                  palette.surface,
                ],
              ),
              borderRadius: DS.borderRadius16,
              border: Border.all(
                color: palette.gold.withValues(alpha: 0.38),
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
                        color: palette.surface.withValues(alpha: 0.82),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: palette.gold.withValues(alpha: 0.22),
                        ),
                      ),
                      child: Icon(
                        Icons.workspace_premium_rounded,
                        color: palette.gold,
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
                          color: palette.textPrimary,
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
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: palette.textSecondary,
                      height: 1.35,
                    ),
                  ),
                ],
                if (provenance != null && provenance.trim().isNotEmpty) ...[
                  const SizedBox(height: DS.spacing8),
                  _chip(
                    l10n.communityShareSource,
                    provenance,
                    palette,
                  ),
                ],
                const SizedBox(height: DS.spacing10),
                Wrap(
                  spacing: DS.spacing6,
                  runSpacing: DS.spacing6,
                  children: [
                    _chip(
                      S.communityShareRarity,
                      metadata['rarity']?.toString() ?? '荣耀',
                      palette,
                    ),
                    if (metadata['unlocked_count'] != null)
                      _chip(
                        S.communityShareUnlocked,
                        '${metadata['unlocked_count']}',
                        palette,
                      ),
                    if (metadata['flame_level'] != null)
                      _chip(
                        S.communityShareLevel,
                        'Lv.${metadata['flame_level']}',
                        palette,
                      ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  static Widget _chip(
    String label,
    String value,
    VisualElementPaletteData palette,
  ) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: palette.panel.withValues(alpha: 0.64),
          borderRadius: DS.borderRadius12,
          border: Border.all(color: palette.hairline),
        ),
        child: Text(
          '$label · $value',
          style: DS.labelSmall.copyWith(
            color: palette.textPrimary,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
      );
}
