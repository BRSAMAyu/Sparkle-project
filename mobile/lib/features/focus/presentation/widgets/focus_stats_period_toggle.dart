import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
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
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.xs),
      decoration: BoxDecoration(
        color: DS.neutral100,
        borderRadius: BorderRadius.circular(DS.md),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: StatsViewPeriod.values.map((p) {
          final isSelected = period == p;
          return GestureDetector(
            onTap: () => onChanged(p),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(
                horizontal: DS.md,
                vertical: DS.xs,
              ),
              decoration: BoxDecoration(
                color: isSelected ? DS.brandPrimary : Colors.transparent,
                borderRadius: BorderRadius.circular(DS.sm),
              ),
              child: Text(
                p.label,
                style: TextStyle(
                  color: isSelected ? DS.neutral0 : DS.neutral600,
                  fontSize: 13,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
}
