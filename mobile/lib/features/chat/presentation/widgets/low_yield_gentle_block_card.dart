import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/presentation/providers/low_yield_block_provider.dart';

class LowYieldGentleBlockCard extends StatefulWidget {
  const LowYieldGentleBlockCard({
    required this.block,
    super.key,
    this.onAccept,
    this.onDismiss,
    this.onCorrect,
  });

  final LowYieldBlock block;
  final FutureOr<void> Function(LowYieldBlock block)? onAccept;
  final FutureOr<void> Function(LowYieldBlock block)? onDismiss;
  final FutureOr<void> Function(LowYieldBlock block)? onCorrect;

  @override
  State<LowYieldGentleBlockCard> createState() =>
      _LowYieldGentleBlockCardState();
}

class _LowYieldGentleBlockCardState extends State<LowYieldGentleBlockCard> {
  bool _handled = false;

  @override
  Widget build(BuildContext context) {
    if (_handled) {
      return const SizedBox.shrink();
    }

    final l10n = context.l10n;
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final block = widget.block;
    final activity = block.currentActivity.isEmpty
        ? l10n.lowYieldActivityFallback
        : block.currentActivity;
    final reason =
        block.reason.isEmpty ? l10n.lowYieldReasonFallback : block.reason;
    final suggestion = block.suggestedAction.isEmpty
        ? l10n.lowYieldSuggestionFallback
        : block.suggestedAction;

    return Semantics(
      container: true,
      label: l10n.lowYieldCardSemantics,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: colorScheme.primaryContainer.withValues(alpha: 0.28),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: colorScheme.primary.withValues(alpha: 0.24),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.tips_and_updates_outlined,
                  color: colorScheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    l10n.lowYieldCardTitle,
                    style: textTheme.titleSmall?.copyWith(
                      color: colorScheme.onPrimaryContainer,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              l10n.lowYieldCardMessage(activity, reason, suggestion),
              style: textTheme.bodyMedium?.copyWith(
                color: colorScheme.onPrimaryContainer,
                height: 1.38,
              ),
            ),
            if ((block.deadlineLabel ?? block.goalLabel) != null) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (block.deadlineLabel != null)
                    _ContextChip(
                      icon: Icons.event_outlined,
                      label: block.deadlineLabel!,
                    ),
                  if (block.goalLabel != null)
                    _ContextChip(
                      icon: Icons.flag_outlined,
                      label: block.goalLabel!,
                    ),
                ],
              ),
            ],
            const SizedBox(height: 12),
            Wrap(
              alignment: WrapAlignment.end,
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton(
                  onPressed: () => _handle(widget.onCorrect),
                  child: Text(l10n.lowYieldActionCorrect),
                ),
                TextButton(
                  onPressed: () => _handle(widget.onDismiss),
                  child: Text(l10n.lowYieldActionContinue),
                ),
                FilledButton.icon(
                  onPressed: () => _handle(widget.onAccept),
                  icon: const Icon(Icons.arrow_forward_rounded),
                  label: Text(l10n.lowYieldActionSwitch),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handle(
    FutureOr<void> Function(LowYieldBlock block)? callback,
  ) async {
    setState(() => _handled = true);
    await callback?.call(widget.block);
  }
}

class _ContextChip extends StatelessWidget {
  const _ContextChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: colorScheme.surface.withValues(alpha: 0.64),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: colorScheme.onSurfaceVariant),
          const SizedBox(width: 6),
          Flexible(
            child: Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
