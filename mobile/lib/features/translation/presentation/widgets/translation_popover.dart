import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/translation/data/services/translation_service.dart';
import 'package:sparkle/features/translation/data/services/knowledge_integration_service.dart';

/// Lightweight popover for word/phrase translation
///
/// Shows: translation + 1-line note, no scrolling
/// Design: Minimal, non-intrusive, quick to dismiss
class TranslationPopover extends ConsumerStatefulWidget {
  const TranslationPopover({
    required this.sourceText,
    this.sourceLang = 'en',
    this.targetLang = 'zh-CN',
    this.domain = 'general',
    this.readingContext,
    this.onSaved,
    super.key,
  });

  final String sourceText;
  final String sourceLang;
  final String targetLang;
  final String domain;
  final String? readingContext;
  final VoidCallback? onSaved;

  @override
  ConsumerState<TranslationPopover> createState() => _TranslationPopoverState();
}

class _TranslationPopoverState extends ConsumerState<TranslationPopover> {
  TranslationResult? _result;
  bool _isLoading = true;
  String? _errorMessage;
  bool _isSaving = false;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    _loadTranslation();
  }

  Future<void> _loadTranslation() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final service = ref.read(translationServiceProvider);
      final result = await service.translate(
        text: widget.sourceText,
        sourceLang: widget.sourceLang,
        targetLang: widget.targetLang,
        domain: widget.domain,
        style: 'concise', // Use concise style for popover
      );

      if (mounted) {
        setState(() {
          _result = result;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _saveToKnowledgeGraph() async {
    if (_result == null || _isSaving || _saved) return;

    setState(() {
      _isSaving = true;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      final knowledgeService = KnowledgeIntegrationService(apiClient.dio);

      final result = await knowledgeService.createVocabularyNode(
        sourceText: widget.sourceText,
        translation: _result!.translation,
        context: widget.readingContext ?? widget.sourceText,
        language: widget.sourceLang,
        domain: widget.domain,
      );

      if (result != null && result.success) {
        if (mounted) {
          setState(() {
            _saved = true;
            _isSaving = false;
          });

          // Show success feedback
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('✅ 已加入生词卡，24小时后复习'),
              duration: Duration(seconds: 2),
            ),
          );

          // Call callback
          widget.onSaved?.call();

          // Auto-close after 1 second
          Future.delayed(const Duration(seconds: 1), () {
            if (mounted) {
              Navigator.of(context).pop();
            }
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _isSaving = false;
          });

          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('❌ 保存失败，请重试'),
              duration: Duration(seconds: 2),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ 保存失败: ${e.toString()}'),
            duration: const Duration(seconds: 2),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 300),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.15),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Source text (truncated)
          Text(
            widget.sourceText,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
              fontStyle: FontStyle.italic,
            ),
          ),
          const SizedBox(height: DS.sm),

          // Content: Translation or loading/error
          if (_isLoading)
            _buildLoading()
          else if (_errorMessage != null)
            _buildError()
          else
            _buildTranslation(),

          // Actions: Save buttons
          if (_result != null) ...[
            const SizedBox(height: DS.md),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  icon: Icon(
                    _saved ? Icons.bookmark : Icons.bookmark_add_outlined,
                    size: 16,
                  ),
                  label: Text(
                    _saved ? '已保存' : (_isSaving ? '保存中...' : '生词卡'),
                    style: const TextStyle(fontSize: 13),
                  ),
                  onPressed: _saved || _isSaving ? null : _saveToKnowledgeGraph,
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.sm,
                      vertical: 4,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildLoading() {
    return const Row(
      children: [
        SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        SizedBox(width: DS.sm),
        Text('翻译中...', style: TextStyle(fontSize: 14)),
      ],
    );
  }

  Widget _buildError() {
    return Row(
      children: [
        Icon(Icons.error_outline, size: 16, color: DS.error),
        const SizedBox(width: DS.sm),
        Expanded(
          child: Text(
            '翻译失败',
            style: TextStyle(fontSize: 14, color: DS.error),
          ),
        ),
      ],
    );
  }

  Widget _buildTranslation() {
    if (_result == null) return const SizedBox.shrink();

    // Extract first note if available
    final firstNote = _result!.segments.isNotEmpty &&
            _result!.segments.first.notes.isNotEmpty
        ? _result!.segments.first.notes.first
        : null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Main translation
        SelectableText(
          _result!.translation,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w500,
            height: 1.4,
          ),
        ),

        // Terminology note (if any)
        if (firstNote != null) ...[
          const SizedBox(height: DS.xs),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.xs,
              vertical: 2,
            ),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              firstNote,
              style: TextStyle(
                fontSize: 11,
                color: DS.brandPrimary,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],

        // Cache hint (for debugging)
        if (_result!.isCacheHit) ...[
          const SizedBox(height: DS.xs),
          Row(
            children: [
              Icon(Icons.flash_on, size: 12, color: Colors.grey[400]),
              const SizedBox(width: 2),
              Text(
                'cached',
                style: TextStyle(fontSize: 10, color: Colors.grey[400]),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

/// Show translation popover as a dialog
void showTranslationPopover(
  BuildContext context, {
  required String sourceText,
  String sourceLang = 'en',
  String targetLang = 'zh-CN',
  String domain = 'general',
  String? readingContext,
  VoidCallback? onSaved,
}) {
  showDialog(
    context: context,
    barrierDismissible: true,
    barrierColor: Colors.black26,
    builder: (context) => Dialog(
      backgroundColor: Colors.transparent,
      elevation: 0,
      child: TranslationPopover(
        sourceText: sourceText,
        sourceLang: sourceLang,
        targetLang: targetLang,
        domain: domain,
        readingContext: readingContext,
        onSaved: onSaved,
      ),
    ),
  );
}
