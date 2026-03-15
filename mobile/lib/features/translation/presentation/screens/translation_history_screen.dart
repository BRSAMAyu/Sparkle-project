import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/translation/data/repositories/local_translation_repository.dart';
import 'package:sparkle/features/translation/presentation/providers/translation_history_provider.dart';

/// Translation history screen
class TranslationHistoryScreen extends ConsumerStatefulWidget {
  const TranslationHistoryScreen({super.key});

  @override
  ConsumerState<TranslationHistoryScreen> createState() =>
      _TranslationHistoryScreenState();
}

class _TranslationHistoryScreenState
    extends ConsumerState<TranslationHistoryScreen> {
  final TextEditingController _searchController = TextEditingController();
  final Map<Id, int> _selectedRatings = {};

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  String _languageCodeToFlag(String code) {
    const flagMap = {
      'auto': '🔍',
      'zh': '🇨🇳',
      'en': '🇺🇸',
      'ja': '🇯🇵',
      'ko': '🇰🇷',
      'fr': '🇫🇷',
      'de': '🇩🇪',
      'es': '🇪🇸',
      'ru': '🇷🇺',
    };
    return flagMap[code] ?? '🌐';
  }

  void _showRatingDialog(Id id, int currentRating) {
    _selectedRatings[id] = currentRating;

    showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(context.l10n.translationRating),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(context.l10n.translationSelectImportance),
              const SizedBox(height: DS.lg),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (index) {
                  final starValue = index + 1;
                  return SparkleIconButton(
                    onPressed: () {
                      setDialogState(() {
                        _selectedRatings[id] = starValue;
                      });
                    },
                    icon: Icon(
                      Icons.star,
                      color:
                          (_selectedRatings[id] ?? currentRating) >= starValue
                              ? DS.warning
                              : DS.neutral300,
                    ),
                    variant: ButtonVariant.ghost,
                    size: DS.spacing40,
                  );
                }),
              ),
            ],
          ),
          actions: [
            SparkleButton.ghost(
              label: context.l10n.commonCancel,
              onPressed: () => Navigator.pop(context),
            ),
            FilledButton(
              onPressed: () async {
                final newRating = _selectedRatings[id] ?? currentRating;
                await ref
                    .read(translationHistoryProvider.notifier)
                    .updateRating(id, newRating);
                _selectedRatings.remove(id);
                if (mounted) Navigator.pop(context);
              },
              child: Text(context.l10n.commonOk),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showDeleteConfirmation(TranslationHistoryItem item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.translationDelete),
        content: Text('${context.l10n.translationDeleteConfirm}\n\n${item.originalText}'),
        actions: [
          SparkleButton.ghost(
            label: context.l10n.commonCancel,
            onPressed: () => Navigator.pop(context, false),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(backgroundColor: DS.error),
            child: Text(context.l10n.commonDelete),
          ),
        ],
      ),
    );

    if ((confirmed ?? false) && mounted) {
      await ref.read(translationHistoryProvider.notifier).delete(item.id);
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(translationHistoryProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.translationHistoryTitle),
        elevation: 0,
        actions: [
          if (state.records.isNotEmpty)
            PopupMenuButton<String>(
              onSelected: (value) async {
                if (value == 'deleteAll') {
                  final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: Text(context.l10n.translationClearAll),
                      content: Text(context.l10n.translationClearConfirm),
                      actions: [
                        SparkleButton.ghost(
                          label: context.l10n.commonCancel,
                          onPressed: () => Navigator.pop(context, false),
                        ),
                        FilledButton(
                          onPressed: () => Navigator.pop(context, true),
                          style:
                              FilledButton.styleFrom(backgroundColor: DS.error),
                          child: Text(context.l10n.translationClearAll),
                        ),
                      ],
                    ),
                  );
                  if ((confirmed ?? false) && mounted) {
                    await ref
                        .read(translationHistoryProvider.notifier)
                        .deleteAll();
                  }
                }
              },
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: 'deleteAll',
                  child: Row(
                    children: [
                      Icon(Icons.delete_forever, color: DS.error),
                      const SizedBox(width: DS.sm),
                      Text(context.l10n.translationClearAll),
                    ],
                  ),
                ),
              ],
            ),
        ],
      ),
      child: ContentConstraint(
        child: Column(
          children: [
            // Search bar
            Padding(
              padding: const EdgeInsets.all(DS.md),
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.panel,
                padding: EdgeInsets.zero,
                child: TextField(
                  controller: _searchController,
                  decoration: InputDecoration(
                    hintText: context.l10n.translationSearchHint,
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? SparkleIconButton(
                            icon: const Icon(Icons.clear),
                            onPressed: () {
                              _searchController.clear();
                              ref
                                  .read(translationHistoryProvider.notifier)
                                  .clearSearch();
                            },
                            variant: ButtonVariant.ghost,
                          )
                        : null,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  onChanged: (value) {
                    ref.read(translationHistoryProvider.notifier).search(value);
                  },
                ),
              ),
            ),

            // Filter chips
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: DS.md),
              child: Row(
                children: [
                  _FilterChip(
                    label: context.l10n.translationFilterAll,
                    isSelected: state.filter == TranslationFilter.all,
                    count: state.statistics['total'] ?? 0,
                    onTap: () => ref
                        .read(translationHistoryProvider.notifier)
                        .setFilter(TranslationFilter.all),
                  ),
                  const SizedBox(width: DS.sm),
                  _FilterChip(
                    label: context.l10n.translationFilterFavorites,
                    isSelected: state.filter == TranslationFilter.favorites,
                    count: state.statistics['favorites'] ?? 0,
                    icon: Icons.star,
                    onTap: () => ref
                        .read(translationHistoryProvider.notifier)
                        .setFilter(TranslationFilter.favorites),
                  ),
                  const SizedBox(width: DS.sm),
                  _FilterChip(
                    label: context.l10n.translationFilterImportant,
                    isSelected: state.filter == TranslationFilter.highRating,
                    count: state.statistics['highRated'] ?? 0,
                    icon: Icons.grade,
                    onTap: () => ref
                        .read(translationHistoryProvider.notifier)
                        .setFilter(TranslationFilter.highRating),
                  ),
                  const SizedBox(width: DS.sm),
                  _FilterChip(
                    label: context.l10n.translationFilterRecent,
                    isSelected: state.filter == TranslationFilter.recent,
                    onTap: () => ref
                        .read(translationHistoryProvider.notifier)
                        .setFilter(TranslationFilter.recent),
                  ),
                ],
              ),
            ),

            const SizedBox(height: DS.md),

            // Content
            Expanded(
              child: state.isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : state.records.isEmpty
                      ? _buildEmptyState(state)
                      : ListView.builder(
                          padding:
                              const EdgeInsets.symmetric(horizontal: DS.md),
                          itemCount: state.records.length,
                          itemBuilder: (context, index) {
                            final item = state.records[index];
                            return _TranslationCard(
                              item: item,
                              languageCodeToFlag: _languageCodeToFlag,
                              context: context,
                              onRatingTap: () =>
                                  _showRatingDialog(item.id, item.rating),
                              onFavoriteToggle: () => ref
                                  .read(translationHistoryProvider.notifier)
                                  .toggleFavorite(item.id),
                              onDelete: () => _showDeleteConfirmation(item),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(TranslationHistoryState state) {
    IconData icon;
    String title;
    String? subtitle;

    if (state.searchQuery.isNotEmpty) {
      icon = Icons.search_off;
      title = context.l10n.translationNoSearchResults;
      subtitle = context.l10n.translationTryOtherKeywords;
    } else if (state.filter == TranslationFilter.favorites) {
      icon = Icons.star_border;
      title = context.l10n.translationNoFavorites;
      subtitle = context.l10n.translationNoFavoritesHint;
    } else if (state.filter == TranslationFilter.highRating) {
      icon = Icons.grade;
      title = context.l10n.translationNoImportant;
      subtitle = context.l10n.translationNoImportantHint;
    } else {
      icon = Icons.translate;
      title = context.l10n.translationNoHistory;
      subtitle = context.l10n.translationNoRecordsHint;
    }

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 64, color: DS.neutral300),
          const SizedBox(height: DS.lg),
          Text(
            title,
            style: TextStyle(
              fontSize: 18,
              color: DS.neutral600,
              fontWeight: FontWeight.w500,
            ),
          ),
          ...[
            const SizedBox(height: DS.sm),
            Text(
              subtitle,
              style: TextStyle(color: DS.neutral400),
            ),
          ],
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
    this.count,
    this.icon,
  });

  final String label;
  final bool isSelected;
  final VoidCallback onTap;
  final int? count;
  final IconData? icon;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? DS.prismPurple : DS.neutral100,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(
                  icon,
                  size: 16,
                  color: isSelected ? DS.textOnPrimary : DS.neutral600,
                ),
                const SizedBox(width: 4),
              ],
              Text(
                label,
                style: TextStyle(
                  color: isSelected ? DS.textOnPrimary : DS.neutral700,
                  fontSize: 13,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
              if (count != null) ...[
                const SizedBox(width: 4),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? DS.textOnPrimary.withValues(alpha: 0.2)
                        : DS.neutral200,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '$count',
                    style: TextStyle(
                      color: isSelected ? DS.textOnPrimary : DS.neutral600,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      );
}

class _TranslationCard extends StatelessWidget {
  const _TranslationCard({
    required this.item,
    required this.languageCodeToFlag,
    required this.context,
    required this.onRatingTap,
    required this.onFavoriteToggle,
    required this.onDelete,
  });

  final TranslationHistoryItem item;
  final String Function(String) languageCodeToFlag;
  final BuildContext context;
  final VoidCallback onRatingTap;
  final VoidCallback onFavoriteToggle;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: InkWell(
          onTap: onRatingTap,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(DS.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header with languages and favorite
                Row(
                  children: [
                    Text(
                      '${languageCodeToFlag(item.sourceLanguage)} ${item.sourceLanguage.toUpperCase()} → '
                      '${languageCodeToFlag(item.targetLanguage)} ${item.targetLanguage.toUpperCase()}',
                      style: TextStyle(
                        fontSize: 12,
                        color: DS.neutral500,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const Spacer(),
                    InkWell(
                      onTap: onFavoriteToggle,
                      borderRadius: DS.borderRadiusFull,
                      child: Icon(
                        item.isFavorited ? Icons.star : Icons.star_border,
                        color: item.isFavorited ? DS.warning : DS.neutral400,
                        size: DS.iconSizeSm,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.sm),

                // Original text
                Text(
                  item.originalText,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: DS.sm),

                // Translated text
                Text(
                  '👉 ${item.translatedText}',
                  style: TextStyle(
                    fontSize: 14,
                    color: DS.neutral700,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: DS.md),

                // Footer with rating and date
                Row(
                  children: [
                    // Rating stars
                    GestureDetector(
                      onTap: onRatingTap,
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: List.generate(
                          5,
                          (index) => Icon(
                            Icons.star,
                            size: 16,
                            color: index < item.rating
                                ? DS.warning
                                : DS.neutral300,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: DS.md),

                    // Date
                    Text(
                      _formatDate(context, item.createdAt),
                      style: TextStyle(
                        fontSize: 12,
                        color: DS.neutral500,
                      ),
                    ),
                    const Spacer(),

                    // Delete button
                    InkWell(
                      onTap: onDelete,
                      borderRadius: DS.borderRadiusFull,
                      child: Icon(
                        Icons.delete_outline,
                        color: DS.error.withValues(alpha: 0.7),
                        size: DS.iconSizeSm,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );

  String _formatDate(BuildContext context, DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inDays == 0) {
      return context.l10n.translationToday;
    } else if (diff.inDays == 1) {
      return context.l10n.translationYesterday;
    } else if (diff.inDays < 7) {
      return context.l10n.translationDaysAgo(diff.inDays);
    } else {
      return '${date.month}/${date.day}';
    }
  }
}
