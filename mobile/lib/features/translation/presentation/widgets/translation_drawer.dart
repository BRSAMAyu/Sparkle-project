import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Translation history item
class TranslationHistoryItem {
  TranslationHistoryItem({
    required this.id,
    required this.sourceText,
    required this.translation,
    required this.sourceLang,
    required this.targetLang,
    required this.timestamp,
    this.isSaved = false,
  });
  final String id;
  final String sourceText;
  final String translation;
  final String sourceLang;
  final String targetLang;
  final DateTime timestamp;
  final bool isSaved;
}

/// In-memory translation history provider (session-only)
///
/// TODO: Replace with persistent storage in Phase 2
final translationHistoryProvider = StateNotifierProvider<
    TranslationHistoryNotifier, List<TranslationHistoryItem>>(
  (ref) => TranslationHistoryNotifier(),
);

class TranslationHistoryNotifier
    extends StateNotifier<List<TranslationHistoryItem>> {
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

  final void Function(TranslationHistoryItem)? onSaveToKnowledge;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(translationHistoryProvider);

    return Drawer(
      child: Column(
        children: [
          // Header
          AppBar(
            title: Text(context.l10n.translationHistoryTitle),
            backgroundColor: DS.brandPrimary,
            foregroundColor: DS.textOnPrimary,
            elevation: 0,
            actions: [
              if (history.isNotEmpty)
                SparkleIconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () {
                    _showClearConfirmation(context, ref);
                  },
                  semanticLabel: context.l10n.translationClearAll,
                  variant: ButtonVariant.ghost,
                ),
            ],
          ),

          // Content
          Expanded(
            child: history.isEmpty
                ? _buildEmptyState(context)
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
              color: DS.neutral100,
              border: Border(
                top: BorderSide(color: DS.neutral300),
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline, size: 14, color: DS.neutral600),
                const SizedBox(width: DS.xs),
                Expanded(
                  child: Text(
                    context.l10n.translationHistorySessionOnly,
                    style: TextStyle(fontSize: 12, color: DS.neutral600),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.translate, size: 64, color: DS.neutral300),
            const SizedBox(height: DS.md),
            Text(
              context.l10n.translationNoHistory,
              style: TextStyle(fontSize: 16, color: DS.neutral600),
            ),
            const SizedBox(height: DS.xs),
            Text(
              context.l10n.translationStartTranslate,
              style: TextStyle(fontSize: 13, color: DS.neutral500),
            ),
          ],
        ),
      );

  Widget _buildHistoryItem(
    BuildContext context,
    WidgetRef ref,
    TranslationHistoryItem item,
  ) =>
      Card(
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
                  color: DS.brandPrimaryConst,
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
                      color: DS.neutral200,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '${item.sourceLang} → ${item.targetLang}',
                      style: const TextStyle(fontSize: 10),
                    ),
                  ),
                  const SizedBox(width: DS.xs),
                  Text(
                    _formatTime(context, item.timestamp),
                    style: TextStyle(
                      fontSize: 10,
                      color: DS.neutral600,
                    ),
                  ),
                ],
              ),
            ],
          ),
          trailing: item.isSaved
              ? Icon(Icons.bookmark, color: DS.brandPrimaryConst, size: 20)
              : (onSaveToKnowledge != null
                  ? SparkleIconButton(
                      icon: const Icon(Icons.bookmark_add_outlined, size: 20),
                      onPressed: () {
                        onSaveToKnowledge!(item);
                        ref
                            .read(translationHistoryProvider.notifier)
                            .markAsSaved(item.id);
                      },
                      semanticLabel: context.l10n.translationSaveToVocabulary,
                      variant: ButtonVariant.ghost,
                    )
                  : null),
          onTap: () {
            // Show full text dialog
            _showFullTextDialog(context, item);
          },
        ),
      );

  String _formatTime(BuildContext context, DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);

    if (diff.inMinutes < 1) {
      return context.l10n.translationJustNow;
    } else if (diff.inMinutes < 60) {
      return context.l10n.translationMinutesAgo(diff.inMinutes);
    } else if (diff.inHours < 24) {
      return context.l10n.translationHoursAgo(diff.inHours);
    } else {
      return '${timestamp.month}/${timestamp.day}';
    }
  }

  void _showFullTextDialog(BuildContext context, TranslationHistoryItem item) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('${item.sourceLang} → ${item.targetLang}'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                context.l10n.translationOriginal,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: DS.neutral500,
                ),
              ),
              const SizedBox(height: DS.xs),
              SelectableText(
                item.sourceText,
                style: const TextStyle(fontSize: 15),
              ),
              const SizedBox(height: DS.md),
              Text(
                context.l10n.translationTranslated,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: DS.neutral500,
                ),
              ),
              const SizedBox(height: DS.xs),
              SelectableText(
                item.translation,
                style: TextStyle(
                  fontSize: 15,
                  color: DS.brandPrimaryConst,
                ),
              ),
            ],
          ),
        ),
        actions: [
          SparkleButton.ghost(
            label: context.l10n.commonClose,
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }

  void _showClearConfirmation(BuildContext context, WidgetRef ref) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.translationClearAll),
        content: Text(context.l10n.translationClearConfirm),
        actions: [
          SparkleButton.ghost(
            label: context.l10n.commonCancel,
            onPressed: () => Navigator.of(context).pop(),
          ),
          SparkleButton.destructive(
            label: context.l10n.translationClearAll,
            onPressed: () {
              ref.read(translationHistoryProvider.notifier).clearHistory();
              Navigator.of(context).pop();
            },
          ),
        ],
      ),
    );
  }
}
