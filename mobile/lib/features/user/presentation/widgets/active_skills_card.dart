import 'package:flutter/material.dart';
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
              '当前激活技能',
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            if (items.isEmpty)
              Text(
                '这一轮还没有明显命中的技能摘要，先保持默认支持方式。',
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
