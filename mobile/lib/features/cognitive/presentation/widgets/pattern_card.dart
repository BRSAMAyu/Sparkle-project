import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';

class PatternCard extends StatelessWidget {
  const PatternCard({required this.pattern, super.key});
  final BehaviorPatternModel pattern;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    Color iconColor;
    IconData icon;
    LinearGradient gradient;

    switch (pattern.patternType) {
      case 'cognitive':
        iconColor = DS.brandPrimary.shade700;
        icon = Icons.psychology;
        gradient = DS.infoGradient;
      case 'emotional':
        iconColor = DS.prismPurple.shade700;
        icon = Icons.sentiment_very_dissatisfied;
        gradient = DS.warningGradient;
      case 'execution':
        iconColor = DS.success.shade700;
        icon = Icons.run_circle;
        gradient = DS.successGradient;
      default:
        iconColor = DS.neutral600;
        icon = Icons.help_outline;
        gradient = DS.primaryGradient;
    }

    return Card(
      elevation: 4,
      shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius20),
      color: isDark ? DS.neutral800 : DS.brandPrimary,
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing8),
                  decoration: BoxDecoration(
                    gradient: gradient,
                    borderRadius: DS.borderRadius12,
                  ),
                  child: Icon(icon, color: DS.brandPrimary),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Text(
                    pattern.patternName,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: isDark ? DS.brandPrimary : DS.neutral900,
                    ),
                  ),
                ),
                if (pattern.isArchived)
                  Icon(Icons.archive, color: DS.neutral500, size: 20),
              ],
            ),
            const SizedBox(height: DS.spacing16),
            if (pattern.description != null)
              SparkleMarkdown(
                content: pattern.description!,
                textColor: isDark ? DS.neutral300 : DS.neutral700,
                codeBackgroundColor: isDark ? DS.neutral700 : DS.neutral100,
                linkColor: DS.brandPrimary,
                fontSize: DS.fontSizeSm,
                lineHeight: 1.55,
              ),
            if (pattern.solutionText != null) ...[
              const SizedBox(height: DS.spacing20),
              Container(
                padding: const EdgeInsets.all(DS.spacing16),
                decoration: BoxDecoration(
                  color: isDark ? DS.neutral700 : DS.neutral100,
                  borderRadius: DS.borderRadius16,
                  border: Border.all(color: DS.neutral200),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.lightbulb_outline, color: iconColor),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: SparkleMarkdown(
                        content:
                            '**${context.l10n.patternCardSolutionLabel}**：${pattern.solutionText!}',
                        textColor: isDark ? DS.neutral200 : DS.neutral800,
                        codeBackgroundColor:
                            isDark ? DS.neutral800 : DS.neutral100,
                        linkColor: DS.brandPrimary,
                        fontSize: DS.fontSizeSm,
                        lineHeight: 1.55,
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: DS.spacing16),
            Align(
              alignment: Alignment.bottomRight,
              child: Text(
                context.l10n.patternCardCreatedAt(
                  Formatters.formatDateShort(pattern.createdAt),
                ),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: DS.neutral500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
