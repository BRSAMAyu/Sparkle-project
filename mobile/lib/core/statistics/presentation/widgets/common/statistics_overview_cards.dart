import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// A single statistics metric card
class StatisticsMetricCard extends StatelessWidget {
  const StatisticsMetricCard({
    required this.title,
    required this.value,
    super.key,
    this.unit,
    this.changePercentage,
    this.icon,
    this.backgroundColor,
    this.valueColor,
    this.isLoading = false,
  });

  /// Card title (e.g., "Total Minutes")
  final String title;

  /// Primary value to display
  final String value;

  /// Unit label (e.g., "分钟", "次")
  final String? unit;

  /// Change from previous period (percentage)
  final double? changePercentage;

  /// Icon for the card
  final IconData? icon;

  /// Background color
  final Color? backgroundColor;

  /// Value color
  final Color? valueColor;

  /// Whether to show a loading state
  final bool isLoading;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: backgroundColor ?? DS.white,
          borderRadius: BorderRadius.circular(DS.borderRadiusLG),
          border: Border.all(color: DS.neutral100),
        ),
        child: isLoading
            ? _buildLoading()
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (icon != null) _buildIcon(),
                  _buildTitle(),
                  const SizedBox(height: DS.sm),
                  _buildValue(),
                  if (changePercentage != null) _buildChange(),
                ],
              ),
      );

  Widget _buildIcon() => Container(
        padding: const EdgeInsets.all(DS.sm),
        decoration: BoxDecoration(
          color: (valueColor ?? DS.brandPrimary).withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(DS.borderRadiusMD),
        ),
        child: Icon(
          icon,
          size: 20,
          color: valueColor ?? DS.brandPrimary,
        ),
      );

  Widget _buildTitle() => Text(
        title,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        style: DS.captionStyle.copyWith(
          color: DS.neutral500,
        ),
      );

  Widget _buildValue() {
    final unitText = unit != null ? ' $unit' : '';
    return Align(
      alignment: Alignment.centerLeft,
      child: FittedBox(
        fit: BoxFit.scaleDown,
        alignment: Alignment.centerLeft,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              value,
              style: DS.headlineStyle.copyWith(
                color: valueColor ?? DS.neutral800,
                fontSize: 28,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            if (unit != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 4, left: DS.xs),
                child: Text(
                  unitText,
                  style: DS.captionStyle.copyWith(
                    color: DS.neutral400,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildChange() {
    final isPositive = (changePercentage ?? 0) >= 0;
    final color = StatisticsChartConfig.getTrendColor(changePercentage);
    final arrow = isPositive ? '↑' : '↓';
    final sign = isPositive ? '+' : '';

    return Container(
      margin: const EdgeInsets.only(top: DS.xs),
      child: Align(
        alignment: Alignment.centerLeft,
        child: FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '$arrow $sign${changePercentage!.toStringAsFixed(1)}%',
                style: DS.captionStyle.copyWith(
                  color: color,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
              const SizedBox(width: DS.xs),
              Text(
                '较上期',
                style: DS.captionStyle.copyWith(
                  color: DS.neutral400,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLoading() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 80,
            height: 14,
            decoration: BoxDecoration(
              color: DS.neutral100,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(height: DS.md),
          Container(
            width: 60,
            height: 28,
            decoration: BoxDecoration(
              color: DS.neutral100,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        ],
      );
}

/// A grid of overview cards for quick statistics summary
class StatisticsOverviewCards extends StatelessWidget {
  const StatisticsOverviewCards({
    required this.cards,
    super.key,
    this.crossAxisCount = 2,
    this.spacing,
    this.padding,
  });

  /// List of card data to display
  final List<OverviewCardData> cards;

  /// Number of columns in the grid
  final int crossAxisCount;

  /// Spacing between cards
  final double? spacing;

  /// Padding around the grid
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) => Padding(
        padding: padding ?? EdgeInsets.zero,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final resolvedSpacing = spacing ?? DS.md;
            if (constraints.maxWidth < 420) {
              final tileWidth = (constraints.maxWidth - resolvedSpacing) / 2;
              return Wrap(
                spacing: resolvedSpacing,
                runSpacing: resolvedSpacing,
                children: [
                  for (var i = 0; i < cards.length; i++)
                    SizedBox(
                      width: tileWidth,
                      child: _buildCardWithAnimation(cards[i], i),
                    ),
                ],
              );
            }

            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: crossAxisCount,
                crossAxisSpacing: resolvedSpacing,
                mainAxisSpacing: resolvedSpacing,
                childAspectRatio: 1.4,
              ),
              itemCount: cards.length,
              itemBuilder: (context, index) =>
                  _buildCardWithAnimation(cards[index], index),
            );
          },
        ),
      );

  Widget _buildCardWithAnimation(OverviewCardData data, int index) =>
      TweenAnimationBuilder<double>(
        key: ValueKey(data.id),
        tween: Tween(begin: 0.0, end: 1.0),
        duration: StatisticsAnimationConfig.cardEntrance,
        curve: StatisticsAnimationConfig.cardCurve,
        builder: (context, value, child) => Transform.translate(
          offset: Offset(0, 20 * (1 - value)),
          child: Opacity(
            opacity: value,
            child: child,
          ),
        ),
        child: StatisticsMetricCard(
          title: data.title,
          value: data.value,
          unit: data.unit,
          changePercentage: data.changePercentage,
          icon: data.icon,
          backgroundColor: data.backgroundColor,
          valueColor: data.valueColor,
          isLoading: data.isLoading,
        ),
      );
}

/// Data class for overview card
class OverviewCardData {
  const OverviewCardData({
    required this.id,
    required this.title,
    required this.value,
    this.unit,
    this.changePercentage,
    this.icon,
    this.backgroundColor,
    this.valueColor,
    this.isLoading = false,
  });

  /// Create from a statistics summary
  factory OverviewCardData.fromSummary({
    required String id,
    required String title,
    required StatisticsSummary summary,
    String? unit,
    IconData? icon,
    Color? valueColor,
    bool isLoading = false,
  }) =>
      OverviewCardData(
        id: id,
        title: title,
        value: summary.total.toStringAsFixed(0),
        unit: unit,
        changePercentage: summary.changePercentage,
        icon: icon,
        valueColor: valueColor,
        isLoading: isLoading,
      );

  /// Create a loading placeholder card
  factory OverviewCardData.loading({required String id}) => OverviewCardData(
        id: id,
        title: '',
        value: '',
        isLoading: true,
      );

  /// Unique identifier
  final String id;

  /// Card title
  final String title;

  /// Display value
  final String value;

  /// Unit label
  final String? unit;

  /// Change percentage
  final double? changePercentage;

  /// Icon
  final IconData? icon;

  /// Background color
  final Color? backgroundColor;

  /// Value color
  final Color? valueColor;

  /// Whether to show loading state
  final bool isLoading;
}

/// Compact single-row statistics bar for tight spaces
class StatisticsMetricBar extends StatelessWidget {
  const StatisticsMetricBar({
    required this.label,
    required this.value,
    super.key,
    this.unit,
    this.changePercentage,
    this.valueColor,
    this.isLoading = false,
  });
  final String label;
  final String value;
  final String? unit;
  final double? changePercentage;
  final Color? valueColor;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Row(
        children: [
          Expanded(
            child: Container(
              height: 14,
              decoration: BoxDecoration(
                color: DS.neutral100,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ),
          const SizedBox(width: DS.sm),
          Container(
            width: 60,
            height: 14,
            decoration: BoxDecoration(
              color: DS.neutral100,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        ],
      );
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: DS.bodyStyle.copyWith(
              color: DS.neutral600,
            ),
          ),
        ),
        const SizedBox(width: DS.sm),
        Flexible(
          child: Wrap(
            alignment: WrapAlignment.end,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: DS.xs,
            runSpacing: DS.xs,
            children: [
              Text(
                value,
                style: DS.bodyStyle.copyWith(
                  color: valueColor ?? DS.neutral800,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              if (unit != null)
                Text(
                  unit!,
                  style: DS.captionStyle.copyWith(
                    color: DS.neutral400,
                  ),
                ),
              if (changePercentage != null) _buildChangeIndicator(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildChangeIndicator() {
    final isPositive = (changePercentage ?? 0) >= 0;
    final color = StatisticsChartConfig.getTrendColor(changePercentage);
    final icon = isPositive ? Icons.arrow_upward : Icons.arrow_downward;
    final sign = isPositive ? '+' : '';

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 2),
        Text(
          '$sign${changePercentage!.toStringAsFixed(1)}%',
          style: DS.captionStyle.copyWith(
            color: color,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      ],
    );
  }
}
