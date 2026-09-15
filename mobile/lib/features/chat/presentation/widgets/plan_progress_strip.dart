import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class PlanProgressStrip extends StatelessWidget {
  const PlanProgressStrip({required this.data, super.key});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final currentStep = (data['current_step'] as num?)?.toInt() ?? 0;
    final steps = (data['steps'] as List<dynamic>? ?? const [])
        .map((item) => item.toString())
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.l10n.chatPlanProgress,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
        ),
        const SizedBox(height: DS.spacing12),
        Row(
          children: List.generate(steps.length, (index) {
            final isActive = index == currentStep;
            final isCompleted = index < currentStep;
            return Expanded(
              child: Padding(
                padding: EdgeInsets.only(
                  right: index == steps.length - 1 ? 0 : DS.spacing8,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      height: 8,
                      decoration: BoxDecoration(
                        color: isCompleted || isActive
                            ? DS.primaryBase
                            : DS.borderSubtle,
                        borderRadius: DS.borderRadius12,
                      ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      steps[index],
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: isActive || isCompleted
                                ? DS.textPrimary
                                : DS.textSecondary,
                            fontWeight: isActive
                                ? DS.fontWeightBold
                                : DS.fontWeightRegular,
                          ),
                    ),
                  ],
                ),
              ),
            );
          }),
        ),
      ],
    );
  }
}
