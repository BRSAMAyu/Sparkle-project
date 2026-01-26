import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/statistics/config/statistics_config.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';

/// Period toggle widget for switching between time periods
///
/// Displays a segmented control or tab bar for selecting
/// today/week/month/year periods.
class StatisticsPeriodToggle extends StatelessWidget {

  const StatisticsPeriodToggle({
    required this.selectedPeriod, required this.onPeriodChanged, super.key,
    this.showCustomOption = false,
    this.isCompact = false,
  });
  /// Currently selected period
  final StatisticsPeriod selectedPeriod;

  /// Callback when period is changed
  final ValueChanged<StatisticsPeriod> onPeriodChanged;

  /// Whether to show the custom period option
  final bool showCustomOption;

  /// Whether to use compact mode (smaller widgets)
  final bool isCompact;

  @override
  Widget build(BuildContext context) {
    final periods = showCustomOption
        ? StatisticsPeriod.values
        : [
            StatisticsPeriod.today,
            StatisticsPeriod.week,
            StatisticsPeriod.month,
            StatisticsPeriod.year,
          ];

    return Container(
      decoration: BoxDecoration(
        color: DS.neutral100,
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
      ),
      padding: EdgeInsets.all(isCompact ? DS.xs : DS.sm),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: periods.map((period) {
          final isSelected = selectedPeriod == period;
          return _PeriodButton(
            period: period,
            isSelected: isSelected,
            isCompact: isCompact,
            onTap: () => onPeriodChanged(period),
          );
        }).toList(),
      ),
    );
  }
}

/// Individual period button
class _PeriodButton extends StatefulWidget {

  const _PeriodButton({
    required this.period,
    required this.isSelected,
    required this.isCompact,
    required this.onTap,
  });
  final StatisticsPeriod period;
  final bool isSelected;
  final bool isCompact;
  final VoidCallback onTap;

  @override
  State<_PeriodButton> createState() => _PeriodButtonState();
}

class _PeriodButtonState extends State<_PeriodButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: StatisticsAnimationConfig.fast,
      vsync: this,
    );
    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: StatisticsAnimationConfig.cardPressScale,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: StatisticsAnimationConfig.cardCurve,
    ),);
  }

  @override
  void didUpdateWidget(_PeriodButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isSelected != oldWidget.isSelected) {
      if (widget.isSelected) {
        _controller.forward().then((_) {
          _controller.reverse();
        });
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final padding = widget.isCompact
        ? const EdgeInsets.symmetric(
            horizontal: DS.md,
            vertical: DS.xs,
          )
        : const EdgeInsets.symmetric(
            horizontal: DS.lg,
            vertical: DS.sm,
          );

    return GestureDetector(
      onTapDown: (_) => _controller.forward(),
      onTapUp: (_) => _controller.reverse(),
      onTapCancel: () => _controller.reverse(),
      onTap: widget.onTap,
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: AnimatedContainer(
          duration: StatisticsAnimationConfig.fast,
          curve: StatisticsAnimationConfig.easeOut,
          padding: padding,
          decoration: BoxDecoration(
            color: widget.isSelected ? DS.white : Colors.transparent,
            borderRadius: BorderRadius.circular(DS.borderRadiusMD),
            boxShadow: widget.isSelected
                ? [
                    BoxShadow(
                      color: DS.black.withValues(alpha: 0.1),
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: Text(
            widget.period.shortLabel,
            style: DS.textStyle.copyWith(
              fontSize: widget.isCompact ? DS.fontSizeSM : DS.fontSizeBase,
              fontWeight: widget.isSelected
                  ? DS.fontWeightSemibold
                  : DS.fontWeightMedium,
              color: widget.isSelected ? DS.brandPrimary : DS.neutral500,
            ),
          ),
        ),
      ),
    );
  }
}

/// Dropdown-style period selector
class StatisticsPeriodDropdown extends StatelessWidget {

  const StatisticsPeriodDropdown({
    required this.selectedPeriod, required this.onPeriodChanged, super.key,
    this.showCustomOption = false,
  });
  final StatisticsPeriod selectedPeriod;
  final ValueChanged<StatisticsPeriod> onPeriodChanged;
  final bool showCustomOption;

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.md, vertical: DS.sm),
      decoration: BoxDecoration(
        color: DS.neutral100,
        borderRadius: BorderRadius.circular(DS.borderRadiusMD),
        border: Border.all(color: DS.neutral200),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<StatisticsPeriod>(
          value: selectedPeriod,
          onChanged: (period) {
            if (period != null) {
              onPeriodChanged(period);
            }
          },
          items: _buildItems(),
          icon: Icon(
            Icons.keyboard_arrow_down,
            color: DS.neutral500,
            size: 20,
          ),
          style: DS.textStyle.copyWith(
            fontSize: DS.fontSizeBase,
            color: DS.neutral700,
          ),
          dropdownColor: DS.white,
          borderRadius: BorderRadius.circular(DS.borderRadiusMD),
          isDense: true,
        ),
      ),
    );

  List<DropdownMenuItem<StatisticsPeriod>> _buildItems() {
    final periods = showCustomOption
        ? StatisticsPeriod.values
        : [
            StatisticsPeriod.today,
            StatisticsPeriod.week,
            StatisticsPeriod.month,
            StatisticsPeriod.year,
          ];

    return periods.map((period) => DropdownMenuItem<StatisticsPeriod>(
        value: period,
        child: Text(period.label),
      ),).toList();
  }
}
