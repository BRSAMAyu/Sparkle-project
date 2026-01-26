import 'package:flutter/material.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';

/// Seed Library Card Widget
/// Displays a seed library in a card format
class SeedLibraryCard extends StatelessWidget {
  const SeedLibraryCard({
    super.key,
    required this.library,
    this.onTap,
    this.onLongPress,
  });

  final SeedLibrary library;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        onLongPress: onLongPress,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                children: [
                  // Icon based on category
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: _getCategoryColor().withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(
                      _getCategoryIcon(),
                      color: _getCategoryColor(),
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          library.name,
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (library.description != null)
                          Text(
                            library.description!,
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: Colors.grey[600],
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
                        const Icon(
                          Icons.verified,
                          color: Colors.amber,
                          size: 20,
                        ),
                      if (library.isFeatured)
                        Icon(
                          Icons.star,
                          color: Colors.orange.shade700,
                          size: 20,
                        ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Category and visibility badges
              Wrap(
                spacing: 8,
                children: [
                  Chip(
                    label: Text(library.categoryDisplayName),
                    visualDensity: VisualDensity.compact,
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  ),
                  Chip(
                    label: Text(library.visibilityDisplayName),
                    visualDensity: VisualDensity.compact,
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    backgroundColor: library.visibility == LibraryVisibility.official
                        ? Colors.amber.shade100
                        : null,
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Stats row
              Row(
                children: [
                  _buildStat(
                    context,
                    Icons.article_outlined,
                    '${library.itemCount}',
                    '内容',
                  ),
                  const SizedBox(width: 16),
                  _buildStat(
                    context,
                    Icons.people_outline,
                    '${library.subscriberCount}',
                    '订阅',
                  ),
                  const SizedBox(width: 16),
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
                        const Icon(Icons.star, size: 16, color: Colors.amber),
                        const SizedBox(width: 4),
                        Text(
                          library.qualityScore!.toStringAsFixed(1),
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Colors.amber.shade700,
                              ),
                        ),
                      ],
                    ),
                ],
              ),

              // Tags
              if (library.tags != null && library.tags!.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: library.tags!.take(3).map((tag) {
                    return Chip(
                      label: Text(
                        tag,
                        style: const TextStyle(fontSize: 12),
                      ),
                      visualDensity: VisualDensity.compact,
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      side: BorderSide.none,
                      backgroundColor: Colors.grey.shade200,
                    );
                  }).toList(),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStat(BuildContext context, IconData icon, String value, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: Colors.grey[600]),
        const SizedBox(width: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
        ),
        const SizedBox(width: 2),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey[600],
                fontSize: 12,
              ),
        ),
      ],
    );
  }

  IconData _getCategoryIcon() {
    switch (library.category) {
      case LibraryCategory.fewShot:
        return Icons.flash_on;
      case LibraryCategory.teachingContent:
        return Icons.school;
      case LibraryCategory.replyTemplate:
        return Icons.template;
      case LibraryCategory.custom:
        return Icons.folder;
    }
  }

  Color _getCategoryColor() {
    switch (library.category) {
      case LibraryCategory.fewShot:
        return Colors.blue;
      case LibraryCategory.teachingContent:
        return Colors.green;
      case LibraryCategory.replyTemplate:
        return Colors.purple;
      case LibraryCategory.custom:
        return Colors.grey;
    }
  }
}
