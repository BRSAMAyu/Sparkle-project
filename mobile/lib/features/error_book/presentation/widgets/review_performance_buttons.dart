import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Review performance rating button group.
///
/// Used on the review page so users can rate mastery for an error record.
/// Options: remembered, fuzzy, and forgotten.
class ReviewPerformanceButtons extends StatelessWidget {
  const ReviewPerformanceButtons({
    required this.onPerformanceSelected,
    super.key,
    this.isLoading = false,
  });
  final ValueChanged<String> onPerformanceSelected;
  final bool isLoading;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SparkleStaggerItem(
            index: 0,
            child: Text(
              context.l10n.ebReviewMasteryPrompt,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightSemibold,
                  ),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Row(
            children: [
              Expanded(
                child: SparkleStaggerItem(
                  index: 1,
                  child: _PerformanceButton(
                    performance: 'forgotten',
                    label: context.l10n.ebForgot,
                    icon: Icons.close,
                    color: DS.error,
                    description: context.l10n.ebForgotHint,
                    isLoading: isLoading,
                    onTap: () {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.warning,
                        ),
                      );
                      onPerformanceSelected('forgotten');
                    },
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: SparkleStaggerItem(
                  index: 2,
                  child: _PerformanceButton(
                    performance: 'fuzzy',
                    label: context.l10n.ebFuzzy,
                    icon: Icons.remove,
                    color: DS.warningLight,
                    description: context.l10n.ebFuzzyHint,
                    isLoading: isLoading,
                    onTap: () {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.selection,
                        ),
                      );
                      onPerformanceSelected('fuzzy');
                    },
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: SparkleStaggerItem(
                  index: 3,
                  child: _PerformanceButton(
                    performance: 'remembered',
                    label: context.l10n.ebRemembered,
                    icon: Icons.check,
                    color: DS.success,
                    description: context.l10n.ebRememberedHint,
                    isLoading: isLoading,
                    onTap: () {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.success,
                        ),
                      );
                      onPerformanceSelected('remembered');
                    },
                  ),
                ),
              ),
            ],
          ),
        ],
      );
}

class _PerformanceButton extends StatelessWidget {
  const _PerformanceButton({
    required this.performance,
    required this.label,
    required this.icon,
    required this.color,
    required this.description,
    required this.isLoading,
    required this.onTap,
  });
  final String performance;
  final String label;
  final IconData icon;
  final Color color;
  final String description;
  final bool isLoading;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: color.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: isLoading ? null : onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(
            vertical: DS.spacing16,
            horizontal: DS.spacing12,
          ),
          decoration: BoxDecoration(
            border: Border.all(color: color.withValues(alpha: 0.3)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Icon(
                icon,
                color: color,
                size: 32,
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                label,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: color,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                description,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: color.withValues(alpha: 0.8),
                ),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Review performance selector bottom sheet.
///
/// Provides a more detailed alternative to the inline button group.
class ReviewPerformanceBottomSheet extends StatelessWidget {
  const ReviewPerformanceBottomSheet({
    required this.onPerformanceSelected,
    super.key,
  });
  final ValueChanged<String> onPerformanceSelected;

  static Future<String?> show(BuildContext context) =>
      showModalBottomSheet<String>(
        context: context,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        builder: (context) => ReviewPerformanceBottomSheet(
          onPerformanceSelected: (performance) {
            Navigator.of(context).pop(performance);
          },
        ),
      );

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              context.l10n.ebReviewMasterySheetTitle,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.ebReviewMasterySheetDesc,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing24),
            _PerformanceOption(
              performance: 'remembered',
              label: context.l10n.ebPerfectRecall,
              description: context.l10n.ebPerfectRecallHint,
              color: DS.success,
              onTap: () => onPerformanceSelected('remembered'),
            ),
            const SizedBox(height: DS.spacing12),
            _PerformanceOption(
              performance: 'fuzzy',
              label: context.l10n.ebFuzzyRecall,
              description: context.l10n.ebFuzzyRecallHint,
              color: DS.warningLight,
              onTap: () => onPerformanceSelected('fuzzy'),
            ),
            const SizedBox(height: DS.spacing12),
            _PerformanceOption(
              performance: 'forgotten',
              label: context.l10n.ebCompleteForgot,
              description: context.l10n.ebCompleteForgotHint,
              color: DS.error,
              onTap: () => onPerformanceSelected('forgotten'),
            ),
            const SizedBox(height: DS.spacing16),
            SparkleButton.ghost(
              onPressed: () => Navigator.of(context).pop(),
              label: context.l10n.toolsWbCancel,
            ),
          ],
        ),
      ),
    );
  }
}

class _PerformanceOption extends StatelessWidget {
  const _PerformanceOption({
    required this.performance,
    required this.label,
    required this.description,
    required this.color,
    required this.onTap,
  });
  final String performance;
  final String label;
  final String description;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: color.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            border: Border.all(color: color.withValues(alpha: 0.3), width: 2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _getIcon(performance),
                  color: color,
                  size: 28,
                ),
              ),
              const SizedBox(width: DS.spacing16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                        color: color,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      description,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right,
                color: color,
              ),
            ],
          ),
        ),
      ),
    );
  }

  IconData _getIcon(String performance) {
    switch (performance) {
      case 'remembered':
        return Icons.check_circle;
      case 'fuzzy':
        return Icons.help;
      case 'forgotten':
        return Icons.cancel;
      default:
        return Icons.help;
    }
  }
}
