import 'package:flutter/material.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';

/// Seed Item Card Widget
/// Displays a seed item in a card format
class SeedItemCard extends StatelessWidget {
  const SeedItemCard({
    required this.item, super.key,
    this.onTap,
    this.onEdit,
    this.onDelete,
  });

  final SeedItem item;
  final VoidCallback? onTap;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) => Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              // Type icon
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: _getItemTypeColor().withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  _getItemTypeIcon(),
                  color: _getItemTypeColor(),
                  size: 24,
                ),
              ),
              const SizedBox(width: 12),

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
                            style: Theme.of(context).textTheme.titleSmall?.copyWith(
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
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: _getDifficultyColor().withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: _getDifficultyColor(),
                              ),
                            ),
                            child: Text(
                              item.difficultyLevelDisplayName!,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: _getDifficultyColor(),
                              ),
                            ),
                          ),
                      ],
                    ),

                    // Content preview
                    if (item.content != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          item.content!,
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Colors.grey[700],
                              ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),

                    // Metadata
                    if (item.subject != null || (item.tags?.isNotEmpty ?? false))
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Wrap(
                          spacing: 6,
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
                                  horizontal: 6,
                                  vertical: 2,
                                ),
                                backgroundColor: Colors.blue.shade50,
                              ),
                            ...?item.tags?.take(2).map((tag) => Chip(
                                label: Text(
                                  tag,
                                  style: const TextStyle(fontSize: 11),
                                ),
                                visualDensity: VisualDensity.compact,
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 6,
                                  vertical: 2,
                                ),
                                backgroundColor: Colors.grey.shade200,
                              ),),
                          ],
                        ),
                      ),
                  ],
                ),
              ),

              // Action buttons
              if (onEdit != null || onDelete != null)
                PopupMenuButton<String>(
                  icon: const Icon(Icons.more_vert),
                  onSelected: (value) {
                    switch (value) {
                      case 'edit':
                        onEdit?.call();
                      case 'delete':
                        _showDeleteDialog(context);
                    }
                  },
                  itemBuilder: (context) => [
                    if (onEdit != null)
                      const PopupMenuItem(
                        value: 'edit',
                        child: Row(
                          children: [
                            Icon(Icons.edit, size: 18),
                            SizedBox(width: 12),
                            Text('编辑'),
                          ],
                        ),
                      ),
                    if (onDelete != null)
                      const PopupMenuItem(
                        value: 'delete',
                        child: Row(
                          children: [
                            Icon(Icons.delete, size: 18, color: Colors.red),
                            SizedBox(width: 12),
                            Text('删除', style: TextStyle(color: Colors.red)),
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
        return Colors.amber;
      case ItemType.exercise:
        return Colors.green;
      case ItemType.knowledge:
        return Colors.purple;
      case ItemType.template:
        return Colors.blue;
      case ItemType.flashcard:
        return Colors.orange;
    }
  }

  String _getItemTypeDisplayName() => item.itemTypeDisplayName;

  Color _getDifficultyColor() {
    switch (item.difficultyLevel) {
      case DifficultyLevel.beginner:
        return Colors.green;
      case DifficultyLevel.intermediate:
        return Colors.blue;
      case DifficultyLevel.advanced:
        return Colors.orange;
      case DifficultyLevel.expert:
        return Colors.red;
      case null:
        return Colors.grey;
    }
  }

  void _showDeleteDialog(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除内容'),
        content: const Text('确定要删除这个内容吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              onDelete?.call();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }
}
