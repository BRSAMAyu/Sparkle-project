import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/design/design_system.dart';
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

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('评分'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('选择重要程度'),
              const SizedBox(height: DS.lg),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (index) {
                  final starValue = index + 1;
                  return IconButton(
                    iconSize: 40,
                    onPressed: () {
                      setDialogState(() {
                        _selectedRatings[id] = starValue;
                      });
                    },
                    icon: Icon(
                      Icons.star,
                      color: (_selectedRatings[id] ?? currentRating) >= starValue
                          ? Colors.amber
                          : DS.neutral300,
                    ),
                  );
                }),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('取消'),
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
              child: const Text('确定'),
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
        title: const Text('删除翻译'),
        content: Text('确定要删除这条翻译记录吗？\n\n${item.originalText}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(backgroundColor: DS.error),
            child: const Text('删除'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      await ref.read(translationHistoryProvider.notifier).delete(item.id);
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(translationHistoryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('翻译历史'),
        elevation: 0,
        actions: [
          if (state.records.isNotEmpty)
            PopupMenuButton<String>(
              onSelected: (value) async {
                if (value == 'deleteAll') {
                  final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: const Text('清空历史'),
                      content: const Text('确定要清空所有翻译历史吗？'),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context, false),
                          child: const Text('取消'),
                        ),
                        FilledButton(
                          onPressed: () => Navigator.pop(context, true),
                          style: FilledButton.styleFrom(backgroundColor: DS.error),
                          child: const Text('清空'),
                        ),
                      ],
                    ),
                  );
                  if (confirmed == true && mounted) {
                    await ref
                        .read(translationHistoryProvider.notifier)
                        .deleteAll();
                  }
                }
              },
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'deleteAll',
                  child: Row(
                    children: [
                      Icon(Icons.delete_forever, color: DS.error),
                      SizedBox(width: DS.sm),
                      Text('清空历史'),
                    ],
                  ),
                ),
              ],
            ),
        ],
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(DS.md),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: '搜索翻译记录...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          ref
                              .read(translationHistoryProvider.notifier)
                              .clearSearch();
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onChanged: (value) {
                ref
                    .read(translationHistoryProvider.notifier)
                    .search(value);
              },
            ),
          ),

          // Filter chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: DS.md),
            child: Row(
              children: [
                _FilterChip(
                  label: '全部',
                  isSelected: state.filter == TranslationFilter.all,
                  count: state.statistics['total'] ?? 0,
                  onTap: () => ref
                      .read(translationHistoryProvider.notifier)
                      .setFilter(TranslationFilter.all),
                ),
                const SizedBox(width: DS.sm),
                _FilterChip(
                  label: '收藏',
                  isSelected: state.filter == TranslationFilter.favorites,
                  count: state.statistics['favorites'] ?? 0,
                  icon: Icons.star,
                  onTap: () => ref
                      .read(translationHistoryProvider.notifier)
                      .setFilter(TranslationFilter.favorites),
                ),
                const SizedBox(width: DS.sm),
                _FilterChip(
                  label: '重要',
                  isSelected: state.filter == TranslationFilter.highRating,
                  count: state.statistics['highRated'] ?? 0,
                  icon: Icons.grade,
                  onTap: () => ref
                      .read(translationHistoryProvider.notifier)
                      .setFilter(TranslationFilter.highRating),
                ),
                const SizedBox(width: DS.sm),
                _FilterChip(
                  label: '最近',
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
                        padding: const EdgeInsets.symmetric(horizontal: DS.md),
                        itemCount: state.records.length,
                        itemBuilder: (context, index) {
                          final item = state.records[index];
                          return _TranslationCard(
                            item: item,
                            languageCodeToFlag: _languageCodeToFlag,
                            onRatingTap: () => _showRatingDialog(item.id, item.rating),
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
    );
  }

  Widget _buildEmptyState(TranslationHistoryState state) {
    IconData icon;
    String title;
    String? subtitle;

    if (state.searchQuery.isNotEmpty) {
      icon = Icons.search_off;
      title = '未找到结果';
      subtitle = '尝试其他关键词';
    } else if (state.filter == TranslationFilter.favorites) {
      icon = Icons.star_border;
      title = '暂无收藏';
      subtitle = '给翻译打星标收藏起来';
    } else if (state.filter == TranslationFilter.highRating) {
      icon = Icons.grade;
      title = '暂无重要翻译';
      subtitle = '给4星及以上的翻译会显示在这里';
    } else {
      icon = Icons.translate;
      title = '暂无翻译记录';
      subtitle = '使用翻译功能后会自动保存';
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
          if (subtitle != null) ...[
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
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? Colors.purple : DS.neutral100,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: 16,
                color: isSelected ? Colors.white : DS.neutral600,
              ),
              const SizedBox(width: 4),
            ],
            Text(
              label,
              style: TextStyle(
                color: isSelected ? Colors.white : DS.neutral700,
                fontSize: 13,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
            if (count != null) ...[
              const SizedBox(width: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: isSelected
                      ? Colors.white.withValues(alpha: 0.2)
                      : DS.neutral200,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '$count',
                  style: TextStyle(
                    color: isSelected ? Colors.white : DS.neutral600,
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
}

class _TranslationCard extends StatelessWidget {
  const _TranslationCard({
    required this.item,
    required this.languageCodeToFlag,
    required this.onRatingTap,
    required this.onFavoriteToggle,
    required this.onDelete,
  });

  final TranslationHistoryItem item;
  final String Function(String) languageCodeToFlag;
  final VoidCallback onRatingTap;
  final VoidCallback onFavoriteToggle;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Card(
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
                  IconButton(
                    iconSize: 20,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    icon: Icon(
                      item.isFavorited ? Icons.star : Icons.star_border,
                      color: item.isFavorited ? Colors.amber : DS.neutral400,
                    ),
                    onPressed: onFavoriteToggle,
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
                      children: List.generate(5, (index) {
                        return Icon(
                          Icons.star,
                          size: 16,
                          color: index < item.rating ? Colors.amber : DS.neutral300,
                        );
                      }),
                    ),
                  ),
                  const SizedBox(width: DS.md),

                  // Date
                  Text(
                    _formatDate(item.createdAt),
                    style: TextStyle(
                      fontSize: 12,
                      color: DS.neutral500,
                    ),
                  ),
                  const Spacer(),

                  // Delete button
                  IconButton(
                    iconSize: 18,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    icon: Icon(
                      Icons.delete_outline,
                      color: DS.error.withValues(alpha: 0.7),
                    ),
                    onPressed: onDelete,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inDays == 0) {
      return '今天';
    } else if (diff.inDays == 1) {
      return '昨天';
    } else if (diff.inDays < 7) {
      return '${diff.inDays}天前';
    } else {
      return '${date.month}/${date.day}';
    }
  }
}
