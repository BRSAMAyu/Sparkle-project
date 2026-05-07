import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/insights/data/models/return_case_file.dart';
import 'package:sparkle/features/insights/presentation/providers/return_case_file_provider.dart';

/// GOAL-011: ReturnCaseFile card.
///
/// Shown to returning users (Aurora detects re-entry after stale window) so
/// the system can pick up where it left off rather than start cold.
/// Surfaces the user's confirmed long-term insights, pending review items,
/// and chronicle summary in a clean, dismissible card.
class ReturnCaseFileCard extends ConsumerWidget {
  const ReturnCaseFileCard({
    super.key,
    this.onContinue,
    this.onDismiss,
  });

  final VoidCallback? onContinue;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncCase = ref.watch(returnCaseFileProvider);

    return asyncCase.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => CompactErrorCard(
        onRetry: () => ref.invalidate(returnCaseFileProvider),
      ),
      data: (caseFile) {
        if (caseFile == null || caseFile.isEmpty) {
          return const SizedBox.shrink();
        }
        return _ReturnCaseBody(
          caseFile: caseFile,
          onContinue: onContinue,
          onDismiss: onDismiss,
          onRebuild: () {
            refreshReturnCaseFile(ref);
          },
        );
      },
    );
  }
}

class _ReturnCaseBody extends StatelessWidget {
  const _ReturnCaseBody({
    required this.caseFile,
    required this.onRebuild,
    this.onContinue,
    this.onDismiss,
  });

  final ReturnCaseFile caseFile;
  final VoidCallback onRebuild;
  final VoidCallback? onContinue;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final summary = caseFile.summary;
    final topInsights = caseFile.confirmedInsights.take(3).toList();

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.30)),
        boxShadow: [
          BoxShadow(
            color: DS.brandPrimary.withValues(alpha: 0.05),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(
                Icons.auto_stories_rounded,
                color: DS.brandPrimary,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  context.l10n.rcfWelcomeBack,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              if (onDismiss != null)
                IconButton(
                  icon: Icon(Icons.close, color: DS.textTertiary, size: 18),
                  onPressed: onDismiss,
                  tooltip: context.l10n.rcfClose,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
            ],
          ),
          const SizedBox(height: 12),
          _SummaryRow(summary: summary),
          if (topInsights.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              context.l10n.rcfConfirmedStrategies,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 6),
            ...topInsights.map((i) => _InsightTile(insight: i)),
          ],
          if (summary.pendingCount > 0) ...[
            const SizedBox(height: 8),
            Text(
              context.l10n.rcfPendingInsights(summary.pendingCount),
              style: TextStyle(
                color: DS.brandPrimary,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: TextButton(
                  onPressed: onRebuild,
                  style: TextButton.styleFrom(
                    foregroundColor: DS.textSecondary,
                  ),
                  child: Text(
                    context.l10n.rcfRefresh,
                    style: const TextStyle(fontSize: 13),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton(
                  onPressed: onContinue,
                  style: FilledButton.styleFrom(
                    backgroundColor: DS.brandPrimary,
                  ),
                  child: Text(
                    context.l10n.rcfContinue,
                    style: const TextStyle(fontSize: 13),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({required this.summary});
  final ReturnCaseFileSummary summary;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            _StatChip(
              label: context.l10n.rcfConfirmed,
              value: summary.confirmedCount,
              color: DS.brandPrimary,
            ),
            const SizedBox(width: 12),
            _StatChip(
              label: context.l10n.rcfPending,
              value: summary.pendingCount,
              color: DS.semanticWarning,
            ),
            const SizedBox(width: 12),
            _StatChip(
              label: context.l10n.rcfTotal,
              value: summary.totalEntries,
              color: DS.textTertiary,
            ),
          ],
        ),
      );
}

class _StatChip extends StatelessWidget {
  const _StatChip({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$value',
            style: TextStyle(
              color: color,
              fontSize: 18,
              fontWeight: FontWeight.w700,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          Text(
            label,
            style: TextStyle(
              color: DS.textTertiary,
              fontSize: 11,
            ),
          ),
        ],
      );
}

class _InsightTile extends StatelessWidget {
  const _InsightTile({required this.insight});
  final ReturnCaseFileInsight insight;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.check_circle_outline,
              color: DS.brandPrimary.withValues(alpha: 0.7),
              size: 14,
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    insight.claim,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: 13,
                      height: 1.52,
                    ),
                  ),
                  if (insight.recommendedFutureUse != null &&
                      insight.recommendedFutureUse!.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(
                        insight.recommendedFutureUse!,
                        style: TextStyle(
                          color: DS.textTertiary,
                          fontSize: 11,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      );
}
