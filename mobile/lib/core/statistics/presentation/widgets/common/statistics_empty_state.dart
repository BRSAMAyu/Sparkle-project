import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Empty state widget for when no statistics data is available
class StatisticsEmptyState extends StatelessWidget {

  const StatisticsEmptyState({
    super.key,
    this.message,
    this.subtitle,
    this.icon,
    this.actionLabel,
    this.onAction,
    this.isLoading = false,
  });
  /// Message to display
  final String? message;

  /// Subtitle for additional context
  final String? subtitle;

  /// Icon to display
  final IconData? icon;

  /// Action button label
  final String? actionLabel;

  /// Callback when action button is pressed
  final VoidCallback? onAction;

  /// Whether to show a loading animation
  final bool isLoading;

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.xl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (isLoading) _buildLoading() else _buildContent(),
        ],
      ),
    );

  Widget _buildContent() => TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: StatisticsAnimationConfig.medium,
      curve: StatisticsAnimationConfig.easeOut,
      builder: (context, value, child) => Opacity(
          opacity: value,
          child: Transform.scale(
            scale: 0.8 + (0.2 * value),
            child: child,
          ),
        ),
      child: Column(
        children: [
          _buildIcon(),
          const SizedBox(height: DS.lg),
          _buildMessage(),
          if (subtitle != null) ...[
            const SizedBox(height: DS.sm),
            _buildSubtitle(),
          ],
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: DS.xl),
            _buildActionButton(),
          ],
        ],
      ),
    );

  Widget _buildIcon() {
    final iconData = icon ?? Icons.bar_chart_outlined;

    return Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        color: StatisticsChartConfig.emptyStateColor.withValues(alpha: 0.3),
        shape: BoxShape.circle,
      ),
      child: Icon(
        iconData,
        size: 40,
        color: StatisticsChartConfig.emptyStateColor,
      ),
    );
  }

  Widget _buildMessage() {
    const defaultMessage = '暂无统计数据';
    return Text(
      message ?? defaultMessage,
      style: DS.headlineStyle.copyWith(
        color: DS.neutral600,
        fontSize: 18,
      ),
      textAlign: TextAlign.center,
    );
  }

  Widget _buildSubtitle() => Text(
      subtitle!,
      style: DS.bodyStyle.copyWith(
        color: DS.neutral400,
      ),
      textAlign: TextAlign.center,
    );

  Widget _buildActionButton() => ElevatedButton(
      onPressed: onAction,
      style: ElevatedButton.styleFrom(
        backgroundColor: DS.brandPrimary,
        foregroundColor: DS.white,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.xl,
          vertical: DS.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DS.borderRadiusMD),
        ),
      ),
      child: Text(
        actionLabel!,
        style: DS.bodyStyle.copyWith(
          fontWeight: DS.fontWeightMedium,
        ),
      ),
    );

  Widget _buildLoading() => SizedBox(
      width: 40,
      height: 40,
      child: CircularProgressIndicator(
        strokeWidth: 3,
        valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
      ),
    );
}

/// Empty state for specific statistics types
class StatisticsEmptyStateForType extends StatelessWidget {

  const StatisticsEmptyStateForType({
    required this.type, super.key,
    this.actionLabel,
    this.onAction,
    this.isLoading = false,
  });
  final StatisticsType type;
  final String? actionLabel;
  final VoidCallback? onAction;
  final bool isLoading;

  @override
  Widget build(BuildContext context) => StatisticsEmptyState(
      message: _getMessage(),
      subtitle: _getSubtitle(),
      icon: _getIcon(),
      actionLabel: actionLabel,
      onAction: onAction,
      isLoading: isLoading,
    );

  String _getMessage() {
    switch (type) {
      case StatisticsType.focus:
        return '暂无专注记录';
      case StatisticsType.agent:
        return '暂无智能体使用记录';
      case StatisticsType.capsule:
        return '暂无好奇心胶囊';
      case StatisticsType.learning:
        return '暂无学习数据';
    }
  }

  String? _getSubtitle() {
    switch (type) {
      case StatisticsType.focus:
        return '开始专注后会在这里看到统计数据';
      case StatisticsType.agent:
        return '使用智能体后会在这里看到统计数据';
      case StatisticsType.capsule:
        return '探索胶囊后会在这里看到统计数据';
      case StatisticsType.learning:
        return '学习后会在这里看到统计数据';
    }
  }

  IconData _getIcon() {
    switch (type) {
      case StatisticsType.focus:
        return Icons.timer_outlined;
      case StatisticsType.agent:
        return Icons.smart_toy_outlined;
      case StatisticsType.capsule:
        return Icons.lightbulb_outlined;
      case StatisticsType.learning:
        return Icons.school_outlined;
    }
  }
}

/// Error state widget for when statistics loading fails
class StatisticsErrorState extends StatelessWidget {

  const StatisticsErrorState({
    super.key,
    this.message,
    this.onRetry,
  });
  final String? message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.xl),
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.0, end: 1.0),
        duration: StatisticsAnimationConfig.medium,
        curve: StatisticsAnimationConfig.easeOut,
        builder: (context, value, child) => Opacity(
            opacity: value,
            child: child,
          ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: DS.error.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.error_outline,
                size: 40,
                color: DS.error,
              ),
            ),
            const SizedBox(height: DS.lg),
            Text(
              message ?? '加载失败',
              style: DS.headlineStyle.copyWith(
                color: DS.neutral600,
                fontSize: 18,
              ),
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: DS.xl),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('重试'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: DS.brandPrimary,
                  side: BorderSide(color: DS.brandPrimary),
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.xl,
                    vertical: DS.md,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(DS.borderRadiusMD),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
}

