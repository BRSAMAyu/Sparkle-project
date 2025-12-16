import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class StatisticsCard extends StatelessWidget {
  final String title;
  final Widget chart;
  final String? subtitle;

  const StatisticsCard({
    required this.title, 
    required this.chart, 
    this.subtitle,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(
        horizontal: AppDesignTokens.spacing16,
        vertical: AppDesignTokens.spacing8,
      ),
      padding: const EdgeInsets.all(AppDesignTokens.spacing16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Colors.white, AppDesignTokens.neutral50],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: AppDesignTokens.borderRadius16,
        boxShadow: AppDesignTokens.shadowMd,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: AppDesignTokens.fontWeightBold,
                ),
              ),
              if (subtitle != null)
                Text(
                  subtitle!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppDesignTokens.neutral600,
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppDesignTokens.spacing16),
          SizedBox(
            height: 200,
            child: chart,
          ),
        ],
      ),
    );
  }
}
