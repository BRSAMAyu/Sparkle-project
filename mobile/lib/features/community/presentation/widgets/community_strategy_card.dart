import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// A community engagement strategy recommendation.
class CommunityStrategy {
  const CommunityStrategy({
    required this.title,
    required this.description,
    required this.strategyType,
    this.icon = Icons.lightbulb_outline,
    this.actionLabel,
    this.onAction,
  });

  final String title;
  final String description;
  final String strategyType;
  final IconData icon;
  final String? actionLabel;
  final VoidCallback? onAction;
}

/// Card showing a community engagement strategy recommendation.
///
/// Used in community screens and dashboard slots to surface
/// personalized strategies for community participation.
class CommunityStrategyCard extends StatelessWidget {
  const CommunityStrategyCard({
    required this.strategy,
    super.key,
    this.onDismiss,
  });

  final CommunityStrategy strategy;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final isChinese = I18nService.instance.isChinese;

    return Semantics(
      container: true,
      label: isChinese ? '社区策略：${strategy.title}' : 'Community strategy: ${strategy.title}',
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.1),
                    borderRadius: DS.borderRadius8,
                  ),
                  child: Icon(
                    strategy.icon,
                    size: 20,
                    color: DS.brandPrimary,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        strategy.title,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              fontWeight: DS.fontWeightSemibold,
                              color: DS.textPrimary,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        strategy.description,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.35,
                            ),
                      ),
                    ],
                  ),
                ),
                if (onDismiss != null)
                  SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    icon: const Icon(Icons.close, size: 16),
                    onPressed: onDismiss,
                  ),
              ],
            ),
            if (strategy.actionLabel != null) ...[
              const SizedBox(height: 10),
              Align(
                alignment: Alignment.centerRight,
                child: SparkleButton(
                  label: strategy.actionLabel!,
                  size: ButtonSize.small,
                  onPressed: strategy.onAction,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
