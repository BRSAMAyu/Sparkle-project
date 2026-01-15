import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Translation history item
class TranslationHistoryItem {
  final String id;
  final String sourceText;
  final String translation;
  final String sourceLang;
  final String targetLang;
  final DateTime timestamp;
  final bool isSaved;

  TranslationHistoryItem({
    required this.id,
    required this.sourceText,
    required this.translation,
    required this.sourceLang,
    required this.targetLang,
    required this.timestamp,
    this.isSaved = false,
  });
}

/// In-memory translation history provider (session-only)
///
/// TODO: Replace with persistent storage in Phase 2
final translationHistoryProvider =
    StateNotifierProvider<TranslationHistoryNotifier, List<TranslationHistoryItem>>(
  (ref) => TranslationHistoryNotifier(),
);

class TranslationHistoryNotifier extends StateNotifier<List<TranslationHistoryItem>> {
  TranslationHistoryNotifier() : super([]);

  void addTranslation({
    required String sourceText,
    required String translation,
    required String sourceLang,
    required String targetLang,
  }) {
    final item = TranslationHistoryItem(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      sourceText: sourceText,
      translation: translation,
      sourceLang: sourceLang,
      targetLang: targetLang,
      timestamp: DateTime.now(),
    );

    state = [item, ...state]; // Add to front

    // Keep max 50 items
    if (state.length > 50) {
      state = state.sublist(0, 50);
    }
  }

  void markAsSaved(String id) {
    state = [
      for (final item in state)
        if (item.id == id)
          TranslationHistoryItem(
            id: item.id,
            sourceText: item.sourceText,
            translation: item.translation,
            sourceLang: item.sourceLang,
            targetLang: item.targetLang,
            timestamp: item.timestamp,
            isSaved: true,
          )
        else
          item,
    ];
  }

  void clearHistory() {
    state = [];
  }
}

/// Side drawer for translation history
///
/// Low priority, doesn't steal focus
/// Useful for reviewing recent translations
class TranslationDrawer extends ConsumerWidget {
  const TranslationDrawer({
    this.onSaveToKnowledge,
    super.key,
  });

  final Function(TranslationHistoryItem)? onSaveToKnowledge;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(translationHistoryProvider);

    return Drawer(
      child: Column(
        children: [
          // Header
          AppBar(
            title: const Text('翻译历史'),
            backgroundColor: DS.brandPrimary,
            foregroundColor: Colors.white,
            elevation: 0,
            actions: [
              if (history.isNotEmpty)
                IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () {
                    _showClearConfirmation(context, ref);
                  },
                  tooltip: '清空历史',
                ),
            ],
          ),

          // Content
          Expanded(
            child: history.isEmpty
                ? _buildEmptyState()
                : ListView.builder(
                    itemCount: history.length,
                    itemBuilder: (context, index) {
                      final item = history[index];
                      return _buildHistoryItem(context, ref, item);
                    },
                  ),
          ),

          // Footer info
          Container(
            padding: const EdgeInsets.all(DS.md),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              border: Border(
                top: BorderSide(color: Colors.grey[300]!),
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline, size: 14, color: Colors.grey[600]),
                const SizedBox(width: DS.xs),
                Expanded(
                  child: Text(
                    '历史记录仅在当前会话有效',
                    style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.translate, size: 64, color: Colors.grey[300]),
          const SizedBox(height: DS.md),
          Text(
            '暂无翻译记录',
            style: TextStyle(fontSize: 16, color: Colors.grey[600]),
          ),
          const SizedBox(height: DS.xs),
          Text(
            '开始翻译文本后会显示在这里',
            style: TextStyle(fontSize: 13, color: Colors.grey[500]),
          ),
        ],
      ),
    );
  }

  Widget _buildHistoryItem(
    BuildContext context,
    WidgetRef ref,
    TranslationHistoryItem item,
  ) {
    return Card(
      margin: const EdgeInsets.symmetric(
        horizontal: DS.sm,
        vertical: DS.xs,
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.all(DS.sm),
        title: Text(
          item.sourceText,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: DS.xs),
            Text(
              item.translation,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 13,
                color: DS.brandPrimary,
              ),
            ),
            const SizedBox(height: DS.xs),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.grey[200],
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${item.sourceLang} → ${item.targetLang}',
                    style: const TextStyle(fontSize: 10),
                  ),
                ),
                const SizedBox(width: DS.xs),
                Text(
                  _formatTime(item.timestamp),
                  style: TextStyle(
                    fontSize: 10,
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ],
        ),
        trailing: item.isSaved
            ? Icon(Icons.bookmark, color: DS.brandPrimary, size: 20)
            : (onSaveToKnowledge != null
                ? IconButton(
                    icon: const Icon(Icons.bookmark_add_outlined, size: 20),
                    onPressed: () {
                      onSaveToKnowledge!(item);
                      ref
                          .read(translationHistoryProvider.notifier)
                          .markAsSaved(item.id);
                    },
                    tooltip: '保存到生词卡',
                  )
                : null),
        onTap: () {
          // Show full text dialog
          _showFullTextDialog(context, item);
        },
      ),
    );
  }

  String _formatTime(DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);

    if (diff.inMinutes < 1) {
      return '刚刚';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes}分钟前';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}小时前';
    } else {
      return '${timestamp.month}/${timestamp.day}';
    }
  }

  void _showFullTextDialog(BuildContext context, TranslationHistoryItem item) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('${item.sourceLang} → ${item.targetLang}'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                '原文',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: DS.xs),
              SelectableText(
                item.sourceText,
                style: const TextStyle(fontSize: 15),
              ),
              const SizedBox(height: DS.md),
              const Text(
                '译文',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: DS.xs),
              SelectableText(
                item.translation,
                style: TextStyle(
                  fontSize: 15,
                  color: DS.brandPrimary,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  void _showClearConfirmation(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('清空翻译历史'),
        content: const Text('确定要清空所有翻译历史记录吗？此操作不可撤销。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              ref.read(translationHistoryProvider.notifier).clearHistory();
              Navigator.of(context).pop();
            },
            style: TextButton.styleFrom(foregroundColor: DS.error),
            child: const Text('清空'),
          ),
        ],
      ),
    );
  }
}
