import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/l10n/app_localizations.dart';

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
            if (isLoading) _buildLoading() else _buildContent(context),
          ],
        ),
      );

  Widget _buildContent(BuildContext context) {
    final l10n = context.l10n;
    return TweenAnimationBuilder<double>(
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
            _buildMessage(context, l10n),
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
  }

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

  Widget _buildMessage(BuildContext context, AppLocalizations l10n) {
    return Text(
      message ?? l10n.statisticsNoDataYet,
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

  Widget _buildActionButton() => SparkleButton(
        label: actionLabel!,
        onPressed: onAction,
        icon: const Icon(Icons.file_download_outlined),
        size: ButtonSize.large,
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
    required this.type,
    super.key,
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
        message: _getMessage(context),
        subtitle: _getSubtitle(context),
        icon: _getIcon(),
        actionLabel: actionLabel,
        onAction: onAction,
        isLoading: isLoading,
      );

  String _getMessage(BuildContext context) {
    final l10n = context.l10n;
    switch (type) {
      case StatisticsType.focus:
        return l10n.statisticsEmptyFocus;
      case StatisticsType.agent:
        return l10n.statisticsEmptyAgent;
      case StatisticsType.capsule:
        return l10n.statisticsEmptyCapsule;
      case StatisticsType.learning:
        return l10n.statisticsEmptyLearning;
    }
  }

  String? _getSubtitle(BuildContext context) {
    final l10n = context.l10n;
    switch (type) {
      case StatisticsType.focus:
        return l10n.statisticsEmptyFocusSubtitle;
      case StatisticsType.agent:
        return l10n.statisticsEmptyAgentSubtitle;
      case StatisticsType.capsule:
        return l10n.statisticsEmptyCapsuleSubtitle;
      case StatisticsType.learning:
        return l10n.statisticsEmptyLearningSubtitle;
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
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
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
                message ?? l10n.statisticsFailedToLoad,
                style: DS.headlineStyle.copyWith(
                  color: DS.neutral600,
                  fontSize: 18,
                ),
                textAlign: TextAlign.center,
              ),
              if (onRetry != null) ...[
                const SizedBox(height: DS.xl),
                SparkleButton.outline(
                  label: l10n.statisticsRetry,
                  onPressed: onRetry!,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ],
          ),
        ),
      );
  }
}
