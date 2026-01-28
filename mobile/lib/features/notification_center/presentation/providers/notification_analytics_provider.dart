import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/features/notification_center/data/models/notification_analytics_model.dart'
    as model;
import 'package:sparkle/features/notification_center/data/repositories/notification_center_repository.dart';

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
  }) => NotificationAnalyticsState(
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
    state = state.copyWith(isLoading: true, error: null, period: period);

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
  final String label;

  static const List<AnalyticsPeriod> all = [
    AnalyticsPeriod('1d', '1天'),
    AnalyticsPeriod('7d', '7天'),
    AnalyticsPeriod('30d', '30天'),
    AnalyticsPeriod('all', '全部'),
  ];
}
