import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/behavior_pattern_model.dart';

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
        iconColor = Colors.purple.shade700;
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
      shape: RoundedRectangleBorder(borderRadius: DS.borderRadius20),
      color: isDark ? DS.neutral800 : DS.brandPrimary,
      child: Padding(
        padding: EdgeInsets.all(DS.spacing20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: EdgeInsets.all(DS.spacing8),
                  decoration: BoxDecoration(
                    gradient: gradient,
                    borderRadius: DS.borderRadius12,
                  ),
                  child: Icon(icon, color: DS.brandPrimary),
                ),
                SizedBox(width: DS.spacing12),
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
            SizedBox(height: DS.spacing16),
            if (pattern.description != null)
              MarkdownBody(
                data: pattern.description!,
                styleSheet: MarkdownStyleSheet(
                  p: theme.textTheme.bodyMedium?.copyWith(
                    color: isDark ? DS.neutral300 : DS.neutral700,
                    height: 1.5,
                  ),
                ),
              ),
            if (pattern.solutionText != null) ...[
              SizedBox(height: DS.spacing20),
              Container(
                padding: EdgeInsets.all(DS.spacing16),
                decoration: BoxDecoration(
                  color: isDark ? DS.neutral700 : DS.neutral100,
                  borderRadius: DS.borderRadius16,
                  border: Border.all(color: DS.neutral200),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.lightbulb_outline, color: iconColor),
                    SizedBox(width: DS.spacing12),
                    Expanded(
                      child: MarkdownBody(
                        data: '**破解咒语**: ${pattern.solutionText!}',
                        styleSheet: MarkdownStyleSheet(
                          p: theme.textTheme.bodyMedium?.copyWith(
                            color: isDark ? DS.neutral200 : DS.neutral800,
                            fontWeight: FontWeight.w500,
                            height: 1.5,
                          ),
                          strong: theme.textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: isDark ? DS.brandPrimary : DS.neutral900,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            SizedBox(height: DS.spacing16),
            Align(
              alignment: Alignment.bottomRight,
              child: Text(
                '创建于: ${pattern.createdAt.toLocal().toString().split(' ')[0]}',
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
