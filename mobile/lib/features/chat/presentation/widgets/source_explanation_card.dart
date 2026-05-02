import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/presentation/providers/source_explanation_provider.dart';

class SourceExplanationCard extends ConsumerStatefulWidget {
  const SourceExplanationCard({
    super.key,
    this.rawMetadata,
    this.useLatestReceiptFallback = false,
  });

  final Map<String, dynamic>? rawMetadata;
  final bool useLatestReceiptFallback;

  @override
  ConsumerState<SourceExplanationCard> createState() =>
      _SourceExplanationCardState();
}

class _SourceExplanationCardState extends ConsumerState<SourceExplanationCard> {
  bool _expanded = false;
  bool _showUnused = false;
  String? _pendingItemId;

  @override
  Widget build(BuildContext context) {
    final localReceipt =
        SourceExplanationReceipt.fromMetadata(widget.rawMetadata);
    if (localReceipt != null) {
      return _buildReceipt(context, localReceipt);
    }

    if (!widget.useLatestReceiptFallback) {
      return const SizedBox.shrink();
    }

    return ref.watch(sourceExplanationProvider).maybeWhen(
          data: (receipt) {
            if (receipt == null) return const SizedBox.shrink();
            return _buildReceipt(context, receipt);
          },
          orElse: () => const SizedBox.shrink(),
        );
  }

  Widget _buildReceipt(
    BuildContext context,
    SourceExplanationReceipt receipt,
  ) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final usedCount = receipt.usedSources.length;
    final unusedCount = receipt.unusedSources.length;
    final confidence = receipt.confidence;

    return Semantics(
      container: true,
      button: true,
      label: context.l10n.sourceExplanationSemantics,
      child: Container(
        margin: const EdgeInsets.only(top: 8),
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHigh,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: scheme.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            InkWell(
              borderRadius: BorderRadius.circular(8),
              onTap: () => setState(() => _expanded = !_expanded),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
                child: Row(
                  children: [
                    Icon(
                      Icons.fact_check_outlined,
                      color: scheme.primary,
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        context.l10n.sourceExplanationUsedSummary(usedCount),
                        style: textTheme.labelLarge?.copyWith(
                          color: scheme.onSurface,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    if (confidence != null)
                      _ConfidencePill(confidence: confidence),
                    Icon(
                      _expanded
                          ? Icons.expand_less_rounded
                          : Icons.expand_more_rounded,
                      color: scheme.onSurfaceVariant,
                    ),
                  ],
                ),
              ),
            ),
            AnimatedCrossFade(
              firstChild: const SizedBox.shrink(),
              secondChild: Padding(
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if ((receipt.reason ?? '').isNotEmpty) ...[
                      Text(
                        receipt.reason!,
                        style: textTheme.bodySmall?.copyWith(
                          color: scheme.onSurfaceVariant,
                          height: 1.35,
                        ),
                      ),
                      const SizedBox(height: 10),
                    ],
                    _SourceSection(
                      title: context.l10n.sourceExplanationUsedSources,
                      icon: Icons.check_circle_outline_rounded,
                      iconColor: scheme.primary,
                      sources: receipt.usedSources,
                      pendingItemId: _pendingItemId,
                      onCorrect: (source) => _submitCorrection(
                        receipt: receipt,
                        source: source,
                      ),
                    ),
                    if (unusedCount > 0) ...[
                      const SizedBox(height: 8),
                      TextButton.icon(
                        style: TextButton.styleFrom(
                          alignment: Alignment.centerLeft,
                          foregroundColor: scheme.onSurfaceVariant,
                          padding: EdgeInsets.zero,
                          minimumSize: const Size(0, 40),
                        ),
                        onPressed: () {
                          setState(() => _showUnused = !_showUnused);
                        },
                        icon: Icon(
                          _showUnused
                              ? Icons.expand_less_rounded
                              : Icons.expand_more_rounded,
                        ),
                        label: Text(
                          context.l10n
                              .sourceExplanationUnusedSources(unusedCount),
                        ),
                      ),
                      AnimatedCrossFade(
                        firstChild: const SizedBox.shrink(),
                        secondChild: _SourceSection(
                          title:
                              context.l10n.sourceExplanationUnusedSourcesTitle,
                          icon: Icons.remove_circle_outline_rounded,
                          iconColor: scheme.tertiary,
                          sources: receipt.unusedSources,
                          pendingItemId: _pendingItemId,
                          onCorrect: (source) => _submitCorrection(
                            receipt: receipt,
                            source: source,
                          ),
                        ),
                        crossFadeState: _showUnused
                            ? CrossFadeState.showSecond
                            : CrossFadeState.showFirst,
                        duration: const Duration(milliseconds: 180),
                      ),
                    ],
                  ],
                ),
              ),
              crossFadeState: _expanded
                  ? CrossFadeState.showSecond
                  : CrossFadeState.showFirst,
              duration: const Duration(milliseconds: 180),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submitCorrection({
    required SourceExplanationReceipt receipt,
    required SourceExplanationItem source,
  }) async {
    setState(() => _pendingItemId = source.id);
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(sourceExplanationActionsProvider).submitAction(
            receiptId: receipt.receiptId,
            action: SourceReceiptAction.correct,
          );
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(
          content: Text(context.l10n.sourceExplanationCorrectionSent),
          action: SnackBarAction(
            label: context.l10n.sourceExplanationUndo,
            onPressed: () {
              unawaited(
                ref.read(sourceExplanationActionsProvider).submitAction(
                      receiptId: receipt.receiptId,
                      action: SourceReceiptAction.dismiss,
                    ),
              );
            },
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(
          content: Text(context.l10n.sourceExplanationCorrectionFailed),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _pendingItemId = null);
      }
    }
  }
}

class _SourceSection extends StatelessWidget {
  const _SourceSection({
    required this.title,
    required this.icon,
    required this.iconColor,
    required this.sources,
    required this.pendingItemId,
    required this.onCorrect,
  });

  final String title;
  final IconData icon;
  final Color iconColor;
  final List<SourceExplanationItem> sources;
  final String? pendingItemId;
  final ValueChanged<SourceExplanationItem> onCorrect;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    if (sources.isEmpty) {
      return Text(
        context.l10n.sourceExplanationNoSources,
        style: textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Icon(icon, size: 16, color: iconColor),
            const SizedBox(width: 6),
            Text(
              title,
              style: textTheme.labelMedium?.copyWith(
                color: scheme.onSurface,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ...sources.map(
          (source) => _SourceTile(
            source: source,
            pending: pendingItemId == source.id,
            onCorrect: () => onCorrect(source),
          ),
        ),
      ],
    );
  }
}

class _SourceTile extends StatelessWidget {
  const _SourceTile({
    required this.source,
    required this.pending,
    required this.onCorrect,
  });

  final SourceExplanationItem source;
  final bool pending;
  final VoidCallback onCorrect;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final relevance = source.relevance;

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  source.title,
                  style: textTheme.bodyMedium?.copyWith(
                    color: scheme.onSurface,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: [
                    if ((source.type ?? '').isNotEmpty)
                      _MetaChip(label: source.type!),
                    if (relevance != null)
                      _MetaChip(
                        label: context.l10n.sourceExplanationRelevance(
                          (relevance * 100).clamp(0, 100).round(),
                        ),
                      ),
                    if ((source.reason ?? '').isNotEmpty)
                      _MetaChip(label: source.reason!),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Semantics(
            button: true,
            label: context.l10n.sourceExplanationCorrectSource,
            child: IconButton(
              tooltip: context.l10n.sourceExplanationCorrectSource,
              onPressed: pending ? null : onCorrect,
              icon: pending
                  ? SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: scheme.primary,
                      ),
                    )
                  : const Icon(Icons.edit_note_rounded),
              color: scheme.primary,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: scheme.secondaryContainer,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: scheme.onSecondaryContainer,
            ),
      ),
    );
  }
}

class _ConfidencePill extends StatelessWidget {
  const _ConfidencePill({required this.confidence});

  final double confidence;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final normalized = confidence <= 1 ? confidence * 100 : confidence;
    final value = normalized.clamp(0, 100).round();

    return Container(
      margin: const EdgeInsets.only(right: 4),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: scheme.primaryContainer,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        context.l10n.sourceExplanationConfidence(value),
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: scheme.onPrimaryContainer,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}
