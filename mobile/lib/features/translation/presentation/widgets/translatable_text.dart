import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/translation/translation.dart';

/// A widget that makes text translatable via long-press selection
///
/// Usage example:
/// ```dart
/// TranslatableText(
///   text: "This is a paragraph of English text that can be translated.",
///   sourceLang: 'en',
///   targetLang: 'zh-CN',
///   domain: 'general',
/// )
/// ```
///
/// Features:
/// - Long press to select text
/// - Automatic translation on selection
/// - Shows translation popover for short selections (<50 chars)
/// - Shows inline block for longer selections
/// - Adds to translation history
class TranslatableText extends ConsumerStatefulWidget {
  const TranslatableText({
    required this.text,
    this.sourceLang = 'en',
    this.targetLang = 'zh-CN',
    this.domain = 'general',
    this.style,
    this.onSaveToKnowledge,
    super.key,
  });

  final String text;
  final String sourceLang;
  final String targetLang;
  final String domain;
  final TextStyle? style;
  final Function(String selectedText, String translation)? onSaveToKnowledge;

  @override
  ConsumerState<TranslatableText> createState() => _TranslatableTextState();
}

class _TranslatableTextState extends ConsumerState<TranslatableText> {
  final TextSelectionController _selectionController =
      TextSelectionController();

  @override
  void dispose() {
    _selectionController.dispose();
    super.dispose();
  }

  void _handleTextSelection(TextSelection selection) {
    final selectedText = widget.text.substring(
      selection.start,
      selection.end,
    );

    if (selectedText.trim().isEmpty) return;

    // Trigger haptic feedback
    HapticFeedback.mediumImpact();

    // Show translation based on length
    if (selectedText.length < 50) {
      // Short text: show popover
      _showTranslationPopover(selectedText);
    } else {
      // Long text: show bottom sheet with inline block
      _showTranslationSheet(selectedText);
    }

    // Add to translation history
    _addToHistory(selectedText);
  }

  void _showTranslationPopover(String selectedText) {
    showTranslationPopover(
      context,
      sourceText: selectedText,
      sourceLang: widget.sourceLang,
      targetLang: widget.targetLang,
      domain: widget.domain,
      onSaveToKnowledge: () {
        Navigator.of(context).pop();
        if (widget.onSaveToKnowledge != null) {
          // Note: Translation result is not available in callback
          // In a real implementation, we'd need to pass the translation result
          widget.onSaveToKnowledge!(selectedText, '');
        }
      },
    );
  }

  void _showTranslationSheet(String selectedText) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.3,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => Padding(
          padding: const EdgeInsets.all(16),
          child: SingleChildScrollView(
            controller: scrollController,
            child: InlineTranslationBlock(
              sourceText: selectedText,
              sourceLang: widget.sourceLang,
              targetLang: widget.targetLang,
              domain: widget.domain,
              initiallyExpanded: true,
              onSaveToKnowledge: () {
                Navigator.of(context).pop();
                if (widget.onSaveToKnowledge != null) {
                  widget.onSaveToKnowledge!(selectedText, '');
                }
              },
            ),
          ),
        ),
      ),
    );
  }

  void _addToHistory(String selectedText) {
    // Translation history will be updated by the popover/block widgets
    // This is just a placeholder for tracking selection events
  }

  @override
  Widget build(BuildContext context) {
    return SelectableText(
      widget.text,
      style: widget.style,
      onSelectionChanged: (selection, cause) {
        if (cause == SelectionChangedCause.longPress) {
          _handleTextSelection(selection);
        }
      },
      contextMenuBuilder: (context, editableTextState) {
        // Custom context menu with translation option
        final selection = editableTextState.textEditingValue.selection;
        if (selection.isCollapsed) {
          return const SizedBox.shrink();
        }

        final selectedText = widget.text.substring(
          selection.start,
          selection.end,
        );

        return AdaptiveTextSelectionToolbar(
          anchors: editableTextState.contextMenuAnchors,
          children: [
            TextSelectionToolbarTextButton(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              onPressed: () {
                _handleTextSelection(selection);
                editableTextState.hideToolbar();
              },
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.translate, size: 16),
                  SizedBox(width: 4),
                  Text('翻译'),
                ],
              ),
            ),
            TextSelectionToolbarTextButton(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              onPressed: () {
                Clipboard.setData(ClipboardData(text: selectedText));
                editableTextState.hideToolbar();
              },
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.copy, size: 16),
                  SizedBox(width: 4),
                  Text('复制'),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

/// Helper class for text selection management
class TextSelectionController {
  TextSelection? _currentSelection;

  TextSelection? get currentSelection => _currentSelection;

  void updateSelection(TextSelection selection) {
    _currentSelection = selection;
  }

  void clearSelection() {
    _currentSelection = null;
  }

  void dispose() {
    _currentSelection = null;
  }
}

/// Example usage widget demonstrating translation integration
class TranslationDemoScreen extends StatelessWidget {
  const TranslationDemoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Translation Demo'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Long-press any text below to translate:',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 16),
            TranslatableText(
              text: '''
In computer science, caching is a technique used to store frequently accessed data in a temporary storage area, called a cache. When an application needs to retrieve data, it first checks the cache. If the data is found in the cache (a cache hit), it can be retrieved much faster than if it had to be fetched from the original source, such as a database or API.

Caching improves performance by reducing the number of expensive operations, such as database queries or network requests. However, cache invalidation can be challenging, as stale data may persist in the cache even after the original data has been updated.
''',
              sourceLang: 'en',
              targetLang: 'zh-CN',
              domain: 'cs', // Computer science domain for terminology
              style: const TextStyle(
                fontSize: 16,
                height: 1.6,
              ),
              onSaveToKnowledge: (selectedText, translation) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('已保存到生词卡')),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
