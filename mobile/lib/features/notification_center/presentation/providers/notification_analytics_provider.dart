import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/features/notification_center/data/models/notification_analytics_model.dart'
    as model;
import 'package:sparkle/features/notification_center/data/repositories/notification_center_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';

part 'notification_analytics_provider.g.dart';

/// Analytics State
class NotificationAnalyticsState {
  const NotificationAnalyticsState({
    this.analytics,
    this.period = '7d',
    this.isLoading = false,
    this.error,
  });
  final model.NotificationAnalytics? analytics;
  final String period;
  final bool isLoading;
  final String? error;

  NotificationAnalyticsState copyWith({
    model.NotificationAnalytics? analytics,
    String? period,
    bool? isLoading,
    String? error,
  }) =>
      NotificationAnalyticsState(
        analytics: analytics ?? this.analytics,
        period: period ?? this.period,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

/// Notification Analytics Notifier
@riverpod
class NotificationAnalytics extends _$NotificationAnalytics {
  late NotificationCenterRepository _repository;

  @override
  NotificationAnalyticsState build() {
    _repository = ref.watch(notificationCenterRepositoryProvider);
    return const NotificationAnalyticsState();
  }

  /// Load analytics for a specific period
  Future<void> loadAnalytics(String period) async {
    state = state.copyWith(isLoading: true, period: period);

    try {
      final analytics = await _repository.getAnalytics(period);

      state = state.copyWith(
        analytics: analytics,
        isLoading: false,
        period: period,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Set period and reload analytics
  Future<void> setPeriod(String period) async {
    await loadAnalytics(period);
  }

  /// Refresh analytics with current period
  Future<void> refresh() async {
    if (state.period.isNotEmpty) {
      await loadAnalytics(state.period);
    }
  }
}

/// Period options
class AnalyticsPeriod {
  const AnalyticsPeriod(this.value, this.label);
  final String value;
  final String? label;

  static const List<AnalyticsPeriod> all = [
    AnalyticsPeriod('1d', null),
    AnalyticsPeriod('7d', null),
    AnalyticsPeriod('30d', null),
    AnalyticsPeriod('all', null),
  ];

  String localizedLabel(AppLocalizations l10n) {
    switch (value) {
      case '1d':
        return l10n.notificationAnalyticsPeriod1d;
      case '7d':
        return l10n.notificationAnalyticsPeriod7d;
      case '30d':
        return l10n.notificationAnalyticsPeriod30d;
      case 'all':
        return l10n.notificationAnalyticsPeriodAll;
      default:
        return label ?? value;
    }
  }
}
