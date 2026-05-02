import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/insights/data/models/growth_dashboard.dart';

class ModelUpdateReceipt extends StatelessWidget {
  const ModelUpdateReceipt({
    required this.update,
    super.key,
  });

  final ModelUpdateItem update;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Semantics(
      label: context.l10n.gdModelReceiptTitle,
      container: true,
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: colors.primary.withValues(alpha: 0.18),
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.receipt_long_rounded,
                  color: colors.primary,
                  size: 20,
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    context.l10n.gdModelReceiptTitle,
                    style: textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            _ReceiptLine(
              label: context.l10n.gdTriggerEvent,
              value: update.triggerEvent,
            ),
            _ReceiptLine(
              label: context.l10n.gdSparkleLearned,
              value: update.whatSparkleLearned,
            ),
            _ReceiptLine(
              label: context.l10n.gdWhatChanged,
              value: update.whatChanged,
            ),
            _ReceiptLine(
              label: context.l10n.gdNotWritten,
              value: update.whatWasNotWritten,
            ),
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                FilledButton.tonalIcon(
                  onPressed: () => _showMessage(
                    context,
                    context.l10n.gdReceiptRemembered,
                  ),
                  icon: const Icon(Icons.check_rounded),
                  label: Text(context.l10n.gdRemembered),
                ),
                OutlinedButton.icon(
                  onPressed: () => _showMessage(
                    context,
                    context.l10n.gdReceiptCorrectPrompt,
                  ),
                  icon: const Icon(Icons.edit_note_rounded),
                  label: Text(context.l10n.gdCorrect),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showMessage(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        action: SnackBarAction(
          label: context.l10n.gdUndo,
          onPressed: () {},
        ),
      ),
    );
  }
}

class _ReceiptLine extends StatelessWidget {
  const _ReceiptLine({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    if (value.trim().isEmpty) {
      return const SizedBox.shrink();
    }
    final colors = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: colors.onSurfaceVariant,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: DS.spacing2),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: colors.onSurface,
                  height: 1.45,
                ),
          ),
        ],
      ),
    );
  }
}
