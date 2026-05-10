import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/error_book/data/models/remediable_pattern.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';

typedef RemedialTemplateGenerator = Future<RemedialTaskTemplate> Function(
  RemediablePattern pattern,
);
typedef RemedialTemplateAccepter = Future<void> Function(
  RemediablePattern pattern,
  RemedialTaskTemplate template,
);

class RemediablePatternsCard extends ConsumerWidget {
  const RemediablePatternsCard({
    super.key,
    this.patterns,
    this.maxPatterns = 3,
    this.onGenerateTemplate,
    this.onAcceptTemplate,
  });

  final List<RemediablePattern>? patterns;
  final int maxPatterns;
  final RemedialTemplateGenerator? onGenerateTemplate;
  final RemedialTemplateAccepter? onAcceptTemplate;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final explicitPatterns = patterns;
    if (explicitPatterns != null) {
      return _buildCard(
        context,
        ref,
        explicitPatterns.take(maxPatterns).toList(),
      );
    }

    return ref.watch(remediablePatternsProvider).when(
          data: (items) =>
              _buildCard(context, ref, items.take(maxPatterns).toList()),
          loading: () => const SizedBox.shrink(),
          error: (_, __) => CompactErrorCard(
            onRetry: () => ref.invalidate(remediablePatternsProvider),
          ),
        );
  }

  Widget _buildCard(
    BuildContext context,
    WidgetRef ref,
    List<RemediablePattern> items,
  ) {
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        DS.spacing12,
        DS.spacing16,
        DS.spacing4,
      ),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                    border:
                        Border.all(color: DS.warning.withValues(alpha: 0.25)),
                  ),
                  child: Icon(
                    Icons.psychology_alt_outlined,
                    color: DS.warning,
                    size: 22,
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.remediablePatternsTitle,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: DS.fontWeightSemibold,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        context.l10n.remediablePatternsDesc,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            ...items.map(
              (pattern) => _RemediablePatternRow(
                pattern: pattern,
                onPressed: () => _openTemplatePreview(context, ref, pattern),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openTemplatePreview(
    BuildContext context,
    WidgetRef ref,
    RemediablePattern pattern,
  ) async {
    try {
      final template = onGenerateTemplate != null
          ? await onGenerateTemplate!(pattern)
          : await ref
              .read(errorBookRepositoryProvider)
              .generateTaskTemplate(pattern.id);
      if (!context.mounted) return;

      final accepted = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => _TaskTemplatePreviewDialog(
          pattern: pattern,
          template: template,
          onAccept: () async {
            if (onAcceptTemplate != null) {
              await onAcceptTemplate!(pattern, template);
            } else {
              await ref
                  .read(errorBookRepositoryProvider)
                  .acceptTaskTemplate(pattern.id);
            }
            ref
              ..invalidate(remediablePatternsProvider)
              ..invalidate(errorListProvider)
              ..invalidate(errorStatsProvider)
              ..invalidate(taskListProvider);
          },
        ),
      );

      if (context.mounted && (accepted ?? false)) {
        AppFeedback.success(
          context,
          context.l10n.remediableTaskAdded,
        );
      }
    } catch (error) {
      if (!context.mounted) return;
      AppFeedback.error(
        context,
        context.l10n.remediableGenerateFailed(error.toString()),
      );
    }
  }
}

class _RemediablePatternRow extends StatelessWidget {
  const _RemediablePatternRow({
    required this.pattern,
    required this.onPressed,
  });

  final RemediablePattern pattern;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      margin: const EdgeInsets.only(top: DS.spacing8),
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfacePrimaryElevated,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 360;
          final content = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                pattern.displayFocus,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing6,
                runSpacing: DS.spacing6,
                children: [
                  _MetricPill(
                    icon: Icons.error_outline,
                    label: context.l10n.errorCountLabel(pattern.errorCount),
                  ),
                  _MetricPill(
                    icon: Icons.hub_outlined,
                    label: pattern.errorTypeLabel,
                  ),
                  _MetricPill(
                    icon: Icons.timer_outlined,
                    label: context.l10n.minutesLabel(pattern.suggestedDurationMinutes),
                  ),
                ],
              ),
              if (pattern.rootCauseSummary?.isNotEmpty ?? false) ...[
                const SizedBox(height: DS.spacing8),
                Text(
                  pattern.rootCauseSummary!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.35,
                  ),
                ),
              ],
            ],
          );

          final action = FilledButton.icon(
            onPressed: onPressed,
            icon: const Icon(Icons.add_task_outlined, size: 18),
            label: Text(context.l10n.generateRemedialTask),
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                content,
                const SizedBox(height: DS.spacing10),
                action,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: content),
              const SizedBox(width: DS.spacing12),
              action,
            ],
          );
        },
      ),
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.brandPrimary),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.brandPrimary,
                    fontWeight: DS.fontWeightMedium,
                  ),
            ),
          ],
        ),
      );
}

class _TaskTemplatePreviewDialog extends StatefulWidget {
  const _TaskTemplatePreviewDialog({
    required this.pattern,
    required this.template,
    required this.onAccept,
  });

  final RemediablePattern pattern;
  final RemedialTaskTemplate template;
  final Future<void> Function() onAccept;

  @override
  State<_TaskTemplatePreviewDialog> createState() =>
      _TaskTemplatePreviewDialogState();
}

class _TaskTemplatePreviewDialogState
    extends State<_TaskTemplatePreviewDialog> {
  bool _accepting = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return AlertDialog(
      title: Text(widget.template.title),
      content: SizedBox(
        width: 520,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                widget.template.objective,
                style: theme.textTheme.bodyMedium?.copyWith(height: 1.4),
              ),
              const SizedBox(height: DS.spacing12),
              _PreviewSection(
                icon: Icons.flag_outlined,
                title: context.l10n.minimumOutputLabel,
                child: Text(widget.template.minimumOutput),
              ),
              const SizedBox(height: DS.spacing12),
              _PreviewSection(
                icon: Icons.check_circle_outline,
                title: context.l10n.successCriteriaLabel,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: widget.template.successCriteria
                      .map((item) => Text('• $item'))
                      .toList(),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _PreviewSection(
                icon: Icons.format_list_numbered,
                title: context.l10n.practiceStepsLabel,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: widget.template.structuredSteps
                      .map(
                        (step) => Padding(
                          padding: const EdgeInsets.only(bottom: DS.spacing8),
                          child: Text(
                            '${step.order}. ${step.title} · ${step.instruction}',
                            style: theme.textTheme.bodySmall?.copyWith(
                              height: 1.35,
                            ),
                          ),
                        ),
                      )
                      .toList(),
                ),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _accepting ? null : () => Navigator.of(context).pop(false),
          child: Text(context.l10n.cancel),
        ),
        FilledButton.icon(
          onPressed: _accepting ? null : _acceptTemplate,
          icon: _accepting
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.playlist_add_check_rounded),
          label: Text(context.l10n.acceptAndAddToday),
        ),
      ],
    );
  }

  Future<void> _acceptTemplate() async {
    setState(() {
      _accepting = true;
    });
    try {
      await widget.onAccept();
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _accepting = false;
        });
      }
      rethrow;
    }
  }
}

class _PreviewSection extends StatelessWidget {
  const _PreviewSection({
    required this.icon,
    required this.title,
    required this.child,
  });

  final IconData icon;
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: DS.brandPrimary),
              const SizedBox(width: DS.spacing6),
              Text(
                title,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: DS.fontWeightSemibold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing6),
          child,
        ],
      );
}
