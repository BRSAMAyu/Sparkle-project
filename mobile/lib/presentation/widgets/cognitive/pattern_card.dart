import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/behavior_pattern_model.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

class PatternCard extends StatelessWidget {
  final BehaviorPatternModel pattern;

  const PatternCard({required this.pattern, super.key});

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
        gradient = AppDesignTokens.infoGradient;
        break;
      case 'emotional':
        iconColor = Colors.purple.shade700;
        icon = Icons.sentiment_very_dissatisfied;
        gradient = AppDesignTokens.warningGradient;
        break;
      case 'execution':
        iconColor = DS.success.shade700;
        icon = Icons.run_circle;
        gradient = AppDesignTokens.successGradient;
        break;
      default:
        iconColor = AppDesignTokens.neutral600;
        icon = Icons.help_outline;
        gradient = AppDesignTokens.primaryGradient;
    }

    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius20),
      color: isDark ? AppDesignTokens.neutral800 : DS.brandPrimary,
      child: Padding(
        padding: const EdgeInsets.all(AppDesignTokens.spacing20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(AppDesignTokens.spacing8),
                  decoration: BoxDecoration(
                    gradient: gradient,
                    borderRadius: AppDesignTokens.borderRadius12,
                  ),
                  child: Icon(icon, color: DS.brandPrimary),
                ),
                const SizedBox(width: AppDesignTokens.spacing12),
                Expanded(
                  child: Text(
                    pattern.patternName,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: AppDesignTokens.fontWeightBold,
                      color: isDark ? DS.brandPrimary : AppDesignTokens.neutral900,
                    ),
                  ),
                ),
                if (pattern.isArchived)
                  const Icon(Icons.archive, color: AppDesignTokens.neutral500, size: 20),
              ],
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            if (pattern.description != null)
              MarkdownBody(
                data: pattern.description!,
                styleSheet: MarkdownStyleSheet(
                  p: theme.textTheme.bodyMedium?.copyWith(
                    color: isDark ? AppDesignTokens.neutral300 : AppDesignTokens.neutral700,
                    height: 1.5,
                  ),
                ),
                shrinkWrap: true,
              ),
            if (pattern.solutionText != null) ...[
              const SizedBox(height: AppDesignTokens.spacing20),
              Container(
                padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                decoration: BoxDecoration(
                  color: isDark ? AppDesignTokens.neutral700 : AppDesignTokens.neutral100,
                  borderRadius: AppDesignTokens.borderRadius16,
                  border: Border.all(color: AppDesignTokens.neutral200),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.lightbulb_outline, color: iconColor),
                    const SizedBox(width: AppDesignTokens.spacing12),
                    Expanded(
                      child: MarkdownBody(
                        data: '**破解咒语**: ${pattern.solutionText!}',
                        styleSheet: MarkdownStyleSheet(
                          p: theme.textTheme.bodyMedium?.copyWith(
                            color: isDark ? AppDesignTokens.neutral200 : AppDesignTokens.neutral800,
                            fontWeight: FontWeight.w500,
                            height: 1.5,
                          ),
                          strong: theme.textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: isDark ? DS.brandPrimary : AppDesignTokens.neutral900,
                          ),
                        ),
                        shrinkWrap: true,
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: AppDesignTokens.spacing16),
            Align(
              alignment: Alignment.bottomRight,
              child: Text(
                '创建于: ${pattern.createdAt.toLocal().toString().split(' ')[0]}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: AppDesignTokens.neutral500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
