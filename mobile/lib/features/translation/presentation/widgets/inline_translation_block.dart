import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/translation/data/services/translation_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Inline translation block for sentences/paragraphs
///
/// Shows original + translation side-by-side or stacked
/// Collapsible to avoid cluttering the reading flow
class InlineTranslationBlock extends ConsumerStatefulWidget {
  const InlineTranslationBlock({
    required this.sourceText,
    this.sourceLang = 'en',
    this.targetLang = 'zh-CN',
    this.domain = 'general',
    this.initiallyExpanded = false,
    this.onSaveToKnowledge,
    super.key,
  });

  final String sourceText;
  final String sourceLang;
  final String targetLang;
  final String domain;
  final bool initiallyExpanded;
  final VoidCallback? onSaveToKnowledge;

  @override
  ConsumerState<InlineTranslationBlock> createState() =>
      _InlineTranslationBlockState();
}

class _InlineTranslationBlockState
    extends ConsumerState<InlineTranslationBlock> {
  bool _isExpanded = false;
  TranslationResult? _result;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _isExpanded = widget.initiallyExpanded;
    if (_isExpanded) {
      _loadTranslation();
    }
  }

  Future<void> _loadTranslation() async {
    if (_result != null) return; // Already loaded

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

  void _toggleExpansion() {
    setState(() {
      _isExpanded = !_isExpanded;
      if (_isExpanded && _result == null && !_isLoading) {
        _loadTranslation();
      }
    });
  }

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.symmetric(vertical: DS.sm),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Original text
            SelectableText(
              widget.sourceText,
              style: TextStyle(
                fontSize: 16,
                height: 1.6,
                color: DS.textPrimary,
              ),
            ),

            const SizedBox(height: DS.xs),

            // Toggle button
            InkWell(
              onTap: _toggleExpansion,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: DS.xs),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      _isExpanded ? Icons.expand_less : Icons.expand_more,
                      size: 18,
                      color: DS.brandPrimaryConst,
                    ),
                    const SizedBox(width: DS.spacing4),
                    Text(
                      _isExpanded ? '隐藏译文' : '显示译文',
                      style: TextStyle(
                        fontSize: 13,
                        color: DS.brandPrimaryConst,
                        fontWeight: DS.fontWeightMedium,
                      ),
                    ),
                    if (_result != null && _result!.isCacheHit) ...[
                      const SizedBox(width: DS.xs),
                      Icon(
                        Icons.flash_on,
                        size: 14,
                        color: DS.neutral400,
                      ),
                    ],
                  ],
                ),
              ),
            ),

            // Translation (collapsible)
            AnimatedSize(
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeInOut,
              child: _isExpanded
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: DS.sm),
                        if (_isLoading)
                          _buildLoading()
                        else if (_errorMessage != null)
                          _buildError()
                        else if (_result != null)
                          _buildTranslation(),
                      ],
                    )
                  : const SizedBox.shrink(),
            ),
          ],
        ),
      );

  Widget _buildLoading() => Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.neutral100,
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Row(
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: DS.sm),
            Text(context.l10n.transTranslating, style: TextStyle(fontSize: 14)),
          ],
        ),
      );

  Widget _buildError() => Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.error.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(Icons.error_outline, size: 18, color: DS.error),
            const SizedBox(width: DS.sm),
            Expanded(
              child: Text(
                '翻译失败，请重试',
                style: TextStyle(fontSize: 14, color: DS.error),
              ),
            ),
          ],
        ),
      );

  Widget _buildTranslation() {
    if (_result == null) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: DS.brandPrimary.withValues(alpha: 0.15),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Translation text
          SelectableText(
            _result!.translation,
            style: TextStyle(
              fontSize: 15,
              height: 1.5,
              color: DS.brandPrimary.withValues(alpha: 0.9),
            ),
          ),

          // Terminology notes (if any)
          if (_result!.segments.any((s) => s.notes.isNotEmpty)) ...[
            const SizedBox(height: DS.sm),
            const Divider(height: 1),
            const SizedBox(height: DS.sm),
            Wrap(
              spacing: DS.xs,
              runSpacing: DS.xs,
              children: [
                for (final segment in _result!.segments)
                  for (final note in segment.notes)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.xs,
                        vertical: DS.spacing4 / 2,
                      ),
                      decoration: BoxDecoration(
                        color: DS.brandPrimary.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        note,
                        style: TextStyle(
                          fontSize: 11,
                          color: DS.brandPrimaryConst,
                        ),
                      ),
                    ),
              ],
            ),
          ],

          // Actions
          if (widget.onSaveToKnowledge != null) ...[
            const SizedBox(height: DS.sm),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                icon: const Icon(Icons.bookmark_add_outlined, size: 16),
                label: const Text(context.l10n.transSaveToWordCard, style: TextStyle(fontSize: 13)),
                onPressed: widget.onSaveToKnowledge,
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.sm,
                    vertical: DS.spacing4,
                  ),
                ),
              ),
            ),
          ],

          // Meta info
          const SizedBox(height: DS.xs),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${_result!.provider} · ${_result!.latencyMs}ms',
                style: TextStyle(
                  fontSize: 10,
                  color: DS.neutral500,
                ),
              ),
              Text(
                '${_result!.sourceLang} → ${_result!.targetLang}',
                style: TextStyle(
                  fontSize: 10,
                  color: DS.neutral500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
