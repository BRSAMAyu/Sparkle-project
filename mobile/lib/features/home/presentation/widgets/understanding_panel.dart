import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/providers/understanding_snapshot_provider.dart';

class UnderstandingPanel extends ConsumerStatefulWidget {
  const UnderstandingPanel({
    this.compact = false,
    this.initiallyExpanded = false,
    this.surface = 'home',
    super.key,
  });

  final bool compact;
  final bool initiallyExpanded;
  final String surface;

  @override
  ConsumerState<UnderstandingPanel> createState() => _UnderstandingPanelState();
}

class _UnderstandingPanelState extends ConsumerState<UnderstandingPanel> {
  late bool _expanded = widget.initiallyExpanded;

  @override
  Widget build(BuildContext context) {
    final snapshotAsync = ref.watch(understandingSnapshotProvider);
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Semantics(
      container: true,
      label: context.l10n.understandingPanelSemanticLabel,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: widget.compact
            ? EdgeInsets.zero
            : const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHighest,
          border: Border.all(color: scheme.outlineVariant),
          borderRadius: BorderRadius.circular(8),
        ),
        child: snapshotAsync.when(
          data: (snapshot) => _buildContent(
            context,
            snapshot,
            scheme,
            textTheme,
          ),
          loading: () => _buildLoading(context, scheme),
          error: (_, __) => _buildError(context, scheme),
        ),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    UnderstandingSnapshot? snapshot,
    ColorScheme scheme,
    TextTheme textTheme,
  ) {
    final empty = snapshot == null || snapshot.isEmpty;
    final visibleClaims = _expanded || widget.compact
        ? snapshot?.claims ?? const <UnderstandingClaim>[]
        : (snapshot?.claims ?? const <UnderstandingClaim>[]).take(2).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        _PanelHeader(
          title: context.l10n.understandingPanelTitle,
          subtitle: empty
              ? context.l10n.understandingPanelEmptySubtitle
              : context.l10n.understandingPanelSubtitle(
                  snapshot.totalClaims,
                  (snapshot.highConfidenceRatio * 100).round(),
                ),
          expanded: _expanded,
          onToggle: widget.compact
              ? null
              : () => setState(() => _expanded = !_expanded),
        ),
        const SizedBox(height: 12),
        if (empty)
          _EmptyUnderstandingState(
            text: context.l10n.understandingPanelEmptyBody,
          )
        else ...[
          if (snapshot.recentlyCorrected.isNotEmpty) ...[
            _RecentlyCorrectedBanner(
              item: snapshot.recentlyCorrected.first,
            ),
            const SizedBox(height: 12),
          ],
          if (snapshot.envelopeStyle.currentTone.isNotEmpty)
            _EnvelopeStyleRow(style: snapshot.envelopeStyle),
          if (snapshot.envelopeStyle.currentTone.isNotEmpty)
            const SizedBox(height: 12),
          ...visibleClaims.map(
            (claim) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _ClaimTile(
                claim: claim,
                onCorrect: claim.userCanCorrect
                    ? () => _openCorrectionDialog(context, claim)
                    : null,
              ),
            ),
          ),
          if (_expanded && snapshot.memoryDeclarations.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              context.l10n.understandingPanelMemoryTitle,
              style: textTheme.labelLarge?.copyWith(
                color: scheme.onSurface,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            ...snapshot.memoryDeclarations.take(3).map(
                  (memory) => _MemoryDeclarationTile(memory: memory),
                ),
          ],
        ],
      ],
    );
  }

  Widget _buildLoading(BuildContext context, ColorScheme scheme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          _PanelHeader(
            title: context.l10n.understandingPanelTitle,
            subtitle: context.l10n.understandingPanelLoading,
            expanded: _expanded,
            onToggle: null,
          ),
          const SizedBox(height: 12),
          LinearProgressIndicator(
            minHeight: 3,
            color: scheme.primary,
            backgroundColor: scheme.surfaceContainerHighest,
          ),
        ],
      );

  Widget _buildError(BuildContext context, ColorScheme scheme) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          _PanelHeader(
            title: context.l10n.understandingPanelTitle,
            subtitle: context.l10n.understandingPanelError,
            expanded: _expanded,
            onToggle: null,
          ),
          const SizedBox(height: 8),
          TextButton.icon(
            onPressed: () => ref.invalidate(understandingSnapshotProvider),
            icon: const Icon(Icons.refresh_rounded, size: 18),
            label: Text(context.l10n.retry),
          ),
        ],
      );

  Future<void> _openCorrectionDialog(
    BuildContext context,
    UnderstandingClaim claim,
  ) async {
    final correction = await showUnderstandingCorrectionDialog(context, claim);
    if (correction == null) return;
    try {
      final effects =
          await ref.read(understandingSnapshotProvider.notifier).correctClaim(
                claim: claim,
                correction: correction.text,
                scope: correction.scope,
              );
      if (!context.mounted) return;
      final effectLabel = effects.isEmpty
          ? context.l10n.understandingCorrectionGenericEffect
          : _scopeLabel(context, correction.scope);
      AppFeedback.undoable(
        context: context,
        message: context.l10n.understandingCorrectionUpdated(effectLabel),
        actionLabel: context.l10n.chatUndo,
        onAction: () {
          unawaited(_openCorrectionDialog(context, claim));
        },
      );
    } catch (_) {
      if (!context.mounted) return;
      AppFeedback.error(context, context.l10n.understandingCorrectionFailed);
    }
  }
}

class _PanelHeader extends StatelessWidget {
  const _PanelHeader({
    required this.title,
    required this.subtitle,
    required this.expanded,
    required this.onToggle,
  });

  final String title;
  final String subtitle;
  final bool expanded;
  final VoidCallback? onToggle;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(Icons.psychology_alt_outlined, color: scheme.primary),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: textTheme.titleMedium?.copyWith(
                  color: scheme.onSurface,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: textTheme.bodySmall?.copyWith(
                  color: scheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        if (onToggle != null)
          Semantics(
            button: true,
            label: expanded
                ? context.l10n.understandingPanelCollapse
                : context.l10n.understandingPanelExpand,
            child: IconButton(
              onPressed: onToggle,
              tooltip: expanded
                  ? context.l10n.understandingPanelCollapse
                  : context.l10n.understandingPanelExpand,
              icon: Icon(
                expanded
                    ? Icons.keyboard_arrow_up_rounded
                    : Icons.keyboard_arrow_down_rounded,
              ),
            ),
          ),
      ],
    );
  }
}

class _ClaimTile extends StatelessWidget {
  const _ClaimTile({
    required this.claim,
    required this.onCorrect,
  });

  final UnderstandingClaim claim;
  final VoidCallback? onCorrect;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final confidenceColor = _confidenceColor(scheme, claim.confidence);
    return Semantics(
      container: true,
      label: context.l10n.understandingClaimSemantic(
        claim.claim,
        (claim.confidence * 100).round(),
      ),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: scheme.surface,
          border: Border.all(color: scheme.outlineVariant),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    claim.scope,
                    style: textTheme.labelMedium?.copyWith(
                      color: scheme.primary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                _ConfidencePill(
                  label: _confidenceText(context, claim.confidenceLabel),
                  color: confidenceColor,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              claim.claim,
              style: textTheme.bodyMedium?.copyWith(
                color: scheme.onSurface,
                height: 1.35,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              claim.evidenceSummary,
              style: textTheme.bodySmall?.copyWith(
                color: scheme.onSurfaceVariant,
                height: 1.35,
              ),
            ),
            if (onCorrect != null) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: onCorrect,
                  icon: const Icon(Icons.edit_note_rounded, size: 18),
                  label: Text(context.l10n.understandingCorrect),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ConfidencePill extends StatelessWidget {
  const _ConfidencePill({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        border: Border.all(color: color.withValues(alpha: 0.35)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: scheme.onSurface,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _EnvelopeStyleRow extends StatelessWidget {
  const _EnvelopeStyleRow({required this.style});

  final EnvelopeStyleSnapshot style;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.primaryContainer.withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.tune_rounded, color: scheme.onPrimaryContainer, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              context.l10n.understandingStyleSummary(
                style.currentTone,
                style.currentVerbosity,
                style.reasonForStyle,
              ),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: scheme.onPrimaryContainer,
                    height: 1.35,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RecentlyCorrectedBanner extends StatelessWidget {
  const _RecentlyCorrectedBanner({required this.item});

  final RecentlyCorrectedUnderstanding item;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.tertiaryContainer.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(Icons.check_circle_outline, color: scheme.onTertiaryContainer),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              context.l10n.understandingRecentlyCorrected(item.correction),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: scheme.onTertiaryContainer,
                    height: 1.35,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MemoryDeclarationTile extends StatelessWidget {
  const _MemoryDeclarationTile({required this.memory});

  final MemoryDeclaration memory;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.bookmark_border_rounded,
            size: 18,
            color: scheme.onSurfaceVariant,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '${memory.content}\n${memory.persistence}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: scheme.onSurfaceVariant,
                    height: 1.35,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyUnderstandingState extends StatelessWidget {
  const _EmptyUnderstandingState({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        text,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: scheme.onSurfaceVariant,
              height: 1.35,
            ),
      ),
    );
  }
}

class UnderstandingCorrectionResult {
  const UnderstandingCorrectionResult({
    required this.text,
    required this.scope,
  });

  final String text;
  final UnderstandingCorrectionScope scope;
}

Future<UnderstandingCorrectionResult?> showUnderstandingCorrectionDialog(
  BuildContext context,
  UnderstandingClaim claim,
) {
  final controller = TextEditingController();
  var selectedScope = UnderstandingCorrectionScope.memoryClaim;
  return showDialog<UnderstandingCorrectionResult?>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (context, setDialogState) {
        final scheme = Theme.of(context).colorScheme;
        return AlertDialog(
          title: Text(context.l10n.understandingCorrectionTitle),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  claim.claim,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: scheme.onSurfaceVariant,
                        height: 1.35,
                      ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: controller,
                  minLines: 2,
                  maxLines: 4,
                  autofocus: true,
                  decoration: InputDecoration(
                    hintText: context.l10n.understandingCorrectionHint,
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  context.l10n.understandingCorrectionScopeTitle,
                  style: Theme.of(context).textTheme.labelLarge,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: UnderstandingCorrectionScope.values
                      .map(
                        (scope) => Semantics(
                          button: true,
                          selected: selectedScope == scope,
                          label: _scopeLabel(context, scope),
                          child: ChoiceChip(
                            label: Text(_scopeLabel(context, scope)),
                            selected: selectedScope == scope,
                            onSelected: (_) {
                              setDialogState(() => selectedScope = scope);
                            },
                          ),
                        ),
                      )
                      .toList(),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: Text(context.l10n.cancel),
            ),
            FilledButton(
              onPressed: () {
                final text = controller.text.trim();
                if (text.isEmpty) return;
                Navigator.of(dialogContext).pop(
                  UnderstandingCorrectionResult(
                    text: text,
                    scope: selectedScope,
                  ),
                );
              },
              child: Text(context.l10n.confirm),
            ),
          ],
        );
      },
    ),
  ).whenComplete(controller.dispose);
}

Color _confidenceColor(ColorScheme scheme, double confidence) {
  if (confidence >= 0.75) return scheme.primary;
  if (confidence >= 0.45) return scheme.tertiary;
  return scheme.error;
}

String _confidenceText(BuildContext context, String label) => switch (label) {
      'high' => context.l10n.understandingConfidenceHigh,
      'medium' => context.l10n.understandingConfidenceMedium,
      _ => context.l10n.understandingConfidenceLow,
    };

String _scopeLabel(BuildContext context, UnderstandingCorrectionScope scope) =>
    switch (scope) {
      UnderstandingCorrectionScope.memoryClaim =>
        context.l10n.understandingScopeMemoryClaim,
      UnderstandingCorrectionScope.routingPolicy =>
        context.l10n.understandingScopeRoutingPolicy,
      UnderstandingCorrectionScope.taskGranularity =>
        context.l10n.understandingScopeTaskGranularity,
      UnderstandingCorrectionScope.planRisk =>
        context.l10n.understandingScopePlanRisk,
      UnderstandingCorrectionScope.knowledgeBottleneck =>
        context.l10n.understandingScopeKnowledgeBottleneck,
      UnderstandingCorrectionScope.wakePolicy =>
        context.l10n.understandingScopeWakePolicy,
    };
