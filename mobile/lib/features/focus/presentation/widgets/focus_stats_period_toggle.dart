import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';

/// Period toggle switch for statistics view (Today/Week/Month)
class FocusStatsPeriodToggle extends StatelessWidget {
  const FocusStatsPeriodToggle({
    required this.period,
    required this.onChanged,
    super.key,
  });

  final StatsViewPeriod period;
  final ValueChanged<StatsViewPeriod> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final animationDuration = context.reduceMotion ? Duration.zero : DS.normal;
    return Container(
      padding: const EdgeInsets.all(DS.xs),
      decoration: BoxDecoration(
        color: DS.neutral100,
        borderRadius: BorderRadius.circular(DS.md),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: StatsViewPeriod.values.map((p) {
          final isSelected = period == p;
          return Semantics(
            button: true,
            selected: isSelected,
            label: p.label(l10n),
            child: Material(
              color: DS.surfacePrimary.withValues(alpha: 0),
              borderRadius: BorderRadius.circular(DS.sm),
              child: InkWell(
                onTap: () => onChanged(p),
                borderRadius: BorderRadius.circular(DS.sm),
                child: AnimatedContainer(
                  duration: animationDuration,
                  constraints:
                      const BoxConstraints(minHeight: DS.touchTargetMinSize),
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.md,
                    vertical: DS.xs,
                  ),
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: isSelected
                        ? DS.brandPrimary
                        : DS.surfacePrimary.withValues(alpha: 0),
                    borderRadius: BorderRadius.circular(DS.sm),
                  ),
                  child: Text(
                    p.label(l10n),
                    style: TextStyle(
                      color: isSelected ? DS.textOnPrimary : DS.neutral600,
                      fontSize: 13,
                      fontWeight:
                          isSelected ? FontWeight.w600 : FontWeight.w500,
                    ),
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
