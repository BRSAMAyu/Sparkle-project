import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/user_state_models.dart';

class ActiveSkillsCard extends StatelessWidget {
  const ActiveSkillsCard({required this.summary, super.key});

  final UserStateFieldEnvelope<Stage35ActiveSkillsSummary>? summary;

  @override
  Widget build(BuildContext context) {
    final items = summary?.value.items ?? const <Stage35ActiveSkillItem>[];
    return GraphiteCardSurface(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.userActiveSkills,
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            if (items.isEmpty)
              Text(
                context.l10n.userActiveSkillsEmpty,
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              )
            else
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: items
                    .take(4)
                    .map(
                      (item) => Chip(
                        label: Text(
                          '${item.name} ${(item.activationMatchScore * 100).round()}%',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                    .toList(),
              ),
          ],
        ),
      ),
    );
  }
}
