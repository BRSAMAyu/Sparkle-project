import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';

/// Shared resource card with quality badge overlay.
///
/// Quality badges:
/// - score >= 0.8: gold "精选" badge
/// - score 0.6-0.8: silver "推荐" badge
/// - score < 0.4: no badge (or "新手友好" if adoption > 0)
class SharedResourceCard extends StatelessWidget {
  const SharedResourceCard({
    required this.resource,
    super.key,
    this.onTap,
    this.onAdopt,
    this.compact = false,
  });

  final SharedResourceInfo resource;
  final VoidCallback? onTap;
  final VoidCallback? onAdopt;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;

    return Semantics(
      button: true,
      label: resource.resourceTitle ?? l10n.sharedResourceTitle,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: EdgeInsets.all(compact ? 10 : 14),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: DS.borderRadius12,
            border: Border.all(color: DS.border),
          ),
          child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row: title + quality badge
            Row(
              children: [
                Expanded(
                  child: Text(
                    resource.resourceTitle ??
                        l10n.sharedResourceTitle,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (resource.qualityScore != null)
                  _QualityBadge(score: resource.qualityScore!),
              ],
            ),

            if (!compact) ...[
              const SizedBox(height: 6),
              // Sharer info
              if (resource.sharer != null)
                Text(
                  l10n.sharedResourceBySharer(resource.sharer!.nickname ?? resource.sharer!.username),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),

              // Summary
              if (resource.resourceSummary != null) ...[
                const SizedBox(height: 4),
                Text(
                  resource.resourceSummary!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textTertiary,
                      ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],

              const SizedBox(height: 8),
              // Stats row
              _StatsRow(resource: resource),

              // Adopt button
              if (onAdopt != null) ...[
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: onAdopt,
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      shape: const RoundedRectangleBorder(
                        borderRadius: DS.borderRadius8,
                      ),
                    ),
                    child: Text(
                      l10n.sharedResourceAdoptIntoPlan,
                    ),
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    ),
    );
  }
}

/// Quality badge displaying the resource quality score tier.
class _QualityBadge extends StatelessWidget {
  const _QualityBadge({required this.score});

  final double score;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;

    if (score >= 0.8) {
      return _badge(
        context,
        label: l10n.sharedResourceFeatured,
        icon: Icons.verified,
        backgroundColor: DS.warning.withValues(alpha: 0.15),
        iconColor: DS.warning,
        textColor: DS.warning,
      );
    }
    if (score >= 0.6) {
      return _badge(
        context,
        label: l10n.sharedResourceRecommended,
        icon: Icons.thumb_up_outlined,
        backgroundColor: DS.neutral400.withValues(alpha: 0.15),
        iconColor: DS.neutral500,
        textColor: DS.neutral600,
      );
    }
    if (score < 0.4 && score > 0) {
      return _badge(
        context,
        label: l10n.sharedResourceBeginnerFriendly,
        icon: Icons.eco_outlined,
        backgroundColor: DS.neutral200.withValues(alpha: 0.65),
        iconColor: DS.neutral600,
        textColor: DS.neutral700,
      );
    }
    // No badge for score 0.4-0.6 or 0
    return const SizedBox.shrink();
  }

  Widget _badge(
    BuildContext context, {
    required String label,
    required IconData icon,
    required Color backgroundColor,
    required Color iconColor,
    required Color textColor,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: backgroundColor,
          borderRadius: DS.borderRadius8,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 12, color: iconColor),
            const SizedBox(width: 3),
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: textColor,
                    fontWeight: FontWeight.w600,
                    fontSize: 10,
                  ),
            ),
          ],
        ),
      );
}

/// Stats row showing adoption count and quality score.
class _StatsRow extends StatelessWidget {
  const _StatsRow({required this.resource});

  final SharedResourceInfo resource;

  @override
  Widget build(BuildContext context) {
    final isChinese = I18nService.instance.isChinese;
    final parts = <String>[];

    final adoption = resource.adoptionCount ?? 0;
    if (adoption > 0) {
      parts.add(
        isChinese ? '采纳 $adoption 次' : '$adoption adoptions',
      );
    }

    final rating = resource.avgRating ?? ((resource.qualityScore ?? 0) * 5);
    if (rating > 0) {
      parts.add(
        isChinese
            ? '平均评分 ${rating.toStringAsFixed(1)}'
            : 'Avg rating ${rating.toStringAsFixed(1)}',
      );
    }

    if (parts.isEmpty) return const SizedBox.shrink();

    return Text(
      parts.join(' · '),
      style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: DS.textTertiary,
          ),
    );
  }
}
