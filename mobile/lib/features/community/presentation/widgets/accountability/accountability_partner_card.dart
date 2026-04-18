import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class AccountabilityPartnerCard extends StatelessWidget {
  const AccountabilityPartnerCard({
    required this.title,
    required this.summary,
    super.key,
    this.leadingIcon = Icons.volunteer_activism_outlined,
    this.accentColor,
    this.bullets = const [],
  });

  final String title;
  final String summary;
  final IconData leadingIcon;
  final Color? accentColor;
  final List<String> bullets;

  @override
  Widget build(BuildContext context) {
    final color = accentColor ?? DS.brandPrimary;

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        gradient: LinearGradient(
          colors: [
            color.withValues(alpha: 0.18),
            DS.surfacePrimary,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(leadingIcon, color: color),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: DS.xs),
                    Text(
                      summary,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (bullets.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: bullets
                  .map(
                    (bullet) => Chip(
                      label: Text(bullet),
                      visualDensity: VisualDensity.compact,
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
        ],
      ),
    );
  }
}
