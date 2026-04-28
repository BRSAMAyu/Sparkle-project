import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Seed Item Card Widget
/// Displays a seed item in a card format
class SeedItemCard extends StatelessWidget {
  const SeedItemCard({
    required this.item,
    super.key,
    this.onTap,
    this.onShare,
    this.onEdit,
    this.onDelete,
  });

  final SeedItem item;
  final VoidCallback? onTap;
  final VoidCallback? onShare;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.only(bottom: DS.spacing8),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(DS.radius12),
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing12),
            child: Row(
              children: [
                // Type icon
                Container(
                  padding: const EdgeInsets.all(DS.spacing10),
                  decoration: BoxDecoration(
                    color: _getItemTypeColor().withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    _getItemTypeIcon(),
                    color: _getItemTypeColor(),
                    size: DS.iconSizeBase,
                  ),
                ),
                const SizedBox(width: DS.spacing12),

                // Content
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Title row
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              item.title ?? _getItemTypeDisplayName(),
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          // Difficulty badge
                          if (item.difficultyLevel != null)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.spacing8,
                                vertical: DS.spacing4,
                              ),
                              decoration: BoxDecoration(
                                color: _getDifficultyColor()
                                    .withValues(alpha: 0.2),
                                borderRadius:
                                    BorderRadius.circular(DS.radius12),
                                border: Border.all(
                                  color: _getDifficultyColor(),
                                ),
                              ),
                              child: Text(
                                item.difficultyLevelDisplayName!,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: DS.fontWeightSemibold,
                                  color: _getDifficultyColor(),
                                ),
                              ),
                            ),
                        ],
                      ),

                      // Content preview
                      if (item.content != null)
                        Padding(
                          padding: const EdgeInsets.only(top: DS.spacing4),
                          child: IgnorePointer(
                            child: ClipRect(
                              child: ConstrainedBox(
                                constraints:
                                    const BoxConstraints(maxHeight: 42),
                                child: SparkleMarkdown(
                                  content: item.content!,
                                  textColor: DS.textSecondary,
                                  codeBackgroundColor: DS.surfaceTertiary,
                                  linkColor: DS.primaryBase,
                                  fontSize: 13,
                                  lineHeight: 1.4,
                                  contentRole: SparkleMarkdownRole.seedBody,
                                ),
                              ),
                            ),
                          ),
                        ),

                      // Metadata
                      if (item.subject != null ||
                          (item.tags?.isNotEmpty ?? false))
                        Padding(
                          padding: const EdgeInsets.only(top: DS.spacing6),
                          child: Wrap(
                            spacing: DS.spacing6,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              if (item.subject != null)
                                Chip(
                                  label: Text(
                                    item.subject!,
                                    style: const TextStyle(fontSize: 11),
                                  ),
                                  visualDensity: VisualDensity.compact,
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: DS.spacing6,
                                    vertical: 2,
                                  ),
                                  backgroundColor:
                                      DS.info.withValues(alpha: 0.1),
                                ),
                              ...?item.tags?.take(2).map(
                                    (tag) => Chip(
                                      label: Text(
                                        tag,
                                        style: const TextStyle(fontSize: 11),
                                      ),
                                      visualDensity: VisualDensity.compact,
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: DS.spacing6,
                                        vertical: 2,
                                      ),
                                      backgroundColor: DS.surfaceTertiary,
                                    ),
                                  ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),

                // Action buttons
                if (onShare != null || onEdit != null || onDelete != null)
                  PopupMenuButton<String>(
                    icon: const Icon(Icons.more_vert),
                    onSelected: (value) {
                      if (value == 'share') {
                        onShare?.call();
                      } else if (value == 'edit') {
                        onEdit?.call();
                      } else if (value == 'delete') {
                        _showDeleteDialog(context);
                      }
                    },
                    itemBuilder: (context) => [
                      if (onShare != null)
                        const PopupMenuItem(
                          value: 'share',
                          child: Row(
                            children: [
                              Icon(Icons.share_outlined, size: 18),
                              SizedBox(width: DS.spacing12),
                              Text(context.l10n.seedShare),
                            ],
                          ),
                        ),
                      if (onEdit != null)
                        const PopupMenuItem(
                          value: 'edit',
                          child: Row(
                            children: [
                              Icon(Icons.edit, size: 18),
                              SizedBox(width: DS.spacing12),
                              Text(context.l10n.seedEdit),
                            ],
                          ),
                        ),
                      if (onDelete != null)
                        PopupMenuItem(
                          value: 'delete',
                          child: Row(
                            children: [
                              Icon(Icons.delete, size: 18, color: DS.error),
                              const SizedBox(width: DS.spacing12),
                              Text(context.l10n.seedDelete, style: TextStyle(color: DS.error)),
                            ],
                          ),
                        ),
                    ],
                  ),
              ],
            ),
          ),
        ),
      );

  IconData _getItemTypeIcon() {
    switch (item.itemType) {
      case ItemType.example:
        return Icons.lightbulb_outline;
      case ItemType.exercise:
        return Icons.fitness_center;
      case ItemType.knowledge:
        return Icons.psychology;
      case ItemType.template:
        return Icons.content_copy;
      case ItemType.flashcard:
        return Icons.style;
    }
  }

  Color _getItemTypeColor() {
    switch (item.itemType) {
      case ItemType.example:
        return DS.warning;
      case ItemType.exercise:
        return DS.success;
      case ItemType.knowledge:
        return DS.brandSecondary;
      case ItemType.template:
        return DS.info;
      case ItemType.flashcard:
        return DS.warningLight;
    }
  }

  String _getItemTypeDisplayName() => item.itemTypeDisplayName;

  Color _getDifficultyColor() {
    switch (item.difficultyLevel) {
      case DifficultyLevel.beginner:
        return DS.success;
      case DifficultyLevel.intermediate:
        return DS.info;
      case DifficultyLevel.advanced:
        return DS.warningLight;
      case DifficultyLevel.expert:
        return DS.error;
      case null:
        return DS.textSecondary;
    }
  }

  void _showDeleteDialog(BuildContext context) {
    unawaited(
      showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text(context.l10n.seedDeleteContent),
          content: const Text(context.l10n.seedDeleteConfirm),
          actions: [
            SparkleButton.ghost(
              onPressed: () => Navigator.pop(context),
              label: context.l10n.toolsWbCancel,
            ),
            SparkleButton.destructive(
              onPressed: () {
                Navigator.pop(context);
                onDelete?.call();
              },
              label: context.l10n.seedDelete,
            ),
          ],
        ),
      ),
    );
  }
}
