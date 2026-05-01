import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';

/// Seed Library Card Widget
/// Displays a seed library in a card format
class SeedLibraryCard extends StatelessWidget {
  const SeedLibraryCard({
    required this.library,
    super.key,
    this.onTap,
    this.onLongPress,
  });

  final SeedLibrary library;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.only(bottom: DS.spacing12),
        child: InkWell(
          onTap: onTap,
          onLongPress: onLongPress,
          borderRadius: BorderRadius.circular(DS.radius12),
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header row
                Row(
                  children: [
                    // Icon based on category
                    Container(
                      padding: const EdgeInsets.all(DS.spacing8),
                      decoration: BoxDecoration(
                        color: _getCategoryColor().withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(DS.radius8),
                      ),
                      child: Icon(
                        _getCategoryIcon(),
                        color: _getCategoryColor(),
                        size: DS.iconSizeBase,
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            library.name,
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          if (library.description != null)
                            Text(
                              library.description!,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                        ],
                      ),
                    ),
                    // Badges
                    Column(
                      children: [
                        if (library.isOfficial)
                          Icon(
                            Icons.verified,
                            color: DS.warning,
                            size: DS.iconSizeSm,
                          ),
                        if (library.isFeatured)
                          Icon(
                            Icons.star,
                            color: DS.warningLight,
                            size: DS.iconSizeSm,
                          ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing12),

                // Category and visibility badges
                Wrap(
                  spacing: DS.spacing8,
                  children: [
                    Chip(
                      label: Text(library.categoryLabel(context.l10n)),
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: DS.spacing4,
                      ),
                    ),
                    Chip(
                      label: Text(library.visibilityLabel(context.l10n)),
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: DS.spacing4,
                      ),
                      backgroundColor:
                          library.visibility == LibraryVisibility.official
                              ? DS.warningAccent
                              : null,
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing12),

                // Stats row
                Row(
                  children: [
                    _buildStat(
                      context,
                      Icons.article_outlined,
                      '${library.itemCount}',
                      '内容',
                    ),
                    const SizedBox(width: DS.spacing16),
                    _buildStat(
                      context,
                      Icons.people_outline,
                      '${library.subscriberCount}',
                      '订阅',
                    ),
                    const SizedBox(width: DS.spacing16),
                    _buildStat(
                      context,
                      Icons.visibility_outlined,
                      '${library.usageCount}',
                      '使用',
                    ),
                    const Spacer(),
                    if (library.qualityScore != null)
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.star,
                              size: DS.iconSizeXs, color: DS.warning,),
                          const SizedBox(width: DS.spacing4),
                          Text(
                            library.qualityScore!.toStringAsFixed(1),
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: DS.warningLight,
                                ),
                          ),
                        ],
                      ),
                  ],
                ),

                // Tags
                if (library.tags != null && library.tags!.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing12),
                  Wrap(
                    spacing: DS.spacing6,
                    runSpacing: DS.spacing6,
                    children: library.tags!
                        .take(3)
                        .map(
                          (tag) => Chip(
                            label: Text(
                              tag,
                              style: const TextStyle(fontSize: DS.fontSizeXs),
                            ),
                            visualDensity: VisualDensity.compact,
                            padding: const EdgeInsets.symmetric(
                              horizontal: DS.spacing6,
                              vertical: 2,
                            ),
                            side: BorderSide.none,
                            backgroundColor: DS.surfaceTertiary,
                          ),
                        )
                        .toList(),
                  ),
                ],
              ],
            ),
          ),
        ),
      );

  Widget _buildStat(
          BuildContext context, IconData icon, String value, String label,) =>
      Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: DS.iconSizeXs, color: DS.textSecondary),
          const SizedBox(width: DS.spacing4),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: DS.fontWeightMedium,
                ),
          ),
          const SizedBox(width: 2),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  fontSize: DS.fontSizeXs,
                ),
          ),
        ],
      );

  IconData _getCategoryIcon() {
    switch (library.category) {
      case LibraryCategory.fewShot:
        return Icons.flash_on;
      case LibraryCategory.teachingContent:
        return Icons.school;
      case LibraryCategory.replyTemplate:
        return Icons.note;
      case LibraryCategory.custom:
        return Icons.folder;
    }
  }

  Color _getCategoryColor() {
    switch (library.category) {
      case LibraryCategory.fewShot:
        return DS.info;
      case LibraryCategory.teachingContent:
        return DS.success;
      case LibraryCategory.replyTemplate:
        return DS.brandSecondary;
      case LibraryCategory.custom:
        return DS.textSecondary;
    }
  }
}
